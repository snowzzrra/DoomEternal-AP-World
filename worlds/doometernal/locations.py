from BaseClasses import Location
from typing import Dict, NamedTuple, Optional

class DoomEternalLocation(Location):
    game: str = "Doom Eternal"

class LocationData(NamedTuple):
    code: Optional[int]
    region: str

# Base ID for Doom Eternal locations, wanted to do 6660000 but I think that one was used for something else in the past (DOOM 1, DOOM 2), so I went with 7770000 instead. Should be plenty of room for all the locations we need to add.
LOCATION_ID_BASE = 7770000

# Special thanks to TastyFresh from the AP After Dark Discord for helping compile this list of locations.
location_data_table: Dict[str, LocationData] = {
    "Hell on Earth - Chainsaw": LocationData(7770001, "Hell on Earth"),
    "Hell on Earth - Heavy Cannon": LocationData(7770002, "Hell on Earth"),
    "Hell on Earth - Frag Grenade": LocationData(7770003, "Hell on Earth"),
    "Hell on Earth - Extra Life - Street Arena Behind Bars": LocationData(7770004, "Hell on Earth"),
    "Hell on Earth - Extra Life - Shopping Center Elevator": LocationData(7770005, "Hell on Earth"),
    "Hell on Earth - Extra Life - Street Arena Behind Breakable Wall": LocationData(7770006, "Hell on Earth"),
    "Hell on Earth - Extra Life - Cliffside in Last Arena": LocationData(7770007, "Hell on Earth"),
    "Hell on Earth - Hell Barges Codex": LocationData(7770008, "Hell on Earth"),
    "Hell on Earth - Remaining Human Populations Part 1 Codex": LocationData(7770009, "Hell on Earth"),
    "Hell on Earth - Remaining Human Populations Part 2 Codex": LocationData(7770010, "Hell on Earth"),
    "Hell on Earth - Formation of the ARC Codex": LocationData(7770011, "Hell on Earth"),
    "Hell on Earth - Hell Priests Codex": LocationData(7770012, "Hell on Earth"),
    "Hell on Earth - Deag Nilox Codex": LocationData(7770013, "Hell on Earth"),
    "Hell on Earth - Modbot 1": LocationData(7770014, "Hell on Earth"),
    "Hell on Earth - Modbot 2": LocationData(7770015, "Hell on Earth"),
    "Hell on Earth - Modbot 3": LocationData(7770016, "Hell on Earth"),
    "Hell on Earth - Zombie Toy": LocationData(7770017, "Hell on Earth"),
    "Hell on Earth - Doom Slayer Toy": LocationData(7770018, "Hell on Earth"),
    "Hell on Earth - Imp Toy": LocationData(7770019, "Hell on Earth"),
    "Hell on Earth - Infinite Extra Lives Cheat": LocationData(7770020, "Hell on Earth"),

    # left some for exultia here, and deleted all of the rest, but i will place them back here soon
    "Exultia - Blood Punch": LocationData(7770021, "Exultia"),
    "Exultia - Dash": LocationData(7770083, "Exultia"),
    "Exultia - Sentinel Battery": LocationData(7770084, "Exultia"),
    "Exultia - Slayer Gate Key": LocationData(7770045, "Exultia"),
    "Exultia - Extra Life - Behind King Novik's Throne": LocationData(7770023, "Exultia"),
    "Exultia - Extra Life - Inside Electric Trap": LocationData(7770024, "Exultia"),
    "Exultia - Extra Life - After Dash": LocationData(7770025, "Exultia"),
    "Exultia - Extra Life - Under Level Start": LocationData(7770026, "Exultia"),
    "Exultia - Extra Life - Close to First Rune": LocationData(7770027, "Exultia"),
    "Exultia - Extra Life - Under Floating Platform": LocationData(7770028, "Exultia"),
    "Exultia - Extra Life - Floating in Goo Room": LocationData(7770029, "Exultia"),
    "Exultia - At Doom's Gate Vinyl Record": LocationData(7770030, "Exultia"),
    "Exultia - Arachnotron Toy": LocationData(7770031, "Exultia"),
    "Exultia - Cacodemon Toy": LocationData(7770032, "Exultia"),
    "Exultia - Hidden Plasma Rifle": LocationData(7770034, "Exultia"),
    "Exultia - Sentinel Crystal 1": LocationData(7770035, "Exultia"),
    "Exultia - Exultia Codex Entry": LocationData(7770036, "Exultia"),
    "Exultia - The Wolf Codex Entry": LocationData(7770037, "Exultia"),
    "Exultia - History of the Sentinels Part One Codex Entry": LocationData(7770038, "Exultia"),
    "Exultia - King Novik Codex Entry": LocationData(7770039, "Exultia"),
    "Exultia - History of the Sentinels Part Two Codex Entry": LocationData(7770040, "Exultia"),
    "Exultia - History of the Sentinels Part Three Codex Entry": LocationData(7770041, "Exultia"),
    "Exultia - The Betrayer Codex Entry": LocationData(7770042, "Exultia"),
    "Exultia - Weapon Modbot 1": LocationData(7770043, "Exultia"),
    "Exultia - Rune 1": LocationData(7770044, "Exultia"),

    # Fortress of Doom
    # The campaign visits the same physical Hub twice during the pre-alpha.
    # Keep only the known mandatory first-visit pickup here. Everything else is
    # conservatively considered second-visit content until room access is mapped.
    "Fortress of Doom - Flame Belch": LocationData(7770073, "Fortress of Doom - First Visit"),
    "Fortress of Doom - Sentinel Crystal 1": LocationData(7770086, "Fortress of Doom - First Visit"),
    "Fortress of Doom - Fortress of Doom Codex Entry": LocationData(7770072, "Fortress of Doom - Second Visit"),
    "Fortress of Doom - Ice Bomb": LocationData(7770074, "Fortress of Doom - Second Visit"),
    "Fortress of Doom - Praetor Suit Token 1": LocationData(7770081, "Fortress of Doom - Second Visit"),
    "Fortress of Doom - Sentinel Crystal 2": LocationData(7770087, "Fortress of Doom - Second Visit"),
    "Fortress of Doom - Sentinel Crystal 3": LocationData(7770088, "Fortress of Doom - Second Visit"),

    "Cultist Base - Extra Life - Hanging Cage": LocationData(7770046, "Cultist Base"),
    "Cultist Base - Extra Life - After Big Fight Outside": LocationData(7770047, "Cultist Base"),
    "Cultist Base - Extra Life - Spike Crushers": LocationData(7770048, "Cultist Base"),
    "Cultist Base - Into Sandy's City Vinyl Record": LocationData(7770049, "Cultist Base"),
    "Cultist Base - Gargoyle Toy": LocationData(7770050, "Cultist Base"),
    "Cultist Base - Soldier (Blaster) Toy": LocationData(7770051, "Cultist Base"),
    "Cultist Base - Extra Life - Before Cultist Key": LocationData(7770052, "Cultist Base"),
    "Cultist Base - Extra Life - Dopefish 2": LocationData(7770053, "Cultist Base"),
    "Cultist Base - Extra Life - Dopefish 3": LocationData(7770054, "Cultist Base"),
    "Cultist Base - Extra Life - Dopefish 1": LocationData(7770055, "Cultist Base"),
    "Cultist Base - Rocket Launcher": LocationData(7770056, "Cultist Base"),
    "Cultist Base - Sentinel Battery 1": LocationData(7770057, "Cultist Base"),
    "Cultist Base - Sentinel Crystal 1": LocationData(7770058, "Cultist Base"),
    "Cultist Base - IDDQD Cheat Code": LocationData(7770059, "Cultist Base"),
    "Cultist Base - Cultist Base Codex Entry": LocationData(7770060, "Cultist Base"),
    "Cultist Base - Weapon Modbot 1": LocationData(7770061, "Cultist Base"),
    "Cultist Base - Praetor Suit Token 1": LocationData(7770062, "Cultist Base"),
    "Cultist Base - Praetor Suit Token 3": LocationData(7770063, "Cultist Base"),
    "Cultist Base - Praetor Suit Token 4": LocationData(7770064, "Cultist Base"),
    "Cultist Base - Praetor Suit Token 5": LocationData(7770065, "Cultist Base"),
    "Cultist Base - Praetor Suit Token 6": LocationData(7770066, "Cultist Base"),
    "Cultist Base - Rune 2": LocationData(7770067, "Cultist Base"),
    "Cultist Base - Sentinel Armor Mastery": LocationData(7770068, "Cultist Base"),
    "Cultist Base - Sentinel Battery 2": LocationData(7770069, "Cultist Base"),
    "Cultist Base - Sentinel Battery 3": LocationData(7770070, "Cultist Base"),
    "Cultist Base - Slayer Key": LocationData(7770071, "Cultist Base"),
    "Cultist Base - Mission Complete": LocationData(7770082, "Cultist Base"),
}
location_name_to_id = {name: data.code for name, data in location_data_table.items()}
