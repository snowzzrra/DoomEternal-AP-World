from collections import Counter
import hashlib
import json
from functools import partial
from typing import ClassVar

from BaseClasses import Entrance, ItemClassification, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import add_rule, forbid_item, set_rule

from .combat_readiness import (
    SPIRIT_BREAKPOINTS,
    is_mission_ready,
    is_spirit_breakpoint_ready,
)

from .generated_content import (
    CAMPAIGN_CONNECTIONS,
    CAMPAIGN_REGIONS,
    MISSION_DIFFICULTY,
)
from .identity import GAME_NAME
from .campaign import (
    BASE_GATE_STAGE_IDS,
    FORTRESS_BOOTSTRAP_LOCATIONS,
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
    TAG_MISSION_LOCAL_ITEM_NAMES,
    WEAPON_UPGRADE_POINTS_NAME,
    WEAPON_UPGRADE_POINTS_ITEM_COUNT,
    item_data_table,
    item_name_to_id,
    starting_weapon_item_names,
    world_pool_weapon_item_names,
    suit_perk_item_names,
)
from .locations import DoomEternalLocation, location_data_table, location_name_to_id
from .logic import (
    FORTRESS_BATTERY_CONSUMER_LOCATIONS,
    build_location_prerequisites,
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
from .options import DLCLogicTiming, DoomEternalOptions, SpecialWeapon, resolve_praetor_suit_upgrade_count
from .settings import DoomEternalSettings
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

    AUTOMAP_STARTING_ITEM = "Reveal Automap Progression Items"

    def effective_starting_inventory(self) -> Counter[str]:
        """Return every item materialized before normal AP receipt delivery."""
        inventory = Counter(self.options.start_inventory.value)
        if self.options.reveal_ap_locations_on_automap.value:
            inventory[self.AUTOMAP_STARTING_ITEM] = 1
        return inventory

    def generate_early(self) -> None:
        self.campaign_plan = make_plan(self.options, self.random, world=self)
        self.starting_weapon_name = self.campaign_plan.get("starting_weapon")
        # Physical-ownership policy: every item materialized before normal AP
        # receipt delivery is logically owned even when its pool classification
        # is useful (R03). Computed before any push_precollected call.
        initial_logical_items = set(self.options.start_inventory.value)
        if self.starting_weapon_name:
            initial_logical_items.add(self.starting_weapon_name)
        initial_logical_items.update(self.campaign_plan.get("bootstrap_inventory", ()))
        initial_logical_items.update(self.campaign_plan.get("readiness_bootstrap_items", ()))
        if self.options.reveal_ap_locations_on_automap.value:
            initial_logical_items.add(self.AUTOMAP_STARTING_ITEM)
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
            if name in TAG_MISSION_LOCAL_ITEM_NAMES and not dlc_enabled:
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
        if self.options.reveal_ap_locations_on_automap.value:
            if self.AUTOMAP_STARTING_ITEM not in self.options.start_inventory.value:
                self.multiworld.push_precollected(self.create_item(self.AUTOMAP_STARTING_ITEM))

    required_client_version = (0, 6, 7)

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

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
        ``start_inventory``, the chosen Starting Weapon, generated bootstrap
        inventory and readiness bootstrap items) are logically active even when
        their pool classification is useful. Hypothetical or placed useful
        copies keep the default AP collect semantics and are never promoted
        globally by this override.
        """
        if item.advancement:
            return item.name
        if item.name in getattr(self, "initial_logical_items", ()):
            return item.name
        return None

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
            "room_mod_v2", "slot_data_v5", "goal_events_v1", "goal_endpoint_events_v1",
            "dlc_missions_v1", "physical_options_v1",
        ]
        if start_inventory:
            capabilities.append("starting_inventory_v1")
        capabilities.extend([
            "starting_weapon_v1", "special_weapon_progression_v1", "ammo_refill_v1",
            "cross_campaign_materialization_v1", "unified_campaign_v1",
        ])

        active_sg = getattr(self, "active_spend_groups", FORTRESS_SPEND_GROUPS)

        data = {
            "campaign_plan": self.campaign_plan,
            "death_link": bool(self.options.death_link.value),
            "praetor_suit_upgrades_in_pool": self.praetor_suit_upgrades_in_pool,
            "randomize_chainsaw": bool(self.options.randomize_chainsaw.value),
            "randomize_dash": bool(self.options.randomize_dash.value),
            "randomize_first_battery": bool(self.options.randomize_first_battery.value),
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
            "dlc_logic_timing": self.options.dlc_logic_timing.current_option_name,
            "goal": self.options.goal.current_option_name,
            "goal_endpoint_event": goal_endpoint_event_name(self.options.goal.current_option_name),
            "goal_endpoint_available": goal_endpoint_available(
                self.options.goal.current_option_name, active_location_names
            ),
            "additional_victory_requirements": sorted(effective_requirements),
            "mission_difficulty": {
                mission: dict(metadata) for mission, metadata in MISSION_DIFFICULTY.items()
            },
            "special_weapon": "The Crucible" if not dlc_enabled else self.options.special_weapon.current_option_name,
            "enhanced_melee_damage": bool(self.options.enhanced_melee_damage.value),
            "apworld_revision": APWORLD_REVISION,
            "content_revision": CONTENT_REVISION,
            "bridge_protocol": BRIDGE_PROTOCOL,
            "compiler_revision": COMPILER_REVISION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "slot_data_revision": SLOT_DATA_REVISION,
            "mod_contract_revision": ROOM_CONTRACT_REVISION,
            "required_capabilities": capabilities,
            "starting_inventory": start_inventory,
            "starting_weapon": self.starting_weapon_name,
        }
        identity = {"slot_data": data, "placements": sorted(
            (location.address, location.item.code, location.item.player)
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None and location.item is not None)}
        data["native_generation_fingerprint"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return data

    def create_regions(self) -> None:
        dlc_enabled = bool(self.options.use_dlc_content.value)
        plan = self.campaign_plan
        active_normal_ids = plan["active_normal_mission_ids"]
        active_stage_ids = set(plan["stage_ids"])

        # 1. Count mission locations to feed scaling
        vanilla_physical_locations = {
            "Hell on Earth - Chainsaw": self.options.randomize_chainsaw.value,
            "Exultia - Dash": self.options.randomize_dash.value,
            "Exultia - Sentinel Battery - King Novik Return Path": self.options.randomize_first_battery.value,
        }
        mission_loc_count = 0
        for loc_name, loc_data in location_data_table.items():
            stage_id = REGION_STAGE.get(loc_data.region)
            if stage_id in active_stage_ids:
                if loc_name in vanilla_physical_locations and not vanilla_physical_locations[loc_name]:
                    continue
                mission_loc_count += 1

        # 2. Get short-world scaling parameters
        active_sg, active_masteries_count, battery_surplus = get_short_world_scaling(
            active_normal_ids,
            mission_loc_count,
            plan["mode"],
            bool(self.options.include_weapon_mastery_challenges.value),
        )
        self.active_spend_groups = active_sg
        self.active_masteries_count = active_masteries_count
        self.battery_surplus = battery_surplus
        plan["active_spend_groups"] = active_sg

        # Active Fortress locations
        has_unmaykr_check = set(BASE_GATE_STAGE_IDS).issubset(set(active_normal_ids))
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
        for loc_name, loc_data in location_data_table.items():
            reg_name = loc_data.region
            if "Fortress of Doom" in reg_name:
                if loc_name not in active_hub_locations:
                    continue
                if loc_name in FORTRESS_BOOTSTRAP_LOCATIONS:
                    reg_name = "Fortress of Doom"
                elif loc_name in active_fortress_consumer_locs and loc_name != "Fortress of Doom - Fully Upgraded Suit Cheat Code":
                    reg_name = "Fortress of Doom"
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
                and is_mission_ready(state, player, key, self)
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
                randomize_first_battery=bool(self.options.randomize_first_battery.value),
                randomize_dash=bool(self.options.randomize_dash.value),
            )
            set_rule(entrance, partial(self._campaign_entrance_access, None, requirement))
            conn_key = (source_name, destination_name)
            if conn_key in SPIRIT_BREAKPOINTS:
                bp_stage_id = SPIRIT_BREAKPOINTS[conn_key]
                add_rule(
                    entrance,
                    lambda state, s_id=bp_stage_id: is_spirit_breakpoint_ready(state, player, s_id, self),
                )

        ordinary = [key for key in plan["sequence"] if key != plan["goal_stage"]]
        visits = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh")
        for visit, base_count in zip(visits, (1, 2, 4, 5, 6, 8, 9)):
            threshold = (base_count * len(ordinary) + 12) // 13 if ordinary else 0
            entrance = hub.connect(regions[f"Fortress of Doom - {visit} Visit"], f"Fortress phase: {visit}")
            entrance.access_rule = lambda state, count=threshold: sum(
                state.has(completion_event(key), player) for key in ordinary
            ) >= count

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

        # Praetor Suit upgrades: explicit bounded option, sampled here to keep
        # the established world RNG stream.
        suit_names = suit_perk_item_names
        manual_automap_count = int(bool(start_inventory[self.AUTOMAP_STARTING_ITEM]))
        automap_start_count = manual_automap_count
        requested_suits = [
            name for name in suit_names
            if name != self.AUTOMAP_STARTING_ITEM and start_inventory[name]
        ]
        requested_real_suit_count = sum(start_inventory[name] for name in requested_suits)

        raw_praetor_count = self.resolve_praetor_suit_upgrade_count()
        eff_praetor_count = min(raw_praetor_count, max(3, round(raw_praetor_count * locations_count / 439)))
        if raw_praetor_count < 3:
            eff_praetor_count = raw_praetor_count

        target_suit_count = max(eff_praetor_count, automap_start_count)
        self.praetor_suit_upgrades_in_pool = target_suit_count - automap_start_count
        for name in requested_suits:
            pool_names.extend([name] * start_inventory[name])
        suit_candidates = [
            name for name in suit_names
            if name != self.AUTOMAP_STARTING_ITEM or not automap_start_count
            if name not in requested_suits
        ]
        sample_k = max(0, target_suit_count - automap_start_count - requested_real_suit_count)
        pool_names.extend(self.multiworld.random.sample(suit_candidates, sample_k))

        pool_names.extend(["Ammo Refill"] * start_inventory.get("Ammo Refill", 0))

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

        # Readiness Bootstrap Precollected Items (Phase 7.7c §6)
        # Bootstrap materialization must be logically active: a precollected
        # readiness item only contributes to Combat Rating / readiness rules when
        # it is traceable as progression in CollectionState. Never silently skip
        # a planned bootstrap witness.
        for name in plan.get("readiness_bootstrap_items", ()):
            if name not in pool_names:
                raise ValueError(
                    f"DOOM Eternal readiness bootstrap item '{name}' is missing from the planned semantic pool"
                )
            pool_names.remove(name)
            item = self.create_item(name)
            item.classification = ItemClassification.progression
            self.multiworld.push_precollected(item)

        for name in plan["bootstrap_inventory"]:
            self.multiworld.push_precollected(self.create_item(name))

        # Explicit start_inventory removes exactly its planned copies; a missing
        # copy is a conservation failure, not a silent skip.
        for name, quantity in start_inventory.items():
            if name == self.AUTOMAP_STARTING_ITEM:
                continue
            for _ in range(quantity):
                if name not in pool_names:
                    raise ValueError(
                        f"DOOM Eternal start_inventory '{name}' exceeds planned item pool quantities"
                    )
                pool_names.remove(name)

        # B=0/B>0 readiness bootstrap witness: the solver proved these exact
        # copies are sufficient inside the free pre-Mission Fortress checks.
        # Materialize them there deterministically so sphere-zero readiness is
        # a placement guarantee instead of fill-order luck (never precollected).
        witness = list(plan.get("bootstrap_placed_items", ()))
        if witness:
            bootstrap_locations = sorted(FORTRESS_NON_CONSUMER_LOCATIONS)
            if len(witness) > len(bootstrap_locations):
                raise ValueError(
                    f"DOOM Eternal bootstrap placement witness has {len(witness)} items; "
                    f"only {len(bootstrap_locations)} free Fortress locations exist"
                )
            for name, location_name in zip(witness, bootstrap_locations):
                if name not in pool_names:
                    raise ValueError(
                        f"DOOM Eternal bootstrap placement witness '{name}' is missing from the planned semantic pool"
                    )
                location = self.multiworld.get_location(location_name, self.player)
                if location.item is not None:
                    raise ValueError(f"DOOM Eternal bootstrap location '{location_name}' is already filled")
                pool_names.remove(name)
                location.place_locked_item(self.create_item(name))
            locations_count = len(self.multiworld.get_unfilled_locations(self.player))

        # Pad with filler and traps to match unfilled locations exactly
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
                "Small Health": 10,
                "Small Armor": 1,
                "Large Health": 10,
                "Large Armor": 10,
                "Armor Shard": 5,
            }
            enabled_traps = sorted(self.options.enabled_traps.value)
            trap_count = amount_needed * self.options.trap_percentage.value // 100 if enabled_traps else 0
            fillers = self.multiworld.random.choices(
                list(filler_weights),
                weights=list(filler_weights.values()),
                k=amount_needed - trap_count,
            )
            pool_names.extend(fillers)
            pool_names.extend(self.multiworld.random.choices(enabled_traps, k=trap_count))

        pool = [self.create_item(name) for name in pool_names]
        self.multiworld.itempool += pool

        # Dynamic Progression Classification (Phase 7.7 / 7.8B)
        from .classification import apply_dynamic_progression_classification
        apply_dynamic_progression_classification(self)

    def resolve_praetor_suit_upgrade_count(self) -> int:
        return resolve_praetor_suit_upgrade_count(
            self.options.praetor_suit_upgrades_in_pool.value,
            self.multiworld.random,
        )

    def set_rules(self) -> None:
        active_location_names = {
            location.name
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None
        }
        sg_count = len(getattr(self, "active_spend_groups", ())) or 12
        first_bat_rand = bool(
            self.options.randomize_first_battery.value
            and "e1m2_war" in self.campaign_plan["active_normal_mission_ids"]
        )
        active_battery_cost = 2 * sg_count + (1 if first_bat_rand else 0)

        prerequisite_table = build_location_prerequisites(
            active_location_names,
            active_region_names={region.name for region in self.multiworld.get_regions(self.player)},
            randomize_chainsaw=bool(self.options.randomize_chainsaw.value),
            randomize_dash=bool(self.options.randomize_dash.value),
            randomize_first_battery=bool(self.options.randomize_first_battery.value),
            special_weapon=(
                "The Crucible"
                if not self.options.use_dlc_content.value
                else self.options.special_weapon.current_option_name
            ),
            active_battery_cost=active_battery_cost,
            campaign_difficulty=self.options.campaign_difficulty.value,
            active_spend_groups=getattr(self, "active_spend_groups", None),
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
