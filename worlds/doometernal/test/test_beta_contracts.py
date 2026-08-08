import importlib.util
import json
from pathlib import Path

from test.bases import WorldTestBase


WORLD = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, WORLD / name)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_version_projection_matches_release_source():
    version = _load("version.py")
    source = json.loads((WORLD.parents[1] / "release" / "version.json").read_text())
    assert version.PUBLIC_VERSION == source["public_version"]
    assert version.BRIDGE_PROTOCOL == source["bridge_protocol"]


def test_dash_ids_remain_distinct_and_reserved_by_option_contract():
    generated = (WORLD / "generated_content.py").read_text()
    world = (WORLD / "__init__.py").read_text()
    assert "('Exultia - Dash', 7770083" in generated
    assert 'if loc_name == "Exultia - Dash" and not self.options.randomize_dash:' in world
    assert 'if self.options.randomize_dash:\n            pool_names.append("Dash")' in world


class DoomEternalBetaTestBase(WorldTestBase):
    game = "DOOM Eternal"


class TestDashFalseDefaultSeed(DoomEternalBetaTestBase):
    options = {"randomize_dash": False}

    def test_default_seed_has_vanilla_dash_contract(self):
        with self.assertRaises(KeyError):
            self.multiworld.get_location("Exultia - Dash", self.player)
        self.assertNotIn("Dash", [item.name for item in self.multiworld.itempool])
        self.assertFalse(self.world.fill_slot_data()["randomize_dash"])


class TestDashTrueSeed(DoomEternalBetaTestBase):
    options = {"randomize_dash": True}

    def test_enabled_seed_has_dash_location_and_item(self):
        self.multiworld.get_location("Exultia - Dash", self.player)
        self.assertIn("Dash", [item.name for item in self.multiworld.itempool])
        self.assertTrue(self.world.fill_slot_data()["randomize_dash"])
