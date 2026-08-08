from .bases import DoomEternalTestBase


class TestDashDisabled(DoomEternalTestBase):
    options: dict[str, object] = {"randomize_dash": False}  # noqa: RUF012

    def test_dash_remains_vanilla(self) -> None:
        with self.assertRaises(KeyError):
            self.multiworld.get_location("Exultia - Dash", self.player)
        self.assertNotIn("Dash", (item.name for item in self.multiworld.itempool))
        self.assertFalse(self.world.fill_slot_data()["randomize_dash"])


class TestDashEnabled(DoomEternalTestBase):
    options: dict[str, object] = {"randomize_dash": True}  # noqa: RUF012

    def test_dash_is_randomized(self) -> None:
        self.multiworld.get_location("Exultia - Dash", self.player)
        self.assertIn("Dash", (item.name for item in self.multiworld.itempool))
        self.assertTrue(self.world.fill_slot_data()["randomize_dash"])
