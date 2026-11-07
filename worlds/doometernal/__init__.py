from collections import Counter
from copy import deepcopy
from random import Random
from typing import ClassVar

from BaseClasses import Item, ItemClassification, Location, Tutorial

from Options import OptionError
from worlds.AutoWorld import WebWorld, World

from . import item_pool, regions, rules
from .campaign import FORTRESS_SPEND_GROUPS, STAGE_BY_ID, make_plan
from .enemy_options import BALANCE_PRESETS, normalize_enemy_options
from .identity import GAME_NAME
from .items import (
    DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES,
    DEVINV_START_INVENTORY_ITEM_NAMES,
    POOL_ITEM_LIMITS,
    SPECIAL_WEAPON_ITEM_NAMES,
    SUPPORT_RUNE_ITEM_NAMES,
    DoomEternalItem,
    item_data_table,
    item_name_to_id,
)
from .locations import kill_reward_name_to_id, location_data_table, location_name_to_id
from .native_enemy_plan import build_native_recipes
from .options import DoomEternalOptions, option_groups
from .planner import PoolConfigurationError
from .player_strings_generated import text as player_text
from .settings import DoomEternalSettings
from .slot_data import REQUIRED_CAPABILITIES, build_slot_data
from .slot_data_contract import ContractError, catalog_tables, load_slot_catalog, validate_slot_data


class DoomEternalWeb(WebWorld):
    theme = "dirt"
    option_groups = option_groups
    tutorials: list[Tutorial] = [  # noqa: RUF012
        Tutorial(
            player_text("apworld.web", "tutorial_title"),
            player_text("apworld.web", "tutorial_description"),
            "English",
            "setup_en.md",
            "setup/en",
            ["snowzzrra"],
        )
    ]


class DoomEternalWorld(World):
    __doc__ = (
        "\n    "
        + player_text("apworld.web", "tagline")
        + "\n    "
        + player_text("apworld.web", "world_description")
        + "\n    "
    )

    game: ClassVar[str] = GAME_NAME
    web = DoomEternalWeb()
    options_dataclass = DoomEternalOptions
    options: DoomEternalOptions
    settings: DoomEternalSettings
    ut_can_gen_without_yaml = True

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
        self.campaign_rng = Random(self.random.getrandbits(128))
        self.enemy_rng = Random(self.random.getrandbits(128))
        self.item_pool_rng = Random(self.random.getrandbits(128))
        self.placement_rng = Random(self.random.getrandbits(128))
        self.access_priority_rng = Random(self.random.getrandbits(128))
        self.preparation_items = []

    @staticmethod
    def interpret_slot_data(slot_data):
        return slot_data

    def effective_starting_inventory(self) -> Counter[str]:
        """Return ownership requested by both starting options."""
        return Counter(self.options.start_inventory.value) + Counter(self.options.start_inventory_from_pool.value)

    def _validate_starting_quantities(self):
        for option in (self.options.start_inventory, self.options.start_inventory_from_pool):
            for name, quantity in option.value.items():
                if type(quantity) is not int or quantity < 0:
                    raise OptionError(player_text("apworld.errors", "inventory_invalid_item_quantity", item=name))

    def _enemy_option_values(self) -> dict[str, object]:
        names = [name for name in self.options_dataclass.type_hints if name.startswith("enemy_")]
        raw = self.options.as_dict(*names, "progressive_difficulty", "use_dlc_content", toggles_as_bools=True)
        for name in ("enemy_preset", "enemy_count_mode"):
            option = getattr(self.options, name)
            raw[name] = option.name_lookup[option.value]
        return {name: "auto" if value == -1 else value for name, value in raw.items()}

    def _normalize_enemy_options(self):
        try:
            return normalize_enemy_options(self.enemy_options_raw)
        except ValueError as error:
            raise OptionError(str(error)) from error

    def _make_campaign_plan(self, candidate=None):
        try:
            return make_plan(self.options, self.campaign_rng, world=self, candidate=candidate)
        except PoolConfigurationError as error:
            raise OptionError(str(error)) from error

    def generate_early(self) -> None:
        tracker_slot = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game)
        if tracker_slot is not None:
            self._restore_tracker_slot(tracker_slot)
            return
        self._validate_starting_quantities()
        start_inventory = self.effective_starting_inventory()
        if start_inventory.get("Blood Punch"):
            raise OptionError(player_text("apworld.errors", "legacy_blood_punch"))
        self.enemy_options_raw = self._enemy_option_values()
        self.enemies = self._normalize_enemy_options()
        self.enemy_plan = None
        self._plan_enemies()
        self._plan_opening_preparation()
        self._plan_kill_rewards()
        self.starting_weapon_name = self.campaign_plan.get("starting_weapon")
        initial_logical_items = set(start_inventory)
        if self.starting_weapon_name:
            initial_logical_items.add(self.starting_weapon_name)
        initial_logical_items.update(self.campaign_plan.get("bootstrap_inventory", ()))
        self.initial_logical_items = frozenset(initial_logical_items)
        self._validate_starting_inventory(start_inventory)

    required_client_version = (0, 6, 7)

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id
    location_name_groups: ClassVar[dict[str, set[str]]] = {"Killsanity": set(kill_reward_name_to_id)}

    def create_item(self, name: str) -> DoomEternalItem:
        item_data = item_data_table[name]
        return DoomEternalItem(name, item_data.classification, item_data.code, self.player)

    def collect_item(self, state, item, remove: bool = False):
        """Initial inventory counts logically even when its pool classification is useful."""
        if item.advancement or item.name in getattr(self, "initial_logical_items", ()):
            return "Blood Punch" if item.name == "Progressive Blood Punch" else item.name
        return None

    def fill_slot_data(self) -> dict[str, object]:
        if hasattr(self, "_tracker_slot"):
            return deepcopy(self._tracker_slot)
        return build_slot_data(self)

    def _plan_enemies(self):
        planning_state = self.campaign_rng.getstate()
        self.campaign_plan = self._make_campaign_plan()
        vanilla_curve = self.enemies.get("revision", 0) >= 7 and self.enemies.get("balance_preset")
        if self.enemies["enabled"] and self.options.mission_order.value == 1 and not vanilla_curve:
            composition = [
                stage for stage in self.campaign_plan["sequence"] if stage != self.campaign_plan["goal_stage"]
            ]
            self.enemy_rng.shuffle(composition)
            if self.campaign_plan["goal_stage"]:
                composition.append(self.campaign_plan["goal_stage"])
            self.campaign_plan["composition_bands"] = {stage: index for index, stage in enumerate(composition)}
        enemy_seed = self.enemy_rng.getrandbits(128)
        self.enemy_plan = build_native_recipes(self.enemies, self.campaign_plan, seed=enemy_seed)
        if self.enemy_plan is not None:
            self.campaign_rng.setstate(planning_state)
            self.campaign_plan = self._make_campaign_plan(self.campaign_plan)
            self.enemy_plan = build_native_recipes(self.enemies, self.campaign_plan, seed=enemy_seed)

    def _plan_opening_preparation(self):
        self.campaign_plan["opening_placed_items"] = []
        if self.campaign_plan.get("opening_stage") and self.campaign_plan[
            "opening_stage"
        ] not in self.campaign_plan.get("unprepared_start_stages", ()):
            from .campaign import solve_stage_bootstrap
            from .native_enemy_safety import OPENING_REGIONS
            from .planner import FastState

            plan = self.campaign_plan
            stage = plan["opening_stage"]
            owned = self.effective_starting_inventory()
            owned.update(plan["bootstrap_inventory"])
            owned[plan["starting_weapon"]] += 1
            owned.update(plan["bootstrap_placed_items"])
            state = FastState(player=self.player)
            state.prog_items.update(owned)
            pool = Counter(plan["semantic_placement_counts"]) - Counter(plan["bootstrap_placed_items"])
            capacity = sum(data.region in OPENING_REGIONS[stage] for data in location_data_table.values())
            preparation = solve_stage_bootstrap(stage, self, state, pool, capacity=capacity)
            if preparation["bootstrap_cost"] != 0:
                plan.setdefault("unprepared_start_stages", []).append(stage)
            plan["opening_placed_items"] = list(preparation["placed_items"])

    def _plan_kill_rewards(self):
        from .killsanity_logic import build_kill_rewards
        from .killsanity_plan import build_campaign_kill_budget

        kill_budget = {"estimated_kills": 0, "finite_sources": []}
        if self.options.killsanity.value:
            kill_budget = build_campaign_kill_budget(self.campaign_plan, self.enemy_plan)
            self.campaign_plan["finite_kill_sources"] = kill_budget["finite_sources"]
            self.campaign_plan["estimated_kills"] = kill_budget["estimated_kills"]
        self.killsanity_plan = build_kill_rewards(
            {
                "enabled": bool(self.options.killsanity.value),
                "interval": self.options.kills_per_check.value,
                "maximum_milestones": (
                    "auto"
                    if self.options.killsanity_maximum_milestones.value == -1
                    else self.options.killsanity_maximum_milestones.value
                ),
            },
            kill_budget["finite_sources"],
            estimated_kills=kill_budget["estimated_kills"],
        )

    def _validate_starting_inventory(self, start_inventory):
        dlc_enabled = bool(self.options.use_dlc_content.value)
        effective_special_weapon = (
            "The Crucible" if not dlc_enabled else self.options.special_weapon.current_option_name
        )
        combined_inventory = start_inventory + Counter(self.campaign_plan["bootstrap_inventory"])
        combined_inventory[self.starting_weapon_name] += 1
        unsafe, invalid_quantity, unavailable = self._inventory_issues(
            combined_inventory, dlc_enabled, effective_special_weapon
        )
        if unsafe:
            raise OptionError(player_text("apworld.errors", "inventory_unsafe", items=", ".join(sorted(unsafe))))
        if unavailable:
            raise OptionError(
                player_text("apworld.errors", "inventory_unavailable", items=", ".join(sorted(unavailable)))
            )
        if invalid_quantity:
            raise OptionError(
                player_text("apworld.errors", "inventory_invalid_quantity", items=", ".join(sorted(invalid_quantity)))
            )
        if start_inventory.get("Chainsaw", 0) and not self.options.randomize_chainsaw.value:
            raise OptionError(player_text("apworld.errors", "inventory_chainsaw_disabled"))
        if start_inventory.get("Dash", 0) and not self.options.randomize_dash.value:
            raise OptionError(player_text("apworld.errors", "inventory_dash_disabled"))

    def _inventory_issues(self, combined_inventory, dlc_enabled, effective_special_weapon):
        unsafe, invalid_quantity, unavailable = [], [], []
        for name, quantity in combined_inventory.items():
            data = item_data_table.get(name)
            if data is None:
                unsafe.append(name)
                continue
            if name in SUPPORT_RUNE_ITEM_NAMES and not dlc_enabled:
                unavailable.append(player_text("apworld.errors", "inventory_requires_dlc", item=name))
                continue
            if self._inventory_persistence_issue(name, data, unsafe, unavailable):
                continue
            if name in SPECIAL_WEAPON_ITEM_NAMES and name != effective_special_weapon:
                unavailable.append(player_text("apworld.errors", "inventory_special_weapon", item=name))
                continue
            maximum = POOL_ITEM_LIMITS.get(name, 1)
            if name == "Sentinel Battery":
                maximum = self.campaign_plan["battery_economy"]["total"]
            if quantity > maximum:
                invalid_quantity.append(player_text("apworld.errors", "inventory_maximum", item=name, maximum=maximum))
        return unsafe, invalid_quantity, unavailable

    def _inventory_persistence_issue(self, name, data, unsafe, unavailable):
        if name not in DEVINV_START_INVENTORY_ITEM_NAMES:
            if data.classification & ItemClassification.trap:
                unsafe.append(player_text("apworld.errors", "inventory_trap", item=name))
            elif data.classification & ItemClassification.filler:
                unsafe.append(player_text("apworld.errors", "inventory_filler", item=name))
            elif name in DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES:
                unsafe.append(player_text("apworld.errors", "inventory_consumable", item=name))
            elif name == "Victory":
                unsafe.append(player_text("apworld.errors", "inventory_goal_item", item=name))
            else:
                unavailable.append(player_text("apworld.errors", "inventory_not_persistent", item=name))
            return True
        return False

    def get_filler_item_name(self) -> str:
        return item_pool.get_filler_item_name(self)

    def create_items(self) -> None:
        return item_pool.create_items(self)

    def get_pre_fill_items(self):
        return item_pool.get_pre_fill_items(self)

    def pre_fill(self) -> None:
        return item_pool.pre_fill(self)

    def fill_hook(
        self,
        progitempool: list[Item],
        usefulitempool: list[Item],
        filleritempool: list[Item],
        fill_locations: list[Location],
    ) -> None:
        return item_pool.fill_hook(self, progitempool, usefulitempool, filleritempool, fill_locations)

    def create_regions(self) -> None:
        return regions.create_regions(self)

    def set_rules(self) -> None:
        return rules.set_rules(self)

    def generate_basic(self) -> None:
        return rules.generate_basic(self)

    def _spoiler_preparation(self):
        plan = self.campaign_plan
        names = Counter(plan["bootstrap_placed_items"]) + Counter(plan["opening_placed_items"])
        entries = [
            player_text("apworld.spoiler", "starting_inventory", item=name) for name in plan["bootstrap_inventory"]
        ]
        locations = dict.fromkeys(getattr(self, "preparation_placements", []) + self.multiworld.get_filled_locations())
        for location in locations:
            item = location.item
            if location.address is not None and item.player == self.player and names[item.name]:
                entries.append(player_text("apworld.spoiler", "item_location", item=item.name, location=location))
                names[item.name] -= 1
        entries.extend(
            player_text("apworld.spoiler", "early_delivery", item=name, count=count)
            for name, count in names.items()
            if count
        )
        return "; ".join(entries) or player_text("apworld.spoiler", "none")

    def write_spoiler(self, spoiler_handle) -> None:
        plan = self.campaign_plan
        sequence = " -> ".join(STAGE_BY_ID[stage]["name"] for stage in plan["sequence"])
        access = "; ".join(
            f"{STAGE_BY_ID[stage]['name']}: {STAGE_BY_ID[stage]['name']} Access"
            for stage in plan["access_items"].values()
        )
        spoiler_handle.write("\n" + player_text("apworld.spoiler", "title", player=self.player_name) + "\n")
        spoiler_handle.write(
            player_text("apworld.spoiler", "mission_order", order=self.options.mission_order.current_option_name) + "\n"
        )
        spoiler_handle.write(player_text("apworld.spoiler", "sequence", sequence=sequence) + "\n")
        spoiler_handle.write(
            player_text(
                "apworld.spoiler", "access_items", items=access or player_text("apworld.spoiler", "sequence_unlocks")
            )
            + "\n"
        )
        spoiler_handle.write(player_text("apworld.spoiler", "goal", goal=self.options.goal.current_option_name) + "\n")
        spoiler_handle.write(
            player_text("apworld.spoiler", "preparation", preparation=self._spoiler_preparation()) + "\n"
        )
        enemy = (
            self.options.enemy_preset.current_option_name
            if self.enemies["enabled"]
            else player_text("apworld.spoiler", "off")
        )
        spoiler_handle.write(player_text("apworld.spoiler", "enemy_preset", preset=enemy) + "\n")
        self._spoiler_planning(spoiler_handle)

    def _spoiler_planning(self, spoiler_handle):
        plan = self.campaign_plan
        spoiler_handle.write(
            player_text(
                "apworld.spoiler",
                "mission_selection",
                requested=plan["requested_mission_count"],
                included=plan["effective_mission_count"],
                forced_goal=str(plan["goal_forced_active"]),
            )
            + "\n"
        )
        spoiler_handle.write(
            player_text(
                "apworld.spoiler",
                "preparation_cr",
                initial=str(plan["bootstrap_initial_cr"]),
                final=str(plan["bootstrap_final_cr"]),
                effective=str(plan["bootstrap_effective_cr"]),
                overshoot=str(plan["bootstrap_overshoot"]),
            )
            + "\n"
        )
        spoiler_handle.write(
            player_text(
                "apworld.spoiler",
                "readiness",
                initial=str(plan["readiness_initial_deficit"]),
                final=str(plan["readiness_final_deficit"]),
                budget=str(plan["resource_permanent_budget"]),
            )
            + "\n"
        )
        for label, key in (
            (player_text("apworld.spoiler", "pool_counts"), "semantic_counts"),
            (player_text("apworld.spoiler", "optional_resources"), "readiness_selection"),
            (player_text("apworld.spoiler", "automatic_adjustments"), "resource_auto_adjustments"),
            (player_text("apworld.spoiler", "composition_bands"), "composition_bands"),
            (player_text("apworld.spoiler", "progression_bands"), "enemy_progression_bands"),
        ):
            entries = "; ".join(f"{name}: {count}" for name, count in sorted(plan.get(key, {}).items()))
            spoiler_handle.write(
                player_text(
                    "apworld.spoiler",
                    "planning_entries",
                    label=label,
                    entries=entries or player_text("apworld.spoiler", "none"),
                )
                + "\n"
            )
        self._spoiler_enemy_planning(spoiler_handle)

    def _spoiler_enemy_planning(self, spoiler_handle):
        plan = self.enemy_plan or {}
        if not plan:
            return
        spoiler_handle.write(player_text("apworld.spoiler", "enemy_seed", seed=plan["seed"]) + "\n")
        for stage, costs in sorted(plan.get("combat_costs", {}).items()):
            waves = costs.get("campaign", {}).get("waves", [])
            peak = max((wave.get("peak_cost", wave["cost"]) for wave in waves), default=0)
            spoiler_handle.write(
                player_text(
                    "apworld.spoiler",
                    "combat",
                    stage=stage,
                    original=format(costs["original"], ".1f"),
                    actual=format(costs["actual"], ".1f"),
                    waves=len(waves),
                    peak=format(peak, ".1f"),
                )
                + "\n"
            )
        for adjustment in plan.get("compiler_adjustments", []):
            details = "; ".join(f"{name}: {value}" for name, value in sorted(adjustment.items()))
            spoiler_handle.write(player_text("apworld.spoiler", "safety_adjustment", details=details) + "\n")

    def _restore_tracker_options(self, slot_data):
        options = slot_data.get("tracker_options")
        names = tuple(DoomEternalOptions.__annotations__)
        if not isinstance(options, dict) or set(options) != set(names):
            raise OptionError(player_text("apworld.errors", "tracker_options_missing"))
        try:
            restored = {
                name: self.options_dataclass.type_hints[name].from_any(deepcopy(options[name])) for name in names
            }
        except Exception as error:
            # Archipelago Range raises plain Exception for out-of-range values.
            if type(error) not in (Exception, OptionError, ValueError, TypeError, KeyError, AssertionError):
                raise
            raise OptionError(str(error)) from error
        for name, option in restored.items():
            setattr(self.options, name, option)

    def _restore_tracker_slot(self, slot_data):
        from .killsanity_logic import restore_kill_rewards

        try:
            catalog = load_slot_catalog()
            data = validate_slot_data(slot_data, catalog, supported_capabilities=frozenset(REQUIRED_CAPABILITIES))
        except ContractError as error:
            raise OptionError(str(error)) from error
        self._restore_tracker_options(slot_data)
        self.stage_profiles = data.stage_profiles
        self.campaign_plan = self._tracker_campaign(slot_data["campaign"])
        self.killsanity_plan = restore_kill_rewards(data.killsanity, catalog)
        self.enemy_plan = self._tracker_enemy_plan(data, catalog)
        preset = self.options.enemy_preset.current_key
        self.enemies = {"enabled": data.recipes.enabled, "balance_preset": preset in BALANCE_PRESETS}
        self._tracker_starting = Counter({self.item_id_to_name[code]: count for code, count in data.starting.items})
        self.starting_weapon_name = self.item_id_to_name[data.starting.weapon_item_id]
        self.initial_logical_items = frozenset(self._tracker_starting)
        self._tracker_slot = deepcopy(slot_data)

    def _tracker_campaign(self, campaign):
        plan = deepcopy(campaign)
        stages = [key for key in STAGE_BY_ID if key in self.stage_profiles]
        access = {stage["access_id"]: key for key, stage in STAGE_BY_ID.items()}
        fortress = campaign["fortress"]
        plan.update(
            stage_ids=stages,
            stages=[dict(STAGE_BY_ID[key]) for key in stages],
            active_normal_mission_ids=[key for key in stages if key != "e5m4_boss"],
            goal_stage=campaign["goal"]["stage_id"],
            access_items={str(code): access[code] for code in campaign["access_items"]},
            active_spend_groups=[
                group for group in FORTRESS_SPEND_GROUPS if group["id"] in fortress["active_spend_group_ids"]
            ],
            battery_surplus=fortress["battery_economy"]["surplus"],
            battery_economy=deepcopy(fortress["battery_economy"]),
            fortress_phase_thresholds=list(fortress["phase_thresholds"]),
        )
        return plan

    def _tracker_enemy_plan(self, data, catalog):
        from .recipe_codec import decode_recipes

        if not data.recipes.enabled:
            return None
        tables = catalog_tables(catalog)
        recipes = decode_recipes(data.recipes)
        return {
            "revision": data.identity.algorithm_revision,
            "maps": {
                key: {"recipes": [self._tracker_recipe(row, tables) for row in stage.rows if row.role_ref == "primary"]}
                for key, stage in recipes.maps.items()
            },
        }

    @staticmethod
    def _tracker_recipe(row, tables):
        source = tables["sources"][row.source_ref]
        stage = tables["maps"][source["stage_id"]]
        origin = next(
            origin
            for origin in stage["origins"] + stage.get("runtime_origins", [])
            if origin["id"] == source["source_id"]
        )
        return {
            "binding": origin["binding"],
            "bodies": [{"species": tables["templates"][body.template_ref]["species"]} for body in row.bodies],
        }

    def _restore_tracker_starting(self):
        existing = self.multiworld.precollected_items[self.player]
        for item in existing:
            self.multiworld.state.remove(item)
        existing.clear()
        for name, count in self._tracker_starting.items():
            for _ in range(count):
                self.multiworld.push_precollected(self.create_item(name))
