from typing import NamedTuple

from BaseClasses import Item, ItemClassification

from .identity import GAME_NAME


class DoomEternalItem(Item):
    game: str = GAME_NAME


class ItemData(NamedTuple):
    code: int | None
    classification: ItemClassification
    world_pool_weapon: bool = False
    starting_weapon: bool = False


ITEM_ID_BASE = 7770000

# Audited from local base-campaign maps/DECLs.  The short route deliberately
# uses only its own fixed quantity; later-map currency remains reserved.
BASE_CAMPAIGN_MAX_SENTINEL_BATTERIES = 28
BASE_CAMPAIGN_SENTINEL_BATTERIES = 28
BASE_CAMPAIGN_SENTINEL_BATTERY_BUNDLES = 13
BASE_CAMPAIGN_SENTINEL_BATTERY_SINGLES = 2
SENTINEL_BATTERY_BUNDLE_VALUE = 2

# Reserved IDs stay unavailable to current item definitions.  7770019 and
# 7770057 belong to location records; 7770105 and 7770119..7770121 are unused.
RESERVED_ITEM_IDS = frozenset({7770019, 7770057, 7770105, 7770119, 7770120, 7770121})
RESERVED_LOCATION_IDS = frozenset({7770055, 7770068})

PROGRESSIVE_SPECIAL_WEAPON_ID = 7770901
PROGRESSIVE_SENTINEL_HAMMER_ID = 7770902
SPECIAL_WEAPON_ITEM_NAMES = frozenset({
    "Progressive Special Weapon",
    "Progressive Sentinel Hammer",
    "The Crucible",
})
SPECIAL_WEAPON_POOL_COUNTS = {
    "Progressive Special Weapon": 3,
    "Progressive Sentinel Hammer": 2,
    "The Crucible": 1,
}

item_data_table: dict[str, ItemData] = {
    # Progression Items (Weapons & Equipment)
    "Heavy Cannon": ItemData(7770000, ItemClassification.progression, True, True),
    "Plasma Rifle": ItemData(7770001, ItemClassification.progression, True, True),
    "Rocket Launcher": ItemData(7770002, ItemClassification.progression, True, True),
    "Super Shotgun": ItemData(7770003, ItemClassification.progression, True, True),
    "Ballista": ItemData(7770004, ItemClassification.progression, True, True),
    "Chaingun": ItemData(7770005, ItemClassification.progression, True, True),
    "BFG-9000": ItemData(7770006, ItemClassification.progression, True),
    "The Crucible": ItemData(7770007, ItemClassification.progression),
    "Combat Shotgun": ItemData(7770900, ItemClassification.progression, True, True),
    "The Unmaykr": ItemData(7770008, ItemClassification.progression),
    "Sentinel Hammer": ItemData(7770009, ItemClassification.progression),
    "Progressive Special Weapon": ItemData(PROGRESSIVE_SPECIAL_WEAPON_ID, ItemClassification.progression),
    "Progressive Sentinel Hammer": ItemData(PROGRESSIVE_SENTINEL_HAMMER_ID, ItemClassification.progression),
    "Chainsaw": ItemData(7770010, ItemClassification.progression),
    "Frag Grenade": ItemData(7770011, ItemClassification.progression),
    "Flame Belch": ItemData(7770012, ItemClassification.progression),
    "Ice Bomb": ItemData(7770013, ItemClassification.progression),
    "Blood Punch": ItemData(7770014, ItemClassification.progression),
    "Dash": ItemData(7770015, ItemClassification.progression),
    "Sentinel Battery": ItemData(7770016, ItemClassification.progression),
    "Sentinel Battery Bundle": ItemData(7770142, ItemClassification.progression),
    "Progressive Health Upgrade": ItemData(7770017, ItemClassification.useful),
    "Progressive Armor Upgrade": ItemData(7770088, ItemClassification.useful),
    "Progressive Ammo Upgrade": ItemData(7770092, ItemClassification.useful),
    "Empyrean Key": ItemData(7770018, ItemClassification.progression),
    "Sticky Bombs": ItemData(7770058, ItemClassification.progression),
    "Full Auto": ItemData(7770059, ItemClassification.progression),
    "Precision Bolt": ItemData(7770060, ItemClassification.progression),
    "Micro Missiles": ItemData(7770061, ItemClassification.progression),
    "Heat Blast": ItemData(7770062, ItemClassification.progression),
    "Heat Blast Mastery": ItemData(7770063, ItemClassification.useful),
    "Microwave Beam": ItemData(7770064, ItemClassification.progression),
    "Microwave Beam Mastery": ItemData(7770065, ItemClassification.useful),
    "Precision Bolt Mastery": ItemData(7770067, ItemClassification.useful),
    "Micro Missiles Mastery": ItemData(7770068, ItemClassification.useful),
    "Full Auto Mastery": ItemData(7770069, ItemClassification.useful),
    "Sticky Bombs Mastery": ItemData(7770070, ItemClassification.useful),
    "Remote Detonate": ItemData(7770071, ItemClassification.progression),
    "Remote Detonate Mastery": ItemData(7770072, ItemClassification.useful),
    "Lock-on Burst": ItemData(7770073, ItemClassification.progression),
    "Lock-on Burst Mastery": ItemData(7770074, ItemClassification.useful),
    "Arbalest": ItemData(7770075, ItemClassification.progression),
    "Arbalest Mastery": ItemData(7770076, ItemClassification.useful),
    "Destroyer Blade": ItemData(7770077, ItemClassification.progression),
    "Destroyer Blade Mastery": ItemData(7770078, ItemClassification.useful),
    "Energy Shield": ItemData(7770079, ItemClassification.progression),
    "Energy Shield Mastery": ItemData(7770080, ItemClassification.useful),
    "Mobile Turret": ItemData(7770081, ItemClassification.progression),
    "Mobile Turret Mastery": ItemData(7770082, ItemClassification.useful),
    "Meat Hook": ItemData(7770083, ItemClassification.progression),
    "Meat Hook Mastery": ItemData(7770084, ItemClassification.useful),
    "Savagery": ItemData(7770085, ItemClassification.useful),
    "Seek and Destroy": ItemData(7770086, ItemClassification.useful),
    "Blood Fueled": ItemData(7770087, ItemClassification.useful),
    "Air Control": ItemData(7770089, ItemClassification.useful),
    "Dazed and Confused": ItemData(7770090, ItemClassification.useful),
    "Saving Throw": ItemData(7770091, ItemClassification.useful),
    "Chrono Strike": ItemData(7770093, ItemClassification.useful),
    "Equipment Fiend": ItemData(7770094, ItemClassification.useful),
    "Punch and Reave": ItemData(7770095, ItemClassification.useful),
    "Faster Ledge Grab": ItemData(7770097, ItemClassification.useful),
    "Faster Weapon Swap": ItemData(7770098, ItemClassification.useful),
    "Faster Dash Recharge": ItemData(7770099, ItemClassification.useful),
    "Dash Refill on Glory Kill": ItemData(7770100, ItemClassification.useful),
    "Reveal Automap Stations": ItemData(7770101, ItemClassification.useful),
    "Reveal Automap Progression Items": ItemData(7770102, ItemClassification.useful),
    "Larger Automap Reveal": ItemData(7770103, ItemClassification.useful),
    "Reveal Dossier Progression Items": ItemData(7770104, ItemClassification.useful),
    "Reduced Hazard Damage": ItemData(7770106, ItemClassification.useful),
    "Reduced Self Damage": ItemData(7770107, ItemClassification.useful),
    "Respawning Barrels": ItemData(7770108, ItemClassification.useful),
    "Ammo from Barrels": ItemData(7770109, ItemClassification.useful),
    "Powerup Extender": ItemData(7770110, ItemClassification.useful),
    "Frag Grenade Cooldown": ItemData(7770111, ItemClassification.useful),
    "Frag Grenade Concussive Blast": ItemData(7770112, ItemClassification.useful),
    "Frag Grenade Cluster Bombs": ItemData(7770113, ItemClassification.useful),
    "Second Frag Grenade": ItemData(7770114, ItemClassification.useful),
    "Ice Bomb Cooldown": ItemData(7770115, ItemClassification.useful),
    "Extended Ice Bomb Duration": ItemData(7770116, ItemClassification.useful),
    "Health from Frozen Demons": ItemData(7770117, ItemClassification.useful),
    "Frozen Melee Shatter": ItemData(7770118, ItemClassification.useful),
    "Rune": ItemData(7770020, ItemClassification.useful),
    "Suit Point": ItemData(7770021, ItemClassification.useful),
    # Filler Items
    "Extra Life": ItemData(7770022, ItemClassification.useful),
    "Extra Life Pack": ItemData(7770023, ItemClassification.useful),
    "Ammo Refill": ItemData(7770024, ItemClassification.useful),
    "Full Heal": ItemData(7770025, ItemClassification.filler),
    "Full Armor": ItemData(7770026, ItemClassification.filler),
    "Fuel": ItemData(7770027, ItemClassification.filler),
    "BFG Ammo": ItemData(7770028, ItemClassification.filler),
    "Soulsphere": ItemData(7770029, ItemClassification.filler),
    "Berserk": ItemData(7770030, ItemClassification.filler),
    "Small Health": ItemData(7770031, ItemClassification.filler),
    "Large Health": ItemData(7770032, ItemClassification.filler),
    "Small Armor": ItemData(7770033, ItemClassification.filler),
    "Large Armor": ItemData(7770034, ItemClassification.filler),
    "Shotgun Ammo": ItemData(7770035, ItemClassification.filler),
    "Bullet Ammo": ItemData(7770036, ItemClassification.filler),
    "Cell Ammo": ItemData(7770037, ItemClassification.filler),
    "Rocket Ammo": ItemData(7770038, ItemClassification.filler),
    "Chainsaw Fuel": ItemData(7770039, ItemClassification.filler),
    "One Extra Life": ItemData(7770040, ItemClassification.useful),
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
    # Locked to the runtime mission-completion check; it has no in-game command.
    "Victory": ItemData(7770096, ItemClassification.progression),
}

item_name_to_id = {name: data.code for name, data in item_data_table.items() if data.code is not None}

SAFE_TRAP_NAMES = frozenset({
    "Imp Trap",
    "Carcass Trap",
    "Revenant Trap",
    "Arachnotron Trap",
    "Hell Knight Trap",
    "Dread Knight Trap",
    "Baron Trap",
    "Tyrant Trap",
    "Marauder Trap",
    "Archvile Trap",
    "Cueball Trap",
    "Ammo Drain Trap",
    "Fuel Drain Trap",
    "BFG Drain Trap",
})

world_pool_weapon_item_names = tuple(
    name for name, data in item_data_table.items() if data.world_pool_weapon and name not in SPECIAL_WEAPON_ITEM_NAMES
)
starting_weapon_item_names = tuple(
    name for name, data in item_data_table.items() if data.starting_weapon
)

PRAETOR_SUIT_UPGRADE_ID_RANGE = range(7770097, 7770122)
suit_perk_item_names = [
    name
    for name, data in item_data_table.items()
    if data.code in PRAETOR_SUIT_UPGRADE_ID_RANGE and data.code not in RESERVED_ITEM_IDS
]

DEVINV_START_INVENTORY_ITEM_NAMES = frozenset({
    "Heavy Cannon", "Plasma Rifle", "Rocket Launcher", "Super Shotgun", "Ballista", "Chaingun", "Combat Shotgun",
    "Chainsaw", "Frag Grenade", "Blood Punch", "Flame Belch", "Ice Bomb", "Dash",
    "Sticky Bombs", "Full Auto", "Precision Bolt", "Micro Missiles", "Heat Blast", "Microwave Beam",
    "Remote Detonate", "Lock-on Burst", "Arbalest", "Destroyer Blade", "Energy Shield", "Mobile Turret",
    "Savagery", "Seek and Destroy", "Blood Fueled", "Air Control", "Dazed and Confused", "Saving Throw",
    "Chrono Strike", "Equipment Fiend", "Punch and Reave", "Sticky Bombs Mastery", "Full Auto Mastery",
    "Micro Missiles Mastery", "Heat Blast Mastery", "Microwave Beam Mastery", "Lock-on Burst Mastery",
    "Arbalest Mastery", "Energy Shield Mastery", "Mobile Turret Mastery", "Precision Bolt Mastery",
    "Remote Detonate Mastery", "Destroyer Blade Mastery", "Meat Hook", "Meat Hook Mastery",
    "Progressive Health Upgrade", "Progressive Armor Upgrade", "Progressive Ammo Upgrade",
    "Faster Ledge Grab", "Faster Weapon Swap", "Faster Dash Recharge", "Dash Refill on Glory Kill",
    "Reveal Automap Stations", "Reveal Automap Progression Items", "Larger Automap Reveal",
    "Reveal Dossier Progression Items", "Reduced Hazard Damage", "Reduced Self Damage", "Respawning Barrels",
    "Ammo from Barrels", "Powerup Extender", "Frag Grenade Cooldown", "Frag Grenade Concussive Blast",
    "Frag Grenade Cluster Bombs", "Second Frag Grenade", "Ice Bomb Cooldown", "Extended Ice Bomb Duration",
    "Health from Frozen Demons", "Frozen Melee Shatter", "Sentinel Battery", "Sentinel Battery Bundle",
    "The Crucible", "Progressive Special Weapon", "Progressive Sentinel Hammer", "Ammo Refill",
})

DEVINV_NON_PERSISTENT_USEFUL_ITEM_NAMES = frozenset({
    "Extra Life", "Extra Life Pack", "One Extra Life",
})

# Canonical eligibility for the parent Dossier > Suit page. Crystal
# progressives are displayed there; Frag and Ice have vanilla Suit-family
# preReqStats. Flame Belch is not part of that Suit group, so its base item is
# deliberately not a page unlocker.
SUIT_PAGE_UNLOCKING_ITEM_NAMES = frozenset(
    {
        "Progressive Health Upgrade",
        "Progressive Armor Upgrade",
        "Progressive Ammo Upgrade",
        "Frag Grenade",
        "Ice Bomb",
        *suit_perk_item_names,
    }
)
SUIT_PAGE_UNLOCKING_ITEM_IDS = frozenset(item_data_table[name].code for name in SUIT_PAGE_UNLOCKING_ITEM_NAMES)
