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
from .logic import (
    MASTERY_SUFFIX,
    build_location_prerequisites,
    connection_requirement,
    effective_victory_requirements,
    required_item_names,
)
from .generated_content import CAMPAIGN_CONNECTIONS
from .planner import (
    ITEM_DEPENDENCIES,
    READINESS_PLACEMENT_SLACK,
    ReadinessTarget,
    derive_readiness_targets,
    select_readiness_items,
)

if TYPE_CHECKING:
    from . import DoomEternalWorld


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


def get_required_readiness_targets(world: DoomEternalWorld) -> list[ReadinessTarget]:
    """Derive required readiness targets from the actual generated campaign plan."""
    return derive_readiness_targets(world.options, world.campaign_plan)


def build_progression_only_state(world: DoomEternalWorld) -> CollectionState:
    """Build a deterministic CollectionState with precollected and existing progression items.

    ``CollectionState(mw)`` already ingests every precollected item (including
    physical initial-inventory items), so precollected items must not be
    collected a second time here.
    """
    mw = world.multiworld
    player = world.player
    state = CollectionState(mw)

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

    active_locations = {loc.name for loc in mw.get_locations(player) if loc.address is not None}
    active_regions = {region.name for region in mw.get_regions(player)}
    requirements = build_location_prerequisites(
        active_locations,
        active_region_names=active_regions,
        randomize_chainsaw=bool(world.options.randomize_chainsaw.value),
        randomize_dash=bool(world.options.randomize_dash.value),
        randomize_first_battery=bool(world.options.randomize_first_battery.value),
        special_weapon=world.options.special_weapon.current_option_name,
        campaign_difficulty=world.options.campaign_difficulty.value,
        active_spend_groups=getattr(world, "active_spend_groups", None),
    )
    hard_items = set().union(*(required_item_names(req) for req in requirements.values()))
    for source, destination, _, condition in CAMPAIGN_CONNECTIONS:
        if source in active_regions and destination in active_regions:
            hard_items.update(required_item_names(connection_requirement(
                condition,
                randomize_dash=bool(world.options.randomize_dash.value),
                randomize_first_battery=bool(world.options.randomize_first_battery.value),
            )))
    combat_baselines = {
        "Combat Shotgun", "Heavy Cannon", "Plasma Rifle", "Rocket Launcher", "Ballista", "Chaingun",
        "Sticky Bombs", "Full Auto", "Precision Bolt", "Micro Missiles", "Heat Blast", "Microwave Beam",
        "Remote Detonate", "Lock-on Burst", "Arbalest", "Destroyer Blade", "Energy Shield", "Mobile Turret",
        "Meat Hook",
    }
    for item in mw.itempool:
        if item.player == player and item.name in combat_baselines and item.name not in hard_items:
            item.classification = ItemClassification.useful
        if item.player == player and item.name in hard_items and not item.advancement:
            original = item.classification
            item.classification = ItemClassification.progression
            ledger.promotions.append(PromotionRecord(
                item.name, 1, original, ItemClassification.progression,
                "active_hard_requirement", 0.0, "Active location or traversal prerequisite", (),
            ))

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

    # 4. Deterministic dependency-aware promotion loop (canonical planner selector)
    base_items = dict(state.prog_items[player])
    additional = {name: len(items) for name, items in useful_items.items() if items}
    selection = select_readiness_items(
        base_items=base_items,
        targets=targets,
        additional=additional,
        world_context=world,
        player=player,
        slack=READINESS_PLACEMENT_SLACK,
    )
    for step in selection.steps:
        item_list = useful_items.get(step.item_name)
        if not item_list:
            # Budget mismatch between planner and classifier would silently
            # drop a required copy; fail closed instead.
            raise ValueError(
                f"DOOM Eternal classification budget mismatch for '{step.item_name}'"
            )
        promoted_item = item_list.pop(0)
        if not item_list:
            del useful_items[step.item_name]
        promoted_item.classification = ItemClassification.progression
        state.collect(promoted_item)

        copy_idx = sum(1 for p in ledger.promotions if p.item_name == step.item_name) + 1
        reason = step.reason if not step.is_dependency else f"dependency_for_{step.package_lead}"
        ledger.promotions.append(PromotionRecord(
            item_name=step.item_name,
            copy_index=copy_idx,
            original_classification=ItemClassification.useful,
            final_classification=ItemClassification.progression,
            reason=reason,
            marginal_cr=step.delta_cr if step.package_size == 1 else 0.0,
            target_description=step.target_description,
            dependency_closure=step.dependency_closure,
        ))

    # Final state accounting
    current_max_deficit = selection.final_deficit
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
