from io import StringIO
from unittest.mock import patch

import pytest
from Fill import distribute_items_restrictive

from Options import OptionError
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.slot_data import build_slot_data
from worlds.doometernal.slot_data_contract import (
    MAX_PAYLOAD_BYTES,
    PayloadSizeError,
    canonical_bytes,
)

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def default_world():
    multiworld = setup_multiworld(DoomEternalWorld, seed=42)
    distribute_items_restrictive(multiworld)
    return multiworld.worlds[1]


def test_recipe_changes_identity(default_world, monkeypatch):
    before = build_slot_data(default_world)
    stage = next(stage for stage in default_world.enemy_plan["maps"].values() if stage["recipes"])
    attributes = stage["recipes"][0]["bodies"][0]["attributes"]
    monkeypatch.setitem(attributes, "damage_percent", attributes["damage_percent"] + 1)
    after = build_slot_data(default_world)
    assert after["identity"]["recipe_digest"] != before["identity"]["recipe_digest"]
    assert after["native_generation_fingerprint"] != before["native_generation_fingerprint"]
    assert after["placement_digest"] == before["placement_digest"]


def test_placement_changes_identity(default_world, monkeypatch):
    before = build_slot_data(default_world)
    location = next(location for location in default_world.multiworld.get_locations(1)
                    if location.address is not None)
    replacement = default_world.create_item("Small Health" if location.item.name != "Small Health" else "Small Armor")
    monkeypatch.setattr(location, "item", replacement)
    after = build_slot_data(default_world)
    assert after["placement_digest"] != before["placement_digest"]
    assert after["native_generation_fingerprint"] != before["native_generation_fingerprint"]
    assert after["identity"]["recipe_digest"] == before["identity"]["recipe_digest"]


def test_serialization_is_identical_without_rng(default_world):
    streams = [default_world.multiworld.random, default_world.random, default_world.campaign_rng,
               default_world.enemy_rng, default_world.item_pool_rng, default_world.placement_rng,
               default_world.access_priority_rng]
    states = [stream.getstate() for stream in streams]
    with patch("random.Random.random", side_effect=AssertionError("Serialization drew randomness")), \
            patch("random.Random.getrandbits", side_effect=AssertionError("Serialization drew randomness")):
        first = canonical_bytes(build_slot_data(default_world))
        second = canonical_bytes(build_slot_data(default_world))
    assert first == second
    assert [stream.getstate() for stream in streams] == states


def test_diagnostics_only_change_spoiler(default_world, monkeypatch):
    before = canonical_bytes(build_slot_data(default_world))
    monkeypatch.setitem(default_world.campaign_plan, "bootstrap_overshoot", 123)
    monkeypatch.setitem(default_world.campaign_plan, "readiness_initial_deficit", 456)
    monkeypatch.setitem(default_world.campaign_plan, "resource_auto_adjustments", {"Sentinel Battery": 2})
    monkeypatch.setitem(default_world.enemy_plan, "seed", "1234")
    monkeypatch.setitem(default_world.enemy_plan, "compiler_adjustments",
                        [{"origin": "actor", "action": "preserve_scripted_boss"}])
    assert canonical_bytes(build_slot_data(default_world)) == before
    output = StringIO()
    default_world.write_spoiler(output)
    text = output.getvalue()
    assert "overshoot 123" in text
    assert "Readiness deficit: 456" in text
    assert "Automatic adjustments: Sentinel Battery: 2" in text
    assert "Enemy generation seed:" in text
    assert "{" not in text


def test_payload_error_is_player_configuration_error(default_world):
    error = PayloadSizeError(MAX_PAYLOAD_BYTES + 1, MAX_PAYLOAD_BYTES)
    with patch("worlds.doometernal.slot_data.validate_slot_data", side_effect=error) as validate:
        with pytest.raises(OptionError, match="8000001") as raised:
            build_slot_data(default_world)
    assert raised.value.__cause__ is error
    validate.assert_called_once()


def test_incomplete_placements_are_rejected(default_world, monkeypatch):
    location = next(location for location in default_world.multiworld.get_locations(1)
                    if location.address is not None)
    monkeypatch.setattr(location, "item", None)
    with pytest.raises(OptionError, match="Room placement is missing an item"):
        build_slot_data(default_world)


def test_large_size():
    options = {
        "mission_pool": "full_saga",
        "killsanity": True,
        "kills_per_check": 1,
        "killsanity_maximum_milestones": 2000,
        "enemy_count_mode": "multiplier",
        "enemy_count_multiplier": 500,
        "enemy_health": {"minimum": 25, "maximum": 400},
        "enemy_damage": {"minimum": 25, "maximum": 400},
        "enemy_speed": {"minimum": 50, "maximum": 200},
        "enemy_size": {"minimum": 50, "maximum": 150},
    }
    multiworld = setup_multiworld(DoomEternalWorld, seed=42, options=options)
    distribute_items_restrictive(multiworld)
    data = build_slot_data(multiworld.worlds[1])
    assert len(canonical_bytes(data)) <= MAX_PAYLOAD_BYTES
    assert data["killsanity"]["count"] == 2000
    assert data["killsanity"]["sources"]
    assert len(data["recipes"]["profiles"]) > 1000
