from collections import Counter
from functools import partial
from typing import ClassVar

from BaseClasses import Entrance, ItemClassification, LocationProgressType, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import forbid_item, set_rule

from .generated_content import (
    CAMPAIGN_CONNECTIONS,
    CAMPAIGN_GOAL_LOCATION,
    CAMPAIGN_REGIONS,
)
from .identity import GAME_NAME
from .items import (
    BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES,
    BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES,
    DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES,
    DEVINV_START_INVENTORY_ITEM_NAMES,
    DoomEternalItem,
    item_data_table,
    item_name_to_id,
    starting_weapon_item_names,
    world_pool_weapon_item_names,
    suit_perk_item_names,
)
from .locations import DoomEternalLocation, location_data_table, location_name_to_id
from .logic import (
    build_location_prerequisites,
    connection_requirement,
    FORTRESS_BATTERY_CONSUMER_LOCATIONS,
    mission_clear_event_name,
    required_item_names,
    requirement_satisfied,
    validate_location_prerequisites,
)
from .options import DeathLinkMode, DoomEternalOptions, resolve_praetor_suit_upgrade_count
from .version import APWORLD_REVISION, BRIDGE_PROTOCOL, COMPILER_REVISION, CONTENT_REVISION


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

    AUTOMAP_STARTING_ITEM = "Reveal Automap Progression Items"

    def generate_early(self) -> None:
        if (
            self.options.start_with_automap.value
            and not self.options.start_inventory.value.get(self.AUTOMAP_STARTING_ITEM, 0)
        ):
            self.multiworld.push_precollected(self.create_item(self.AUTOMAP_STARTING_ITEM))
        unsafe = []
        invalid_quantity = []
        unavailable = []
        for name, quantity in self.options.start_inventory.value.items():
            data = item_data_table.get(name)
            if data is None:
                unsafe.append(name)
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
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                invalid_quantity.append(name)
            elif name.startswith("Progressive ") and quantity > 4:
                invalid_quantity.append(f"{name} (maximum 4 ordered tiers)")
            elif name in suit_perk_item_names and quantity > 1:
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
        battery_quantity = self.options.start_inventory.value.get("Sentinel Battery", 0)
        available_batteries = BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES - (
            0 if self.options.randomize_first_battery.value else 1
        )
        if battery_quantity > available_batteries:
            raise ValueError(
                "DOOM Eternal start_inventory Sentinel Battery exceeds current pool quantity: "
                f"requested {battery_quantity}, available {available_batteries}"
            )
        selected_weapon = self.options.starting_weapon.selected_weapon_name
        if selected_weapon and self.options.start_inventory.value.get(selected_weapon, 0):
            raise ValueError(
                f"Starting Weapon '{selected_weapon}' is redundant with start_inventory"
            )
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

    def fill_slot_data(self) -> dict[str, object]:
        start_inventory = dict(self.options.start_inventory.value)
        capabilities = ["room_mod_v1"]
        capabilities.append("physical_options_v1")
        if start_inventory:
            capabilities.append("starting_inventory_v1")
        capabilities.append("starting_weapon_v1")
        return {
            "death_link": bool(self.options.death_link.value),
            "death_link_mode": self.options.death_link_mode.get_option_name(
                self.options.death_link_mode.value
            ).lower(),
            "praetor_suit_upgrades_in_pool": self.praetor_suit_upgrades_in_pool,
            "randomize_chainsaw": bool(self.options.randomize_chainsaw.value),
            "randomize_dash": bool(self.options.randomize_dash.value),
            "randomize_first_battery": bool(self.options.randomize_first_battery.value),
            "include_weapon_mastery_challenges": bool(self.options.include_weapon_mastery_challenges.value),
            "trap_percentage": int(self.options.trap_percentage.value),
            "enabled_traps": sorted(self.options.enabled_traps.value),
            "start_with_automap": bool(self.options.start_with_automap.value),
            "apworld_revision": APWORLD_REVISION,
            "content_revision": CONTENT_REVISION,
            "bridge_protocol": BRIDGE_PROTOCOL,
            "compiler_revision": COMPILER_REVISION,
            "manifest_schema_version": 2,
            "mod_contract_revision": 1,
            "required_capabilities": capabilities,
            "starting_inventory": start_inventory,
            "starting_weapon": self.starting_weapon_name,
        }

    def create_regions(self) -> None:
        for region_name in CAMPAIGN_REGIONS:
            region = Region(region_name, self.player, self.multiworld)
            self.multiworld.regions.append(region)

        # Place locations in their respective regions
        vanilla_physical_locations = {
            "Hell on Earth - Chainsaw": self.options.randomize_chainsaw.value,
            "Exultia - Dash": self.options.randomize_dash.value,
            "Exultia - Sentinel Battery - King Novik Return Path": self.options.randomize_first_battery.value,
        }
        for loc_name, loc_data in location_data_table.items():
            if loc_name in vanilla_physical_locations and not vanilla_physical_locations[loc_name]:
                continue
            if loc_data.region == "Weapon Masteries" and not self.options.include_weapon_mastery_challenges.value:
                continue
            region = self.multiworld.get_region(loc_data.region, self.player)
            location = DoomEternalLocation(self.player, loc_name, loc_data.code, region)
            if loc_name in FORTRESS_BATTERY_CONSUMER_LOCATIONS:
                location.progress_type = LocationProgressType.EXCLUDED
            region.locations.append(location)

        mission_clear_events: dict[str, str] = {}
        for mission_name in {
            location.removesuffix(" - Mission Complete")
            for location in location_data_table
            if location.endswith(" - Mission Complete")
        }:
            mission_location = f"{mission_name} - Mission Complete"
            public_location = self.multiworld.get_location(mission_location, self.player)
            region = public_location.parent_region
            if region is None:
                raise ValueError(f"Mission Complete location has no terminal region: {mission_location}")
            event_name = mission_clear_event_name(mission_name)
            event_item = region.add_event(
                event_name,
                event_name,
                rule=lambda state, public_location=public_location: public_location.can_reach(state),
                location_type=DoomEternalLocation,
                item_type=DoomEternalItem,
            )
            event_item.classification = ItemClassification.progression_skip_balancing
            mission_clear_events[region.name] = event_name

        for source_name, destination_name, entrance_name, condition in CAMPAIGN_CONNECTIONS:
            source = self.multiworld.get_region(source_name, self.player)
            destination = self.multiworld.get_region(destination_name, self.player)
            if not entrance_name and not condition:
                boundary_event = mission_clear_events.get(source_name)
                if not boundary_event:
                    source.connect(destination)
                    continue
                entrance = source.create_exit(entrance_name or f"{source_name} -> {destination_name}")
                entrance.connect(destination)
                set_rule(
                    entrance,
                    partial(
                        self._campaign_entrance_access,
                        boundary_event,
                        connection_requirement(
                            condition,
                            randomize_first_battery=bool(self.options.randomize_first_battery.value),
                        ),
                    ),
                )
                continue
            generated_entrance_name = entrance_name or f"{source_name} -> {destination_name}"
            entrance = Entrance(self.player, generated_entrance_name, source)
            source.exits.append(entrance)
            entrance.connect(destination)
            set_rule(
                entrance,
                partial(
                    self._campaign_entrance_access,
                    mission_clear_events.get(source_name),
                    connection_requirement(
                        condition,
                        randomize_first_battery=bool(self.options.randomize_first_battery.value),
                    ),
                ),
            )

    def create_items(self) -> None:
        start_inventory = Counter(self.options.start_inventory.value)
        # Base progression items to seed into the world
        pool_names = [
            *world_pool_weapon_item_names,
            "Chainsaw",
            "Meat Hook",
            "Frag Grenade",
            "Blood Punch",
            "Flame Belch",
            "Ice Bomb",
            "Sticky Bombs",
            "Full Auto",
            "Precision Bolt",
            "Micro Missiles",
            "Heat Blast",
            "Microwave Beam",
            "Remote Detonate",
            "Lock-on Burst",
            "Arbalest",
            "Destroyer Blade",
            "Energy Shield",
            "Mobile Turret",
            "Savagery",
            "Seek and Destroy",
            "Blood Fueled",
            "Air Control",
            "Dazed and Confused",
            "Saving Throw",
            "Chrono Strike",
            "Equipment Fiend",
            "Punch and Reave",
            "Sticky Bombs Mastery",
            "Full Auto Mastery",
            "Micro Missiles Mastery",
            "Heat Blast Mastery",
            "Microwave Beam Mastery",
            "Lock-on Burst Mastery",
            "Arbalest Mastery",
            "Energy Shield Mastery",
            "Mobile Turret Mastery",
            "Precision Bolt Mastery",
            "Remote Detonate Mastery",
            "Destroyer Blade Mastery",
            "Meat Hook Mastery",
            *(["Progressive Health Upgrade"] * 4),
            *(["Progressive Armor Upgrade"] * 4),
            *(["Progressive Ammo Upgrade"] * 4),
        ]
        suit_names = suit_perk_item_names
        manual_automap_count = int(bool(start_inventory[self.AUTOMAP_STARTING_ITEM]))
        option_automap_count = int(bool(self.options.start_with_automap.value))
        automap_start_count = max(option_automap_count, manual_automap_count)
        requested_suits = [
            name for name in suit_names
            if name != self.AUTOMAP_STARTING_ITEM and start_inventory[name]
        ]
        requested_real_suit_count = sum(start_inventory[name] for name in requested_suits)
        requested_suit_count = requested_real_suit_count + automap_start_count
        suit_count = self.resolve_praetor_suit_upgrade_count()
        target_suit_count = max(suit_count, automap_start_count)
        self.praetor_suit_upgrades_in_pool = target_suit_count - automap_start_count
        if requested_suit_count > target_suit_count:
            raise ValueError(
                "DOOM Eternal start_inventory requests more Praetor Suit upgrades than option allows: "
                f"requested {requested_suit_count}, pool limit {target_suit_count}"
            )
        for name in requested_suits:
            pool_names.extend([name] * start_inventory[name])
        suit_candidates = [
            name for name in suit_names
            if name != self.AUTOMAP_STARTING_ITEM or not automap_start_count
            if name not in requested_suits
        ]
        pool_names.extend(self.multiworld.random.sample(
            suit_candidates,
            target_suit_count - automap_start_count - requested_real_suit_count,
        ))

        if not self.options.randomize_chainsaw.value:
            pool_names.remove("Chainsaw")

        if self.options.randomize_dash.value:
            pool_names.append("Dash")

        randomized_battery_singles = BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES
        if self.options.randomize_first_battery.value:
            pool_names.extend(["Sentinel Battery"] * randomized_battery_singles)
        else:
            pool_names.extend(["Sentinel Battery"] * (randomized_battery_singles - 1))
        pool_names.extend(["Sentinel Battery Bundle"] * BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES)

        available = Counter(pool_names)
        unavailable = {
            name: quantity
            for name, quantity in start_inventory.items()
            if name != self.AUTOMAP_STARTING_ITEM
            if available[name] < quantity
        }
        if unavailable:
            details = ", ".join(
                f"{name} requested {quantity}, available {available[name]}"
                for name, quantity in sorted(unavailable.items())
            )
            raise ValueError(f"DOOM Eternal start_inventory exceeds item pool quantities: {details}")

        self.starting_weapon_name = self.options.starting_weapon.selected_weapon_name
        if self.starting_weapon_name is None:
            eligible_weapons = [
                name for name in starting_weapon_item_names
                if available[name] and not start_inventory[name]
            ]
            if not eligible_weapons:
                raise ValueError("Starting Weapon random selection has no eligible pool weapon")
            self.starting_weapon_name = self.multiworld.random.choice(eligible_weapons)

        pool_names.remove(self.starting_weapon_name)
        self.multiworld.push_precollected(self.create_item(self.starting_weapon_name))
        for name, quantity in start_inventory.items():
            if name == self.AUTOMAP_STARTING_ITEM:
                continue
            for _ in range(quantity):
                pool_names.remove(name)

        self.multiworld.get_location(CAMPAIGN_GOAL_LOCATION, self.player).place_locked_item(self.create_item("Victory"))

        locations_count = len(self.multiworld.get_unfilled_locations(self.player))

        filler_weights = {
            "Extra Life": 10,
            "Ammo Refill": 80 if self.options.randomize_chainsaw.value else 20,
            "Full Heal": 8,
            "Full Armor": 8,
            "Soulsphere": 5,
            "Berserk": 3,
            "Small Health": 10,
            "Small Armor": 1,
            "Large Health": 10,
            "Large Armor": 10,
            "Armor Shard": 5,
        }

        # Pad with filler; traps replace only this padding.
        amount_needed = locations_count - len(pool_names)
        if amount_needed > 0:
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

    def resolve_praetor_suit_upgrade_count(self) -> int:
        return resolve_praetor_suit_upgrade_count(
            self.options.praetor_suit_upgrades_in_pool.value,
            self.multiworld.random,
        )

    def set_rules(self) -> None:
        active_location_names = {
            location.name for location in self.multiworld.get_locations(self.player)
        }
        prerequisite_table = build_location_prerequisites(
            active_location_names,
            randomize_chainsaw=bool(self.options.randomize_chainsaw.value),
        )
        validate_location_prerequisites(prerequisite_table, active_location_names, set(item_data_table))
        for location_name, requirement in prerequisite_table.items():
            location = self.multiworld.get_location(location_name, self.player)
            set_rule(
                location,
                partial(requirement_satisfied, requirement, player=self.player),
            )
            for item_name in required_item_names(requirement):
                forbid_item(location, item_name, self.player)

        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
