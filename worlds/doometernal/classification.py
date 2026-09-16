"""DOOM Eternal Archipelago v0.6 — Dynamic Progression Classification Authority.

Implements Phase 7.7 Dynamic Item Progression Classification:
- Derives required readiness targets from active campaign plan (RMO, MAI, Vanilla).
- Computes baseline progression-only expected state (precollected + existing progression).
- Handles Weapon Mastery / WUP requirements for victory and accessibility.
- Deterministically evaluates candidate items from the useful pool using production
  readiness (evaluate_player_loadout_cr and evaluate_mission_readiness).
- Promotes only proven-required copies to ItemClassification.progression.
- Maintains canonical diagnostic ledger recording promotions and unpromoted items.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

from BaseClasses import CollectionState, ItemClassification

from .campaign import STAGE_BY_ID
from .combat_rating import (
    CATEGORY_CAPS,
    ITEM_CONTRIBUTIONS,
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    DARK_LORD_STAGE_ID,
    SPIRIT_BREAKPOINTS,
    evaluate_mission_readiness,
)
from .items import DoomEternalItem, item_data_table
from .logic import MASTERY_SUFFIX, effective_victory_requirements

if TYPE_CHECKING:
    from . import DoomEternalWorld


@dataclass(frozen=True)
class ReadinessTarget:
    """Represents a logically required readiness target in the active campaign."""
    stage_id: str
    context: str = "base"  # "base", "spirit_breakpoint", "dark_lord_defeated"
    description: str = ""


@dataclass
class PromotionRecord:
    """Record of a promoted item copy."""
    item_name: str
    copy_index: int
    original_classification: ItemClassification
    final_classification: ItemClassification
    reason: str  # "cr_readiness", "spirit_breakpoint", "dark_lord_breakpoint", "mastery_accessibility", "hard_existing"
    marginal_cr: float
    target_description: str
    dependency_closure: tuple[str, ...] = ()


@dataclass
class UnpromotedRecord:
    """Record of a useful CR-positive candidate not promoted."""
    item_name: str
    copies_available: int
    reason_not_promoted: str


@dataclass
class ClassificationLedger:
    """Canonical P7.7 Classification Ledger."""
    promotions: list[PromotionRecord] = field(default_factory=list)
    unpromoted: list[UnpromotedRecord] = field(default_factory=list)
    initial_player_cr: float = 0.0
    final_player_cr: float = 0.0
    targets_count: int = 0
    all_targets_satisfied: bool = False
    max_remaining_deficit: float = 0.0

    def summary_by_item(self) -> dict[str, dict[str, Any]]:
        """Return promotion count and reasons summarized by item name."""
        summary: dict[str, dict[str, Any]] = {}
        for p in self.promotions:
            if p.item_name not in summary:
                summary[p.item_name] = {
                    "count": 0,
                    "reasons": set(),
                    "total_marginal_cr": 0.0,
                    "targets": set(),
                }
            summary[p.item_name]["count"] += 1
            summary[p.item_name]["reasons"].add(p.reason)
            summary[p.item_name]["total_marginal_cr"] += p.marginal_cr
            summary[p.item_name]["targets"].add(p.target_description)
        return summary


# Dependency lookup for items
ITEM_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "Sticky Bombs Mastery": ("Combat Shotgun", "Sticky Bombs"),
    "Full Auto Mastery": ("Combat Shotgun", "Full Auto"),
    "Precision Bolt Mastery": ("Heavy Cannon", "Precision Bolt"),
    "Micro Missiles Mastery": ("Heavy Cannon", "Micro Missiles"),
    "Heat Blast Mastery": ("Plasma Rifle", "Heat Blast"),
    "Microwave Beam Mastery": ("Plasma Rifle", "Microwave Beam"),
    "Lock-on Burst Mastery": ("Rocket Launcher", "Lock-on Burst"),
    "Remote Detonate Mastery": ("Rocket Launcher", "Remote Detonate"),
    "Destroyer Blade Mastery": ("Ballista", "Destroyer Blade"),
    "Arbalest Mastery": ("Ballista", "Arbalest"),
    "Mobile Turret Mastery": ("Chaingun", "Mobile Turret"),
    "Energy Shield Mastery": ("Chaingun", "Energy Shield"),
    "Meat Hook Mastery": ("Super Shotgun",),
    "Faster Dash Recharge": ("Dash",),
    "Microwave Beam": ("Plasma Rifle",),
    "Micro Missiles": ("Heavy Cannon",),
    "Heat Blast": ("Plasma Rifle",),
    "Remote Detonate": ("Rocket Launcher",),
    "Arbalest": ("Ballista",),
    "Destroyer Blade": ("Ballista",),
    "Energy Shield": ("Chaingun",),
    "Mobile Turret": ("Chaingun",),
}


def get_required_readiness_targets(world: DoomEternalWorld) -> list[ReadinessTarget]:
    """Derive required readiness targets from the actual generated campaign plan."""
    targets: list[ReadinessTarget] = []
    seen: set[tuple[str, str]] = set()

    def add_target(stage_id: str, context: str = "base", desc: str = "") -> None:
        key = (stage_id, context)
        if key not in seen:
            seen.add(key)
            targets.append(ReadinessTarget(stage_id, context, desc))

    plan = world.campaign_plan
    order = getattr(world.options, "mission_order", None)
    order_val = order.current_option_name if hasattr(order, "current_option_name") else "vanilla"

    spirit_stage_ids = set(SPIRIT_BREAKPOINTS.values())
    goal_opt = getattr(world.options, "goal", None)
    goal_name = goal_opt.current_option_name if hasattr(goal_opt, "current_option_name") else ""
    is_dark_lord_goal = (goal_name == "kill_the_dark_lord" or plan.get("goal_stage") == DARK_LORD_STAGE_ID)

    dlc_timing = getattr(getattr(world, "options", None), "dlc_logic_timing", None)
    is_from_the_beginning = (dlc_timing is not None and getattr(dlc_timing, "value", 0) == 1)
    dlc_stages = {
        "e4m1_rig", "e4m2_swamp", "e4m3_mcity",
        "e5m1_spear", "e5m2_earth", "e5m3_hell", "e5m4_boss",
    }

    if order_val == "mission_access_as_items":
        # MAI: active normal missions + goal mission
        active_ids = list(plan.get("active_normal_mission_ids", []))
        goal_stage = plan.get("goal_stage")
        if goal_stage and goal_stage not in active_ids and goal_stage in STAGE_BY_ID:
            active_ids.append(goal_stage)
        for s_id in active_ids:
            s_name = STAGE_BY_ID[s_id]["name"]
            if not (is_from_the_beginning and s_id in dlc_stages):
                add_target(s_id, "base", f"Mission: {s_name}")
            if s_id in spirit_stage_ids:
                add_target(s_id, "spirit_breakpoint", f"Spirit Breakpoint: {s_name}")
    else:
        # RMO or Vanilla: sequence of stages
        sequence = plan.get("sequence", [])
        for s_id in sequence:
            s_name = STAGE_BY_ID[s_id]["name"]
            if not (is_from_the_beginning and s_id in dlc_stages):
                add_target(s_id, "base", f"Mission: {s_name}")
            if s_id in spirit_stage_ids:
                add_target(s_id, "spirit_breakpoint", f"Spirit Breakpoint: {s_name}")

    # Boss / Dark Lord readiness
    if is_dark_lord_goal or DARK_LORD_STAGE_ID in plan.get("active_normal_mission_ids", ()):
        add_target(DARK_LORD_STAGE_ID, "dark_lord_defeated", "Boss: The Dark Lord Defeated")

    return targets


def build_progression_only_state(world: DoomEternalWorld) -> CollectionState:
    """Build a deterministic CollectionState with precollected and existing progression items."""
    mw = world.multiworld
    player = world.player
    state = CollectionState(mw)

    # Precollected items
    for item in mw.precollected_items.get(player, []):
        state.collect(item)

    # Generated items in pool that are progression
    for item in mw.itempool:
        if item.player == player and item.advancement:
            state.collect(item)

    return state


def apply_dynamic_progression_classification(world: DoomEternalWorld) -> ClassificationLedger:
    """Execute dynamic progression classification on world.multiworld.itempool for world.player.

    Evaluates readiness targets, promotes necessary WUP and CR contributors deterministically,
    and returns the diagnostic ledger.
    """
    ledger = ClassificationLedger()
    mw = world.multiworld
    player = world.player

    # 1. Targets
    targets = get_required_readiness_targets(world)
    ledger.targets_count = len(targets)

    # 2. Baseline progression-only state
    state = build_progression_only_state(world)
    cr_initial = evaluate_player_loadout_cr(state, player, world)
    ledger.initial_player_cr = cr_initial.total

    # 3. WUP for Mastery accessibility (§10)
    # Check if Complete All Weapon Mastery Challenges is an active victory requirement
    active_loc_names = {loc.name for loc in mw.get_locations(player)}
    eff_victories = effective_victory_requirements(
        set(world.options.additional_victory_requirements.value),
        active_loc_names,
        use_dlc_content=bool(world.options.use_dlc_content.value),
        goal=world.options.goal.current_option_name,
    )
    mastery_req_active = "Complete All Weapon Mastery Challenges" in eff_victories

    # Find unpromoted useful items in player's pool
    useful_items: dict[str, list[DoomEternalItem]] = {}
    for item in mw.itempool:
        if item.player == player and not item.advancement and item.classification == ItemClassification.useful:
            useful_items.setdefault(item.name, []).append(item)

    # Promote WUP for mastery accessibility if required
    wup_name = "Weapon Upgrade Points (3)"
    if mastery_req_active and wup_name in useful_items:
        active_mastery_count = getattr(world, "active_masteries_count", 13)
        needed_wup_bundles = 3 * active_mastery_count
        wup_list = useful_items[wup_name]
        promoted_count = min(needed_wup_bundles, len(wup_list))
        for idx in range(promoted_count):
            item_to_promote = wup_list.pop(0)
            item_to_promote.classification = ItemClassification.progression
            state.collect(item_to_promote)
            ledger.promotions.append(PromotionRecord(
                item_name=wup_name,
                copy_index=idx + 1,
                original_classification=ItemClassification.useful,
                final_classification=ItemClassification.progression,
                reason="mastery_accessibility",
                marginal_cr=0.0,
                target_description="Victory: Complete All Weapon Mastery Challenges",
                dependency_closure=(),
            ))
        if not wup_list:
            del useful_items[wup_name]

    # 4. Evaluate current readiness across all targets
    def evaluate_all_targets(eval_state: CollectionState) -> tuple[float, ReadinessTarget | None]:
        max_def = -999.0
        worst_target = None
        for t in targets:
            res = evaluate_mission_readiness(eval_state, player, t.stage_id, world, context=t.context)
            # deficit = effective_cr - player_cr - allowance
            defic = res.effective_cr - res.player_cr - res.allowance
            if defic > max_def:
                max_def = defic
                worst_target = t
        return max_def, worst_target

    current_max_deficit, worst_t = evaluate_all_targets(state)
    current_player_cr = evaluate_player_loadout_cr(state, player, world).total

    # 5. Deterministic promotion loop (§11)
    while current_max_deficit > 0:
        best_candidate: str | None = None
        best_package: tuple[str, ...] = ()
        best_delta_deficit: float = 0.0
        best_delta_cr: float = 0.0
        best_target_desc: str = ""
        best_reason: str = "cr_readiness"

        for cand_name in sorted(useful_items.keys()):
            # Check dependencies
            deps = ITEM_DEPENDENCIES.get(cand_name, ())
            missing_deps = [d for d in deps if not state.has(d, player)]

            # Can we satisfy missing deps from useful candidates?
            possible = True
            package_items = []
            for d in missing_deps:
                if d in useful_items and useful_items[d]:
                    package_items.append(d)
                else:
                    possible = False
                    break
            if not possible:
                continue

            full_package = tuple(package_items + [cand_name])

            # Simulate collecting full package in temp state
            temp_state = state.copy()
            for pkg_item_name in full_package:
                temp_item = DoomEternalItem(
                    pkg_item_name,
                    ItemClassification.progression,
                    item_data_table[pkg_item_name].code,
                    player,
                )
                temp_state.collect(temp_item)

            new_max_def, new_worst = evaluate_all_targets(temp_state)
            delta_def = current_max_deficit - new_max_def
            new_cr = evaluate_player_loadout_cr(temp_state, player, world).total
            delta_cr = new_cr - current_player_cr

            if delta_def <= 1e-6:
                # No progress toward bottleneck deficit
                continue

            # Check if this candidate is better
            is_better = False
            if best_candidate is None:
                is_better = True
            elif delta_def > best_delta_deficit + 1e-6:
                is_better = True
            elif abs(delta_def - best_delta_deficit) <= 1e-6:
                if len(full_package) < len(best_package):
                    is_better = True
                elif len(full_package) == len(best_package):
                    if delta_cr > best_delta_cr + 1e-6:
                        is_better = True
                    elif abs(delta_cr - best_delta_cr) <= 1e-6:
                        if cand_name < best_candidate:
                            is_better = True

            if is_better:
                best_candidate = cand_name
                best_package = full_package
                best_delta_deficit = delta_def
                best_delta_cr = delta_cr
                if worst_t is not None:
                    best_target_desc = worst_t.description
                    if worst_t.context == "spirit_breakpoint":
                        best_reason = "spirit_breakpoint"
                    elif worst_t.context == "dark_lord_defeated":
                        best_reason = "dark_lord_breakpoint"
                    else:
                        best_reason = "cr_readiness"

        if best_candidate is None:
            # No available candidate can reduce deficit further
            break

        # Apply promotion for all items in best_package
        for pkg_name in best_package:
            item_list = useful_items[pkg_name]
            promoted_item = item_list.pop(0)
            if not item_list:
                del useful_items[pkg_name]
            promoted_item.classification = ItemClassification.progression
            state.collect(promoted_item)

            copy_idx = sum(1 for p in ledger.promotions if p.item_name == pkg_name) + 1
            ledger.promotions.append(PromotionRecord(
                item_name=pkg_name,
                copy_index=copy_idx,
                original_classification=ItemClassification.useful,
                final_classification=ItemClassification.progression,
                reason=best_reason if pkg_name == best_candidate else f"dependency_for_{best_candidate}",
                marginal_cr=best_delta_cr if len(best_package) == 1 else 0.0,
                target_description=best_target_desc,
                dependency_closure=ITEM_DEPENDENCIES.get(pkg_name, ()),
            ))

        current_player_cr = evaluate_player_loadout_cr(state, player, world).total
        current_max_deficit, worst_t = evaluate_all_targets(state)

    # Final state accounting
    cr_final = evaluate_player_loadout_cr(state, player, world)
    ledger.final_player_cr = cr_final.total
    ledger.max_remaining_deficit = round(current_max_deficit, 2)
    ledger.all_targets_satisfied = (current_max_deficit <= 0.0)

    # 6. Record unpromoted useful CR-positive candidates
    for name, remaining_items in sorted(useful_items.items()):
        if name in ITEM_CONTRIBUTIONS or name in NORMAL_RUNE_NAMES or name in SUPPORT_RUNE_NAMES or name == wup_name or name.startswith("Progressive "):
            ledger.unpromoted.append(UnpromotedRecord(
                item_name=name,
                copies_available=len(remaining_items),
                reason_not_promoted="Readiness targets satisfied or category cap reached",
            ))

    world.classification_ledger = ledger
    return ledger
