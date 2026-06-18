from BaseClasses import Item, ItemClassification
from typing import Dict, NamedTuple, Optional

class DoomEternalItem(Item):
    game: str = "Doom Eternal"

class ItemData(NamedTuple):
    code: Optional[int]
    classification: ItemClassification

ITEM_ID_BASE = 7770000

item_data_table: Dict[str, ItemData] = {
    # Progression Items (Weapons & Equipment)
    "Heavy Cannon": ItemData(7770000, ItemClassification.progression),
    "Plasma Rifle": ItemData(7770001, ItemClassification.progression),
    "Rocket Launcher": ItemData(7770002, ItemClassification.progression),
    "Super Shotgun": ItemData(7770003, ItemClassification.progression),
    "Ballista": ItemData(7770004, ItemClassification.progression),
    "Chaingun": ItemData(7770005, ItemClassification.progression),
    "BFG-9000": ItemData(7770006, ItemClassification.progression),
    "The Crucible": ItemData(7770007, ItemClassification.progression),
    "The Unmaykr": ItemData(7770008, ItemClassification.progression),
    "Sentinel Hammer": ItemData(7770009, ItemClassification.progression),
    "Chainsaw": ItemData(7770010, ItemClassification.progression),
    "Frag Grenade": ItemData(7770011, ItemClassification.progression),
    "Flame Belch": ItemData(7770012, ItemClassification.progression),
    "Ice Bomb": ItemData(7770013, ItemClassification.progression),
    "Blood Punch": ItemData(7770014, ItemClassification.progression),
    "Dash": ItemData(7770015, ItemClassification.progression),
    "Sentinel Battery": ItemData(7770016, ItemClassification.progression),
    "Sentinel Crystal": ItemData(7770017, ItemClassification.progression),
    "Empyrean Key": ItemData(7770018, ItemClassification.progression),
    "Sticky Bombs": ItemData(7770058, ItemClassification.progression),
    "Full Auto": ItemData(7770059, ItemClassification.progression),
    "Precision Bolt": ItemData(7770060, ItemClassification.progression),
    "Micro Missiles": ItemData(7770061, ItemClassification.progression),

    # Useful Items
    "Weapon Mastery Coin": ItemData(7770019, ItemClassification.useful),
    "Rune": ItemData(7770020, ItemClassification.useful),
    "Suit Point": ItemData(7770021, ItemClassification.useful),
    "Extra Life": ItemData(7770022, ItemClassification.useful),
    "Extra Life Pack": ItemData(7770023, ItemClassification.useful),
    "Ammo Refill": ItemData(7770024, ItemClassification.useful),
    "Full Heal": ItemData(7770025, ItemClassification.useful),
    "Full Armor": ItemData(7770026, ItemClassification.useful),
    "Fuel": ItemData(7770027, ItemClassification.useful),
    "BFG Ammo": ItemData(7770028, ItemClassification.useful),
    "Soulsphere": ItemData(7770029, ItemClassification.useful),
    "Berserk": ItemData(7770030, ItemClassification.useful),

    # Filler Items
    "Small Health": ItemData(7770031, ItemClassification.filler),
    "Large Health": ItemData(7770032, ItemClassification.filler),
    "Small Armor": ItemData(7770033, ItemClassification.filler),
    "Large Armor": ItemData(7770034, ItemClassification.filler),
    "Shotgun Ammo": ItemData(7770035, ItemClassification.filler),
    "Bullet Ammo": ItemData(7770036, ItemClassification.filler),
    "Cell Ammo": ItemData(7770037, ItemClassification.filler),
    "Rocket Ammo": ItemData(7770038, ItemClassification.filler),
    "Chainsaw Fuel": ItemData(7770039, ItemClassification.filler),
    "One Extra Life": ItemData(7770040, ItemClassification.filler),
    "Armor Shard": ItemData(7770041, ItemClassification.filler),
    "Ammo Cache": ItemData(7770042, ItemClassification.filler),

    # Traps
    "Imp Trap": ItemData(7770043, ItemClassification.trap),
    "Carcass Trap": ItemData(7770044, ItemClassification.trap),
    "Revenant Trap": ItemData(7770045, ItemClassification.trap),
    "Arachnotron Trap": ItemData(7770046, ItemClassification.trap),
    "Hell Knight Trap": ItemData(7770047, ItemClassification.trap),
    "Dread Knight Trap": ItemData(7770048, ItemClassification.trap),
    "Baron Trap": ItemData(7770049, ItemClassification.trap),
    "Tyrant Trap": ItemData(7770050, ItemClassification.trap),
    "Marauder Trap": ItemData(7770051, ItemClassification.trap),
    "Archvile Trap": ItemData(7770052, ItemClassification.trap),
    "Cueball Trap": ItemData(7770053, ItemClassification.trap),
    "Ammo Drain Trap": ItemData(7770054, ItemClassification.trap),
    "Fuel Drain Trap": ItemData(7770055, ItemClassification.trap),
    "BFG Drain Trap": ItemData(7770056, ItemClassification.trap),
    "Armor Drain Trap": ItemData(7770057, ItemClassification.trap),
}

item_name_to_id = {name: data.code for name, data in item_data_table.items()}
