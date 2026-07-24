from typing import ClassVar

import settings
from BaseClasses import Entrance, Region
from worlds.AutoWorld import WebWorld, World
from worlds.generic.Rules import forbid_item, set_rule
from worlds.LauncherComponents import (
    Component,
    Type,
    components,
    icon_paths,
)
from worlds.LauncherComponents import (
    launch as launch_component,
)

from .items import (
    BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES,
    BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES,
    SENTINEL_BATTERY_BUNDLE_VALUE,
    DoomEternalItem,
    item_data_table,
    item_name_to_id,
    suit_perk_item_names,
)
from .locations import DoomEternalLocation, location_data_table, location_name_to_id
from .logic import (
    EXTERNAL_VANILLA_PREREQUISITES,
    build_location_prerequisites,
    requirement_satisfied,
    validate_external_vanilla_prerequisites,
    validate_location_prerequisites,
)
from .options import DoomEternalOptions
from .regions import regions


def launch_client(*args: str):
    from .Client import launch
    launch_component(launch, name="DoomEternalClient", args=args)


components.append(
    Component(
        "DOOM Eternal Client",
        game_name="Doom Eternal",
        func=launch_client,
        component_type=Type.CLIENT,
        icon="doom_eternal",
    )
)
icon_paths["doom_eternal"] = f"ap:{__name__}/doom_logo.png"


class DoomEternalSettings(settings.Group):
    class ClientDirectory(settings.UserFolderPath):
        """Folder containing bridge_client.py and the native helper files."""

        description = "DOOM Eternal Mod Folder (containing bridge_client.py)"

    client_directory: ClientDirectory = ClientDirectory(
        "~/DoomEternalArchipelago/client"
    )


class DoomEternalWeb(WebWorld):
    theme = "dirt"

class DoomEternalWorld(World):
    """
    Rip and tear, until it is done.
    Doom Eternal Randomizer for Archipelago.
    """
    game: str = "Doom Eternal"
    web = DoomEternalWeb()
    options_dataclass = DoomEternalOptions
    options: DoomEternalOptions
    settings: ClassVar[DoomEternalSettings]
    required_client_version = (0, 6, 7)

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    def create_item(self, name: str) -> DoomEternalItem:
        item_data = item_data_table[name]
        return DoomEternalItem(name, item_data.classification, item_data.code, self.player)

    @staticmethod
    def has_sentinel_battery_currency(state, player: int, amount: int) -> bool:
        return (
            state.count("Sentinel Battery", player)
            + SENTINEL_BATTERY_BUNDLE_VALUE
            * state.count("Sentinel Battery Bundle", player)
        ) >= amount

    def fill_slot_data(self) -> dict:
        return {
            "death_link": bool(self.options.death_link.value),
        }

    # Suffice to say this isn't even close to being complete, but it's a start. I'll be adding more locations, items, and rules as I continue development.
    def create_regions(self) -> None:
        # Create regions
        for region_name in regions:
            region = Region(region_name, self.player, self.multiworld)
            self.multiworld.regions.append(region)

        # Place locations in their respective regions
        for loc_name, loc_data in location_data_table.items():
            region = self.multiworld.get_region(loc_data.region, self.player)
            location = DoomEternalLocation(self.player, loc_name, loc_data.code, region)
            region.locations.append(location)

        # connections test
        menu = self.multiworld.get_region("Menu", self.player)
        hell_on_earth = self.multiworld.get_region("Hell on Earth", self.player)
        fortress_first_visit = self.multiworld.get_region("Fortress of Doom - First Visit", self.player)
        exultia = self.multiworld.get_region("Exultia", self.player)
        fortress_second_visit = self.multiworld.get_region("Fortress of Doom - Second Visit", self.player)
        cultist_base = self.multiworld.get_region("Cultist Base", self.player)
        doom_hunter_base = self.multiworld.get_region("Doom Hunter Base", self.player)
        fortress_third_visit = self.multiworld.get_region("Fortress of Doom - Third Visit", self.player)
        super_gore_nest = self.multiworld.get_region("Super Gore Nest", self.player)
        weapon_masteries = self.multiworld.get_region("Weapon Masteries", self.player)

        # Actual pre-alpha campaign order:
        # E1M1 -> Hub (Flame Belch) -> E1M2 -> Hub (Ice Bomb, Suit Point,
        # Ripatorium) -> E1M3.
        menu.connect(hell_on_earth)
        menu.connect(weapon_masteries)

        entrance_to_first_hub = Entrance(self.player, "Return to Fortress after Hell on Earth", hell_on_earth)
        hell_on_earth.exits.append(entrance_to_first_hub)
        entrance_to_first_hub.connect(fortress_first_visit)

        entrance_to_exultia = Entrance(self.player, "Portal to Exultia", fortress_first_visit)
        fortress_first_visit.exits.append(entrance_to_exultia)
        entrance_to_exultia.connect(exultia)

        entrance_to_second_hub = Entrance(self.player, "Return to Fortress after Exultia", exultia)
        exultia.exits.append(entrance_to_second_hub)
        entrance_to_second_hub.connect(fortress_second_visit)

        entrance_to_cultist_base = Entrance(self.player, "Portal to Cultist Base", fortress_second_visit)
        fortress_second_visit.exits.append(entrance_to_cultist_base)
        entrance_to_cultist_base.connect(cultist_base)

        entrance_to_doom_hunter_base = Entrance(self.player, "Portal to Doom Hunter Base", cultist_base)
        cultist_base.exits.append(entrance_to_doom_hunter_base)
        entrance_to_doom_hunter_base.connect(doom_hunter_base)

        entrance_to_third_hub = Entrance(self.player, "Return to Fortress after Doom Hunter Base", doom_hunter_base)
        doom_hunter_base.exits.append(entrance_to_third_hub)
        entrance_to_third_hub.connect(fortress_third_visit)

        entrance_to_sgn = Entrance(self.player, "Portal to Super Gore Nest", fortress_third_visit)
        fortress_third_visit.exits.append(entrance_to_sgn)
        entrance_to_sgn.connect(super_gore_nest)


    def create_items(self) -> None:
        # Base progression items to seed into the world
        pool_names = [
            # Cultist Base still uses a vanilla scripted reward for the
            # Super Shotgun/Revenant sequence. Keep only that weapon and its
            # bundled Meat Hook out of the PTB pool for now; Rocket Launcher
            # remains in scope.
            "Heavy Cannon", "Plasma Rifle", "Rocket Launcher",
            "Ballista", "Chaingun",
            "Chainsaw", "Frag Grenade", "Blood Punch", "Flame Belch", "Ice Bomb",
            "Sticky Bombs", "Full Auto", "Precision Bolt", "Micro Missiles",
            "Heat Blast", "Microwave Beam", "Remote Detonate", "Lock-on Burst",
            "Arbalest", "Destroyer Blade", "Energy Shield", "Mobile Turret",
            "Savagery", "Seek and Destroy", "Blood Fueled", "Air Control",
            "Dazed and Confused", "Saving Throw", "Chrono Strike",
            "Equipment Fiend", "Punch and Reave",
            "Sticky Bombs Mastery", "Full Auto Mastery", "Micro Missiles Mastery",
            "Heat Blast Mastery", "Microwave Beam Mastery", "Lock-on Burst Mastery",
            "Arbalest Mastery", "Energy Shield Mastery", "Mobile Turret Mastery",
            "Precision Bolt Mastery", "Remote Detonate Mastery",
            "Destroyer Blade Mastery", "Meat Hook Mastery",
            *(["Progressive Health Upgrade"] * 4),
            *(["Progressive Armor Upgrade"] * 4),
            *(["Progressive Ammo Upgrade"] * 4),
        ]
        pool_names.extend(self.multiworld.random.sample(suit_perk_item_names, 6))

        if not self.options.randomize_chainsaw:
            self.multiworld.get_location(
                "Hell on Earth - Chainsaw", self.player
            ).place_locked_item(self.create_item("Chainsaw"))
            pool_names.remove("Chainsaw")

        if self.options.randomize_dash:
            pool_names.append("Dash")
        else:
            self.multiworld.get_location(
                "Exultia - Dash", self.player
            ).place_locked_item(self.create_item("Dash"))

        randomized_battery_singles = BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES
        if self.options.randomize_first_battery:
            pool_names.extend(["Sentinel Battery"] * randomized_battery_singles)
        else:
            # The physical Exultia Battery remains an AP location in both
            # modes.  The default keeps its required first Battery locked to
            # that pickup; enabling the option leaves the location randomized.
            self.multiworld.get_location(
                "Exultia - Sentinel Battery", self.player
            ).place_locked_item(self.create_item("Sentinel Battery"))
            pool_names.extend(
                ["Sentinel Battery"] * (randomized_battery_singles - 1)
            )
        pool_names.extend(
            ["Sentinel Battery Bundle"] * BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES
        )

        self.multiworld.get_location(
            "Fortress of Doom - Super Gore Nest Transition", self.player
        ).place_locked_item(self.create_item("Victory"))

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

        prerequisite_table = build_location_prerequisites(set(location_data_table))
        validate_location_prerequisites(
            prerequisite_table, set(location_data_table), set(item_data_table)
        )
        validate_external_vanilla_prerequisites(
            EXTERNAL_VANILLA_PREREQUISITES,
            prerequisite_table,
            set(location_data_table),
            set(item_data_table),
            {
                item.name for item in self.multiworld.get_items()
                if item.player == self.player
            },
        )
        for location_name, requirement in prerequisite_table.items():
            location = self.multiworld.get_location(location_name, self.player)
            set_rule(
                location,
                lambda state, requirement=requirement: requirement_satisfied(
                    requirement, state, self.player
                ),
            )
            for item_name in requirement.all_of:
                forbid_item(location, item_name, self.player)
            if requirement.battery_currency:
                forbid_item(location, "Sentinel Battery", self.player)
                forbid_item(location, "Sentinel Battery Bundle", self.player)

        self.multiworld.completion_condition[self.player] = (
            lambda state: state.has("Victory", self.player)
        )
