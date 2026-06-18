from typing import ClassVar
from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import set_rule
from BaseClasses import Region, Entrance, Item
from .options import DoomEternalOptions
from .items import item_data_table, item_name_to_id, DoomEternalItem
from .locations import location_data_table, location_name_to_id, DoomEternalLocation
from .regions import regions

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

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    def create_item(self, name: str) -> DoomEternalItem:
        item_data = item_data_table[name]
        return DoomEternalItem(name, item_data.classification, item_data.code, self.player)

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
        fortress = self.multiworld.get_region("Fortress of Doom", self.player)
        hell_on_earth = self.multiworld.get_region("Hell on Earth", self.player)
        exultia = self.multiworld.get_region("Exultia", self.player)
        
        menu.connect(fortress)
        fortress.connect(hell_on_earth)
        
        entrance_to_exultia = Entrance(self.player, "Portal to Exultia", hell_on_earth)
        hell_on_earth.exits.append(entrance_to_exultia)
        entrance_to_exultia.connect(exultia)

    def create_items(self) -> None:
        # For our E1M1 prototype, we explicitly generate a balanced pool of 23 items
        # to fill the 23 mapped locations (20 in E1M1 + 3 in Exultia).
        
        # 9 Progression Items
        pool_names = [
            "Heavy Cannon", "Chainsaw", "Frag Grenade", 
            "Dash", "Large Health", "Flame Belch",
            "Sticky Bombs", "Full Auto", "Precision Bolt", "Micro Missiles",
            
            # 5 Useful
            "Extra Life", "Extra Life Pack", "Soulsphere", 
            "Berserk", "Weapon Mastery Coin",
            
            # 5 Filler
            "Large Health", "Large Armor",
            "Ammo Refill", "Fuel", "BFG Ammo",
            
            # 3 Traps
            "Imp Trap", "Hell Knight Trap", "Marauder Trap"
        ]
        
        pool = [self.create_item(name) for name in pool_names]
        self.multiworld.itempool += pool
        
    def set_rules(self) -> None:


        set_rule(self.multiworld.get_entrance("Portal to Exultia", self.player),
                 lambda state: state.has("Heavy Cannon", self.player))
        
        # placeholder condition
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Dash", self.player)
