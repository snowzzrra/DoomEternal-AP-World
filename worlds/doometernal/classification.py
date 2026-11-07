"""Promote items required by active checks and combat readiness."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from BaseClasses import CollectionState, ItemClassification

from Options import OptionError

from .campaign import STAGE_BY_ID
from .combat_rating import (
    ITEM_CONTRIBUTIONS,
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import READINESS_PLACEMENT_SLACK, derive_readiness_targets, select_readiness_items
from .generated_content import CAMPAIGN_CONNECTIONS
from .items import DoomEternalItem
from .logic import (
    MASTERY_SUFFIX,
    build_location_prerequisites,
    connection_requirement,
    required_item_names,
)
from .player_strings_generated import text as player_text

if TYPE_CHECKING:
    from . import DoomEternalWorld


@dataclass
class PromotionRecord:
    """Record of a promoted item copy."""

    item_name: str
    copy_index: int
    original_classification: ItemClassification
    final_classification: ItemClassification
    reason: str
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
    promotions: list[PromotionRecord] = field(default_factory=list)
    unpromoted: list[UnpromotedRecord] = field(default_factory=list)
    initial_player_cr: float = 0.0
    final_player_cr: float = 0.0
    targets_count: int = 0
    all_targets_satisfied: bool = False
    max_remaining_deficit: float = 0.0


def build_progression_only_state(world: DoomEternalWorld) -> CollectionState:
    """Precollected items are already included by CollectionState."""
    mw = world.multiworld
    player = world.player
    state = CollectionState(mw)

    for item in mw.itempool:
        if item.player == player and item.advancement:
            state.collect(item, prevent_sweep=True)

    state.sweep_for_advancements(loc for loc in mw.get_locations(player) if loc.address is None)

    return state


def apply_dynamic_progression_classification(world: DoomEternalWorld) -> ClassificationLedger:
    builder = _ProgressionClassifier(world=world)
    return builder.build()


class _ProgressionClassifier:
    def __init__(self, world: DoomEternalWorld):
        self.world = world

    def build(self):
        self._hard_requirements()
        self._validate_pool()
        self._classify_combat()
        self._classify_blood_punch()
        self._classify_batteries()
        self._classify_preparation()
        self._baseline()
        self._classify_mastery_points()
        self._select_readiness()
        self._record_readiness()
        return self._record_unpromoted()

    def _hard_requirements(self):
        self.ledger = ClassificationLedger()
        self.mw = self.world.multiworld
        self.player = self.world.player
        self.targets = derive_readiness_targets(self.world.options, self.world.campaign_plan)
        self.ledger.targets_count = len(self.targets)
        self.active_locations = {loc.name for loc in self.mw.get_locations(self.player) if loc.address is not None}
        self.active_regions = {region.name for region in self.mw.get_regions(self.player)}
        requirements = build_location_prerequisites(
            self.active_locations,
            active_region_names=self.active_regions,
            randomize_chainsaw=bool(self.world.options.randomize_chainsaw.value),
            randomize_dash=bool(self.world.options.randomize_dash.value),
            special_weapon=self.world.options.special_weapon.current_option_name
            if self.world.options.use_dlc_content.value
            else "The Crucible",
            logic_difficulty=self.world.options.logic_difficulty.value,
            active_spend_groups=getattr(self.world, "active_spend_groups", None),
            enemy_plan=getattr(self.world, "enemy_plan", None),
        )
        self.hard_items = set().union(*(required_item_names(req) for req in requirements.values()))
        self._traversal_requirements()

    def _validate_pool(self):
        if self.world.options.item_pool_counts.value:
            available = self._available_item_names()
            from .items import item_data_table

            missing = sorted(name for name in self.hard_items if name in item_data_table and name not in available)
            if missing:
                raise OptionError(player_text("apworld.errors", "pool_excludes_requirements", items=", ".join(missing)))

    def _classify_combat(self):
        combat_baselines = {
            "Combat Shotgun",
            "Heavy Cannon",
            "Plasma Rifle",
            "Rocket Launcher",
            "Ballista",
            "Chaingun",
            "Sticky Bombs",
            "Full Auto",
            "Precision Bolt",
            "Micro Missiles",
            "Heat Blast",
            "Microwave Beam",
            "Remote Detonate",
            "Lock-on Burst",
            "Arbalest",
            "Destroyer Blade",
            "Energy Shield",
            "Mobile Turret",
            "Meat Hook",
        }
        for item in self.mw.itempool:
            if item.player == self.player and item.name in combat_baselines and (item.name not in self.hard_items):
                item.classification = ItemClassification.useful
            if item.player == self.player and item.name in self.hard_items and (not item.advancement):
                original = item.classification
                item.classification = ItemClassification.progression
                self.ledger.promotions.append(
                    PromotionRecord(
                        item.name,
                        1,
                        original,
                        ItemClassification.progression,
                        "active_hard_requirement",
                        0.0,
                        "Active location or traversal prerequisite",
                        (),
                    )
                )

    def _classify_blood_punch(self):
        starting_blood_punch = next(
            (item for item in self.mw.precollected_items[self.player] if item.name == "Progressive Blood Punch"), None
        )
        if starting_blood_punch is not None:
            starting_blood_punch.classification = ItemClassification.progression
        needs_blood_punch = starting_blood_punch is None
        for item in self.mw.itempool:
            if item.player == self.player and item.name == "Progressive Blood Punch":
                item.classification = ItemClassification.progression if needs_blood_punch else ItemClassification.useful
                needs_blood_punch = False

    def _classify_batteries(self):
        battery_required = sum(group["cost"] for group in self.world.active_spend_groups)
        battery_required -= sum(item.name == "Sentinel Battery" for item in self.mw.precollected_items[self.player])
        battery_required -= self.world.campaign_plan["battery_economy"]["native_first_battery"]
        for item in self.mw.itempool:
            if item.player == self.player and item.name == "Sentinel Battery":
                item.classification = (
                    ItemClassification.progression if battery_required > 0 else ItemClassification.useful
                )
                battery_required -= 1

    def _classify_preparation(self):
        bootstrap_copies = Counter(self.world.campaign_plan.get("bootstrap_placed_items", ()))
        arsenal = set(getattr(self.world, "frontloaded_arsenal", ()))
        bootstrap_copies.update(arsenal)
        for item in self.mw.itempool:
            if item.player == self.player and bootstrap_copies[item.name] > 0:
                bootstrap_copies[item.name] -= 1
                if not item.advancement:
                    original = item.classification
                    item.classification = ItemClassification.progression
                    self.ledger.promotions.append(
                        PromotionRecord(
                            item.name,
                            1,
                            original,
                            ItemClassification.progression,
                            "early_arsenal" if item.name in arsenal else "starting_stage_witness",
                            0.0,
                            "Early arsenal" if item.name in arsenal else "Concrete starting-stage readiness witness",
                            (),
                        )
                    )

    def _baseline(self):
        self.state = build_progression_only_state(self.world)
        cr_initial = evaluate_player_loadout_cr(self.state, self.player, self.world)
        self.ledger.initial_player_cr = cr_initial.total
        self.active_mastery_count = sum(name.endswith(MASTERY_SUFFIX) for name in self.active_locations)
        self.useful_items: dict[str, list[DoomEternalItem]] = {}
        for item in self.mw.itempool:
            if (
                item.player == self.player
                and (not item.advancement)
                and (item.classification == ItemClassification.useful)
            ):
                self.useful_items.setdefault(item.name, []).append(item)

    def _classify_mastery_points(self):
        self.wup_name = "Weapon Upgrade Points (3)"
        needed_wup_bundles = max(0, 3 * self.active_mastery_count - self.state.count(self.wup_name, self.player))
        if needed_wup_bundles > len(self.useful_items.get(self.wup_name, ())):
            raise OptionError(player_text("apworld.errors", "mastery_points_insufficient"))
        if needed_wup_bundles:
            wup_list = self.useful_items[self.wup_name]
            for idx in range(needed_wup_bundles):
                item_to_promote = wup_list.pop(0)
                item_to_promote.classification = ItemClassification.progression
                self.state.collect(item_to_promote, prevent_sweep=True)
                self.ledger.promotions.append(
                    PromotionRecord(
                        item_name=self.wup_name,
                        copy_index=idx + 1,
                        original_classification=ItemClassification.useful,
                        final_classification=ItemClassification.progression,
                        reason="mastery_accessibility",
                        marginal_cr=0.0,
                        target_description="Weapon Mastery Challenges",
                        dependency_closure=(),
                    )
                )
            if not wup_list:
                del self.useful_items[self.wup_name]

    def _select_readiness(self):
        base_items = dict(self.state.prog_items[self.player])
        additional = {name: len(items) for name, items in self.useful_items.items() if items}
        self.selection = select_readiness_items(
            base_items=base_items,
            targets=self.targets,
            additional=additional,
            world_context=self.world,
            player=self.player,
            slack=READINESS_PLACEMENT_SLACK,
        )
        for step in self.selection.steps:
            item_list = self.useful_items.get(step.item_name)
            if not item_list:
                raise ValueError(player_text("apworld.errors", "classification_budget_mismatch", item=step.item_name))
            promoted_item = item_list.pop(0)
            if not item_list:
                del self.useful_items[step.item_name]
            promoted_item.classification = ItemClassification.progression
            self.state.collect(promoted_item, prevent_sweep=True)
            copy_idx = sum(1 for p in self.ledger.promotions if p.item_name == step.item_name) + 1
            reason = step.reason if not step.is_dependency else f"dependency_for_{step.package_lead}"
            self.ledger.promotions.append(
                PromotionRecord(
                    item_name=step.item_name,
                    copy_index=copy_idx,
                    original_classification=ItemClassification.useful,
                    final_classification=ItemClassification.progression,
                    reason=reason,
                    marginal_cr=step.delta_cr if step.package_size == 1 else 0.0,
                    target_description=step.target_description,
                    dependency_closure=step.dependency_closure,
                )
            )

    def _record_readiness(self):
        current_max_deficit = self.selection.final_deficit
        cr_final = evaluate_player_loadout_cr(self.state, self.player, self.world)
        self.ledger.final_player_cr = cr_final.total
        self.ledger.max_remaining_deficit = round(current_max_deficit, 2)
        self.ledger.all_targets_satisfied = current_max_deficit <= 0.0

    def _record_unpromoted(self):
        for name, remaining_items in sorted(self.useful_items.items()):
            if (
                name in ITEM_CONTRIBUTIONS
                or name in NORMAL_RUNE_NAMES
                or name in SUPPORT_RUNE_NAMES
                or (name == self.wup_name)
                or name.startswith("Progressive ")
            ):
                self.ledger.unpromoted.append(
                    UnpromotedRecord(
                        item_name=name,
                        copies_available=len(remaining_items),
                        reason_not_promoted="Readiness targets satisfied or category cap reached",
                    )
                )
        self.world.classification_ledger = self.ledger
        return self.ledger

    def _traversal_requirements(self):
        if any(
            STAGE_BY_ID[stage_id]["source"] == "tag2"
            for stage_id in self.world.campaign_plan.get("active_normal_mission_ids", ())
        ):
            self.hard_items.add("Meat Hook")
        for source, destination, _, condition in CAMPAIGN_CONNECTIONS:
            if source in self.active_regions and destination in self.active_regions:
                self.hard_items.update(
                    required_item_names(
                        connection_requirement(condition, randomize_dash=bool(self.world.options.randomize_dash.value))
                    )
                )

    def _available_item_names(self):
        available = {item.name for item in self.mw.itempool if item.player == self.player}
        available.update(item.name for item in self.mw.precollected_items[self.player])
        if "Progressive Blood Punch" in available:
            available.add("Blood Punch")
        if not self.world.options.randomize_chainsaw.value:
            available.add("Chainsaw")
        if not self.world.options.randomize_dash.value:
            available.add("Dash")
        return available
