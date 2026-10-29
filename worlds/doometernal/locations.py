"""APWorld location facade backed by generated content data."""

from typing import NamedTuple

from BaseClasses import Location

from .generated_content import LOCATION_NAME_TO_ID, LOCATION_ROWS
from .identity import GAME_NAME
from .slot_data_contract import MAX_KILL_REWARDS


class DoomEternalLocation(Location):
    game: str = GAME_NAME


class LocationData(NamedTuple):
    code: int | None
    region: str


LOCATION_ID_BASE = 7770000
location_data_table: dict[str, LocationData] = {
    name: LocationData(code, region) for name, code, region in LOCATION_ROWS
}
KILL_REWARD_ID_BASE = 2_200_000_000
kill_reward_name_to_id = {
    f"Kill Reward {ordinal:04d}": KILL_REWARD_ID_BASE + ordinal
    for ordinal in range(1, MAX_KILL_REWARDS + 1)
}
assert set(kill_reward_name_to_id.values()).isdisjoint(LOCATION_NAME_TO_ID.values())
assert KILL_REWARD_ID_BASE > 2_147_483_647
location_name_to_id = {**LOCATION_NAME_TO_ID, **kill_reward_name_to_id}


def optional_location_enabled(name: str, options) -> bool:
    if name.endswith(" - Slayer Gate Complete"):
        return bool(options.include_slayer_gates.value)
    if " - Secret Encounter - " in name:
        return bool(options.include_secret_encounters.value)
    return True
