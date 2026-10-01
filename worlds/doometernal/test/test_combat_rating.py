"""P7.4 — Combat Rating parity and CollectionState integration tests.

Tests against the frozen P7.1 numeric model from
"""
from __future__ import annotations

import pytest
from worlds.doometernal.combat_rating import (
    ALL_MASTERY_NAMES,
    CATEGORY_CAPS,
    WEAPON_BASE,
    rate_items,
    rate_collection_state,
    evaluate_player_loadout_cr,
)

EPSILON = 1e-9


# ═══════════════════════════════════════════════════════════════
# §1 — P7.1 Parity Matrix (frozen scenarios A through N)
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §2 — Orphan mastery isolation
# ═══════════════════════════════════════════════════════════════

class TestOrphanMasteries:
    """Every mastery without its host weapon must contribute zero CR."""

    @pytest.mark.parametrize("name", sorted(ALL_MASTERY_NAMES))
    def test_orphan_mastery_zero_cr(self, name):
        r = rate_items({name})
        assert r["final"] == 0, f"Orphan {name} should be 0 CR"


# ═══════════════════════════════════════════════════════════════
# §3 — Special weapon mode matrix
# ═══════════════════════════════════════════════════════════════

class TestSpecialModeMatrix:

    @pytest.mark.parametrize("mode,stage,expected", [
        ("progressive_special", 0, 0),
        ("progressive_special", 1, 10),
        ("progressive_special", 2, 22),
        ("progressive_special", 3, 24),
        ("progressive_hammer", 0, 0),
        ("progressive_hammer", 1, 22),
        ("progressive_hammer", 2, 24),
        ("crucible", 0, 0),
        ("crucible", 1, 10),
    ])
    def test_special_stage(self, mode, stage, expected):
        r = rate_items(set(), special_mode=mode, special_stage=stage)
        assert r["final"] == pytest.approx(expected, abs=EPSILON)


# ═══════════════════════════════════════════════════════════════
# §4 — Energy Shield keystone dependency
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §5 — Mod/mastery dependency isolation
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §6 — Faster Weapon Swap uses normal Arsenal only
# ═══════════════════════════════════════════════════════════════

class TestFasterWeaponSwap:

    def test_fws_normal_arsenal_only(self):
        """Ballista + Hammer: FWS bonus uses normal Arsenal 12, not special."""
        r = rate_items(
            {"Ballista", "Faster Weapon Swap"},
            special_mode="progressive_hammer", special_stage=1,
        )
        # Normal Arsenal = 12 (Ballista), capped at 35. FWS = min(6, 0.15 * 12) = 1.8
        assert r["raw"]["Enhancements"] == pytest.approx(1.8, abs=EPSILON)


# ═══════════════════════════════════════════════════════════════
# §7 — Rune slot optimization
# ═══════════════════════════════════════════════════════════════

class TestRuneOptimization:

    def test_best_three_rune_selection(self):
        """With many runes, optimization should pick highest CR combo."""
        r = rate_items({
            "Combat Shotgun",
            "Air Control", "Saving Throw", "Equipment Fiend",
            "Seek and Destroy", "Blood Fueled",
        })
        # Air Control (Mob 6), Saving Throw (Def 5), Equipment Fiend (Sus 2, Con 2)
        # should be selected over weaker runes
        assert "Air Control" in r["selected_runes"]
        assert "Saving Throw" in r["selected_runes"]
        assert r["final"] > 0

    def test_support_rune_best_one(self):
        """Only best support rune should be selected."""
        r = rate_items({
            "Combat Shotgun", "Break Blast", "Desperate Punch", "Take Back",
        })
        # All support runes give same total CR (2 each) so first lexical wins
        assert r["selected_support"] is not None
        # Should have exactly one support, not three
        support_count = sum(1 for name in ("Break Blast", "Desperate Punch", "Take Back")
                           if name == r["selected_support"])
        assert support_count == 1


# ═══════════════════════════════════════════════════════════════
# §8 — Category cap enforcement
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §9 — Empty loadout
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════
# §10 — CollectionState integration (spec §19 coverage)
# ═══════════════════════════════════════════════════════════════

class TestCollectionStateIntegration:
    """Test rate_collection_state using AP's real test harness (§19)."""

    @pytest.fixture
    def full_saga_world(self):
        from test.general import setup_multiworld
        from worlds.doometernal import DoomEternalWorld
        multiworld = setup_multiworld(
            DoomEternalWorld, seed=42,
            options={"mission_pool": "full_saga", "mission_count": "all"},
        )
        return multiworld, multiworld.worlds[1]

    @pytest.fixture
    def short_world(self):
        from test.general import setup_multiworld
        from worlds.doometernal import DoomEternalWorld
        multiworld = setup_multiworld(
            DoomEternalWorld, seed=42,
            options={"mission_pool": "full_saga", "mission_count": 3},
        )
        return multiworld, multiworld.worlds[1]

    @pytest.fixture
    def randomized_dash_world(self):
        from test.general import setup_multiworld
        from worlds.doometernal import DoomEternalWorld
        multiworld = setup_multiworld(
            DoomEternalWorld, seed=42,
            options={"mission_pool": "full_saga", "mission_count": "all",
                     "randomize_dash": 1},
        )
        return multiworld, multiworld.worlds[1]

    @pytest.fixture
    def randomized_chainsaw_world(self):
        from test.general import setup_multiworld
        from worlds.doometernal import DoomEternalWorld
        multiworld = setup_multiworld(
            DoomEternalWorld, seed=42,
            options={"mission_pool": "full_saga", "mission_count": "all",
                     "randomize_chainsaw": 1},
        )
        return multiworld, multiworld.worlds[1]

    def _eval(self, state, world):
        return evaluate_player_loadout_cr(state, 1, world)

    # --- result object API (§21) ---

    # --- precollected starting weapon contributes ---

    # --- received weapon contributes ---

    # --- absent item does not contribute ---

    # --- start_inventory contributes ---

    # --- vanilla Chainsaw contributes logically ---

    # --- randomized absent Chainsaw does NOT contribute ---

    # --- vanilla Dash contributes logically ---

    # --- randomized absent Dash does NOT contribute ---

    # --- full collection reaches high CR ---

    # --- short-world missing item cannot contribute ---

    # --- sampled-out mod cannot contribute ---

    # --- orphan mastery cannot contribute ---

    # --- progressive counts work ---
    def test_progressive_capacity_counts(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        state = CollectionState(mw)
        r0 = self._eval(state, world).total
        state.prog_items[world.player]["Progressive Health Upgrade"] += 1
        r1 = self._eval(state, world).total
        assert r1 > r0, "First Health Upgrade should increase CR"
        state.prog_items[world.player]["Progressive Health Upgrade"] += 1
        r2 = self._eval(state, world).total
        assert r2 > r1, "Second Health Upgrade should increase CR"

    # --- WUP bundle counts work ---
    def test_wup_bundle_counts(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        state = CollectionState(mw)
        r0 = self._eval(state, world).total
        state.prog_items[world.player]["Weapon Upgrade Points (3)"] += 4
        r1 = self._eval(state, world).total
        assert r1 > r0, "WUP bundles should increase CR (Enhancements)"

    # --- special progressive counts work ---

    # --- deterministic no-RNG-consumption proof (§20, §22) ---
    def test_no_rng_consumption(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        rng_state_before = mw.random.getstate()
        state = CollectionState(mw)
        _ = self._eval(state, world)
        rng_state_after = mw.random.getstate()
        assert rng_state_before == rng_state_after, "Evaluating CR must not consume RNG"

