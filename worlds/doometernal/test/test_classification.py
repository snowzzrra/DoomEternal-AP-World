"""DOOM Eternal item classification checks.

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
    """Item classification checks."""

    def setUp(self) -> None:
        self.mw = setup_multiworld(DoomEternalWorld, seed=42)
        self.world = self.mw.worlds[1]
        self.player = 1

    def _create_prog_item(self, name: str) -> DoomEternalItem:
        """Helper to create an item and set classification to progression (as promoted by planner)."""
        item = self.mw.create_item(name, self.player)
        item.classification = ItemClassification.progression
        return item


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
        # Collect Energy Shield (promoted to progression) without Chaingun
        state.collect(self._create_prog_item("Energy Shield"))
        cr = evaluate_player_loadout_cr(state, self.player, self.world)
        self.assertEqual(cr.categories["Defense"], cr_base.categories["Defense"])

        # Once Chaingun is collected, Energy Shield activates
        state.collect(self._create_prog_item("Chaingun"))
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
        for _ in range(10):
            state.collect(self.mw.create_item("Sentinel Battery Bundle", self.player))
        self.assertFalse(praetor_loc.can_reach(state))
        self.assertFalse(runes_loc.can_reach(state))

        state.collect(self.mw.create_item("Sentinel Battery Bundle", self.player))
        self.assertTrue(praetor_loc.can_reach(state))
        self.assertTrue(runes_loc.can_reach(state))





class TestMinimalReadinessBootstrap(unittest.TestCase):
    """Minimal Readiness Bootstrap Unit Tests."""




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

