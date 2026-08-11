"""APWorld location facade backed by generated content data."""

from typing import NamedTuple

from BaseClasses import Location

from .generated_content import LOCATION_NAME_TO_ID, LOCATION_ROWS
from .identity import GAME_NAME


class DoomEternalLocation(Location):
    game: str = GAME_NAME


class LocationData(NamedTuple):
    code: int | None
    region: str


LOCATION_ID_BASE = 7770000
location_data_table: dict[str, LocationData] = {
    name: LocationData(code, region) for name, code, region in LOCATION_ROWS
}
location_name_to_id = LOCATION_NAME_TO_ID
