from BaseClasses import Item, ItemClassification
from typing import Dict, NamedTuple, Optional

class DoomEternalItem(Item):
    game: str = "Doom Eternal"

class ItemData(NamedTuple):
    code: Optional[int]
    classification: ItemClassification

# Base ID for Doom Eternal items
ITEM_ID_BASE = 7770000

# Mapping of all item names to their data
item_data_table: Dict[str, ItemData] = {
    # Weapons & Mods (Progressive)
    "Combat Shotgun": ItemData(ITEM_ID_BASE + 1, ItemClassification.progression),
    "Progressive Sticky Bombs": ItemData(ITEM_ID_BASE + 2, ItemClassification.progression),
    "Progressive Full Auto": ItemData(ITEM_ID_BASE + 3, ItemClassification.progression),
    "Heavy Cannon": ItemData(ITEM_ID_BASE + 4, ItemClassification.progression),
    "Progressive Precision Bolt": ItemData(ITEM_ID_BASE + 5, ItemClassification.progression),
    "Progressive Micro Missiles": ItemData(ITEM_ID_BASE + 6, ItemClassification.progression),
    "Plasma Rifle": ItemData(ITEM_ID_BASE + 7, ItemClassification.progression),
    "Progressive Heat Blast": ItemData(ITEM_ID_BASE + 8, ItemClassification.progression),
    "Progressive Microwave Beam": ItemData(ITEM_ID_BASE + 9, ItemClassification.progression),
    "Rocket Launcher": ItemData(ITEM_ID_BASE + 10, ItemClassification.progression),
    "Progressive Remote Detonation": ItemData(ITEM_ID_BASE + 11, ItemClassification.progression),
    "Progressive Lock-On Burst": ItemData(ITEM_ID_BASE + 12, ItemClassification.progression),
    "Super Shotgun": ItemData(ITEM_ID_BASE + 13, ItemClassification.progression),
    "Progressive Super Shotgun Upgrades": ItemData(ITEM_ID_BASE + 14, ItemClassification.progression),
    "Ballista": ItemData(ITEM_ID_BASE + 15, ItemClassification.progression),
    "Progressive Arbalest": ItemData(ITEM_ID_BASE + 16, ItemClassification.progression),
    "Progressive Destroyer Blade": ItemData(ITEM_ID_BASE + 17, ItemClassification.progression),
    "Chaingun": ItemData(ITEM_ID_BASE + 18, ItemClassification.progression),
    "Progressive Mobile Turret": ItemData(ITEM_ID_BASE + 19, ItemClassification.progression),
    "Progressive Energy Shield": ItemData(ITEM_ID_BASE + 20, ItemClassification.progression),
    
    # Base Equipment
    "Chainsaw": ItemData(ITEM_ID_BASE + 21, ItemClassification.progression),
    "Frag Grenade": ItemData(ITEM_ID_BASE + 22, ItemClassification.progression),
    "Flame Belch": ItemData(ITEM_ID_BASE + 23, ItemClassification.progression),
    "Blood Punch": ItemData(ITEM_ID_BASE + 24, ItemClassification.progression),
    "Ice Bomb": ItemData(ITEM_ID_BASE + 25, ItemClassification.progression),
    "BFG-9000": ItemData(ITEM_ID_BASE + 26, ItemClassification.progression),
    "The Crucible": ItemData(ITEM_ID_BASE + 27, ItemClassification.progression),
    "The Unmaykr": ItemData(ITEM_ID_BASE + 28, ItemClassification.progression),
    "Sentinel Hammer": ItemData(ITEM_ID_BASE + 29, ItemClassification.progression),

    # Abilities / Upgrades
    "Dash": ItemData(ITEM_ID_BASE + 30, ItemClassification.progression),
    "Progressive Blood Punch Upgrade": ItemData(ITEM_ID_BASE + 31, ItemClassification.useful),
    "Progressive Sentinel Hammer Upgrade": ItemData(ITEM_ID_BASE + 32, ItemClassification.useful),

    # NOTE: More items will be appended here automatically later as part of repetitive tasks.
}

item_name_to_id = {name: data.code for name, data in item_data_table.items() if data.code is not None}
