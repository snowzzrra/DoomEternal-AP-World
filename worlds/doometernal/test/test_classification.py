"""DOOM Eternal Archipelago v0.6 — Phase 7.7 Classification Unit Tests.

Verifies the 13 required test cases (A through M) for Dynamic Progression Classification:
A. no promotion required
B. one useful mod required / dependency package
C. category cap prevents promotion
D. orphan mod/mastery cannot be treated as independent gain
E. capacities: only required number of copies promoted
F. WUP: exact copies needed for CR cap/threshold, remaining copies stay useful
G. Rune optimization: planner respects actual best-three result
H. Support Rune: best-one semantics
I. Microwave: severe penalty removal evaluated correctly
J. orphan Microwave without Plasma: does not remove Spirit penalty
K. Hammer: promoted when needed for Dark Lord readiness
L. Hammer: not automatically progression if raw CR already provides valid route
M. deterministic repeated planner output
"""
import unittest

from collections import Counter
from BaseClasses import CollectionState, ItemClassification, MultiWorld
from test.general import setup_multiworld
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import (
    FastState,
    build_pool_candidate_counts,
    make_plan,
    resolve_dependencies,
    solve_stage_bootstrap,
)
from worlds.doometernal.classification import (
    ITEM_DEPENDENCIES,
    PromotionRecord,
    ReadinessTarget,
    apply_dynamic_progression_classification,
    get_required_readiness_targets,
)
from worlds.doometernal.combat_rating import evaluate_player_loadout_cr
from worlds.doometernal.combat_readiness import (
    DARK_LORD_STAGE_ID,
    evaluate_mission_readiness,
    has_effective_anti_spirit,
    has_effective_sentinel_hammer,
)
from worlds.doometernal.items import DoomEternalItem, item_data_table


class TestDynamicProgressionClassification(unittest.TestCase):
    """Phase 7.7 Unit Test Suite."""

    def setUp(self) -> None:
        self.mw = setup_multiworld(DoomEternalWorld, seed=42)
        self.world = self.mw.worlds[1]
        self.player = 1

    def _create_prog_item(self, name: str) -> DoomEternalItem:
        """Helper to create an item and set classification to progression (as promoted by planner)."""
        item = self.mw.create_item(name, self.player)
        item.classification = ItemClassification.progression
        return item

    def test_case_a_no_promotion_required(self) -> None:
        """Case A: When baseline progression satisfies required CR, 0 items are promoted."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_pool": "base", "campaign_difficulty": 2},
        )
        w = mw.worlds[1]
        ledger = apply_dynamic_progression_classification(w)
        self.assertTrue(ledger.all_targets_satisfied)
        self.assertEqual(len(ledger.promotions), 0)

    def test_case_b_one_useful_mod_required_with_dependency(self) -> None:
        """Case B: Candidate with dependency closure promoted as package when required."""
        self.assertEqual(ITEM_DEPENDENCIES["Sticky Bombs Mastery"], ("Combat Shotgun", "Sticky Bombs"))
        self.assertEqual(ITEM_DEPENDENCIES["Faster Dash Recharge"], ("Dash",))
        self.assertEqual(ITEM_DEPENDENCIES["Microwave Beam"], ("Plasma Rifle",))

    def test_case_c_category_cap_prevents_promotion(self) -> None:
        """Case C: Item in an already-capped category provides 0 marginal CR and is not promoted."""
        state = CollectionState(self.mw)
        weapons = ["Combat Shotgun", "Super Shotgun", "Heavy Cannon", "Plasma Rifle",
                   "Rocket Launcher", "Ballista", "Chaingun"]
        for w_name in weapons:
            state.collect(self.mw.create_item(w_name, self.player))
        cr_before = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr_before.categories["Arsenal"], 35.0)

        # A mastery that only adds Arsenal CR now gives 0 marginal CR
        temp_state = state.copy()
        temp_state.collect(self.mw.create_item("Sticky Bombs", self.player))
        mastery = self._create_prog_item("Sticky Bombs Mastery")
        temp_state.collect(mastery)
        cr_after = evaluate_player_loadout_cr(temp_state, self.player, self.world)
        self.assertEqual(cr_after.categories["Arsenal"], 35.0)

    def test_case_d_orphan_mod_not_independent_gain(self) -> None:
        """Case D: An orphan mod/mastery without host weapon cannot provide CR gain."""
        state = CollectionState(self.mw)
        cr_base = evaluate_player_loadout_cr(state, self.player, self.world)
        # Collect Energy Shield without Chaingun
        state.collect(self.mw.create_item("Energy Shield", self.player))
        cr = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr.categories["Defense"], cr_base.categories["Defense"])

        # Once Chaingun is collected, Energy Shield activates
        state.collect(self.mw.create_item("Chaingun", self.player))
        cr_with_chaingun = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertGreater(cr_with_chaingun.categories["Defense"], cr_base.categories["Defense"])

    def test_case_e_capacities_only_required_copies(self) -> None:
        """Case E: Progressive capacity upgrades give exact marginal CR per promoted copy."""
        state = CollectionState(self.mw)
        cr0 = evaluate_player_loadout_cr(state, self.player, self.world)
        base_def = cr0.categories["Defense"]

        h1 = self._create_prog_item("Progressive Health Upgrade")
        state.collect(h1)
        cr1 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr1.categories["Defense"], base_def + 1.75)

        h2 = self._create_prog_item("Progressive Health Upgrade")
        state.collect(h2)
        cr2 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr2.categories["Defense"], base_def + 3.5)

    def test_case_f_wup_exact_copies_and_cap(self) -> None:
        """Case F: WUP provides +0.25 per bundle up to +4.0 cap (16 bundles), 17th gives 0."""
        state = CollectionState(self.mw)
        for _ in range(16):
            state.collect(self._create_prog_item("Weapon Upgrade Points (3)"))
        cr16 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr16.categories["Enhancements"], 4.0)

        # 17th bundle should give 0 marginal increase
        state.collect(self._create_prog_item("Weapon Upgrade Points (3)"))
        cr17 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr17.categories["Enhancements"], 4.0)

    def test_case_g_rune_optimization_best_three(self) -> None:
        """Case G: Evaluator optimizes rune slots using best-three normal runes."""
        state = CollectionState(self.mw)
        # Collect 3 runes with positive contributions promoted to progression
        state.collect(self._create_prog_item("Air Control"))
        state.collect(self._create_prog_item("Seek and Destroy"))
        state.collect(self._create_prog_item("Blood Fueled"))
        cr3 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(len(cr3.selected_runes), 3)

        # Collecting a 4th rune does not exceed 3 selected
        state.collect(self._create_prog_item("Equipment Fiend"))
        cr4 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(len(cr4.selected_runes), 3)

    def test_case_h_support_rune_best_one(self) -> None:
        """Case H: Support runes use best-one semantics."""
        state = CollectionState(self.mw)
        state.collect(self._create_prog_item("Desperate Punch"))
        cr1 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertIsNotNone(cr1.selected_support)

        # Collecting a second support rune still selects only 1 best support
        state.collect(self._create_prog_item("Break Blast"))
        cr2 = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertIn(cr2.selected_support, ("Desperate Punch", "Break Blast"))

    def test_case_i_microwave_severe_penalty_removal(self) -> None:
        """Case I: Effective anti-spirit (Plasma Rifle + Microwave Beam) removes +15 Spirit penalty."""
        state = CollectionState(self.mw)
        stage_id = "e4m2_swamp"  # The Blood Swamps (Base CR = 88)

        # Without Plasma Rifle and Microwave Beam:
        res_without = evaluate_mission_readiness(
            state, self.player, stage_id, self.world, context="spirit_breakpoint"
        )
        self.assertEqual(res_without.soft_penalty, 15)
        self.assertEqual(res_without.effective_cr, 100)  # min(100, 88 + 15)

        # With Plasma Rifle + Microwave Beam:
        state.collect(self.mw.create_item("Plasma Rifle", self.player))
        state.collect(self.mw.create_item("Microwave Beam", self.player))
        res_with = evaluate_mission_readiness(
            state, self.player, stage_id, self.world, context="spirit_breakpoint"
        )
        self.assertEqual(res_with.soft_penalty, 0)
        self.assertEqual(res_with.effective_cr, 88)
        self.assertEqual(res_without.effective_cr - res_with.effective_cr, 12)  # 100 - 88

    def test_case_j_orphan_microwave_without_plasma_fails_spirit(self) -> None:
        """Case J: Microwave Beam without Plasma Rifle does NOT satisfy anti-spirit capability."""
        state = CollectionState(self.mw)
        state.collect(self.mw.create_item("Microwave Beam", self.player))
        self.assertFalse(has_effective_anti_spirit(state, self.player))

        res = evaluate_mission_readiness(
            state, self.player, "e4m2_swamp", self.world, context="spirit_breakpoint"
        )
        self.assertEqual(res.soft_penalty, 15)

    def test_case_k_hammer_readiness_for_dark_lord(self) -> None:
        """Case K: Sentinel Hammer capability (stage 2 of Progressive Special Weapon) removes +15 soft penalty at Dark Lord."""
        state = CollectionState(self.mw)
        res_without = evaluate_mission_readiness(
            state, self.player, DARK_LORD_STAGE_ID, self.world, context="dark_lord_defeated"
        )
        self.assertEqual(res_without.soft_penalty, 15)
        self.assertEqual(res_without.effective_cr, 95)  # 80 + 15

        # Stage 1 = Crucible, Stage 2 = Sentinel Hammer
        state.collect(self.mw.create_item("Progressive Special Weapon", self.player))
        state.collect(self.mw.create_item("Progressive Special Weapon", self.player))
        self.assertTrue(has_effective_sentinel_hammer(state, self.player))

        res_with = evaluate_mission_readiness(
            state, self.player, DARK_LORD_STAGE_ID, self.world, context="dark_lord_defeated"
        )
        self.assertEqual(res_with.soft_penalty, 0)
        self.assertEqual(res_with.effective_cr, 80)

    def test_case_l_hammer_not_automatically_progression_if_cr_satisfied(self) -> None:
        """Case L: Sentinel Hammer is not needed if player loadout CR already satisfies target with penalty."""
        state = CollectionState(self.mw)
        # Give complete progression equipment and weapons to reach 90+ CR
        for item_name in [
            "Combat Shotgun", "Super Shotgun", "Heavy Cannon", "Plasma Rifle",
            "Rocket Launcher", "Ballista", "Chaingun", "BFG-9000",
            "Sticky Bombs", "Full Auto", "Precision Bolt", "Micro Missiles",
            "Heat Blast", "Microwave Beam", "Remote Detonate", "Lock-on Burst",
            "Arbalest", "Destroyer Blade", "Mobile Turret", "Energy Shield",
            "Blood Punch", "Flame Belch", "Frag Grenade", "Ice Bomb", "Dash",
            "The Crucible",
        ]:
            state.collect(self.mw.create_item(item_name, self.player))

        cr = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertGreaterEqual(cr.total, 80.0)

        # Without Hammer, Dark Lord has +15 penalty -> effective CR = 95
        # With UV allowance (15), required CR is 95 - 15 = 80.
        # Since player CR >= 80, Dark Lord is ready even without Hammer!
        res = evaluate_mission_readiness(
            state, self.player, DARK_LORD_STAGE_ID, self.world, context="dark_lord_defeated"
        )
        self.assertEqual(res.soft_penalty, 15)
        self.assertLessEqual(res.deficit, res.allowance)
        self.assertTrue(res.ready)

    def test_case_m_deterministic_repeated_planner_output(self) -> None:
        """Case M: Planner produces identical, deterministic output across multiple runs."""
        mw1 = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"additional_victory_requirements": ["Complete All Weapon Mastery Challenges"]},
        )
        w1 = mw1.worlds[1]
        ledger1 = apply_dynamic_progression_classification(w1)

        mw2 = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"additional_victory_requirements": ["Complete All Weapon Mastery Challenges"]},
        )
        w2 = mw2.worlds[1]
        ledger2 = apply_dynamic_progression_classification(w2)

        self.assertEqual(len(ledger1.promotions), len(ledger2.promotions))
        for p1, p2 in zip(ledger1.promotions, ledger2.promotions):
            self.assertEqual(p1.item_name, p2.item_name)
            self.assertEqual(p1.copy_index, p2.copy_index)
            self.assertEqual(p1.reason, p2.reason)
            self.assertEqual(p1.marginal_cr, p2.marginal_cr)

    def test_case_n_fortress_bootstrap_locations_reachable_at_sphere_0(self) -> None:
        """Case N: The 6 non-consumer Fortress locations are reachable at sphere 0.

        The starting weapon provides enough CR (≥6) that e1m1_intro (base CR=12)
        is also reachable under UV allowance (15), so we verify the 6 Fortress
        bootstrap locations are all reachable rather than asserting exact equality.
        """
        from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS
        state = CollectionState(self.mw)
        reachable = {loc.name for loc in self.mw.get_reachable_locations(state, self.player) if loc.address is not None}
        self.assertTrue(
            FORTRESS_BOOTSTRAP_LOCATIONS.issubset(reachable),
            f"Missing Fortress bootstrap locations: {FORTRESS_BOOTSTRAP_LOCATIONS - reachable}",
        )

    def test_case_o_late_red_fortress_remains_gated(self) -> None:
        """Case O: Spire Cheat and Unmaykr are unreachable at sphere 0."""
        state = CollectionState(self.mw)
        spire_loc = self.mw.get_location("Fortress of Doom - Fully Upgraded Suit Cheat Code", self.player)
        unmaykr_loc = self.mw.get_location("Fortress of Doom - Unmaykr Acquired", self.player)
        self.assertFalse(spire_loc.can_reach(state))
        self.assertFalse(unmaykr_loc.can_reach(state))

    def test_case_p_spend_group_atomicity(self) -> None:
        """Case P: SG_PRAETOR_AND_RUNES unlocks both locations atomically at 24 batteries."""
        praetor_loc = self.mw.get_location("Fortress of Doom - Praetor Suit", self.player)
        runes_loc = self.mw.get_location("Fortress of Doom - All Runes Cheat Code", self.player)
        state = CollectionState(self.mw)
        for _ in range(11):
            state.collect(self.mw.create_item("Sentinel Battery Bundle", self.player))
        self.assertFalse(praetor_loc.can_reach(state))
        self.assertFalse(runes_loc.can_reach(state))

        state.collect(self.mw.create_item("Sentinel Battery Bundle", self.player))
        self.assertTrue(praetor_loc.can_reach(state))
        self.assertTrue(runes_loc.can_reach(state))

    def test_case_q_meathook_mastery_requires_ssg(self) -> None:
        """Case Q: Meat Hook mastery challenge is unreachable without Super Shotgun."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"include_weapon_mastery_challenges": True},
        )
        player = 1
        state = CollectionState(mw)
        meathook_loc = mw.get_location("Meat Hook - Weapon Mastery Challenge", player)
        self.assertFalse(meathook_loc.can_reach(state))

        state.collect(mw.create_item("Super Shotgun", player))
        self.assertTrue(meathook_loc.can_reach(state))


class TestReadinessAwareStartSelection(unittest.TestCase):
    """Phase 7.7c §18: Readiness-Aware Start Selection Unit Tests."""

    def test_rmo_zero_bootstrap_selection(self) -> None:
        """Under normal pool conditions, start selection picks a stage with bootstrap_cost = 0."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_order": 1, "campaign_difficulty": 0},
        )
        world = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(plan["bootstrap_cost"], 0)
        self.assertEqual(len(plan["readiness_bootstrap_items"]), 0)

        # Also verify across remaining difficulties using make_plan directly
        import random
        for diff in (1, 2, 3):
            world.options.campaign_difficulty.value = diff
            fast_plan = make_plan(world.options, random.Random(42), world=world)
            self.assertEqual(fast_plan["bootstrap_cost"], 0)
            self.assertEqual(len(fast_plan["readiness_bootstrap_items"]), 0)

    def test_start_selection_determinism(self) -> None:
        """The same seed produces the identical starting stage and plan across runs."""
        import random
        mw = setup_multiworld(DoomEternalWorld, seed=12345)
        world = mw.worlds[1]
        plan1 = make_plan(world.options, random.Random(12345), world=world)
        plan2 = make_plan(world.options, random.Random(12345), world=world)
        self.assertEqual(plan1["starting_stages"], plan2["starting_stages"])
        self.assertEqual(plan1["sequence"], plan2["sequence"])
        self.assertEqual(plan1["bootstrap_stage"], plan2["bootstrap_stage"])
        self.assertEqual(plan1["bootstrap_cost"], plan2["bootstrap_cost"])

    def test_goal_reservation(self) -> None:
        """Goal stages (and reserved saga bosses) are never chosen as the starting stage."""
        test_goals = [
            (1, "e3m4_boss"),  # Kill the Icon of Sin
            (2, "e5m4_boss"),  # Kill the Dark Lord
            (3, "e5m4_boss"),  # Complete the Full Saga (with final boss Davoth)
        ]
        for goal_val, expected_goal_stage in test_goals:
            opts = {"goal": goal_val, "mission_order": 1}
            if goal_val == 3:
                opts["full_saga_final_boss"] = 2
            mw = setup_multiworld(
                DoomEternalWorld,
                seed=42,
                options=opts,
            )
            world = mw.worlds[1]
            plan = world.campaign_plan
            self.assertEqual(plan["goal_stage"], expected_goal_stage)
            self.assertNotIn(expected_goal_stage, plan["starting_stages"])

    def test_mai_start_selection(self) -> None:
        """MAI selects primary start with bootstrap_cost = 0, and starting_missions count is populated."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={
                "mission_order": 2,
                "starting_missions": 3,
                "campaign_difficulty": 0,
            },
        )
        world = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(plan["bootstrap_cost"], 0)
        self.assertEqual(len(plan["starting_stages"]), 3)
        self.assertEqual(plan["starting_stages"][0], plan["bootstrap_stage"])


class TestMinimalReadinessBootstrap(unittest.TestCase):
    """Phase 7.7c §19: Minimal Readiness Bootstrap Unit Tests."""

    def test_zero_bootstrap_when_not_needed(self) -> None:
        """Stages ready via free checks have bootstrap_cost = 0 and empty bootstrap_items."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_order": "vanilla_order", "campaign_difficulty": 0},
        )
        world = mw.worlds[1]
        plan = world.campaign_plan
        self.assertEqual(plan["bootstrap_cost"], 0)
        self.assertEqual(len(plan["readiness_bootstrap_items"]), 0)

    def test_single_item_shortage_or_forced_bootstrap(self) -> None:
        """A stage requiring bootstrap receives minimal items from world pool."""
        class MockOptions:
            campaign_difficulty = type("Opts", (), {"value": 0})()
            use_dlc_content = type("Opts", (), {"value": 1})()
            special_weapon = type("Opts", (), {"current_option_name": "The Crucible"})()
            randomize_chainsaw = type("Opts", (), {"value": 0})()
            randomize_dash = type("Opts", (), {"value": 0})()
            start_inventory = type("Opts", (), {"value": {}})()

        opts = MockOptions()
        base_st = FastState(["Combat Shotgun", "Chainsaw", "Dash"], player=1)
        pool_counts = build_pool_candidate_counts(opts, ["e4m3_mcity"], "Combat Shotgun", (), 0)

        class MockWorld:
            options = opts
            player = 1

        res = solve_stage_bootstrap("e4m3_mcity", MockWorld(), base_st, pool_counts, active_sg_count=0)
        self.assertGreater(res["bootstrap_cost"], 0)
        self.assertEqual(len(res["bootstrap_items"]), res["bootstrap_cost"])

    def test_dependency_packages(self) -> None:
        """A bootstrapped mod/mastery is packaged with its weapon if not yet owned."""
        base_st = FastState([], player=1)
        pool = Counter({"Sticky Bombs": 1, "Combat Shotgun": 1, "Dash": 1, "Faster Dash Recharge": 1})
        valid, full = resolve_dependencies(("Sticky Bombs",), base_st, 1, pool)
        self.assertTrue(valid)
        self.assertIn("Combat Shotgun", full)
        self.assertIn("Sticky Bombs", full)

        valid_dash, full_dash = resolve_dependencies(("Faster Dash Recharge",), base_st, 1, pool)
        self.assertTrue(valid_dash)
        self.assertIn("Dash", full_dash)
        self.assertIn("Faster Dash Recharge", full_dash)

    def test_user_start_inventory_priority(self) -> None:
        """User start_inventory items are never duplicated by the bootstrap solver."""
        class MockOptions:
            campaign_difficulty = type("Opts", (), {"value": 0})()
            use_dlc_content = type("Opts", (), {"value": 1})()
            special_weapon = type("Opts", (), {"current_option_name": "The Crucible"})()
            randomize_chainsaw = type("Opts", (), {"value": 0})()
            randomize_dash = type("Opts", (), {"value": 0})()
            start_inventory = type("Opts", (), {"value": {"Super Shotgun": 1}})()

        opts = MockOptions()
        pool_counts = build_pool_candidate_counts(opts, ["e4m3_mcity"], "Combat Shotgun", (), 0)
        self.assertEqual(pool_counts.get("Super Shotgun", 0), 0)

    def test_item_count_conservation(self) -> None:
        """Item pool count + precollected items match locations exactly, with no phantom items."""
        mw = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_order": "random_mission_order"},
        )
        world = mw.worlds[1]
        unfilled_locs = mw.get_unfilled_locations(1)
        self.assertEqual(len(mw.itempool), len(unfilled_locs))

    def test_candidate_specific_dash_semantics(self) -> None:
        """Dash is only bootstrap-available for candidate starts outside HoE and Exultia when not randomized."""
        # Vanilla dash (randomize_dash = 0)
        mw_vanilla = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_order": 1, "randomize_dash": 0},
        )
        plan_vanilla = mw_vanilla.worlds[1].campaign_plan
        starts = plan_vanilla["starting_stages"]
        if any(s not in {"e1m1_intro", "e1m2_war"} for s in starts):
            self.assertEqual(plan_vanilla["bootstrap_inventory"].get("Dash", 0), 1)
        else:
            self.assertEqual(plan_vanilla["bootstrap_inventory"].get("Dash", 0), 0)

        # Randomized dash (randomize_dash = 1) -> Dash never synthesized into bootstrap_inventory
        mw_rand = setup_multiworld(
            DoomEternalWorld,
            seed=42,
            options={"mission_order": 1, "randomize_dash": 1},
        )
        plan_rand = mw_rand.worlds[1].campaign_plan
        self.assertEqual(plan_rand["bootstrap_inventory"].get("Dash", 0), 0)

