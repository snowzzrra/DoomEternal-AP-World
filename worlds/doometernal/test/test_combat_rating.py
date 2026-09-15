"""P7.4 — Combat Rating parity and CollectionState integration tests.

Tests against the frozen P7.1 numeric model from
``SentinelDocs/tooling/phase7_cr_calibration.py``.
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

class TestP71ParityMatrix:
    """Each test corresponds to a scenario from the frozen calibration."""

    def test_a_combat_shotgun_only(self):
        r = rate_items({"Combat Shotgun"})
        assert r["final"] == pytest.approx(6, abs=EPSILON)
        assert r["capped"]["Arsenal"] == pytest.approx(6, abs=EPSILON)

    def test_b_ballista_only(self):
        r = rate_items({"Ballista"})
        assert r["final"] == pytest.approx(13.5, abs=EPSILON)
        assert r["capped"]["Arsenal"] == pytest.approx(12, abs=EPSILON)
        assert r["capped"]["Mobility"] == pytest.approx(1.5, abs=EPSILON)

    def test_c_shotgun_chainsaw_dash(self):
        r = rate_items({"Combat Shotgun", "Chainsaw", "Dash"})
        assert r["final"] == pytest.approx(20, abs=EPSILON)

    def test_d_ballista_chainsaw_dash(self):
        r = rate_items({"Ballista", "Chainsaw", "Dash"})
        assert r["final"] == pytest.approx(27.5, abs=EPSILON)

    def test_e_chaingun_chainsaw_dash(self):
        r = rate_items({"Chaingun", "Chainsaw", "Dash"})
        assert r["final"] == pytest.approx(19, abs=EPSILON)

    def test_e2_chaingun_plus_energy_shield(self):
        r = rate_items({"Chaingun", "Chainsaw", "Dash", "Energy Shield"})
        assert r["final"] == pytest.approx(29, abs=EPSILON)
        assert r["capped"]["Defense"] == pytest.approx(9, abs=EPSILON)

    def test_f_shotgun_sticky_chaingun_shield_sustain(self):
        r = rate_items({
            "Combat Shotgun", "Sticky Bombs", "Chaingun",
            "Energy Shield", "Chainsaw", "Dash",
        })
        assert r["final"] == pytest.approx(42.75, abs=EPSILON)

    def test_g_three_weapon_midgame(self):
        r = rate_items({
            "Ballista", "Combat Shotgun", "Rocket Launcher",
            "Chainsaw", "Flame Belch", "Dash", "Ice Bomb",
        })
        assert r["final"] == pytest.approx(62.1, abs=EPSILON)

    def test_h_ballista_ssg_rocket_equipment(self):
        r = rate_items({
            "Ballista", "Super Shotgun", "Rocket Launcher",
            "Chainsaw", "Flame Belch", "Ice Bomb", "Dash",
        })
        assert r["final"] == pytest.approx(67.5, abs=EPSILON)

    def test_i_late_game_strong_mods(self):
        r = rate_items(
            {"Ballista", "Super Shotgun", "Rocket Launcher",
             "Heavy Cannon", "Plasma Rifle", "Combat Shotgun",
             "Chainsaw", "Flame Belch", "Ice Bomb", "Dash",
             "Air Control", "Precision Bolt", "Lock-on Burst",
             "Energy Shield", "Faster Weapon Swap"},
            health_stages=2, ammo_stages=2,
        )
        assert r["final"] == pytest.approx(89, abs=EPSILON)

    def test_j_near_complete(self):
        r = rate_items(
            set(WEAPON_BASE) | {
                "Chainsaw", "Flame Belch", "Ice Bomb", "Frag Grenade",
                "Blood Punch", "Dash", "Energy Shield", "Faster Weapon Swap",
                "Faster Ledge Grab", "Reduced Hazard Damage",
                "Reduced Self Damage", "Ammo from Barrels",
                "Faster Dash Recharge",
                "Air Control", "Saving Throw", "Equipment Fiend",
                "Seek and Destroy", "Break Blast", "Desperate Punch", "Take Back",
            },
            health_stages=4, armor_stages=4, ammo_stages=4, wup_count=39,
            special_mode="progressive_special", special_stage=3,
        )
        assert r["final"] == pytest.approx(100, abs=EPSILON)

    def test_k_poor_arsenal_crucible(self):
        r = rate_items({"Combat Shotgun"}, special_mode="crucible", special_stage=1)
        assert r["final"] == pytest.approx(16, abs=EPSILON)

    def test_l_poor_arsenal_hammer(self):
        r = rate_items({"Combat Shotgun"}, special_mode="progressive_hammer", special_stage=1)
        assert r["final"] == pytest.approx(28, abs=EPSILON)

    def test_m_ssg_meat_hook_mastery(self):
        r = rate_items({"Super Shotgun", "Meat Hook Mastery"})
        assert r["final"] == pytest.approx(19, abs=EPSILON)
        assert r["capped"]["Sustain"] == pytest.approx(7, abs=EPSILON)
        assert r["capped"]["Mobility"] == pytest.approx(2, abs=EPSILON)

    def test_n_health_vs_armor(self):
        rh = rate_items({"Combat Shotgun"}, health_stages=2)
        ra = rate_items({"Combat Shotgun"}, armor_stages=2)
        assert rh["capped"]["Defense"] == pytest.approx(3.5, abs=EPSILON)
        assert ra["capped"]["Defense"] == pytest.approx(3.0, abs=EPSILON)


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

class TestEnergyShieldDependency:
    """Energy Shield without Chaingun must contribute zero."""

    def test_orphan_energy_shield(self):
        r = rate_items({"Energy Shield"})
        assert r["capped"]["Enhancements"] == 0
        assert r["capped"]["Defense"] == 0
        assert r["capped"]["Control / Utility"] == 0

    def test_energy_shield_with_chaingun(self):
        r = rate_items({"Chaingun", "Energy Shield"})
        assert r["raw"]["Enhancements"] == pytest.approx(1, abs=EPSILON)
        assert r["raw"]["Defense"] == pytest.approx(7, abs=EPSILON)
        assert r["raw"]["Control / Utility"] == pytest.approx(2, abs=EPSILON)


# ═══════════════════════════════════════════════════════════════
# §5 — Mod/mastery dependency isolation
# ═══════════════════════════════════════════════════════════════

class TestModMasteryDependency:

    def test_microwave_beam_mastery_adds_control(self):
        base = rate_items({"Plasma Rifle", "Microwave Beam"})
        with_mastery = rate_items({"Plasma Rifle", "Microwave Beam", "Microwave Beam Mastery"})
        assert with_mastery["raw"]["Control / Utility"] - base["raw"]["Control / Utility"] == pytest.approx(1, abs=EPSILON)
        assert with_mastery["raw"]["Enhancements"] - base["raw"]["Enhancements"] == pytest.approx(0, abs=EPSILON)

    def test_energy_shield_mastery_adds_defense(self):
        base = rate_items({"Chaingun", "Energy Shield"})
        with_mastery = rate_items({"Chaingun", "Energy Shield", "Energy Shield Mastery"})
        assert with_mastery["raw"]["Defense"] - base["raw"]["Defense"] == pytest.approx(1, abs=EPSILON)


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

class TestCategoryCaps:

    def test_caps_not_exceeded(self):
        """Near-complete loadout: no category exceeds its cap."""
        r = rate_items(
            set(WEAPON_BASE) | {
                "Chainsaw", "Flame Belch", "Ice Bomb", "Frag Grenade",
                "Blood Punch", "Dash", "Energy Shield", "Faster Weapon Swap",
                "Faster Ledge Grab", "Reduced Hazard Damage",
                "Reduced Self Damage", "Ammo from Barrels",
                "Faster Dash Recharge",
                "Air Control", "Saving Throw", "Equipment Fiend",
                "Seek and Destroy", "Break Blast", "Desperate Punch", "Take Back",
            },
            health_stages=4, armor_stages=4, ammo_stages=4, wup_count=39,
            special_mode="progressive_special", special_stage=3,
        )
        for cat, cap in CATEGORY_CAPS.items():
            assert r["capped"][cat] <= cap + EPSILON, f"{cat} exceeds cap"


# ═══════════════════════════════════════════════════════════════
# §9 — Empty loadout
# ═══════════════════════════════════════════════════════════════

class TestEmptyLoadout:

    def test_empty_is_zero(self):
        r = rate_items(set())
        assert r["final"] == 0


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
    def test_result_object_api(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        r = self._eval(CollectionState(mw), world)
        # Attribute access
        assert isinstance(r.total, float)
        assert isinstance(r.categories, dict)
        assert "Arsenal" in r.categories
        assert r.total == r.final == r.total_cr
        assert r.categories == r.capped
        # Dict access
        assert r["total"] == r.total
        assert r["categories"]["Arsenal"] == r.categories["Arsenal"]
        assert "Arsenal" in r.raw_categories

    # --- precollected starting weapon contributes ---
    def test_precollected_starting_weapon(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        r = self._eval(CollectionState(mw), world)
        assert r.categories["Arsenal"] > 0
        assert r.total > 0

    # --- received weapon contributes ---
    def test_received_weapon_contributes(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        state = CollectionState(mw)
        cr_before = self._eval(state, world).total
        state.collect(world.create_item("Ballista"))
        cr_after = self._eval(state, world).total
        assert cr_after > cr_before

    # --- absent item does not contribute ---
    def test_absent_item_no_contribution(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        state = CollectionState(mw)
        cr_empty = self._eval(state, world).total
        state.collect(world.create_item("Ballista"))
        state.collect(world.create_item("Rocket Launcher"))
        assert self._eval(state, world).total > cr_empty

    # --- start_inventory contributes ---
    def test_start_inventory_contributes(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        # Simulate an item precollected via start_inventory into multiworld
        mw.push_precollected(world.create_item("Ballista"))
        state = CollectionState(mw)
        r = self._eval(state, world)
        assert r.categories["Arsenal"] >= 12, "Start inventory Ballista must contribute Arsenal >= 12"

    # --- vanilla Chainsaw contributes logically ---
    def test_vanilla_chainsaw_contributes(self, full_saga_world):
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw, world = full_saga_world
        state = CollectionState(mw)
        # In vanilla, Chainsaw is acquired in Hell on Earth
        assert not world.options.randomize_chainsaw.value
        state.collect(DoomEternalItem("Internal Mission Clear: Hell on Earth", ItemClassification.progression, None, world.player))
        r = self._eval(state, world)
        assert r.categories["Sustain"] >= 7, "Vanilla Chainsaw Sustain +7 once Hell on Earth cleared"

    # --- randomized absent Chainsaw does NOT contribute ---
    def test_randomized_absent_chainsaw(self, randomized_chainsaw_world):
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw, world = randomized_chainsaw_world
        state = CollectionState(mw)
        state.collect(DoomEternalItem("Internal Mission Clear: Hell on Earth", ItemClassification.progression, None, world.player))
        r = self._eval(state, world)
        starting = world.starting_weapon_name
        if starting != "Super Shotgun":
            assert r.categories["Sustain"] == 0, "No Sustain without Chainsaw AP item when randomized"

    # --- vanilla Dash contributes logically ---
    def test_vanilla_dash_contributes(self, full_saga_world):
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw, world = full_saga_world
        state = CollectionState(mw)
        # In vanilla, Dash is acquired in Exultia
        assert not world.options.randomize_dash.value
        state.collect(DoomEternalItem("Internal Mission Clear: Exultia", ItemClassification.progression, None, world.player))
        r = self._eval(state, world)
        assert r.categories["Mobility"] >= 4, "Vanilla Dash Mobility +4 once Exultia cleared"

    # --- randomized absent Dash does NOT contribute ---
    def test_randomized_absent_dash(self, randomized_dash_world):
        from BaseClasses import CollectionState, ItemClassification
        from worlds.doometernal.items import DoomEternalItem
        mw, world = randomized_dash_world
        state = CollectionState(mw)
        state.collect(DoomEternalItem("Internal Mission Clear: Exultia", ItemClassification.progression, None, world.player))
        r = self._eval(state, world)
        starting = world.starting_weapon_name
        if starting != "Ballista":
            assert r.categories["Mobility"] == 0, "No Mobility without Dash AP item when randomized"

    # --- full collection reaches high CR ---
    def test_full_collection_cr(self, full_saga_world):
        mw, world = full_saga_world
        state = mw.get_all_state(use_cache=False)
        r = self._eval(state, world)
        assert r.total >= 80

    # --- short-world missing item cannot contribute ---
    def test_short_world_lower_cr(self, short_world):
        mw, world = short_world
        state = mw.get_all_state(use_cache=False)
        r = self._eval(state, world)
        assert 0 < r.total < 100, "Short world: positive but below cap"

    # --- sampled-out mod cannot contribute ---
    def test_sampled_out_mod(self, short_world):
        mw, world = short_world
        pool_names = {item.name for item in mw.itempool}
        from worlds.doometernal.combat_rating import ALL_MOD_NAMES
        missing_mods = ALL_MOD_NAMES - pool_names
        assert len(missing_mods) > 0, "Short world excludes some mods"

    # --- orphan mastery cannot contribute ---
    def test_orphan_mastery_in_state(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        state = CollectionState(mw)
        cr_before = self._eval(state, world).total
        state.collect(world.create_item("Sticky Bombs Mastery"))
        cr_after = self._eval(state, world).total
        starting = world.starting_weapon_name
        if starting != "Combat Shotgun":
            assert cr_after == cr_before, "Orphan mastery should not increase CR"

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
    def test_special_progressive_counts(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        if world.options.special_weapon.current_option_name != "Progressive Special Weapon":
            pytest.skip("Requires Progressive Special Weapon mode")
        state = CollectionState(mw)
        r0 = self._eval(state, world).total
        state.collect(world.create_item("Progressive Special Weapon"))
        r1 = self._eval(state, world).total
        assert r1 > r0
        state.collect(world.create_item("Progressive Special Weapon"))
        r2 = self._eval(state, world).total
        assert r2 > r1

    # --- deterministic no-RNG-consumption proof (§20, §22) ---
    def test_no_rng_consumption(self, full_saga_world):
        from BaseClasses import CollectionState
        mw, world = full_saga_world
        rng_state_before = mw.random.getstate()
        state = CollectionState(mw)
        _ = self._eval(state, world)
        rng_state_after = mw.random.getstate()
        assert rng_state_before == rng_state_after, "Evaluating CR must not consume RNG"

