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
    "Hell on Earth - Extra Life 1": LocationData(7770004, "Hell on Earth"),
    "Hell on Earth - Extra Life 2": LocationData(7770005, "Hell on Earth"),
    "Hell on Earth - Extra Life 3": LocationData(7770006, "Hell on Earth"),
    "Hell on Earth - Extra Life 4": LocationData(7770007, "Hell on Earth"),
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
    "Exultia - Completion": LocationData(7770021, "Exultia"),
    "Exultia - Extra Life 1": LocationData(7770022, "Exultia"),
    "Exultia - Extra Life 2": LocationData(7770023, "Exultia"),
}
location_name_to_id = {name: data.code for name, data in location_data_table.items()}
