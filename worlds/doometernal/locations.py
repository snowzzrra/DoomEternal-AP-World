"""APWorld location facade backed by generated content data."""

from typing import NamedTuple
import importlib.util
from pathlib import Path

from BaseClasses import Location
try:
    from .identity import GAME_NAME
except ImportError:  # build_apworld_identity loads this module standalone
    GAME_NAME = "DOOM Eternal"

try:
    from .generated_content import LOCATION_NAME_TO_ID, LOCATION_ROWS
except ImportError:  # build_apworld_identity loads this file outside its package
    _spec = importlib.util.spec_from_file_location("doometernal_generated_content", Path(__file__).with_name("generated_content.py"))
    assert _spec and _spec.loader
    _generated = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_generated)
    LOCATION_NAME_TO_ID = _generated.LOCATION_NAME_TO_ID
    LOCATION_ROWS = _generated.LOCATION_ROWS


class DoomEternalLocation(Location):
    game: str = GAME_NAME


class LocationData(NamedTuple):
    code: int | None
    region: str


# Kept for public compatibility with older tooling.
LOCATION_ID_BASE = 7770000
location_data_table: dict[str, LocationData] = {
    name: LocationData(code, region) for name, code, region in LOCATION_ROWS
}
location_name_to_id = LOCATION_NAME_TO_ID
