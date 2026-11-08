"""Materialize Secret Encounter time limits from qualified source durations."""

import json
from importlib.resources import files


def load_secret_encounter_timers() -> dict:
    path = files(__package__).joinpath("secret_encounter_timers.json")
    return json.loads(path.read_text(encoding="utf-8"))
