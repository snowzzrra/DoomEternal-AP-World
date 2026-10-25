

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.options import ItemPoolCounts, ResourceProfile
from worlds.doometernal.planner import build_semantic_counts
from worlds.doometernal import campaign as campaign_module
from worlds.doometernal import logic


CAMPAIGN = {"mission_pool": "custom", "custom_missions": {"Hell on Earth", "Exultia", "Final Sin"},
            "mission_count": 3, "goal": "kill_the_icon_of_sin", "mission_order": "random_mission_order"}










def test_hard_quantities_and_explicit_items_survive_auto_budget(monkeypatch):
    mw = setup_multiworld(DoomEternalWorld, seed=705, options=CAMPAIGN)
    options = mw.worlds[1].options
    options.resource_profile = ResourceProfile.from_any("generous")
    options.item_pool_counts = ItemPoolCounts.from_any({"Progressive Armor Upgrade": 4})
    requirement = logic.LocationRequirement(
        all_of=("Progressive Health Upgrade",),
        custom_rule=lambda state, player: state.has("Progressive Health Upgrade", player, 3),
    )
    monkeypatch.setattr(logic, "build_location_prerequisites", lambda *args, **kwargs: {"quantity": requirement})
    pool = build_semantic_counts(
        options, active_normal_ids=tuple(stage["id"] for stage in campaign_module.CAMPAIGN_STAGES
                                        if stage["source"] == "base")[:6],
        starting_weapon="Combat Shotgun", active_sg=(), active_masteries_count=0,
        battery_surplus=0, targets=(), placement_budget=0,
    )
    assert pool.total_counts["Progressive Health Upgrade"] >= 3
    assert pool.total_counts["Progressive Armor Upgrade"] == 4
