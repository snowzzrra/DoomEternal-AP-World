from typing import ClassVar
import settings
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import set_rule
from worlds.LauncherComponents import (
    Component,
    Type,
    components,
    launch as launch_component,
)
from BaseClasses import Region, Entrance, Item
from .options import DoomEternalOptions
from .items import (
    CURRENT_ROUTE_SENTINEL_BATTERIES,
    CURRENT_ROUTE_WEAPON_MASTERY_TOKENS,
    item_data_table,
    item_name_to_id,
    suit_perk_item_names,
    DoomEternalItem,
)
from .locations import location_data_table, location_name_to_id, DoomEternalLocation
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
    )
)


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

        # Actual pre-alpha campaign order:
        # E1M1 -> Hub (Flame Belch) -> E1M2 -> Hub (Ice Bomb, Suit Point,
        # Ripatorium) -> E1M3.
        menu.connect(hell_on_earth)

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
            *(["Weapon Mastery Token"] * CURRENT_ROUTE_WEAPON_MASTERY_TOKENS),
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

        if self.options.randomize_first_battery:
            pool_names.extend(["Sentinel Battery"] * CURRENT_ROUTE_SENTINEL_BATTERIES)
        else:
            self.multiworld.get_location(
                "Exultia - Sentinel Battery", self.player
            ).place_locked_item(self.create_item("Sentinel Battery"))
            pool_names.extend(["Sentinel Battery"] * (CURRENT_ROUTE_SENTINEL_BATTERIES - 1))

        self.multiworld.get_location(
            "Cultist Base - Mission Complete", self.player
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
            "Armor Drain Trap": 2,
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
            lambda state: state.has("Sentinel Battery", self.player),
        )

        set_rule(
            self.multiworld.get_location("Fortress of Doom - Sentinel Crystal 2", self.player),
            lambda state: state.has("Sentinel Battery", self.player, 3),
        )
        set_rule(
            self.multiworld.get_location("Fortress of Doom - Sentinel Crystal 3", self.player),
            lambda state: state.has("Sentinel Battery", self.player, 5),
        )

        self.multiworld.completion_condition[self.player] = (
            lambda state: state.has("Victory", self.player)
        )
