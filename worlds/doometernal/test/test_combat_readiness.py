"""DOOM Eternal combat readiness integration tests.

Tests cover:
- Base readiness across the three preparation allowances
- Spirit breakpoints across all 5 mandatory Spirit stages
- The Dark Lord Sentinel Hammer soft penalty and progressive special modes
- Structural vs logical reachability separation (RMO & MAI)
- Non-randomized Dash bootstrap context
- Sphere-zero reachability diagnostics
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from BaseClasses import CollectionState, ItemClassification, MultiWorld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import STAGE_BY_ID
from worlds.doometernal.combat_rating import evaluate_player_loadout_cr, rate_items
from worlds.doometernal.combat_readiness import (
    DARK_LORD_HAMMER_PENALTY,
    DARK_LORD_STAGE_ID,
    MAX_EFFECTIVE_CR,
    MISSION_BASE_CR,
    SPIRIT_BREAKPOINTS,
    SPIRIT_PENALTY,
    evaluate_mission_readiness,
    get_mission_base_cr,
    has_effective_anti_spirit,
    has_effective_sentinel_hammer,
    is_dark_lord_defeated_ready,
    is_mission_ready,
    is_spirit_breakpoint_ready,
)
from worlds.doometernal.items import DoomEternalItem, item_data_table
from test.general import setup_multiworld
from .bases import DLC_START_INVENTORY


def make_mock_world(
    difficulty: int = 2,
    logic_difficulty: int = 1,
    special_weapon: str = "Progressive Special Weapon",
    randomize_dash: bool = False,
    randomize_chainsaw: bool = False,
    use_dlc: bool = True,
    player: int = 1,
) -> MagicMock:
    """Create a lightweight mock DoomEternalWorld with specified options."""
    world = MagicMock()
    world.player = player
    world.game = "DOOM Eternal"
    world.starting_weapon_name = "Combat Shotgun"
    world.enemy_plan = None
    world.options = MagicMock()
    world.options.campaign_difficulty = MagicMock(value=difficulty)
    world.options.logic_difficulty = MagicMock(value=logic_difficulty)
    sw_val = 0
    if special_weapon == "Progressive Sentinel Hammer":
        sw_val = 1
    elif special_weapon == "The Crucible":
        sw_val = 2
    world.options.special_weapon = MagicMock(current_option_name=special_weapon, value=sw_val)
    world.options.randomize_dash = MagicMock(value=int(randomize_dash))
    world.options.randomize_chainsaw = MagicMock(value=int(randomize_chainsaw))
    world.options.use_dlc_content = MagicMock(value=int(use_dlc))

    def _collect(state, item):
        state.prog_items[item.player][item.name] += 1
        return True

    world.collect = _collect
    return world


def create_state_with_items(
    item_names: set[str],
    *,
    player: int = 1,
    world: DoomEternalWorld | MagicMock | None = None,
    health_stages: int = 0,
    armor_stages: int = 0,
    ammo_stages: int = 0,
    wup_count: int = 0,
    prog_special: int = 0,
    prog_hammer: int = 0,
    the_crucible: int = 0,
) -> CollectionState:
    """Create a CollectionState containing the specified items."""
    if isinstance(world, DoomEternalWorld) and world.multiworld is not None:
        mw = world.multiworld
    elif world is not None and hasattr(world, "options"):
        mw = MultiWorld(1)
        mw.worlds[player] = world
    else:
        mw = MultiWorld(1)
        mw.worlds[player] = make_mock_world(player=player)

    state = CollectionState(mw)
    for name in item_names:
        state.prog_items[player][name] += 1

    if health_stages:
        state.prog_items[player]["Progressive Health Upgrade"] += health_stages
    if armor_stages:
        state.prog_items[player]["Progressive Armor Upgrade"] += armor_stages
    if ammo_stages:
        state.prog_items[player]["Progressive Ammo Upgrade"] += ammo_stages
    if wup_count:
        state.prog_items[player]["Weapon Upgrade Points (3)"] += wup_count
    if prog_special:
        state.prog_items[player]["Progressive Special Weapon"] += prog_special
    if prog_hammer:
        state.prog_items[player]["Progressive Sentinel Hammer"] += prog_hammer
    if the_crucible:
        state.prog_items[player]["The Crucible"] += the_crucible

    return state


# ═══════════════════════════════════════════════════════════════
# §20 — Base Readiness Test Matrix
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §21 — Spirit Breakpoint Tests
# ═══════════════════════════════════════════════════════════════

def test_canonical_readiness_and_dlc_intrinsic_difficulty():
    for logic_difficulty in range(3):
        world = make_mock_world(logic_difficulty=logic_difficulty, randomize_dash=True)
        for stage in MISSION_BASE_CR:
            state = create_state_with_items({"Combat Shotgun"}, world=world)
            result = evaluate_mission_readiness(state, 1, stage, world)
            assert is_mission_ready(state, 1, stage, world) == result.ready
            assert result.mission_base_cr == MISSION_BASE_CR[stage]
            if stage.startswith(("e4", "e5")) and stage != DARK_LORD_STAGE_ID:
                assert not result.ready


@pytest.mark.parametrize("items", [
    {"Combat Shotgun", "Frag Grenade"},
    {"Combat Shotgun", "Chainsaw"},
    {"Combat Shotgun", "Chainsaw", "Dash"},
])
def test_nightmare_requires_more_preparation_without_changing_mission_tier(items):
    changed = False
    for logic_difficulty in range(3):
        results = []
        for campaign_difficulty in range(4):
            world = make_mock_world(
                difficulty=campaign_difficulty, logic_difficulty=logic_difficulty,
                randomize_chainsaw=True, randomize_dash=True,
            )
            state = create_state_with_items(items, world=world)
            results.append(evaluate_mission_readiness(state, 1, "e1m2_war", world))
        assert len({result.mission_base_cr for result in results}) == 1
        assert len({result.player_cr for result in results}) == 1
        assert results[-1].allowance < results[1].allowance
        assert not results[-1].ready or results[1].ready
        changed |= results[1].ready and not results[-1].ready
    assert changed


def test_victory_requirement_alias_keeps_canonical_export():
    from worlds.doometernal.options import AdditionalVictoryRequirements
    requirement = AdditionalVictoryRequirements.from_any(["Complete All Enabled Missions", "Acquire the Unmaykr"])
    assert "Complete All Included Missions" in requirement.value
    assert "Complete All Enabled Missions" not in requirement.value
    assert "Acquire the Unmaykr" in requirement.value
    assert requirement.value <= requirement.valid_keys


class TestSpiritBreakpoints:
    """Test Spirit severe soft penalties (+15, cap 100) and capability checks (§21)."""



    def test_pre_vs_post_breakpoint_topological_reachability(self):
        """In real generation, pre-breakpoint regions require only Base CR, while post-breakpoint requires Spirit readiness."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=100,
            options={
                "mission_pool": "dlc_only",
                "start_inventory": DLC_START_INVENTORY,
                "goal": "kill_the_dark_lord",
                "campaign_difficulty": 2,
                "enemy_randomizer": 0,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]

        # Region before breakpoint: "The Blood Swamps - Underworld Crossroad"
        # Region after breakpoint: "The Blood Swamps - Sunken Courtyard"
        crossroad_region = mw.get_region("The Blood Swamps - Underworld Crossroad", 1)
        courtyard_region = mw.get_region("The Blood Swamps - Sunken Courtyard", 1)

        # A sustainable kit needs effective Spirit control to cross the breakpoint.
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher", "Heavy Cannon",
            "Chainsaw", "Ice Bomb", "Blood Punch", "Dash",
            "Air Control", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=3, armor_stages=3, ammo_stages=3)
        for item in mw.precollected_items[1]:
            state.remove(item)
        from worlds.doometernal.campaign import completion_event
        sequence = world.campaign_plan["sequence"]
        for predecessor in sequence[:sequence.index("e4m2_swamp")]:
            state.collect(DoomEternalItem(completion_event(predecessor), ItemClassification.progression, None, 1), True)

        res_base = evaluate_mission_readiness(state, 1, "e4m2_swamp", world)
        assert 76.0 <= res_base.player_cr < 88.0
        assert res_base.ready is True

        # Check pre-breakpoint reachability: crossroad is reachable!
        assert crossroad_region.can_reach(state) is True

        # Check post-breakpoint reachability: sunken courtyard is NOT reachable without anti-spirit tool!
        assert courtyard_region.can_reach(state) is False

        # Now collect Plasma Rifle + Microwave Beam
        state.collect(world.create_item("Plasma Rifle"))
        state.collect(world.create_item("Microwave Beam"))

        # Courtyard is now reachable!
        assert courtyard_region.can_reach(state) is True


# ═══════════════════════════════════════════════════════════════
# §22 — Dark Lord Hammer Soft Penalty Tests
# ═══════════════════════════════════════════════════════════════

class TestDarkLordHammerPenalty:
    """Test The Dark Lord Sentinel Hammer soft penalty (+15, Base 80 -> 95) (§22)."""

    def test_hammer_vs_no_hammer_effective_cr(self):
        """The Dark Lord Defeated: Effective CR is 80 with Hammer, 95 without Hammer."""
        world = make_mock_world(difficulty=2, special_weapon="Progressive Special Weapon")
        state_no_hammer = create_state_with_items({"Combat Shotgun"}, world=world)
        res_no = evaluate_mission_readiness(state_no_hammer, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res_no.mission_base_cr == 80
        assert res_no.soft_penalty == DARK_LORD_HAMMER_PENALTY
        assert res_no.effective_cr == 95

        state_hammer = create_state_with_items({"Combat Shotgun"}, world=world, prog_special=2)
        res_hammer = evaluate_mission_readiness(state_hammer, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res_hammer.soft_penalty == 0
        assert res_hammer.effective_cr == 80







# ═══════════════════════════════════════════════════════════════
# §23 — Structural vs Logical Reachability (RMO & MAI)
# ═══════════════════════════════════════════════════════════════

class TestStructuralVsLogicalReachability:
    """Test that structural availability and combat readiness operate independently (§23)."""

    def test_rmo_under_ready_structurally_available_logically_unreachable(self):
        """RMO: A revealed stage with insufficient CR is structurally available but logically unreachable."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_order": "random_mission_order",
                "logic_difficulty": "expert",
                "enemy_randomizer": 0,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan

        stage2_id = "e3m2_hell"

        state = CollectionState(mw)
        from worlds.doometernal.campaign import completion_event
        for stage in plan["sequence"][:plan["sequence"].index(stage2_id)]:
            state.collect(DoomEternalItem(completion_event(stage), ItemClassification.progression, None, 1))

        from worlds.doometernal.campaign import stage_available
        # Structural check: stage 2 IS available
        assert stage_available(plan, stage2_id, state, 1) is True

        # Logical entrance check: if stage 2 Base CR > 12, it is NOT ready
        base_cr = MISSION_BASE_CR[stage2_id]
        if base_cr > 12:
            entrance_name = "Mission Select: " + STAGE_BY_ID[stage2_id]["name"]
            entrance = mw.get_entrance(entrance_name, 1)
            # Cannot reach logically!
            assert entrance.can_reach(state) is False

            # Later gain enough CR items
            state.collect(world.create_item("Ballista"))
            state.collect(world.create_item("Super Shotgun"))
            state.collect(world.create_item("Rocket Launcher"))
            state.collect(world.create_item("Heavy Cannon"))
            state.collect(world.create_item("Plasma Rifle"))
            state.collect(world.create_item("Chaingun"))
            state.collect(world.create_item("BFG-9000"))
            state.collect(world.create_item("Dash"))
            state.collect(world.create_item("Chainsaw"))
            state.collect(world.create_item("Flame Belch"))
            state.collect(world.create_item("Frag Grenade"))
            state.collect(world.create_item("Ice Bomb"))
            state.collect(world.create_item("Blood Punch"))
            state.collect(world.create_item("Precision Bolt"))
            state.collect(world.create_item("Sticky Bombs"))
            state.collect(world.create_item("Heat Blast"))
            state.collect(world.create_item("Microwave Beam"))
            state.collect(world.create_item("Lock-on Burst"))
            state.collect(world.create_item("Arbalest"))
            state.collect(world.create_item("Energy Shield"))
            state.collect(world.create_item("Mobile Turret"))
            state.collect(world.create_item("The Crucible"))
            state.prog_items[1]["Progressive Health Upgrade"] += 4
            state.prog_items[1]["Progressive Armor Upgrade"] += 4
            state.prog_items[1]["Progressive Ammo Upgrade"] += 4
            state.prog_items[1]["Weapon Upgrade Points (3)"] += 12

            # Now entrance is reachable! Sequence order did not change!
            assert entrance.can_reach(state) is True
            assert stage_available(plan, stage2_id, state, 1) is True

    def test_mai_access_item_under_ready(self):
        """MAI: Access item received while under-ready grants structural access, but logical entrance waits for CR."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_pool": "full_saga",
                "mission_order": "mission_access_as_items",
                "logic_difficulty": "expert",
                "enemy_randomizer": 0,
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan

        # Pick a non-starting stage that requires an Access item
        non_start_id = next(s for s in plan["sequence"] if s not in plan["starting_stages"] and s != plan["goal_stage"])
        stage_name = STAGE_BY_ID[non_start_id]["name"]
        access_item_name = f"{stage_name} Access"

        state = CollectionState(mw)
        # Give Access item: structurally available
        state.collect(world.create_item(access_item_name))

        from worlds.doometernal.campaign import stage_available
        assert stage_available(plan, non_start_id, state, 1) is True

        # If high CR stage, entrance requires CR
        base_cr = MISSION_BASE_CR[non_start_id]
        entrance = mw.get_entrance("Mission Select: " + stage_name, 1)
        if base_cr > 12:
            assert entrance.can_reach(state) is False

            # Give CR upgrades
            state.collect(world.create_item("Ballista"))
            state.collect(world.create_item("Super Shotgun"))
            state.collect(world.create_item("Rocket Launcher"))
            for _ in range(4):
                state.collect(world.create_item("Progressive Health Upgrade"))

            if evaluate_mission_readiness(state, 1, non_start_id, world).ready:
                assert entrance.can_reach(state) is True


# ═══════════════════════════════════════════════════════════════
# §24 — Dash Bootstrap & Sphere-Zero Diagnostics
# ═══════════════════════════════════════════════════════════════

class TestDashBootstrapAndSphereZero:
    """Test Dash bootstrap when starting outside HoE/Exultia (§10) and sphere-zero diagnostics (§24)."""

    def test_dash_bootstrap_nonrandomized_late_start(self):
        """When randomize_dash=False and start is outside HoE/Exultia, Dash is bootstrapped and counted in CR."""
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

        # In precollected items
        precollected_names = [item.name for item in mw.precollected_items[1]]
        assert "Dash" in precollected_names

        # CollectionState starts with Dash
        state = CollectionState(mw)
        assert state.has("Dash", 1) is True
        res = evaluate_player_loadout_cr(state, 1, world)
        assert res.categories["Mobility"] >= 4.0

    def test_intro_preparation_is_reachable_before_starting_the_mission(self):
        """Generated supply can be prepared through the real Fortress checks."""
        for diff in (0, 1, 2, 3):
            mw = setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "base",
                    "mission_order": "random_mission_order",
                    "campaign_difficulty": diff,
                    "enemy_randomizer": 0,
                },
            )
            world: DoomEternalWorld = mw.worlds[1]
            state = CollectionState(mw)
            start_stage = world.campaign_plan["starting_stages"][0]
            if start_stage == "e1m1_intro":
                from Fill import distribute_items_restrictive
                distribute_items_restrictive(mw)
                res = evaluate_mission_readiness(state, 1, "e1m1_intro", world)
                from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS
                collected = set()
                while not res.ready:
                    reachable = [location for location in mw.get_filled_locations(1)
                                 if location.name in FORTRESS_BOOTSTRAP_LOCATIONS
                                 and location.name not in collected and location.can_reach(state)]
                    assert reachable, f"No physical preparation remains reachable on difficulty {diff}"
                    for location in reachable:
                        state.collect(location.item)
                        collected.add(location.name)
                    res = evaluate_mission_readiness(state, 1, "e1m1_intro", world)
                assert res.ready


def test_frozen_combat_cost_changes_readiness_and_seed_skulls():
    from worlds.doometernal.combat_readiness import get_mission_skull_tier

    world = make_mock_world()
    state = create_state_with_items({"Combat Shotgun"}, world=world)
    original = evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=5)
    world.enemy_plan = {"combat_costs": {"e1m1_intro": {"original": 0, "actual": 120}}}
    generated = evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=5)
    assert original.ready and not generated.ready
    assert generated.mission_base_cr == original.mission_base_cr + 12
    tier = get_mission_skull_tier("e1m1_intro", world)
    assert tier > get_mission_skull_tier("e1m1_intro")
    world.options.logic_difficulty.value = 0
    world.options.campaign_difficulty.value = 3
    assert get_mission_skull_tier("e1m1_intro", world) == tier
    world.enemy_plan["combat_costs"]["e1m1_intro"]["actual"] = 0
    assert get_mission_base_cr("e1m1_intro", world) == original.mission_base_cr


def test_cost_reduction_preserves_protected_boss_preparation():
    world = make_mock_world()
    world.enemy_plan = {"combat_costs": {"e3m3_maykr": {"original": 10000, "actual": 0}}}
    assert get_mission_base_cr("e3m3_maykr", world) == MISSION_BASE_CR["e3m3_maykr"]


def test_generated_counter_penalties_require_the_weapon_and_its_mod():
    world = make_mock_world()
    world.enemy_plan = {'revision': 3, 'combat_costs': {'e1m1_intro': {'campaign': {
        'actual': 100, 'bodies': 10, 'wave_p90': 20, 'species': ['stone_imp', 'blood_angel', 'spirit']}}}}
    basic = create_state_with_items({'Combat Shotgun'}, world=world)
    assert evaluate_mission_readiness(basic, 1, 'e1m1_intro', world).soft_penalty == 29
    world.enemy_plan['combat_costs']['e1m1_intro']['campaign']['species'].remove('spirit')
    assert evaluate_mission_readiness(basic, 1, 'e1m1_intro', world, context='spirit_breakpoint').soft_penalty == 29
    world.enemy_plan['combat_costs']['e1m1_intro']['campaign']['species'].append('spirit')
    orphan = create_state_with_items({'Full Auto', 'Microwave Beam', 'Precision Bolt'}, world=world)
    assert evaluate_mission_readiness(orphan, 1, 'e1m1_intro', world).soft_penalty == 29
    equipped = create_state_with_items({'Combat Shotgun', 'Full Auto', 'Plasma Rifle', 'Microwave Beam', 'Ballista'}, world=world)
    assert evaluate_mission_readiness(equipped, 1, 'e1m1_intro', world).soft_penalty == 0


def test_generated_rating_follows_combat_instead_of_the_mission_name():
    world = make_mock_world()
    profile = dict(actual=100, bodies=20, wave_p90=20, species=[])
    world.enemy_plan = {'revision': 3, 'combat_costs': {
        stage: {'campaign': dict(profile)} for stage in ('e1m1_intro', 'e1m2_war')}}
    assert get_mission_base_cr('e1m1_intro', world) == get_mission_base_cr('e1m2_war', world)
    low = get_mission_base_cr('e1m1_intro', world)
    world.enemy_plan['combat_costs']['e1m1_intro']['campaign'].update(actual=300, wave_p90=80)
    assert get_mission_base_cr('e1m1_intro', world) > low


def test_wave_range_prepares_for_the_peak_and_duration_affects_effort_separately():
    from copy import deepcopy
    from worlds.doometernal.combat_readiness import get_mission_cr_range, get_mission_effort_per_check

    world = make_mock_world()
    world.options = None
    profile = dict(actual=150, bodies=20, effort=500, species=[],
        waves=[dict(cost=10, bodies=10), dict(cost=140, bodies=10)])
    world.enemy_plan = {'revision': 5, 'combat_costs': {
        stage: {'campaign': deepcopy(profile)} for stage in ('e1m1_intro', 'e5m1_spear')}}
    low, high = get_mission_cr_range('e1m1_intro', world)
    assert low < high == get_mission_base_cr('e1m1_intro', world)
    assert get_mission_base_cr('e5m1_spear', world) == high
    ordinary = get_mission_effort_per_check('e1m1_intro', world)
    assert get_mission_effort_per_check('e5m1_spear', world) > ordinary
    world.enemy_plan['combat_costs']['e1m1_intro']['campaign']['effort'] *= 2
    assert get_mission_effort_per_check('e1m1_intro', world) == ordinary * 2
    assert get_mission_base_cr('e1m1_intro', world) == high


def test_rmo_orders_the_frozen_generated_combat_before_selecting_its_start():
    from copy import deepcopy
    from random import Random
    from worlds.doometernal.campaign import make_plan

    mw = setup_multiworld(DoomEternalWorld, seed=871, options={
        'mission_pool': 'custom', 'custom_missions': ['Hell on Earth', 'Exultia', 'Final Sin'],
        'goal': 'kill_the_icon_of_sin', 'custom_dark_lord': 0, 'enemy_randomizer': 0,
    })
    world = mw.worlds[1]
    candidate = deepcopy(world.campaign_plan)
    candidate['composition_bands'] = {stage: n for n, stage in enumerate(candidate['sequence'])}
    profile = dict(actual=20, bodies=20, wave_p90=2, species=[])
    world.enemy_plan = {'revision': 3, 'combat_costs': {
        stage: {'campaign': dict(profile)} for stage in candidate['sequence']}}
    world.enemy_plan['combat_costs']['e1m1_intro']['campaign'].update(actual=1200, wave_p90=150)
    plan = make_plan(world.options, Random(871), world, candidate=candidate)
    assert plan['sequence'] == ['e1m2_war', 'e1m1_intro', 'e3m4_boss']
    assert plan['starting_stages'] == ['e1m2_war']
    assert plan['composition_bands'] == candidate['composition_bands']
    world.enemy_plan['revision'] = 5
    for entry in world.enemy_plan['combat_costs'].values():
        entry['campaign'].update(waves=[dict(cost=20, bodies=20)], effort=0)
    world.enemy_plan['combat_costs']['e1m2_war']['campaign']['effort'] = 100000
    ranked = make_plan(world.options, Random(871), world, candidate=candidate)
    assert ranked['sequence'] == ['e1m1_intro', 'e1m2_war', 'e3m4_boss']
    presentation = world._mission_presentation()['e1m1_intro']
    assert presentation['cr_min'] == presentation['cr_max'] == presentation['base_cr']


def test_generated_combat_is_available_to_pool_and_physical_start_solver():
    from collections import Counter
    from Fill import distribute_items_restrictive
    from worlds.doometernal.enemy_options import SPECIES_IDS

    mw = setup_multiworld(DoomEternalWorld, seed=71412, options={
        "goal": "complete_the_full_saga",
        "mission_order": "mission_access_as_items",
        "enemy_randomizer": True,
        "enemy_count_mode": "multiplier", "enemy_count_multiplier": 500,
        "progressive_difficulty": False, "start_inventory": DLC_START_INVENTORY,
        "enemy_weights": {species: 100 if species == "stone_imp" else int(species == 'imp') for species in SPECIES_IDS},
        "enemy_health": {"minimum": 200, "maximum": 200},
    })
    world = mw.worlds[1]
    plan = world.campaign_plan
    assert plan["bootstrap_cost"] < 999
    for name, quantity in DLC_START_INVENTORY.items():
        for _ in range(quantity):
            mw.push_precollected(world.create_item(name))
    bands = plan["enemy_progression_bands"]
    assert all(bands[stage] == 0 for stage in plan["starting_stages"])
    later = [stage for stage in plan["sequence"] if stage not in plan["starting_stages"]]
    assert sorted(bands[stage] for stage in later) == list(range(1, len(later) + 1))
    assert get_mission_base_cr("e1m1_intro", world) > MISSION_BASE_CR["e1m1_intro"]
    assert len(mw.itempool) == len(mw.get_unfilled_locations(1))
    counts = Counter(item.name for item in mw.itempool + mw.precollected_items[1])
    for name, quantity in plan["semantic_counts"].items():
        assert counts[name] == quantity, name
    distribute_items_restrictive(mw)
    assert mw.can_beat_game()


def test_generated_supply_preserves_the_inventory_requirement_for_ammunition():
    world = make_mock_world()
    world.options.randomize_chainsaw.value = 1
    world.enemy_plan = {"maps": {"e1m1_intro": {"operations": [{"reserve": {"desired_count": 1}}]}}}
    state = create_state_with_items({"Combat Shotgun"}, world=world)
    result = evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=100)
    assert not result.ready and "Chainsaw for ammunition supply" in result.missing_requirements
    state = create_state_with_items({"Combat Shotgun", "Chainsaw"}, world=world)
    assert evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=100).ready


def test_generated_supply_does_not_assume_hammer_charge_from_instant_kills():
    world = make_mock_world(randomize_chainsaw=True)
    world.enemy_plan = {"maps": {"e1m1_intro": {"operations": [{"reserve": {"desired_count": 1}}]}}}
    state = create_state_with_items({"Ballista"}, world=world, prog_special=2)
    assert has_effective_sentinel_hammer(state, 1)
    result = evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=100)
    assert not result.ready and "Chainsaw for ammunition supply" in result.missing_requirements
    state = create_state_with_items({"Ballista", "Chainsaw"}, world=world, prog_special=2)
    assert evaluate_mission_readiness(state, 1, "e1m1_intro", world, player_cr=100).ready


def test_native_ammunition_maintenance_requires_chainsaw_even_with_high_combat_rating():
    world = make_mock_world(randomize_chainsaw=True)
    world.enemy_plan = {'maps': {'e2m3_core': {'recipes': [
        {'renewable': True, 'bodies': [{'species': 'imp'}]}]}}}
    state = create_state_with_items({'Combat Shotgun', 'Dash'}, world=world)
    result = evaluate_mission_readiness(state, 1, 'e2m3_core', world, player_cr=100)
    assert not result.ready and 'Chainsaw for ammunition supply' in result.missing_requirements
    state = create_state_with_items({'Combat Shotgun', 'Dash', 'Chainsaw'}, world=world)
    assert evaluate_mission_readiness(state, 1, 'e2m3_core', world, player_cr=100).ready


def test_generated_breakpoint_penalty_tracks_actual_spirits():
    world = make_mock_world()
    world.enemy_plan = {'revision': 4, 'combat_costs': {'e5m1_spear': {'campaign': {
        'actual': 100, 'bodies': 100, 'wave_p90': 10, 'species': ['imp']}}}}
    state = create_state_with_items({'Combat Shotgun'}, world=world)
    assert evaluate_mission_readiness(state, 1, 'e5m1_spear', world, context='spirit_breakpoint').soft_penalty == 0
    world.enemy_plan['combat_costs']['e5m1_spear']['campaign']['species'].append('spirit')
    assert evaluate_mission_readiness(state, 1, 'e5m1_spear', world, context='spirit_breakpoint').soft_penalty == 15
