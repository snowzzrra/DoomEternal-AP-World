import unittest

from worlds.doometernal.items import item_data_table, item_name_to_id
from worlds.doometernal.locations import location_name_to_id


class TestItemRegistry(unittest.TestCase):
    def test_rune_is_not_an_item_and_location_id_remains_valid(self) -> None:
        self.assertNotIn("Rune", item_data_table)
        self.assertNotIn("Rune", item_name_to_id)
        self.assertNotIn(7770020, item_name_to_id.values())
        self.assertEqual(location_name_to_id["Hell on Earth - Infinite Extra Lives Cheat"], 7770020)
