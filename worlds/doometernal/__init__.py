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
            
        # Create connections between regions (Entrances)
        menu = self.multiworld.get_region("Menu", self.player)
        fortress = self.multiworld.get_region("Fortress of Doom", self.player)
        hell_on_earth = self.multiworld.get_region("Hell on Earth", self.player)
        exultia = self.multiworld.get_region("Exultia", self.player)
        
        menu.connect(fortress)
        fortress.connect(hell_on_earth)
        
        # We explicitly name this entrance so we can easily fetch it in set_rules
        entrance_to_exultia = Entrance(self.player, "Portal to Exultia", hell_on_earth)
        hell_on_earth.exits.append(entrance_to_exultia)
        entrance_to_exultia.connect(exultia)

    def create_items(self) -> None:
        # For now, just generate the items exactly matching the locations count
        pool = []
        for item_name in self.item_name_to_id.keys():
            if len(pool) < len(self.location_name_to_id):
                pool.append(self.create_item(item_name))
        
        # Fill the rest with some useful filler to avoid generation errors
        while len(pool) < len(self.location_name_to_id):
            pool.append(self.create_item("Progressive Sentinel Hammer Upgrade"))
            
        self.multiworld.itempool += pool
        
    def set_rules(self) -> None:
        set_rule(self.multiworld.get_location("Exultia - Slayer Key", self.player),
                 lambda state: state.has("Dash", self.player))

        set_rule(self.multiworld.get_entrance("Portal to Exultia", self.player),
                 lambda state: state.has("Combat Shotgun", self.player))
        
        # Test end goal so there is any at all. Will be adding actual options later (such as actually beating the game)
        self.multiworld.completion_condition[self.player] = lambda state: state.has("BFG-9000", self.player)
