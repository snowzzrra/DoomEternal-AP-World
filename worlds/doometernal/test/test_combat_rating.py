from worlds.doometernal.combat_rating import ALL_MASTERY_NAMES, rate_items


def test_orphan_equipment_needs_its_host():
    for name in ALL_MASTERY_NAMES:
        assert rate_items({name})["final"] == 0, name
    orphan = rate_items({"Energy Shield"})
    complete = rate_items({"Energy Shield", "Chaingun"})
    assert orphan["final"] == 0
    assert complete["raw"]["Defense"] > orphan["raw"]["Defense"]


def test_best_three_rune_selection():
    best = {"Air Control", "Saving Throw", "Blood Fueled"}
    expected = rate_items({"Combat Shotgun"} | best)
    actual = rate_items({"Combat Shotgun", "Seek and Destroy", "Equipment Fiend"} | best)
    assert set(actual["selected_runes"]) == best
    assert actual["final"] == expected["final"]
    assert actual["raw"] == expected["raw"]


def test_support_rune_best_one():
    supports = {"Break Blast", "Desperate Punch", "Take Back"}
    actual = rate_items({"Combat Shotgun"} | supports)
    singles = [rate_items({"Combat Shotgun", name}) for name in supports]
    assert actual["final"] == max(result["final"] for result in singles)
    assert actual["raw"] == next(result["raw"] for result in singles
                                  if result["selected_support"] == actual["selected_support"])
