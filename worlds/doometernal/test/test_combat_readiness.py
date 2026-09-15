"""DOOM Eternal Archipelago v0.6 — Combat Readiness Solver Integration Tests (P7.6).

Tests cover:
- Base readiness matrix against frozen P7.1 anchors and P7.5 allowances
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
    SKILL_ALLOWANCES,
    SPIRIT_BREAKPOINTS,
    SPIRIT_PENALTY,
    evaluate_mission_readiness,
    get_mission_base_cr,
    get_skill_allowance,
    has_effective_anti_spirit,
    has_effective_sentinel_hammer,
    is_dark_lord_defeated_ready,
    is_mission_ready,
    is_spirit_breakpoint_ready,
)
from worlds.doometernal.items import DoomEternalItem, item_data_table
from test.general import setup_multiworld


def make_mock_world(
    difficulty: int = 2,
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
    world.options = MagicMock()
    world.options.campaign_difficulty = MagicMock(value=difficulty)
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

class TestBaseReadinessMatrix:
    """Test Base CR and Skill Allowance interactions across anchor states (§20)."""

    def test_canonical_catalog_completeness(self):
        """All 20 canonical stages exist in MISSION_BASE_CR."""
        assert len(MISSION_BASE_CR) == 20
        for stage_id in STAGE_BY_ID:
            assert stage_id in MISSION_BASE_CR

    def test_skill_allowances_values(self):
        """Skill allowances exactly match frozen P7.5 values."""
        assert get_skill_allowance(0) == 6   # ITYTD
        assert get_skill_allowance(1) == 10  # HMP
        assert get_skill_allowance(2) == 15  # UV
        assert get_skill_allowance(3) == 20  # Nightmare
        with pytest.raises(ValueError):
            get_skill_allowance(4)

    def test_hoe12_anchor_a_itytd(self):
        """HoE (12): Anchor A (CR 6) + ITYTD (6) -> ready."""
        world = make_mock_world(difficulty=0)  # ITYTD (allowance 6)
        state = create_state_with_items({"Combat Shotgun"}, world=world)
        res = evaluate_mission_readiness(state, 1, "e1m1_intro", world)
        assert res.player_cr == 6.0
        assert res.mission_base_cr == 12
        assert res.allowance == 6
        assert res.ready is True

    def test_exultia25_anchor_c_itytd(self):
        """Exultia (25): Anchor C (CR 20) + ITYTD (6) -> ready (20 + 6 >= 25)."""
        world = make_mock_world(difficulty=0, randomize_dash=True, randomize_chainsaw=True)
        state = create_state_with_items({"Combat Shotgun", "Chainsaw", "Dash"}, world=world)
        res = evaluate_mission_readiness(state, 1, "e1m2_war", world)
        assert res.player_cr == 20.0
        assert res.mission_base_cr == 25
        assert res.allowance == 6
        assert res.ready is True

    def test_cultist42_anchor_c_nightmare(self):
        """Cultist Base (42): Anchor C (CR 20) + Nightmare (20) -> NOT ready (20 + 20 = 40 < 42)."""
        world = make_mock_world(difficulty=3, randomize_dash=True, randomize_chainsaw=True)
        state = create_state_with_items({"Combat Shotgun", "Chainsaw", "Dash"}, world=world)
        res = evaluate_mission_readiness(state, 1, "e1m3_cult", world)
        assert res.player_cr == 20.0
        assert res.mission_base_cr == 42
        assert res.allowance == 20
        assert res.ready is False

    def test_doom_hunter50_anchor_f_hmp(self):
        """Doom Hunter Base (50): Anchor F (CR 42.75) + HMP (10) -> ready (42.75 + 10 = 52.75 >= 50)."""
        world = make_mock_world(difficulty=1, randomize_dash=True, randomize_chainsaw=True)
        state = create_state_with_items({
            "Combat Shotgun", "Sticky Bombs", "Chaingun",
            "Energy Shield", "Chainsaw", "Dash",
        }, world=world)
        res = evaluate_mission_readiness(state, 1, "e1m4_boss", world)
        assert res.player_cr == 42.75
        assert res.mission_base_cr == 50
        assert res.allowance == 10
        assert res.ready is True

    def test_sentinel_prime55_anchor_f_boundary(self):
        """Sentinel Prime (55): Anchor F (CR 42.75): HMP (10) -> NOT ready; UV (15) -> ready."""
        world_hmp = make_mock_world(difficulty=1, randomize_dash=True, randomize_chainsaw=True)
        world_uv = make_mock_world(difficulty=2, randomize_dash=True, randomize_chainsaw=True)
        items = {
            "Combat Shotgun", "Sticky Bombs", "Chaingun",
            "Energy Shield", "Chainsaw", "Dash",
        }
        state_hmp = create_state_with_items(items, world=world_hmp)
        state_uv = create_state_with_items(items, world=world_uv)
        # HMP: 42.75 + 10 = 52.75 < 55 -> False
        assert evaluate_mission_readiness(state_hmp, 1, "e2m4_boss", world_hmp).ready is False
        # UV: 42.75 + 15 = 57.75 >= 55 -> True
        assert evaluate_mission_readiness(state_uv, 1, "e2m4_boss", world_uv).ready is True

    def test_arc63_anchor_g_ready_everywhere(self):
        """ARC Complex (63): Anchor G (CR 62.1) -> ready on all difficulties (even ITYTD 6)."""
        items = {
            "Ballista", "Combat Shotgun", "Rocket Launcher",
            "Chainsaw", "Flame Belch", "Dash", "Ice Bomb",
        }
        for diff in (0, 1, 2, 3):
            world = make_mock_world(difficulty=diff, randomize_dash=True, randomize_chainsaw=True)
            state = create_state_with_items(items, world=world)
            res = evaluate_mission_readiness(state, 1, "e2m2_base", world)
            assert res.player_cr == 62.1
            assert res.ready is True

    def test_reclaimed77_anchor_g_uv(self):
        """Reclaimed Earth (77): Anchor G (CR 62.1) + UV (15) -> ready (62.1 + 15 = 77.1 >= 77)."""
        world = make_mock_world(difficulty=2, randomize_dash=True, randomize_chainsaw=True)
        items = {
            "Ballista", "Combat Shotgun", "Rocket Launcher",
            "Chainsaw", "Flame Belch", "Dash", "Ice Bomb",
        }
        state = create_state_with_items(items, world=world)
        res = evaluate_mission_readiness(state, 1, "e5m2_earth", world)
        assert res.player_cr == 62.1
        assert res.mission_base_cr == 77
        assert res.ready is True

    def test_final_sin87_anchor_h_boundary(self):
        """Final Sin (87): Anchor H (CR 67.5): UV (15) -> NOT ready; NM (20) -> ready."""
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher",
            "Chainsaw", "Flame Belch", "Ice Bomb", "Dash",
        }
        world_uv = make_mock_world(difficulty=2, randomize_dash=True, randomize_chainsaw=True)
        world_nm = make_mock_world(difficulty=3, randomize_dash=True, randomize_chainsaw=True)
        state_uv = create_state_with_items(items, world=world_uv)
        state_nm = create_state_with_items(items, world=world_nm)
        # UV: 67.5 + 15 = 82.5 < 87 -> False
        assert evaluate_mission_readiness(state_uv, 1, "e3m4_boss", world_uv).ready is False
        # NM: 67.5 + 20 = 87.5 >= 87 -> True
        assert evaluate_mission_readiness(state_nm, 1, "e3m4_boss", world_nm).ready is True

    def test_holt94_anchor_i_itytd(self):
        """The Holt (94): Anchor I (CR 89) + ITYTD (6) -> ready (89 + 6 = 95 >= 94)."""
        world = make_mock_world(difficulty=0, randomize_dash=True, randomize_chainsaw=True)
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher",
            "Heavy Cannon", "Plasma Rifle", "Combat Shotgun",
            "Chainsaw", "Flame Belch", "Ice Bomb", "Dash",
            "Air Control", "Precision Bolt", "Lock-on Burst",
            "Energy Shield", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=2, ammo_stages=2)
        res = evaluate_mission_readiness(state, 1, "e4m3_mcity", world)
        assert res.player_cr == 89.0
        assert res.mission_base_cr == 94
        assert res.ready is True


# ═══════════════════════════════════════════════════════════════
# §21 — Spirit Breakpoint Tests
# ═══════════════════════════════════════════════════════════════

class TestSpiritBreakpoints:
    """Test Spirit severe soft penalties (+15, cap 100) and capability checks (§21)."""

    @pytest.mark.parametrize("stage_id, base_cr, expected_penalized", [
        ("e5m1_spear", 75, 90),
        ("e5m2_earth", 77, 92),
        ("e5m3_hell", 82, 97),
        ("e4m2_swamp", 88, 100),
        ("e4m3_mcity", 94, 100),
    ])
    def test_spirit_breakpoint_effective_cr(self, stage_id, base_cr, expected_penalized):
        """Without anti-spirit: Effective CR = min(100, Base + 15). With anti-spirit: Effective CR = Base."""
        world = make_mock_world(difficulty=2)
        # 1. State WITHOUT Microwave Beam
        state_no_mb = create_state_with_items({"Combat Shotgun"}, world=world)
        res_no_mb = evaluate_mission_readiness(state_no_mb, 1, stage_id, world, context="spirit_breakpoint")
        assert res_no_mb.mission_base_cr == base_cr
        assert res_no_mb.soft_penalty == SPIRIT_PENALTY
        assert res_no_mb.effective_cr == expected_penalized

        # 2. State WITH Plasma Rifle + Microwave Beam
        state_mb = create_state_with_items({"Combat Shotgun", "Plasma Rifle", "Microwave Beam"}, world=world)
        res_mb = evaluate_mission_readiness(state_mb, 1, stage_id, world, context="spirit_breakpoint")
        assert res_mb.soft_penalty == 0
        assert res_mb.effective_cr == base_cr

    def test_orphan_microwave_beam_penalty_persists(self):
        """Orphan Microwave Beam without Plasma Rifle does NOT remove the Spirit penalty."""
        world = make_mock_world(difficulty=2)
        # Owns Microwave Beam but lacks Plasma Rifle
        state = create_state_with_items({"Combat Shotgun", "Microwave Beam"}, world=world)
        assert has_effective_anti_spirit(state, 1) is False
        res = evaluate_mission_readiness(state, 1, "e4m2_swamp", world, context="spirit_breakpoint")
        assert res.soft_penalty == SPIRIT_PENALTY
        assert res.effective_cr == 100

    def test_pre_vs_post_breakpoint_topological_reachability(self):
        """In real generation, pre-breakpoint regions require only Base CR, while post-breakpoint requires Spirit readiness."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=100,
            options={
                "mission_pool": "dlc_only",
                "goal": "kill_the_dark_lord",
                "campaign_difficulty": 2,  # UV (allowance 15)
                "dlc_logic_timing": "from_the_beginning",
            },
        )
        world: DoomEternalWorld = mw.worlds[1]

        # The Blood Swamps: Base CR 88, Breakpoint connection into Sunken Courtyard
        # Player CR 75 + UV 15 = 90 >= 88 (Base ready)
        # Without Microwave Beam, post-breakpoint effective CR is 100 (90 < 100 -> NOT ready)
        # With Plasma + Microwave Beam, post-breakpoint effective CR is 88 (90 >= 88 -> ready)

        # Region before breakpoint: "The Blood Swamps - Underworld Crossroad"
        # Region after breakpoint: "The Blood Swamps - Sunken Courtyard"
        crossroad_region = mw.get_region("The Blood Swamps - Underworld Crossroad", 1)
        courtyard_region = mw.get_region("The Blood Swamps - Sunken Courtyard", 1)

        # Build loadout with 75 <= CR < 85 without Microwave Beam
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher", "Heavy Cannon",
            "Chainsaw", "Ice Bomb", "Blood Punch", "Dash",
            "Air Control", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=2, ammo_stages=1)
        # Mark structural access to swamp
        state.collect(DoomEternalItem("Internal Mission Clear: UAC Atlantica Facility", ItemClassification.progression, None, 1))

        res_base = evaluate_mission_readiness(state, 1, "e4m2_swamp", world)
        assert 75.0 <= res_base.player_cr < 85.0
        assert res_base.ready is True  # Base CR 88 is satisfied!

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

    def test_cr80_uv15_boundary_without_hammer(self):
        """CR 80 + UV (15) without Hammer: 80 + 15 = 95 >= 95 -> ready exactly at boundary."""
        world = make_mock_world(difficulty=2, special_weapon="The Crucible")
        # Build exact 80.0 CR loadout
        # Base 5-weapon + primary runes + masteries (Anchor LATE_BASE = 80.0)
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher", "Heavy Cannon", "Combat Shotgun",
            "Chainsaw", "Flame Belch", "Ice Bomb", "Dash", "Blood Punch",
            "Precision Bolt", "Lock-on Burst", "Air Control", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=2, armor_stages=1, ammo_stages=2)
        res = evaluate_mission_readiness(state, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res.player_cr >= 80.0
        assert res.soft_penalty == DARK_LORD_HAMMER_PENALTY
        assert res.allowance == 15
        assert res.ready is True

    def test_cr80_hmp10_not_ready_without_hammer(self):
        """CR 80 + HMP (10) without Hammer: 80 + 10 = 90 < 95 -> NOT ready."""
        world = make_mock_world(difficulty=1, special_weapon="The Crucible")
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher", "Heavy Cannon", "Combat Shotgun",
            "Chainsaw", "Ice Bomb", "Dash", "Blood Punch",
            "Precision Bolt", "Air Control", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=2, ammo_stages=2)
        res = evaluate_mission_readiness(state, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res.player_cr >= 80.0
        assert res.allowance == 10
        assert res.ready is False

    def test_cr89_itytd6_ready_without_hammer(self):
        """CR 89 + ITYTD (6) without Hammer: 89 + 6 = 95 >= 95 -> ready."""
        world = make_mock_world(difficulty=0, special_weapon="The Crucible")
        items = {
            "Ballista", "Super Shotgun", "Rocket Launcher",
            "Heavy Cannon", "Plasma Rifle", "Combat Shotgun",
            "Chainsaw", "Flame Belch", "Ice Bomb", "Dash",
            "Air Control", "Precision Bolt", "Lock-on Burst",
            "Energy Shield", "Faster Weapon Swap",
        }
        state = create_state_with_items(items, world=world, health_stages=2, ammo_stages=2)
        res = evaluate_mission_readiness(state, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res.player_cr == 89.0
        assert res.allowance == 6
        assert res.ready is True

    def test_progressive_special_weapon_stages(self):
        """Progressive Special Weapon: Stage 1 = Crucible (penalty applies), Stage 2+ = Hammer (penalty removed)."""
        world = make_mock_world(difficulty=2, special_weapon="Progressive Special Weapon")
        # Stage 1: only Crucible
        state_s1 = create_state_with_items({"Combat Shotgun"}, world=world, prog_special=1)
        assert has_effective_sentinel_hammer(state_s1, 1, "Progressive Special Weapon") is False
        res_s1 = evaluate_mission_readiness(state_s1, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res_s1.soft_penalty == DARK_LORD_HAMMER_PENALTY

        # Stage 2: Sentinel Hammer unlocked
        state_s2 = create_state_with_items({"Combat Shotgun"}, world=world, prog_special=2)
        assert has_effective_sentinel_hammer(state_s2, 1, "Progressive Special Weapon") is True
        res_s2 = evaluate_mission_readiness(state_s2, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res_s2.soft_penalty == 0

    def test_progressive_sentinel_hammer_stages(self):
        """Progressive Sentinel Hammer: Stage 1+ unlocks Hammer."""
        world = make_mock_world(difficulty=2, special_weapon="Progressive Sentinel Hammer")
        state = create_state_with_items({"Combat Shotgun"}, world=world, prog_hammer=1)
        assert has_effective_sentinel_hammer(state, 1, "Progressive Sentinel Hammer") is True
        res = evaluate_mission_readiness(state, 1, DARK_LORD_STAGE_ID, world, context="dark_lord_defeated")
        assert res.soft_penalty == 0


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
                "campaign_difficulty": 0,  # ITYTD (allowance 6)
            },
        )
        world: DoomEternalWorld = mw.worlds[1]
        plan = world.campaign_plan

        # Suppose stage 2 in sequence is a high-CR stage (e.g. Urdak or Final Sin)
        # Clear stage 1 to structurally reveal stage 2
        stage1_id = plan["sequence"][0]
        stage2_id = plan["sequence"][1]

        state = CollectionState(mw)
        # Empty state with start inventory (Combat Shotgun CR 6 + allowance 6 = 12)
        # Stage 1 (e1m1_intro or other)
        # Mark stage 1 clear event
        from worlds.doometernal.campaign import completion_event
        state.collect(DoomEternalItem(completion_event(stage1_id), ItemClassification.progression, None, 1))

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
                "campaign_difficulty": 0,  # ITYTD (allowance 6)
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
                "goal": "kill_the_dark_lord",
                "randomize_dash": 0,
                "campaign_difficulty": 2,
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

    def test_sphere_zero_base_rmo(self):
        """Base RMO: Hell on Earth starts ready at frame zero on all difficulties."""
        for diff in (0, 1, 2, 3):
            mw = setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options={
                    "mission_pool": "base",
                    "mission_order": "random_mission_order",
                    "campaign_difficulty": diff,
                },
            )
            world: DoomEternalWorld = mw.worlds[1]
            state = CollectionState(mw)
            start_stage = world.campaign_plan["starting_stages"][0]
            if start_stage == "e1m1_intro":
                res = evaluate_mission_readiness(state, 1, "e1m1_intro", world)
                assert res.ready is True, f"HoE must be ready at sphere zero on diff {diff}"
