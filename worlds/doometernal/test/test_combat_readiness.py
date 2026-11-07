from __future__ import annotations

from types import SimpleNamespace

import pytest
from BaseClasses import CollectionState, ItemClassification

from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.combat_rating import evaluate_player_loadout_cr
from worlds.doometernal.combat_readiness import evaluate_mission_readiness
from worlds.doometernal.items import DoomEternalItem

from .bases import DLC_START_INVENTORY


def test_victory_requirement_alias_keeps_canonical_export():
    from worlds.doometernal.options import AdditionalVictoryRequirements
    requirement = AdditionalVictoryRequirements.from_any(["Complete All Enabled Missions", "Acquire the Unmaykr"])
    assert "Complete All Included Missions" in requirement.value
    assert "Complete All Enabled Missions" not in requirement.value
    assert "Acquire the Unmaykr" in requirement.value
    assert requirement.value <= requirement.valid_keys


class TestSpiritBreakpoints:
    @pytest.mark.parametrize("difficulty", ["relaxed", "standard"])
    def test_pre_vs_post_breakpoint_topological_reachability(self, difficulty):
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=100,
            options={
                "mission_pool": "dlc_only",
                "start_inventory": DLC_START_INVENTORY,
                "goal": "kill_the_dark_lord",
                "campaign_difficulty": 2,
                "logic_difficulty": difficulty,
                "enemy_randomizer": 0,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]

        crossroad_region = mw.get_region("The Blood Swamps - Underworld Crossroad", 1)
        courtyard_region = mw.get_region("The Blood Swamps - Sunken Courtyard", 1)

        items = {
            "Ballista",
            "Super Shotgun",
            "Rocket Launcher",
            "Heavy Cannon",
            "Chainsaw",
            "Ice Bomb",
            "Blood Punch",
            "Dash",
            "Flame Belch",
            "Faster Weapon Swap",
        }
        state = CollectionState(mw)
        state.prog_items[1].clear()
        state.prog_items[1].update(dict.fromkeys(items, 1))
        for stat in ("Health", "Armor", "Ammo"):
            state.prog_items[1][f"Progressive {stat} Upgrade"] = 1
        from worlds.doometernal.campaign import completion_event

        sequence = world.campaign_plan["sequence"]
        for predecessor in sequence[: sequence.index("e4m2_swamp")]:
            state.collect(DoomEternalItem(completion_event(predecessor), ItemClassification.progression, None, 1), True)

        res_base = evaluate_mission_readiness(state, 1, "e4m2_swamp", world)
        assert res_base.ready is True

        assert crossroad_region.can_reach(state) is True

        assert courtyard_region.can_reach(state) is False

        state.collect(world.create_item("Plasma Rifle"))
        state.collect(world.create_item("Microwave Beam"))

        assert courtyard_region.can_reach(state) is True


class TestStructuralVsLogicalReachability:
    @pytest.mark.parametrize("order", ["random_mission_order", "mission_access_as_items"])
    def test_mission_access_waits_for_readiness(self, order):
        from worlds.doometernal.campaign import completion_event, stage_available

        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_order": order,
                "logic_difficulty": "expert",
                "enemy_randomizer": False,
            },
        )
        world = mw.worlds[1]
        plan = world.campaign_plan
        stage = "e3m2_hell"
        state = CollectionState(mw)
        if order == "mission_access_as_items":
            assert stage not in plan["starting_stages"]
            state.collect(world.create_item("Nekravol Access"))
        else:
            for predecessor in plan["sequence"][: plan["sequence"].index(stage)]:
                state.collect(DoomEternalItem(completion_event(predecessor), ItemClassification.progression, None, 1))
        entrance = mw.get_entrance("Mission Select: Nekravol", 1)
        assert stage_available(plan, stage, state, 1)
        assert not entrance.can_reach(state)
        for item in mw.get_items():
            if item.code is not None:
                state.collect(item, prevent_sweep=True)
        assert stage_available(plan, stage, state, 1)
        assert entrance.can_reach(state)


class TestDashBootstrapAndSphereZero:
    def test_dash_bootstrap_nonrandomized_late_start(self):
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "dlc_only",  # Starts at UAC Atlantica
                "start_inventory": DLC_START_INVENTORY,
                "goal": "kill_the_dark_lord",
                "randomize_dash": 0,
                "campaign_difficulty": 2,
                "enemy_randomizer": 0,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        assert "Dash" in world.campaign_plan["bootstrap_inventory"]

        precollected_names = [item.name for item in mw.precollected_items[1]]
        assert "Dash" in precollected_names

        state = CollectionState(mw)
        assert state.has("Dash", 1) is True
        res = evaluate_player_loadout_cr(state, 1, world)
        assert res.categories["Mobility"] >= 4.0


def frozen_readiness_world():
    from worlds.doometernal.slot_data_contract import StageProfile

    world = SimpleNamespace()
    world.stage_profiles = {
        "e1m1_intro": StageProfile(
            cr_min=27,
            cr_max=48,
            opening_cr_min=12,
            opening_cr_max=18,
            counter_ids=("blood_angel",),
            opening_counter_ids=("stone_imp",),
            renewable_ammo=True,
            native_chainsaw_before_combat=True,
            skulls=3,
            effort_per_check_milli=1234,
        )
    }
    return world


def test_frozen_counter_requirements_still_follow_inventory():
    from worlds.doometernal.combat_readiness import _enemy_counter_penalties

    world = frozen_readiness_world()
    missing = SimpleNamespace(has=lambda *args: False)
    complete = SimpleNamespace(has=lambda *args: True)
    assert _enemy_counter_penalties(missing, 1, "e1m1_intro", world) == {"blood_angel": 8}
    assert _enemy_counter_penalties(missing, 1, "e1m1_intro", world, opening=True) == {"stone_imp": 6}
    assert _enemy_counter_penalties(complete, 1, "e1m1_intro", world) == {}
    assert _enemy_counter_penalties(complete, 1, "e1m1_intro", world, opening=True) == {}
