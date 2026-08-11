from collections import Counter
from functools import partial
from typing import ClassVar

from BaseClasses import CollectionState, Entrance, ItemClassification, Region, Tutorial
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
    SENTINEL_BATTERY_BUNDLE_VALUE,
    DoomEternalItem,
    item_data_table,
    item_name_to_id,
    normal_pool_weapon_item_names,
    suit_perk_item_names,
)
from .locations import DoomEternalLocation, location_data_table, location_name_to_id
from .logic import (
    EXTERNAL_VANILLA_PREREQUISITES,
    build_location_prerequisites,
    required_item_names,
    requirement_satisfied,
    validate_external_vanilla_prerequisites,
    validate_location_prerequisites,
)
from .options import DoomEternalOptions
from .regions import regions
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

    def generate_early(self) -> None:
        """Common start_inventory is ownership bootstrap, never consumable replay."""
        unsafe = []
        for name in self.options.start_inventory.value:
            data = item_data_table.get(name)
            if data is None or not (data.classification & (ItemClassification.progression | ItemClassification.useful)):
                unsafe.append(name)
        if unsafe:
            raise ValueError(
                "DOOM Eternal start_inventory supports persistent progression/useful items only: "
                + ", ".join(sorted(unsafe))
            )
        selected_weapon = self.options.starting_weapon.selected_weapon_name
        if selected_weapon and self.options.start_inventory.value.get(selected_weapon, 0):
            raise ValueError(
                f"Starting Weapon '{selected_weapon}' is redundant with start_inventory"
            )
    required_client_version = (0, 6, 7)

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    def create_item(self, name: str) -> DoomEternalItem:
        item_data = item_data_table[name]
        return DoomEternalItem(name, item_data.classification, item_data.code, self.player)

    @staticmethod
    def has_sentinel_battery_currency(state: CollectionState, player: int, amount: int) -> bool:
        return (
            state.count("Sentinel Battery", player)
            + SENTINEL_BATTERY_BUNDLE_VALUE * state.count("Sentinel Battery Bundle", player)
        ) >= amount

    def fill_slot_data(self) -> dict[str, object]:
        start_inventory = dict(self.options.start_inventory.value)
        capabilities = ["room_mod_v1"]
        capabilities.append("physical_options_v1")
        if start_inventory:
            capabilities.append("starting_inventory_v1")
        capabilities.append("starting_weapon_v1")
        return {
            "death_link": bool(self.options.death_link.value),
            "randomize_chainsaw": bool(self.options.randomize_chainsaw.value),
            "randomize_dash": bool(self.options.randomize_dash.value),
            "randomize_first_battery": bool(self.options.randomize_first_battery.value),
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
        # Create regions
        for region_name in dict.fromkeys((*regions, *CAMPAIGN_REGIONS)):
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
            region = self.multiworld.get_region(loc_data.region, self.player)
            location = DoomEternalLocation(self.player, loc_name, loc_data.code, region)
            region.locations.append(location)

        for source_name, destination_name, entrance_name in CAMPAIGN_CONNECTIONS:
            source = self.multiworld.get_region(source_name, self.player)
            destination = self.multiworld.get_region(destination_name, self.player)
            if not entrance_name:
                source.connect(destination)
                continue
            entrance = Entrance(self.player, entrance_name, source)
            source.exits.append(entrance)
            entrance.connect(destination)

    def create_items(self) -> None:
        # Base progression items to seed into the world
        pool_names = [
            # Cultist Base still uses a vanilla scripted reward for the
            # Super Shotgun/Revenant sequence, but Super Shotgun remains
            # eligible for normal starting-weapon randomization.
            *normal_pool_weapon_item_names,
            "Chainsaw",
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
        pool_names.extend(self.multiworld.random.sample(suit_perk_item_names, 6))

        if not self.options.randomize_chainsaw:
            pool_names.remove("Chainsaw")

        if self.options.randomize_dash:
            pool_names.append("Dash")

        randomized_battery_singles = BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES
        if self.options.randomize_first_battery:
            pool_names.extend(["Sentinel Battery"] * randomized_battery_singles)
        else:
            pool_names.extend(["Sentinel Battery"] * (randomized_battery_singles - 1))
        pool_names.extend(["Sentinel Battery Bundle"] * BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES)

        start_inventory = Counter(self.options.start_inventory.value)
        available = Counter(pool_names)
        unavailable = {
            name: quantity
            for name, quantity in start_inventory.items()
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
                name for name in normal_pool_weapon_item_names
                if available[name] and not start_inventory[name]
            ]
            if not eligible_weapons:
                raise ValueError("Starting Weapon random selection has no eligible pool weapon")
            self.starting_weapon_name = self.multiworld.random.choice(eligible_weapons)

        pool_names.remove(self.starting_weapon_name)
        self.multiworld.push_precollected(self.create_item(self.starting_weapon_name))
        for name, quantity in start_inventory.items():
            for _ in range(quantity):
                pool_names.remove(name)

        self.multiworld.get_location(CAMPAIGN_GOAL_LOCATION, self.player).place_locked_item(self.create_item("Victory"))

        locations_count = len(self.multiworld.get_unfilled_locations(self.player))

        filler_weights = {
            "Extra Life": 10,
            "Ammo Refill": 40,
            "Small Health": 10,
            "Small Armor": 1,
            "Large Health": 10,
            "Large Armor": 10,
            "Armor Shard": 5,
            "Imp Trap": 2,
            "Carcass Trap": 2,
            "Revenant Trap": 2,
            "Arachnotron Trap": 2,
            "Hell Knight Trap": 2,
            "Dread Knight Trap": 2,
            "Baron Trap": 2,
            "Tyrant Trap": 2,
            "Marauder Trap": 2,
            "Archvile Trap": 2,
            "Cueball Trap": 2,
            "Ammo Drain Trap": 2,
            "Fuel Drain Trap": 2,
            "BFG Drain Trap": 2,
        }

        # Pad with filler
        amount_needed = locations_count - len(pool_names)
        if amount_needed > 0:
            fillers = self.multiworld.random.choices(
                list(filler_weights),
                weights=list(filler_weights.values()),
                k=amount_needed,
            )
            pool_names.extend(fillers)

        pool = [self.create_item(name) for name in pool_names]
        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        set_rule(
            self.multiworld.get_entrance("Portal to Exultia", self.player),
            lambda state: state.has("Heavy Cannon", self.player),
        )

        set_rule(
            self.multiworld.get_entrance("Portal to Cultist Base", self.player),
            lambda state: self.has_sentinel_battery_currency(state, self.player, 1),
        )

        set_rule(
            self.multiworld.get_entrance("Continue to Final Sin", self.player),
            lambda state: state.has("Blood Punch", self.player),
        )

        active_location_names = {
            location.name for location in self.multiworld.get_locations(self.player)
        }
        prerequisite_table = build_location_prerequisites(active_location_names)
        validate_location_prerequisites(prerequisite_table, active_location_names, set(item_data_table))
        validate_external_vanilla_prerequisites(
            EXTERNAL_VANILLA_PREREQUISITES,
            prerequisite_table,
            active_location_names,
            set(item_data_table),
            {item.name for item in self.multiworld.get_items() if item.player == self.player},
        )
        for location_name, requirement in prerequisite_table.items():
            location = self.multiworld.get_location(location_name, self.player)
            set_rule(
                location,
                partial(requirement_satisfied, requirement, player=self.player),
            )
            for item_name in required_item_names(requirement):
                forbid_item(location, item_name, self.player)
            if requirement.battery_currency:
                forbid_item(location, "Sentinel Battery", self.player)
                forbid_item(location, "Sentinel Battery Bundle", self.player)

        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
