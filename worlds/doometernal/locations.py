from BaseClasses import Location
from typing import Dict, NamedTuple, Optional

class DoomEternalLocation(Location):
    game: str = "Doom Eternal"

class LocationData(NamedTuple):
    code: Optional[int]
    region: str

# Base ID for Doom Eternal locations, wanted to do 6660000 but I think that one was used for something else in the past (DOOM 1, DOOM 2), so I went with 7770000 instead. Should be plenty of room for all the locations we need to add.
LOCATION_ID_BASE = 7770000

# Special thanks to TastyFresh from the AP After Dark Discord for helping compile this list of locations and their corresponding regions.

location_data_table: Dict[str, LocationData] = {
    # Fortress of Doom
    "Fortress of Doom - Suit Point 1": LocationData(LOCATION_ID_BASE + 1, "Fortress of Doom"),
    "Fortress of Doom - Suit Point 2": LocationData(LOCATION_ID_BASE + 2, "Fortress of Doom"),
    "Fortress of Doom - Suit Point 3": LocationData(LOCATION_ID_BASE + 3, "Fortress of Doom"),
    "Fortress of Doom - Suit Point 4": LocationData(LOCATION_ID_BASE + 4, "Fortress of Doom"),
    "Fortress of Doom - Suit Point 5": LocationData(LOCATION_ID_BASE + 5, "Fortress of Doom"),
    "Fortress of Doom - Codex Page 1": LocationData(LOCATION_ID_BASE + 6, "Fortress of Doom"),
    "Fortress of Doom - Cheat Code 1": LocationData(LOCATION_ID_BASE + 7, "Fortress of Doom"),
    "Fortress of Doom - Cheat Code 2": LocationData(LOCATION_ID_BASE + 8, "Fortress of Doom"),
    
    # Hell on Earth
    "Hell on Earth - Completion": LocationData(LOCATION_ID_BASE + 9, "Hell on Earth"),
    "Hell on Earth - Yellow Keycard": LocationData(LOCATION_ID_BASE + 10, "Hell on Earth"),
    "Hell on Earth - Extra Life 1": LocationData(LOCATION_ID_BASE + 11, "Hell on Earth"),
    "Hell on Earth - Extra Life 2": LocationData(LOCATION_ID_BASE + 12, "Hell on Earth"),
    "Hell on Earth - Extra Life 3": LocationData(LOCATION_ID_BASE + 13, "Hell on Earth"),
    "Hell on Earth - Extra Life 4": LocationData(LOCATION_ID_BASE + 14, "Hell on Earth"),
    "Hell on Earth - Codex Page 1": LocationData(LOCATION_ID_BASE + 15, "Hell on Earth"),
    "Hell on Earth - Codex Page 2": LocationData(LOCATION_ID_BASE + 16, "Hell on Earth"),
    "Hell on Earth - Codex Page 3": LocationData(LOCATION_ID_BASE + 17, "Hell on Earth"),
    "Hell on Earth - Codex Page 4": LocationData(LOCATION_ID_BASE + 18, "Hell on Earth"),
    "Hell on Earth - Codex Page 5": LocationData(LOCATION_ID_BASE + 19, "Hell on Earth"),
    "Hell on Earth - Codex Page 6": LocationData(LOCATION_ID_BASE + 20, "Hell on Earth"),
    "Hell on Earth - Automap": LocationData(LOCATION_ID_BASE + 21, "Hell on Earth"),
    "Hell on Earth - Toy 1": LocationData(LOCATION_ID_BASE + 22, "Hell on Earth"),
    "Hell on Earth - Toy 2": LocationData(LOCATION_ID_BASE + 23, "Hell on Earth"),
    "Hell on Earth - Toy 3": LocationData(LOCATION_ID_BASE + 24, "Hell on Earth"),
    "Hell on Earth - Cheat Code 1": LocationData(LOCATION_ID_BASE + 25, "Hell on Earth"),
    
    # Exultia
    "Exultia - Completion": LocationData(LOCATION_ID_BASE + 26, "Exultia"),
    "Exultia - Sentinel Power Core 1": LocationData(LOCATION_ID_BASE + 27, "Exultia"),
    "Exultia - Sentinel Power Core 2": LocationData(LOCATION_ID_BASE + 28, "Exultia"),
    "Exultia - Sentinel Power Core 3": LocationData(LOCATION_ID_BASE + 29, "Exultia"),
    "Exultia - Slayer Key": LocationData(LOCATION_ID_BASE + 30, "Exultia"),
    "Exultia - Secret Gore Nest 1": LocationData(LOCATION_ID_BASE + 31, "Exultia"),
    "Exultia - Secret Gore Nest 2": LocationData(LOCATION_ID_BASE + 32, "Exultia"),
    "Exultia - Empyrean Key": LocationData(LOCATION_ID_BASE + 33, "Exultia"),
    "Exultia - Automap": LocationData(LOCATION_ID_BASE + 34, "Exultia"),

    # NOTE: More locations will be appended here later.
}

location_name_to_id = {name: data.code for name, data in location_data_table.items() if data.code is not None}
