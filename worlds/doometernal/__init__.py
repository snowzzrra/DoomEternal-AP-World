from collections import Counter
import hashlib
import json
import logging
from functools import partial
from typing import ClassVar

from BaseClasses import CollectionState, Entrance, Item, ItemClassification, Location, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import add_rule, forbid_item, set_rule

from .combat_readiness import (
    get_mission_base_cr,
    get_skill_allowance,
    SPIRIT_BREAKPOINTS,
    is_mission_ready,
    is_spirit_breakpoint_ready,
)
from .combat_rating import MOD_HOST, WEAPON_NAMES, evaluate_player_loadout_cr

from .generated_content import (
    CAMPAIGN_CONNECTIONS,
    CAMPAIGN_REGIONS,
    MISSION_DIFFICULTY,
)
from .identity import GAME_NAME
from .enemy_options import normalize_enemy_options
from .enemy_plan import validate_frozen_enemy_plan
from .native_enemy_plan import build_native_recipes
from .campaign import (
    BASE_GATE_STAGE_IDS,
    FORTRESS_NON_CONSUMER_LOCATIONS,
    FORTRESS_SPEND_GROUPS,
    ORDERED_MASTERY_CHALLENGES,
    REGION_STAGE,
    STAGE_BY_ID,
    STAGE_SLAYER_GATE_KEYS,
    completion_event,
    get_short_world_scaling,
    make_plan,
    stage_available,
)
from .items import (
    BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES,
    BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES,
    DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES,
    DEVINV_START_INVENTORY_ITEM_NAMES,
    DoomEternalItem,
    SPECIAL_WEAPON_ITEM_NAMES,
    SPECIAL_WEAPON_POOL_COUNTS,
    SUPPORT_RUNE_ITEM_NAMES,
    WEAPON_UPGRADE_POINTS_NAME,
    WEAPON_UPGRADE_POINTS_ITEM_COUNT,
    item_data_table,
    item_name_to_id,
    starting_weapon_item_names,
    world_pool_weapon_item_names,
    suit_perk_item_names,
)
from .locations import DoomEternalLocation, location_data_table, location_name_to_id, optional_location_enabled
from .logic import (
    FORTRESS_BATTERY_CONSUMER_LOCATIONS,
    build_location_prerequisites,
    CRUCIBLE_CHALLENGE, crucible_challenge_enabled,
    connection_requirement,
    goal_endpoint_event_name,
    mission_clear_event_name,
    active_catalog_location_names,
    LocationRequirement,
    is_dlc_mission_local_name,
    effective_victory_requirements,
    goal_endpoint_available,
    GOAL_ENDPOINT_LOCATIONS,
    MASTERY_SUFFIX,
    validate_full_saga_catalog,
    validate_goal_endpoint,
    victory_requirement_location_event_name,
    required_item_names,
    requirement_satisfied,
    validate_location_prerequisites,
)
from .options import DeathLinkMode, DoomEternalOptions, SpecialWeapon
from .settings import DoomEternalSettings
from .generated_content import MASTERY_REQUIREMENT_COUNTS
from .version import (
    APWORLD_REVISION,
    BRIDGE_PROTOCOL,
    COMPILER_REVISION,
    CONTENT_REVISION,
    MANIFEST_SCHEMA_VERSION,
    ROOM_CONTRACT_REVISION,
    SLOT_DATA_REVISION,
    SLOT_DATA_SCHEMA_VERSION,
)


class DoomEternalWeb(WebWorld):
    theme = "dirt"
    tutorials: list[Tutorial] = [  # noqa: RUF012
        Tutorial(
            "DOOM Eternal Setup Guide",
            "A guide to installing and connecting DOOM Eternal for Archipelago.",
            "English",
            "setup_en.md",
            "setup/en",
            ["snowzzrra"],
        )
    ]


class DoomEternalWorld(World):
    """
    Rip and tear, until it is done.
    Doom Eternal Randomizer for Archipelago.
    """

    game: ClassVar[str] = GAME_NAME
    web = DoomEternalWeb()
    options_dataclass = DoomEternalOptions
    options: DoomEternalOptions
    settings: DoomEternalSettings


    def effective_starting_inventory(self) -> Counter[str]:
        """Return every item materialized before normal AP receipt delivery."""
        return Counter(self.options.start_inventory.value)

    def _enemy_option_values(self) -> dict[str, object]:
        names = [name for name in self.options_dataclass.type_hints if name.startswith("enemy_")]
        raw = self.options.as_dict(*names, "progressive_difficulty", "use_dlc_content", toggles_as_bools=True)
        for name in ("enemy_preset", "enemy_count_mode"):
            option = getattr(self.options, name)
            raw[name] = option.name_lookup[option.value]
        return {name: "auto" if value == -1 else value for name, value in raw.items()}

    def generate_early(self) -> None:
        if self.options.start_inventory.value.get("Blood Punch"):
            raise ValueError("Blood Punch belongs to legacy rooms; new seeds require Progressive Blood Punch (0..4)")
        self.enemy_options_raw = self._enemy_option_values()
        self.enemies = normalize_enemy_options(self.enemy_options_raw)
        self.enemy_plan = None
        planning_state = self.random.getstate()
        self.campaign_plan = make_plan(self.options, self.random, world=self)
        vanilla_curve = self.enemies.get('revision', 0) >= 7 and self.enemies.get('balance_preset')
        if self.enemies['enabled'] and self.options.mission_order.value == 1 and not vanilla_curve:
            composition = [stage for stage in self.campaign_plan['sequence'] if stage != self.campaign_plan['goal_stage']]
            self.random.shuffle(composition)
            if self.campaign_plan['goal_stage']: composition.append(self.campaign_plan['goal_stage'])
            self.campaign_plan['composition_bands'] = {stage: index for index, stage in enumerate(composition)}
        enemy_seed = self.random.getrandbits(128)
        self.enemy_plan = build_native_recipes(self.enemies, self.campaign_plan, seed=enemy_seed)
        if self.enemy_plan is not None:
            from .campaign import ReadinessBootstrapError
            from .native_enemy_safety import OPENING_REGIONS
            candidate = self.campaign_plan
            starts = [candidate['bootstrap_stage']]
            if candidate.get('opening_stage') and self.options.mission_order.value in (1, 2):
                starts.extend(stage for stage in candidate['sequence'] if stage in OPENING_REGIONS
                              and stage != starts[0])
            for start in starts:
                trial = candidate
                if start != candidate['bootstrap_stage']:
                    trial = {**candidate, 'opening_stage': start, 'bootstrap_stage': start,
                             'sequence': [start] + [stage for stage in candidate['sequence'] if stage != start],
                             'starting_stages': ([start] + [stage for stage in candidate['starting_stages']
                                                           if stage != start])[:len(candidate['starting_stages'])]}
                    if self.options.mission_order.value == 2:
                        trial['enemy_progression_bands'] = {stage: 0 if stage in trial['starting_stages'] else band
                            for stage, band in candidate['enemy_progression_bands'].items()}
                    self.enemy_plan = build_native_recipes(self.enemies, trial, seed=enemy_seed)
                self.random.setstate(planning_state)
                try:
                    self.campaign_plan = make_plan(self.options, self.random, world=self, candidate=trial)
                except ReadinessBootstrapError:
                    if start == starts[-1]:
                        raise
                else:
                    break
            self.enemy_plan = build_native_recipes(self.enemies, self.campaign_plan, seed=enemy_seed)
        if self.campaign_plan.get('opening_stage'):
            from .campaign import solve_stage_bootstrap
            from .native_enemy_safety import OPENING_REGIONS
            from .planner import FastState
            plan = self.campaign_plan
            stage = plan['opening_stage']
            owned = Counter(self.options.start_inventory.value)
            owned.update(plan['bootstrap_inventory'])
            owned[plan['starting_weapon']] += 1
            owned.update(plan['bootstrap_placed_items'])
            state = FastState(player=self.player)
            state.prog_items.update(owned)
            pool = Counter(plan['semantic_placement_counts']) - Counter(plan['bootstrap_placed_items'])
            capacity = sum(data.region in OPENING_REGIONS[stage] for data in location_data_table.values())
            preparation = solve_stage_bootstrap(stage, self, state, pool, capacity=capacity)
            if preparation['bootstrap_cost'] != 0:
                raise ValueError(f'The first mission {stage} cannot provide its required arsenal through {capacity} opening checks: {preparation}; owned={dict(owned)}')
            plan['opening_placed_items'] = list(preparation['placed_items'])
        from .killsanity_plan import build_campaign_kill_budget, build_killsanity_plan
        kill_budget = dict(estimated_kills=0, finite_sources=[])
        if self.options.killsanity.value:
            kill_budget = build_campaign_kill_budget(
                self.campaign_plan, self.enemy_plan)
            self.campaign_plan['finite_kill_sources'] = kill_budget['finite_sources']
            self.campaign_plan['estimated_kills'] = kill_budget['estimated_kills']
        self.killsanity_plan = build_killsanity_plan({
            "enabled": bool(self.options.killsanity.value),
            "interval": self.options.kills_per_check.value,
            "maximum_milestones": ("auto" if self.options.killsanity_maximum_milestones.value == -1
                                   else self.options.killsanity_maximum_milestones.value),
        }, kill_budget['finite_sources'], estimated_kills=kill_budget['estimated_kills'])
        self.starting_weapon_name = self.campaign_plan.get("starting_weapon")
        initial_logical_items = set(self.options.start_inventory.value)
        if self.starting_weapon_name:
            initial_logical_items.add(self.starting_weapon_name)
        initial_logical_items.update(self.campaign_plan.get("bootstrap_inventory", ()))
        self.initial_logical_items = frozenset(initial_logical_items)
        dlc_enabled = bool(self.options.use_dlc_content.value)
        effective_special_weapon = (
            "The Crucible" if not dlc_enabled else self.options.special_weapon.current_option_name
        )
        special_maximum = SPECIAL_WEAPON_POOL_COUNTS[effective_special_weapon]
        unsafe = []
        invalid_quantity = []
        unavailable = []
        for name, quantity in self.options.start_inventory.value.items():
            data = item_data_table.get(name)
            if data is None:
                unsafe.append(name)
                continue
            if name in SUPPORT_RUNE_ITEM_NAMES and not dlc_enabled:
                unavailable.append(f"{name} (requires Use DLC Content ON)")
                continue
            if name not in DEVINV_START_INVENTORY_ITEM_NAMES:
                if data.classification & ItemClassification.trap:
                    unsafe.append(f"{name} (trap)")
                elif data.classification & ItemClassification.filler:
                    unsafe.append(f"{name} (filler/consumable)")
                elif name in DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES:
                    unsafe.append(f"{name} (consumable)")
                elif name == "Victory":
                    unsafe.append(f"{name} (goal item)")
                else:
                    unavailable.append(f"{name} (not in current persistent pool)")
                continue
            if name in SPECIAL_WEAPON_ITEM_NAMES and name != effective_special_weapon:
                unavailable.append(f"{name} (incompatible Special Weapon mode)")
                continue
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                invalid_quantity.append(name)
            elif name == effective_special_weapon and quantity > special_maximum:
                invalid_quantity.append(f"{name} (maximum {special_maximum})")
            elif name.startswith("Progressive ") and quantity > 4:
                invalid_quantity.append(f"{name} (maximum 4 ordered tiers)")
            elif name in suit_perk_item_names and quantity > 1:
                invalid_quantity.append(f"{name} (maximum 1 pool copy)")
            elif name in SUPPORT_RUNE_ITEM_NAMES and quantity > 1:
                invalid_quantity.append(f"{name} (maximum 1 pool copy)")
        if unsafe:
            raise ValueError(
                "DOOM Eternal start_inventory cannot contain traps, filler/consumables, or Victory: "
                + ", ".join(sorted(unsafe))
            )
        if unavailable:
            raise ValueError(
                "DOOM Eternal start_inventory item is not legal in current persistent pool: "
                + ", ".join(sorted(unavailable))
            )
        if invalid_quantity:
            raise ValueError(
                "DOOM Eternal start_inventory has invalid quantity: "
                + ", ".join(sorted(invalid_quantity))
            )
        if self.options.start_inventory.value.get("Chainsaw", 0) and not self.options.randomize_chainsaw.value:
            raise ValueError("DOOM Eternal start_inventory Chainsaw unavailable when randomize_chainsaw is disabled")
        if self.options.start_inventory.value.get("Dash", 0) and not self.options.randomize_dash.value:
            raise ValueError("DOOM Eternal start_inventory Dash unavailable when randomize_dash is disabled")
        selected_weapon = self.options.starting_weapon.selected_weapon_name
        if selected_weapon and self.options.start_inventory.value.get(selected_weapon, 0):
            raise ValueError(
                f"Starting Weapon '{selected_weapon}' is redundant with start_inventory"
            )

    required_client_version = (0, 6, 7)

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    @classmethod
    def stage_modify_multidata(cls, multiworld, multidata):
        from worlds.AutoWorld import data_package_checksum
        from .killsanity_plan import milestone_names

        names = {}
        for player in multiworld.get_game_players(cls.game):
            names.update(milestone_names(multiworld.worlds[player].killsanity_plan))
        if names:
            package = dict(multidata["datapackage"][cls.game])
            package["location_name_to_id"] = {**package["location_name_to_id"], **names}
            package["location_name_groups"] = {**package["location_name_groups"],
                                               "Everywhere": sorted(package["location_name_to_id"])}
            package.pop("checksum")
            package["checksum"] = data_package_checksum(package)
            multidata["datapackage"] = {**multidata["datapackage"], cls.game: package}

    def _campaign_entrance_access(self, event_name, requirement, state) -> bool:
        if event_name and not state.has(event_name, self.player):
            return False
        return requirement_satisfied(requirement, state, self.player)

    def create_item(self, name: str) -> DoomEternalItem:
        item_data = item_data_table[name]
        return DoomEternalItem(name, item_data.classification, item_data.code, self.player)

    def collect_item(self, state, item, remove: bool = False):
        """Logical ownership policy for physically granted initial inventory.

        Items the player owns before normal receipt delivery (explicit
        ``start_inventory``, the chosen Starting Weapon, Dash and Chainsaw)
        are logically active even when
        their pool classification is useful. Hypothetical or placed useful
        copies keep the default AP collect semantics and are never promoted
        globally by this override.
        """
        if item.advancement or item.name in getattr(self, "initial_logical_items", ()):
            return "Blood Punch" if item.name == "Progressive Blood Punch" else item.name
        return None

    def _mission_presentation(self) -> dict[str, dict[str, int | float]]:
        from .combat_readiness import get_mission_skull_tier, get_mission_cr_range, get_mission_effort_per_check
        return {stage_id: {
            "base_cr": get_mission_base_cr(stage_id, self),
            "skill_allowance": get_skill_allowance(self.options.logic_difficulty.value, self.options.campaign_difficulty.value),
            "skull_tier": get_mission_skull_tier(stage_id, self),
            **({'cr_min': get_mission_cr_range(stage_id, self)[0],
                'cr_max': get_mission_cr_range(stage_id, self)[1],
                'effort_per_check': get_mission_effort_per_check(stage_id, self)}
               if (self.enemy_plan or {}).get('revision', 0) >= 5 else {}),
        } for stage_id in self.campaign_plan["sequence"]}

    def fill_slot_data(self) -> dict[str, object]:
        start_inventory = dict(self.effective_starting_inventory())
        start_inventory.update(self.campaign_plan["bootstrap_inventory"])
        dlc_enabled = bool(self.options.use_dlc_content.value)
        active_location_names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        effective_requirements = effective_victory_requirements(
            set(self.options.additional_victory_requirements.value),
            active_location_names,
            use_dlc_content=dlc_enabled,
            include_dlc_missions=True,
            goal=self.options.goal.current_option_name,
        )
        capabilities = [
            "room_mod_v2", "slot_data_v6", "goal_events_v1", "goal_endpoint_events_v1",
            "dlc_missions_v1", "physical_options_v1",
        ]
        if start_inventory:
            capabilities.append("starting_inventory_v1")
        capabilities.extend([
            "starting_weapon_v1", "special_weapon_progression_v1", "ammo_refill_v1",
            "cross_campaign_materialization_v1", "unified_campaign_v1", "deathlink_mode_v1",
            "fortress_economy_v1", "progressive_blood_punch_v1",
        ])

        active_sg = getattr(self, "active_spend_groups", FORTRESS_SPEND_GROUPS)

        data = {
            "campaign_plan": self.campaign_plan,
            "death_link": bool(self.options.death_link.value),
            "death_link_mode": (
                "hardcore" if self.options.death_link_mode.value == DeathLinkMode.option_hardcore else "soft"
            ),
            "praetor_suit_upgrades_in_pool": self.praetor_suit_upgrades_in_pool,
            "randomize_chainsaw": bool(self.options.randomize_chainsaw.value),
            "randomize_dash": bool(self.options.randomize_dash.value),
            "randomize_first_battery": True,
            "include_slayer_gates": bool(self.options.include_slayer_gates.value),
            "include_secret_encounters": bool(self.options.include_secret_encounters.value),
            "easier_secret_encounters": bool(self.options.easier_secret_encounters.value),
            "include_weapon_mastery_challenges": bool(self.options.include_weapon_mastery_challenges.value),
            "reveal_ap_locations_on_automap": bool(self.options.reveal_ap_locations_on_automap.value),
            "trap_percentage": int(self.options.trap_percentage.value),
            "enabled_traps": sorted(self.options.enabled_traps.value),
            "use_dlc_content": dlc_enabled,
            "include_dlc_missions": bool(dlc_enabled and any(
                STAGE_BY_ID[stage_id]["source"] in ("tag1", "tag2")
                for stage_id in self.campaign_plan["stage_ids"]
            )),
            "mission_pool": self.options.mission_pool.current_option_name.lower().replace(" ", "_"),
            "dark_lord_enabled": self.campaign_plan["dark_lord_active"],
            "requested_mission_count": self.campaign_plan["requested_mission_count"],
            "effective_mission_count": self.campaign_plan["effective_mission_count"],
            "active_normal_mission_ids": self.campaign_plan["active_normal_mission_ids"],
            "goal_stage_id": self.campaign_plan["goal_stage"],
            "goal_forced_active": self.campaign_plan.get("goal_forced_active", False),
            "mission_order": self.options.mission_order.current_option_name.lower().replace(" ", "_"),
            "rmo_sequence": self.campaign_plan["sequence"] if self.options.mission_order.value == 1 else [],
            "mai_starting_stage_ids": self.campaign_plan["starting_stages"] if self.options.mission_order.value == 2 else [],
            "active_fortress_spend_group_ids": [sg["id"] for sg in active_sg],
            "active_location_count": len([loc for loc in self.multiworld.get_locations(self.player) if loc.address is not None]),
            "cr_dataset_version": "0.1",
            "logic_difficulty": self.options.logic_difficulty.current_option_name,
            "mastery_requirements": self.options.mastery_requirements.current_option_name,
            "mastery_requirement_counts": MASTERY_REQUIREMENT_COUNTS[self.options.mastery_requirements.current_option_name],
            "resource_profile": self.options.resource_profile.current_option_name,
            "item_pool_counts": dict(self.options.item_pool_counts.value),
            "filler_weights": dict(self.options.filler_weights.value),
            "trap_weights": dict(self.options.trap_weights.value),
            "goal": self.options.goal.current_option_name,
            "goal_endpoint_event": goal_endpoint_event_name(self.options.goal.current_option_name),
            "goal_endpoint_available": goal_endpoint_available(
                self.options.goal.current_option_name, active_location_names
            ),
            "additional_victory_requirements": sorted(effective_requirements),
            "mission_difficulty": {
                mission: dict(metadata) for mission, metadata in MISSION_DIFFICULTY.items()
            },
            "mission_presentation_v2": self._mission_presentation(),
            "special_weapon": "The Crucible" if not dlc_enabled else self.options.special_weapon.current_option_name,
            "enhanced_melee_damage": bool(self.options.enhanced_melee_damage.value),
            "apworld_revision": APWORLD_REVISION,
            "content_revision": CONTENT_REVISION,
            "bridge_protocol": BRIDGE_PROTOCOL,
            "compiler_revision": COMPILER_REVISION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "slot_data_schema_version": SLOT_DATA_SCHEMA_VERSION,
            "slot_data_revision": SLOT_DATA_REVISION,
            "mod_contract_revision": ROOM_CONTRACT_REVISION,
            "required_capabilities": capabilities,
            "starting_inventory": start_inventory,
            "starting_weapon": self.starting_weapon_name,
            "enemies": self.enemies,
            "enemy_plan": self.enemy_plan,
            "killsanity_options": {
                "enabled": bool(self.options.killsanity.value),
                "interval": self.options.kills_per_check.value,
                "maximum_milestones": ("auto" if self.options.killsanity_maximum_milestones.value == -1
                                       else self.options.killsanity_maximum_milestones.value),
            },
            "killsanity": self.killsanity_plan,
        }
        data.update(self.enemy_options_raw)
        validate_frozen_enemy_plan(data.get("enemy_plan"), data["enemies"])
        identity = {"slot_data": {key: value for key, value in data.items()
                                 if not key.startswith("enemy_") and key != "progressive_difficulty"}, "placements": sorted(
            (location.address, location.item.code, location.item.player)
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None and location.item is not None)}
        data["native_generation_fingerprint"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return data

    def create_regions(self) -> None:
        dlc_enabled = bool(self.options.use_dlc_content.value)
        special_weapon = self.options.special_weapon.current_option_name if dlc_enabled else "The Crucible"
        catalog_locations = {
            name: data for name, data in location_data_table.items()
            if (name != CRUCIBLE_CHALLENGE or crucible_challenge_enabled(special_weapon))
            and optional_location_enabled(name, self.options)
        }
        plan = self.campaign_plan
        active_normal_ids = plan["active_normal_mission_ids"]
        active_stage_ids = set(plan["stage_ids"])

        vanilla_physical_locations = {
            "Hell on Earth - Chainsaw": self.options.randomize_chainsaw.value,
            "Exultia - Dash": self.options.randomize_dash.value,
        }
        # Regions and the item pool consume the same pre-economy scaling decision.
        active_sg = plan["active_spend_groups"]
        active_masteries_count = plan["active_masteries_count"]
        battery_surplus = plan["battery_surplus"]
        self.active_spend_groups = active_sg
        self.active_masteries_count = active_masteries_count
        self.battery_surplus = battery_surplus

        # Active Fortress locations
        has_unmaykr_check = bool(self.options.include_slayer_gates.value) and set(BASE_GATE_STAGE_IDS).issubset(set(active_normal_ids))
        active_fortress_consumer_locs = {loc for sg in active_sg for loc in sg["locations"]}
        active_hub_locations = (
            FORTRESS_NON_CONSUMER_LOCATIONS
            | active_fortress_consumer_locs
            | ({"Fortress of Doom - Unmaykr Acquired"} if has_unmaykr_check else set())
        )

        # Active Mastery Challenge locations
        active_mastery_locations = {
            loc for _, loc in ORDERED_MASTERY_CHALLENGES[:active_masteries_count]
        }

        # 3. Create active regions
        player, multiworld = self.player, self.multiworld
        menu = Region("Menu", player, multiworld)
        multiworld.regions.append(menu)
        hub = Region("Fortress of Doom", player, multiworld)
        multiworld.regions.append(hub)
        menu.connect(hub, "Campaign: Fortress")

        for visit in ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"):
            multiworld.regions.append(Region(f"Fortress of Doom - {visit} Visit", player, multiworld))

        if active_masteries_count > 0:
            wm_region = Region("Weapon Masteries", player, multiworld)
            multiworld.regions.append(wm_region)
            menu.connect(wm_region, "Menu to Weapon Masteries")

        for stage_id in active_stage_ids:
            stage = STAGE_BY_ID[stage_id]
            for reg_name in stage["regions"]:
                multiworld.regions.append(Region(reg_name, player, multiworld))

        # 4. Instantiate active locations into regions
        for loc_name, loc_data in catalog_locations.items():
            reg_name = loc_data.region
            if "Fortress of Doom" in reg_name:
                if loc_name not in active_hub_locations:
                    continue
            elif reg_name == "Weapon Masteries":
                if loc_name not in active_mastery_locations:
                    continue
            else:
                stage_id = REGION_STAGE.get(reg_name)
                if stage_id not in active_stage_ids:
                    continue
                if loc_name in vanilla_physical_locations and not vanilla_physical_locations[loc_name]:
                    continue

            region = multiworld.get_region(reg_name, player)
            location = DoomEternalLocation(player, loc_name, loc_data.code, region)
            region.locations.append(location)

        if plan.get("fixed_dash_completion_stage") == "e1m2_war":
            region = multiworld.get_region(catalog_locations["Exultia - Dash"].region, player)
            region.add_event("Fixed Dash Acquisition", "Dash", location_type=DoomEternalLocation,
                             item_type=DoomEternalItem)

        # 5. Create Mission Clear events
        for s in plan["stages"]:
            if s["kind"] == "mission":
                mission_name = s["name"]
                mission_location = f"{mission_name} - Mission Complete"
                try:
                    public_location = multiworld.get_location(mission_location, player)
                except KeyError:
                    continue
                region = public_location.parent_region
                event_name = mission_clear_event_name(mission_name)
                event_item = region.add_event(
                    event_name,
                    event_name,
                    rule=lambda state, public_location=public_location: public_location.can_reach(state),
                    location_type=DoomEternalLocation,
                    item_type=DoomEternalItem,
                )
                event_item.classification = ItemClassification.progression_skip_balancing
                if (plan.get("fixed_dash_completion_stage") == s["id"]
                        and s["id"] != "e1m2_war"):
                    dash = region.add_event(
                        "Fixed Dash Acquisition", "Dash",
                        rule=lambda state, public_location=public_location: public_location.can_reach(state),
                        location_type=DoomEternalLocation, item_type=DoomEternalItem,
                    )
                    dash.classification = ItemClassification.progression_skip_balancing

        # 6. Suffix victory requirement events
        requirement_location_suffixes = {
            "Complete All Slayer Gates": " - Slayer Gate Complete",
            "Complete All Escalation Encounters": " - Escalation Encounter Wave ",
            "Complete All Secret Encounters": " - Secret Encounter - ",
            "Complete All Mission Challenges": " - All Mission Challenges Completed",
            "Complete All Weapon Mastery Challenges": MASTERY_SUFFIX,
        }
        for location in list(multiworld.get_locations(player)):
            location_name = location.name
            for requirement_name, suffix in requirement_location_suffixes.items():
                if (suffix in location_name if suffix.endswith(" - ") or suffix.endswith(" ")
                    else location_name.endswith(suffix)):
                    region = location.parent_region
                    event_name = victory_requirement_location_event_name(requirement_name, location_name)
                    event_item = region.add_event(
                        event_name,
                        event_name,
                        rule=lambda state, loc=location: loc.can_reach(state),
                        location_type=DoomEternalLocation,
                        item_type=DoomEternalItem,
                    )
                    event_item.classification = ItemClassification.progression_skip_balancing

        # 7. Goal endpoint event
        active_location_names = {loc.name for loc in multiworld.get_locations(player)}
        for endpoint_goal, endpoint_location_name in GOAL_ENDPOINT_LOCATIONS.items():
            if endpoint_goal == "Complete the Full Saga" and self.options.goal.current_option_name == endpoint_goal:
                endpoint_location_name = GOAL_ENDPOINT_LOCATIONS[
                    "Kill the Icon of Sin" if plan["goal_stage"] == "e3m4_boss" else "Kill the Dark Lord"
                ]
            if not goal_endpoint_available(endpoint_goal, active_location_names):
                continue
            goal_location = multiworld.get_location(endpoint_location_name, player)
            goal_region = goal_location.parent_region
            goal_event_name = goal_endpoint_event_name(endpoint_goal)
            goal_event = goal_region.add_event(
                goal_event_name,
                goal_event_name,
                rule=lambda state, goal_location=goal_location: goal_location.can_reach(state),
                location_type=DoomEternalLocation,
                item_type=DoomEternalItem,
            )
            goal_event.classification = ItemClassification.progression_skip_balancing

        # 8. Hook up connections
        regions = {region.name: region for region in multiworld.get_regions(player)}
        for stage_id in plan["sequence"]:
            stage = STAGE_BY_ID[stage_id]
            entrance = hub.connect(regions[stage["entry_region"]], "Mission Select: " + stage["name"])
            entrance.access_rule = (
                lambda state, key=stage_id:
                stage_available(plan, key, state, player)
                and is_mission_ready(state, player, key, self,
                                     context='opening' if key == plan.get('opening_stage') else 'base')
            )

        for source_name, destination_name, entrance_name, condition in CAMPAIGN_CONNECTIONS:
            if source_name not in regions or destination_name not in regions:
                continue
            source_stage = REGION_STAGE.get(source_name)
            if (source_stage is None or source_stage != REGION_STAGE.get(destination_name)) and not (
                source_name == "Menu" and destination_name == "Weapon Masteries"
            ):
                continue
            entrance = regions[source_name].connect(regions[destination_name], entrance_name)
            requirement = connection_requirement(
                condition,
                randomize_dash=bool(self.options.randomize_dash.value),
            )
            set_rule(entrance, partial(self._campaign_entrance_access, None, requirement))
            from .native_enemy_safety import OPENING_REGIONS
            opening = OPENING_REGIONS.get(plan.get('opening_stage'), ())
            if source_name in opening and destination_name not in opening:
                add_rule(entrance, lambda state, key=plan['opening_stage']:
                         is_mission_ready(state, player, key, self))
            conn_key = (source_name, destination_name)
            if conn_key in SPIRIT_BREAKPOINTS:
                bp_stage_id = SPIRIT_BREAKPOINTS[conn_key]
                add_rule(
                    entrance,
                    lambda state, s_id=bp_stage_id: is_spirit_breakpoint_ready(state, player, s_id, self),
                )

        ordinary = [key for key in plan["sequence"] if key != plan["goal_stage"]]
        visits = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh")
        for index, visit in enumerate(visits):
            threshold = 0 if index == 0 else plan["fortress_phase_thresholds"][index]
            entrance = hub.connect(regions[f"Fortress of Doom - {visit} Visit"], f"Fortress phase: {visit}")
            entrance.access_rule = lambda state, count=threshold: sum(
                state.has(completion_event(key), player) for key in ordinary
            ) >= count

        from .killsanity_logic import create_killsanity_locations
        create_killsanity_locations(self)

    def create_items(self) -> None:
        """Instantiate the canonical semantic multiset exactly once."""
        start_inventory = self.effective_starting_inventory()
        plan = self.campaign_plan
        semantic_counts = plan.get("semantic_counts") or {}
        if not semantic_counts:
            raise ValueError("DOOM Eternal semantic item pool was not planned")
        pool_names: list[str] = []
        for name, quantity in sorted(semantic_counts.items()):
            pool_names.extend([name] * quantity)

        locations_count = len(self.multiworld.get_unfilled_locations(self.player))

        self.praetor_suit_upgrades_in_pool = plan["praetor_suit_upgrades_in_pool"]

        # Starting Weapon: physical ownership path. The planner already
        # excluded it from the semantic multiset.
        if not hasattr(self, "starting_weapon_name") or self.starting_weapon_name is None:
            self.starting_weapon_name = plan.get("starting_weapon") or self.options.starting_weapon.selected_weapon_name
            if self.starting_weapon_name is None:
                eligible_weapons = [
                    name for name in starting_weapon_item_names
                    if name not in pool_names and not start_inventory[name]
                ]
                if not eligible_weapons:
                    raise ValueError("Starting Weapon random selection has no eligible pool weapon")
                self.starting_weapon_name = self.multiworld.random.choice(eligible_weapons)
        if self.starting_weapon_name in pool_names:
            pool_names.remove(self.starting_weapon_name)
        self.multiworld.push_precollected(self.create_item(self.starting_weapon_name))
        for name in plan["bootstrap_inventory"]:
            self.multiworld.push_precollected(self.create_item(name))

        # Explicit start_inventory removes exactly its planned copies; a missing
        # copy is a conservation failure, not a silent skip.
        for name, quantity in start_inventory.items():
            for _ in range(quantity):
                if name not in pool_names:
                    raise ValueError(
                        f"DOOM Eternal start_inventory '{name}' exceeds planned item pool quantities"
                    )
                pool_names.remove(name)

        self.frontloaded_arsenal = []
        if self.enemies["enabled"]:
            owned = set(start_inventory) | set(plan["bootstrap_inventory"]) | set(plan.get("readiness_bootstrap_items", ())) | {self.starting_weapon_name}
            ammunition = {"Combat Shotgun": "shells", "Super Shotgun": "shells", "Heavy Cannon": "bullets",
                          "Chaingun": "bullets", "Plasma Rifle": "cells", "Ballista": "cells", "Rocket Launcher": "rockets"}
            families = {ammunition[name] for name in owned if name in ammunition}
            for _ in range(2):
                candidates = sorted(set(pool_names) & set(WEAPON_NAMES) - owned)
                if not candidates:
                    break
                diverse = [name for name in candidates if ammunition.get(name) not in families]
                weapon = self.random.choice(diverse or candidates)
                self.frontloaded_arsenal.append(weapon)
                owned.add(weapon)
                families.add(ammunition[weapon])
                mods = sorted(name for name in pool_names if MOD_HOST.get(name) == weapon)
                if mods:
                    mod = self.random.choice(mods)
                    self.frontloaded_arsenal.append(mod)

        # Pad with filler and traps to match unfilled locations exactly
        locations_count = len(self.multiworld.get_unfilled_locations(self.player))
        amount_needed = locations_count - len(pool_names)
        if amount_needed < 0:
            raise ValueError(
                f"DOOM Eternal item pool requires {len(pool_names)} locations; only {locations_count} enabled"
            )
        if amount_needed > 0:
            filler_weights = {
                "Extra Life": 10,
                "Ammo Refill": 30 if self.options.randomize_chainsaw.value else 20,
                "Full Heal": 8,
                "Full Armor": 8,
                "Soulsphere": 5,
                "Berserk": 3,
                "Onslaught": 3,
                "Overdrive": 3,
                "Small Health": 10,
                "Small Armor": 1,
                "Large Health": 10,
                "Large Armor": 10,
                "Armor Shard": 5,
            }
            profile = self.options.resource_profile.current_option_name
            for name in ("Full Heal", "Full Armor", "Soulsphere"):
                filler_weights[name] = (filler_weights[name] * 2 if profile == "Generous"
                                        else max(1, filler_weights[name] // 2) if profile == "Lean"
                                        else filler_weights[name])
            filler_weights.update(self.options.filler_weights.value)
            enabled_traps = sorted(self.options.enabled_traps.value)
            trap_weights = {name: self.options.trap_weights.value.get(name, 1) for name in enabled_traps}
            enabled_traps = [name for name in enabled_traps if trap_weights[name] > 0]
            trap_count = amount_needed * self.options.trap_percentage.value // 100 if enabled_traps else 0
            if amount_needed > trap_count and not any(filler_weights.values()):
                raise ValueError("Filler Weights must leave a positive weight for residual locations")
            if amount_needed > trap_count:
                pool_names.extend(self.multiworld.random.choices(
                    list(filler_weights), weights=list(filler_weights.values()), k=amount_needed - trap_count))
            if trap_count:
                pool_names.extend(self.multiworld.random.choices(enabled_traps,
                                  weights=[trap_weights[name] for name in enabled_traps], k=trap_count))

        pool = [self.create_item(name) for name in pool_names]
        self.multiworld.itempool += pool
        from .classification import apply_dynamic_progression_classification
        apply_dynamic_progression_classification(self)
        preparation = Counter(plan.get('bootstrap_placed_items', ())) + Counter(plan.get('opening_placed_items', ()))
        for item in self.multiworld.itempool:
            if item.player == self.player and item.name in preparation:
                item.classification = ItemClassification.progression
        for name, quantity in Counter(plan.get("bootstrap_placed_items", ())).items():
            if plan.get('opening_stage'):
                continue
            early = (self.multiworld.early_items if name in self.options.non_local_items.value
                     else self.multiworld.local_early_items)[self.player]
            early[name] = max(early.get(name, 0), quantity)

    def pre_fill(self) -> None:
        plan = self.campaign_plan
        if not plan.get('opening_stage'):
            return
        from .campaign import FORTRESS_BOOTSTRAP_LOCATIONS
        from .native_enemy_safety import OPENING_REGIONS
        state = CollectionState(self.multiworld)
        events = [location for location in self.multiworld.get_locations() if location.address is None]
        opening = OPENING_REGIONS[plan['opening_stage']]
        for items, regions in ((plan['bootstrap_placed_items'], ()),
                               (plan['opening_placed_items'], opening)):
            for name in items:
                if name in self.options.non_local_items.value:
                    early = self.multiworld.early_items[self.player]
                    early[name] = max(early.get(name, 0), 1)
                    state.collect(self.create_item(name), True)
                    state.sweep_for_advancements(events)
                    continue
                locations = [loc for loc in self.multiworld.get_unfilled_locations(self.player)
                             if loc.address is not None and loc.can_reach(state)
                             and (loc.name in FORTRESS_BOOTSTRAP_LOCATIONS or loc.parent_region.name in regions)]
                if not locations:
                    raise ValueError(f'No reachable opening check can provide {name}')
                item = next(item for item in self.multiworld.itempool
                            if item.player == self.player and item.name == name)
                location = self.random.choice(sorted(locations, key=lambda loc: loc.name))
                location.place_locked_item(item)
                self.multiworld.itempool.remove(item)
                state.collect(item, True, location)
                state.sweep_for_advancements(events)

    def set_rules(self) -> None:
        active_location_names = {
            location.name
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None
        }
        active_battery_cost = sum(group["cost"] for group in self.active_spend_groups)

        prerequisite_table = build_location_prerequisites(
            active_location_names,
            active_region_names={region.name for region in self.multiworld.get_regions(self.player)},
            randomize_chainsaw=bool(self.options.randomize_chainsaw.value),
            randomize_dash=bool(self.options.randomize_dash.value),
            special_weapon=(
                "The Crucible"
                if not self.options.use_dlc_content.value
                else self.options.special_weapon.current_option_name
            ),
            active_battery_cost=active_battery_cost,
            logic_difficulty=self.options.logic_difficulty.value,
            active_spend_groups=getattr(self, "active_spend_groups", None),
            enemy_plan=self.enemy_plan,
        )
        validate_location_prerequisites(
            prerequisite_table,
            active_location_names,
            set(item_data_table),
        )
        for location_name, requirement in prerequisite_table.items():
            location = self.multiworld.get_location(location_name, self.player)
            set_rule(
                location,
                partial(requirement_satisfied, requirement, player=self.player),
            )
            for item_name in required_item_names(requirement):
                forbid_item(location, item_name, self.player)

        for location_name in FORTRESS_BATTERY_CONSUMER_LOCATIONS & active_location_names:
            location = self.multiworld.get_location(location_name, self.player)
            forbid_item(location, "Sentinel Battery", self.player)
            forbid_item(location, "Sentinel Battery Bundle", self.player)

        effective_requirements = effective_victory_requirements(
            set(self.options.additional_victory_requirements.value),
            active_location_names,
            use_dlc_content=bool(self.options.use_dlc_content.value),
            include_dlc_missions=True,
            goal=self.options.goal.current_option_name,
        )
        mission_events = {
            completion_event(s["id"]) for s in self.campaign_plan["stages"]
        }
        required_events = {goal_endpoint_event_name(self.options.goal.current_option_name)}
        if "Complete All Included Missions" in effective_requirements:
            required_events.update(mission_events)
        if "Acquire the Unmaykr" in effective_requirements:
            required_events.add(goal_endpoint_event_name("Acquire the Unmaykr"))
        for requirement_name in effective_requirements - {"Complete All Included Missions", "Acquire the Unmaykr"}:
            suffix = {
                "Complete All Slayer Gates": " - Slayer Gate Complete",
                "Complete All Escalation Encounters": " - Escalation Encounter Wave ",
                "Complete All Secret Encounters": " - Secret Encounter - ",
                "Complete All Mission Challenges": " - All Mission Challenges Completed",
                "Complete All Weapon Mastery Challenges": MASTERY_SUFFIX,
            }[requirement_name]
            candidate_locations = active_location_names
            required_events.update(
                victory_requirement_location_event_name(requirement_name, location)
                for location in candidate_locations
                if (suffix in location if suffix.endswith(" - ") or suffix.endswith(" ")
                    else location.endswith(suffix))
            )

        def completion_condition(state):
            goal_stage = self.campaign_plan["goal_stage"]
            if goal_stage is not None:
                ordinary_complete = all(state.has(completion_event(key), self.player)
                                        for key in self.campaign_plan["sequence"] if key != goal_stage)
                goal_access = self.campaign_plan["goal_as_item"] and state.has(
                    STAGE_BY_ID[goal_stage]["name"] + " Access", self.player)
                if not (ordinary_complete or goal_access):
                    return False
            return all(
                state.has(event_name, self.player) for event_name in required_events
            )

        self.multiworld.completion_condition[self.player] = completion_condition

    def fill_hook(
        self,
        progitempool: list[Item],
        usefulitempool: list[Item],
        filleritempool: list[Item],
        fill_locations: list[Location],
    ) -> None:
        arsenal = set(getattr(self, 'frontloaded_arsenal', ()))
        access_priority = {}
        if self.options.mission_order.value == 2 and self.enemies.get('balance_preset'):
            ranks = self.campaign_plan['enemy_progression_bands']
            count = max(1, max(ranks.values()))
            for stage in self.campaign_plan['access_items'].values():
                access_priority[STAGE_BY_ID[stage]['name'] + ' Access'] = ranks[stage] / count + self.random.uniform(-0.6, 0.6)

        def sort_key(item: Item) -> float:
            if item.player == self.player:
                if item.name in arsenal:
                    return 1
                if item.name in access_priority:
                    return 1.5 + access_priority[item.name]
                if "Battery" in item.name:
                    return 3
            return 2

        progitempool.sort(key=sort_key)
