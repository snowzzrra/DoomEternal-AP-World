"""Canonical semantic pool planner and readiness package selector.

This module is the single source of truth for:

- optional-item dependency closure (:data:`ITEM_DEPENDENCIES`),
- readiness target derivation for the active campaign,
- greedy dependency-aware optional selection driven by the production
  readiness evaluator and resource-profile variety,
- compact short-world semantic pool composition,
- the bootstrap solver's candidate-pool view.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from BaseClasses import ItemClassification

from .combat_rating import (
    ALL_MASTERY_NAMES,
    ALL_MOD_NAMES,
    ITEM_CONTRIBUTIONS,
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    WEAPON_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    DARK_LORD_STAGE_ID,
    HOOK_TRAVERSAL_STAGES,
    SPIRIT_BREAKPOINTS,
    evaluate_mission_readiness,
)
from .generated_content import CAMPAIGN_STAGES
from .items import (
    SPECIAL_WEAPON_POOL_COUNTS,
    WEAPON_UPGRADE_POINTS_ITEM_COUNT,
    WEAPON_UPGRADE_POINTS_NAME,
    item_data_table,
    world_pool_weapon_item_names,
    suit_perk_item_names,
)

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}

READINESS_PLACEMENT_SLACK: float = 6.0

FULL_LENGTH_MIN_MISSIONS = 9

CORE_EQUIPMENT = ("Frag Grenade", "Progressive Blood Punch", "Flame Belch", "Ice Bomb")

NORMAL_RUNES_ORDERED = (
    "Savagery", "Seek and Destroy", "Blood Fueled",
    "Air Control", "Dazed and Confused", "Saving Throw",
    "Chrono Strike", "Equipment Fiend", "Punch and Reave",
)

SUPPORT_RUNES_ORDERED = tuple(sorted(SUPPORT_RUNE_NAMES))

PRIMARY_BASE_MODS = (
    "Sticky Bombs", "Precision Bolt", "Microwave Beam",
    "Remote Detonate", "Arbalest", "Energy Shield",
)
SECONDARY_MODS = (
    "Full Auto", "Micro Missiles", "Heat Blast",
    "Lock-on Burst", "Destroyer Blade", "Mobile Turret",
)
ALL_MODS_ORDERED = PRIMARY_BASE_MODS + SECONDARY_MODS

STAGE_SLAYER_GATE_KEYS = {
    "e1m2_war": "Slayer Gate Key Exultia",
    "e1m3_cult": "Slayer Gate Key Cultist Base",
    "e2m1_nest": "Slayer Gate Key Super Gore Nest",
    "e2m2_base": "Slayer Gate Key ARC Complex",
    "e2m3_core": "Slayer Gate Key Mars Core",
    "e3m1_slayer": "Slayer Gate Key Taras Nabad",
    "e4m1_rig": "Slayer Gate Key UAC Atlantica Facility",
    "e4m3_mcity": "Slayer Gate Key The Holt",
}

ORDERED_MASTERY_CHALLENGES = (
    ("Sticky Bombs", "Sticky Bombs - Weapon Mastery Challenge"),
    ("Precision Bolt", "Precision Bolt - Weapon Mastery Challenge"),
    ("Heat Blast", "Heat Blast - Weapon Mastery Challenge"),
    ("Remote Detonate", "Remote Detonate - Weapon Mastery Challenge"),
    ("Arbalest", "Arbalest - Weapon Mastery Challenge"),
    ("Energy Shield", "Energy Shield - Weapon Mastery Challenge"),
    ("Full Auto", "Full Auto - Weapon Mastery Challenge"),
    ("Micro Missiles", "Micro Missiles - Weapon Mastery Challenge"),
    ("Microwave Beam", "Microwave Beam - Weapon Mastery Challenge"),
    ("Lock-on Burst", "Lock-on Burst - Weapon Mastery Challenge"),
    ("Meat Hook", "Meat Hook - Weapon Mastery Challenge"),
    ("Destroyer Blade", "Destroyer Blade - Weapon Mastery Challenge"),
    ("Mobile Turret", "Mobile Turret - Weapon Mastery Challenge"),
)

# Canonical dependency closure for optional combat/upgrade families.
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
    "Meat Hook Mastery": ("Super Shotgun", "Meat Hook"),
    "Meat Hook": ("Super Shotgun",),
    "Faster Dash Recharge": ("Dash",),
    "Sticky Bombs": ("Combat Shotgun",),
    "Full Auto": ("Combat Shotgun",),
    "Precision Bolt": ("Heavy Cannon",),
    "Micro Missiles": ("Heavy Cannon",),
    "Heat Blast": ("Plasma Rifle",),
    "Microwave Beam": ("Plasma Rifle",),
    "Remote Detonate": ("Rocket Launcher",),
    "Lock-on Burst": ("Rocket Launcher",),
    "Arbalest": ("Ballista",),
    "Destroyer Blade": ("Ballista",),
    "Energy Shield": ("Chaingun",),
    "Mobile Turret": ("Chaingun",),
}
ITEM_DEPENDENCIES.update({
    name: tuple(dict.fromkeys(dep for _, _, deps in contributions for dep in deps))
    for name, contributions in ITEM_CONTRIBUTIONS.items()
    if name in suit_perk_item_names
})

# Items the dynamic classifier demotes to ``useful`` before readiness
# evaluation (combat baseline); they only count once promoted.
COMBAT_BASELINE_NAMES = frozenset(WEAPON_NAMES) | frozenset(ALL_MOD_NAMES)

# mods required by active location rules in logic.build_location_prerequisites
HARD_MOD_BY_STAGE: dict[str, tuple[str, ...]] = {
    "e3m3_maykr": ("Precision Bolt",),
    "e4m3_mcity": ("Microwave Beam",),
}

_CAPACITY_STATS = ("Health", "Armor", "Ammo")
_CAPACITY_MAX_STAGES = 4
_PRAETOR_CAP = 1


class FastState:
    """Minimal CollectionState-compatible state used by planner/solver."""

    __slots__ = ("prog_items", "player")

    def __init__(self, items=None, player=1):
        self.prog_items = Counter(items or ())
        self.player = player

    @classmethod
    def from_counts(cls, counts: Mapping[str, int], player: int = 1) -> "FastState":
        state = cls(player=player)
        state.prog_items = Counter({name: qty for name, qty in counts.items() if qty})
        return state

    def count(self, item_name, player):
        return self.prog_items[item_name] + (self.prog_items["Progressive Blood Punch"] if item_name == "Blood Punch" else 0)

    def has(self, item_name, player):
        return self.count(item_name, player) > 0

    def copy(self):
        st = FastState(player=self.player)
        st.prog_items = Counter(self.prog_items)
        return st

    def collect(self, item_name):
        self.prog_items[item_name] += 1


def _item_is_progression(name: str) -> bool:
    data = item_data_table.get(name)
    return bool(data is not None and data.classification & ItemClassification.progression)


def _option_value(options, attribute: str, default: int = 0) -> int:
    """Read an option value, tolerating lightweight option mocks."""
    option = getattr(options, attribute, None)
    return int(getattr(option, "value", default))


# ═══════════════════════════════════════════════════════════════
# Readiness targets
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReadinessTarget:
    """Represents a logically required readiness target in the active campaign."""
    stage_id: str
    context: str = "base"  # "base", "spirit_breakpoint", "dark_lord_defeated"
    description: str = ""


def derive_readiness_targets(options, plan: Mapping[str, Any]) -> list[ReadinessTarget]:
    """Derive required readiness targets from the generated campaign plan."""
    targets: list[ReadinessTarget] = []
    seen: set[tuple[str, str]] = set()

    def add_target(stage_id: str, context: str = "base", desc: str = "") -> None:
        key = (stage_id, context)
        if key not in seen:
            seen.add(key)
            targets.append(ReadinessTarget(stage_id, context, desc))

    plan = plan or {}
    order = getattr(options, "mission_order", None)
    order_val = order.current_option_name if hasattr(order, "current_option_name") else "vanilla"

    spirit_stage_ids = set(SPIRIT_BREAKPOINTS.values())
    goal_opt = getattr(options, "goal", None)
    goal_name = goal_opt.current_option_name if hasattr(goal_opt, "current_option_name") else ""
    is_dark_lord_goal = (goal_name == "kill_the_dark_lord" or plan.get("goal_stage") == DARK_LORD_STAGE_ID)

    if order_val == "mission_access_as_items":
        active_ids = list(plan.get("active_normal_mission_ids", []))
        goal_stage = plan.get("goal_stage")
        if goal_stage and goal_stage not in active_ids and goal_stage in STAGE_BY_ID:
            active_ids.append(goal_stage)
        for s_id in active_ids:
            s_name = STAGE_BY_ID[s_id]["name"]
            add_target(s_id, "base", f"Mission: {s_name}")
            if s_id in spirit_stage_ids:
                add_target(s_id, "spirit_breakpoint", f"Spirit Breakpoint: {s_name}")
    else:
        sequence = plan.get("sequence", [])
        for s_id in sequence:
            s_name = STAGE_BY_ID[s_id]["name"]
            add_target(s_id, "base", f"Mission: {s_name}")
            if s_id in spirit_stage_ids:
                add_target(s_id, "spirit_breakpoint", f"Spirit Breakpoint: {s_name}")

    if (
        is_dark_lord_goal
        or DARK_LORD_STAGE_ID in plan.get("active_normal_mission_ids", ())
        or DARK_LORD_STAGE_ID in plan.get("stage_ids", ())
        or DARK_LORD_STAGE_ID in plan.get("sequence", ())
    ):
        add_target(DARK_LORD_STAGE_ID, "dark_lord_defeated", "Boss: The Dark Lord Defeated")

    return targets


# ═══════════════════════════════════════════════════════════════
# Greedy readiness package selection
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SelectionStep:
    """One activated item copy inside a dependency-complete package."""
    item_name: str
    copy_index: int
    package_lead: str
    package_size: int
    is_dependency: bool
    delta_deficit: float
    delta_cr: float
    target_description: str
    reason: str
    dependency_closure: tuple[str, ...]


@dataclass
class ReadinessSelection:
    steps: list[SelectionStep] = field(default_factory=list)
    counts: Counter[str] = field(default_factory=Counter)
    initial_deficit: float = 0.0
    final_deficit: float = 0.0
    satisfied: bool = False
    evaluations: int = 0


def _reason_for_context(context: str) -> str:
    if context == "spirit_breakpoint":
        return "spirit_breakpoint"
    if context == "dark_lord_defeated":
        return "dark_lord_breakpoint"
    return "cr_readiness"


def select_readiness_items(
    *,
    base_items: Mapping[str, int],
    targets: Sequence[ReadinessTarget],
    additional: Mapping[str, int],
    world_context: Any,
    player: int = 1,
    slack: float = READINESS_PLACEMENT_SLACK,
) -> ReadinessSelection:
    """Deterministically activate dependency-complete item packages until every
    readiness target is satisfied with ``slack`` headroom, or no candidate can
    improve the worst deficit. Pure function of its inputs (no RNG).
    """
    selection = ReadinessSelection()
    if not targets:
        selection.satisfied = True
        return selection

    state = FastState.from_counts(base_items, player=player)
    used: Counter[str] = Counter()
    cr_cache: dict[tuple, float] = {}
    target_cache: dict[tuple, tuple[float, ReadinessTarget | None]] = {}

    def state_key(st: FastState) -> tuple:
        return tuple(sorted(st.prog_items.items()))

    def player_cr(st: FastState) -> float:
        key = state_key(st)
        cached = cr_cache.get(key)
        if cached is None:
            cached = float(evaluate_player_loadout_cr(st, player, world_context).total)
            cr_cache[key] = cached
        return cached

    def worst_deficit(st: FastState) -> tuple[float, ReadinessTarget | None]:
        key = state_key(st)
        cached = target_cache.get(key)
        if cached is not None:
            return cached
        cr = player_cr(st)
        worst = -999.0
        worst_target: ReadinessTarget | None = None
        for target in targets:
            result = evaluate_mission_readiness(
                st, player, target.stage_id, world_context,
                context=target.context, player_cr=cr,
            )
            deficit = result.effective_cr - result.player_cr - result.allowance
            if result.preparation_deficit > 0:
                deficit = max(deficit, result.preparation_deficit)
            if deficit > worst:
                worst = deficit
                worst_target = target
        cached = (worst, worst_target)
        target_cache[key] = cached
        selection.evaluations += 1
        return cached

    current_deficit, current_worst = worst_deficit(state)
    selection.initial_deficit = current_deficit
    current_cr = player_cr(state)

    while current_deficit > -slack:
        best_lead: str | None = None
        best_package: tuple[str, ...] = ()
        best_delta_deficit = 0.0
        best_delta_cr = 0.0

        for cand_name in sorted(additional):
            if used[cand_name] >= additional[cand_name]:
                continue
            package_items: list[str] = []
            possible = True
            for dep in ITEM_DEPENDENCIES.get(cand_name, ()):
                if state.has(dep, player):
                    continue
                if used[dep] < additional.get(dep, 0):
                    package_items.append(dep)
                else:
                    possible = False
                    break
            if not possible:
                continue
            package_items.append(cand_name)
            full_package = tuple(package_items)

            temp_state = state.copy()
            for pkg_name in full_package:
                temp_state.collect(pkg_name)

            new_max_def, _ = worst_deficit(temp_state)
            delta_def = current_deficit - new_max_def
            if delta_def <= 1e-6:
                continue
            new_cr = player_cr(temp_state)
            delta_cr = new_cr - current_cr

            is_better = False
            if best_lead is None:
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
                        if cand_name < best_lead:
                            is_better = True

            if is_better:
                best_lead = cand_name
                best_package = full_package
                best_delta_deficit = delta_def
                best_delta_cr = delta_cr

        if best_lead is None:
            break

        reason = _reason_for_context(current_worst.context if current_worst is not None else "base")
        target_description = current_worst.description if current_worst is not None else ""

        for pkg_name in best_package:
            state.collect(pkg_name)
            used[pkg_name] += 1
            copy_index = selection.counts[pkg_name] + 1
            selection.counts[pkg_name] += 1
            selection.steps.append(SelectionStep(
                item_name=pkg_name,
                copy_index=copy_index,
                package_lead=best_lead,
                package_size=len(best_package),
                is_dependency=(pkg_name != best_lead),
                delta_deficit=best_delta_deficit,
                delta_cr=best_delta_cr,
                target_description=target_description,
                reason=reason,
                dependency_closure=ITEM_DEPENDENCIES.get(pkg_name, ()),
            ))

        current_cr = player_cr(state)
        current_deficit, current_worst = worst_deficit(state)

    selection.final_deficit = current_deficit
    selection.satisfied = current_deficit <= 0.0
    return selection


# ═══════════════════════════════════════════════════════════════
# Canonical semantic pool
# ═══════════════════════════════════════════════════════════════

@dataclass
class SemanticPool:
    """Concrete multiset authority for one generated world."""
    total_counts: Counter[str] = field(default_factory=Counter)      # pool + requested
    placement_counts: Counter[str] = field(default_factory=Counter)  # itempool view
    compact: bool = False
    optional_selected: Counter[str] = field(default_factory=Counter)
    readiness_initial_deficit: float = 0.0
    readiness_final_deficit: float = 0.0
    readiness_evaluations: int = 0
    auto_adjustments: Counter[str] = field(default_factory=Counter)

    def counts_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.total_counts.items() if qty > 0}

    def placement_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.placement_counts.items() if qty > 0}


def is_compact_campaign(active_normal_ids: Sequence[str]) -> bool:
    return len(active_normal_ids) < FULL_LENGTH_MIN_MISSIONS


def mastery_resource_family_count(normal_mission_count: int) -> int:
    if normal_mission_count <= 3:
        return 2
    if normal_mission_count <= 5:
        return 3
    if normal_mission_count <= 8:
        return 5
    return 13


def special_weapon_pool_count(special_name: str, *, use_dlc: bool, n_normals: int) -> int:
    """Special-weapon multiplicities for full and compact campaigns."""
    if use_dlc and special_name.startswith("Progressive"):
        if n_normals >= FULL_LENGTH_MIN_MISSIONS:
            return SPECIAL_WEAPON_POOL_COUNTS[special_name]
        # Compact: enough real copies to unlock Crucible + Hammer. The further
        # Hammer upgrade (Progressive Special Weapon stage 3 / Hammer stage 2)
        # is omitted when unnecessary.
        return 2 if special_name == "Progressive Special Weapon" else 1
    return SPECIAL_WEAPON_POOL_COUNTS.get(special_name, 1)


def build_semantic_counts(
    options,
    *,
    active_normal_ids: Sequence[str],
    starting_weapon: str | None,
    active_sg: Sequence[Mapping[str, Any]],
    active_masteries_count: int,
    battery_surplus: int,
    targets: Sequence[ReadinessTarget] | None = None,
    player: int = 1,
    world_context: Any = None,
    suit_counts: Mapping[str, int] | None = None,
    compact_runes: Sequence[str] = (),
    placement_budget: int | None = None,
) -> SemanticPool:
    """Build the concrete semantic multiset for the active campaign.

    Compact short worlds include a family floor and select additional copies
    with the production readiness evaluator. Full-length campaigns use full-size economies.
    """
    start_inv = Counter(options.start_inventory.value)
    n_normals = len(active_normal_ids)
    compact = is_compact_campaign(active_normal_ids)
    profile = _option_value(options, "resource_profile", 0)
    lean = profile == 2
    overrides = dict(getattr(getattr(options, "item_pool_counts", None), "value", {}) or {})
    use_dlc = bool(_option_value(options, "use_dlc_content", 1))

    pool = SemanticPool(compact=compact)
    base_pool: Counter[str] = Counter()      # policy floor of pool copies
    optional_caps: Counter[str] = Counter()  # extra selectable copies beyond floor
    mandatory_mods: set[str] = set()
    for name, quantity in (suit_counts or {}).items():
        base_pool[name] = max(0, quantity - start_inv.get(name, 0))
    if compact or lean:
        for name in compact_runes:
            base_pool[name] = max(0, 1 - start_inv.get(name, 0))
        for stat in _CAPACITY_STATS:
            name = f"Progressive {stat} Upgrade"
            base_pool[name] = max(0, 1 - start_inv.get(name, 0))

    if compact:
        mod_floor = min(12, max(6, 2 * n_normals)) if profile == 1 else (0 if lean else 6)
        for mod in ALL_MODS_ORDERED[:mod_floor]:
            base_pool[mod] = max(0, 1 - start_inv.get(mod, 0))
        if profile == 1:
            for rune in NORMAL_RUNES_ORDERED[:min(9, 2 * n_normals)]:
                base_pool[rune] = max(0, 1 - start_inv.get(rune, 0))
            for stat in _CAPACITY_STATS:
                name = f"Progressive {stat} Upgrade"
                base_pool[name] = max(0, min(4, (4 * n_normals + 8) // 9) - start_inv.get(name, 0))

    # --- Weapons (guarantee: 7 normal + BFG-9000) -------------------------
    for weapon in world_pool_weapon_item_names:
        if weapon == starting_weapon:
            continue
        base_pool[weapon] = max(0, 1 - start_inv.get(weapon, 0))

    # --- Core equipment ---------------------------------------------------
    for equipment in CORE_EQUIPMENT:
        quantity = 4 if equipment == "Progressive Blood Punch" else 1
        base_pool[equipment] = max(0, quantity - start_inv.get(equipment, 0))

    # Independent attachment: TAG2 readiness requires it even with masteries off.
    base_pool["Meat Hook"] = max(0, 1 - start_inv.get("Meat Hook", 0))
    mandatory_mods.add("Meat Hook")

    # --- Randomized capabilities -----------------------------------------
    if _option_value(options, "randomize_chainsaw") or start_inv.get("Chainsaw"):
        base_pool["Chainsaw"] = max(0, 1 - start_inv.get("Chainsaw", 0))
    if _option_value(options, "randomize_dash") or start_inv.get("Dash"):
        base_pool["Dash"] = max(0, 1 - start_inv.get("Dash", 0))

    # --- Special weapons ---------------------------------------------------
    special_opt = getattr(options, "special_weapon", None)
    special_name = "The Crucible" if not use_dlc else getattr(
        special_opt, "current_option_name", "Progressive Special Weapon"
    )
    special_policy = special_weapon_pool_count(special_name, use_dlc=use_dlc, n_normals=n_normals)
    base_pool[special_name] = max(0, special_policy - start_inv.get(special_name, 0))

    # --- Slayer Gate Keys --------------------------------------------------
    for stage_id, key_name in STAGE_SLAYER_GATE_KEYS.items():
        if not options.include_slayer_gates.value:
            continue
        if stage_id not in active_normal_ids:
            continue
        if stage_id in ("e4m1_rig", "e4m3_mcity") and not use_dlc:
            continue
        base_pool[key_name] = max(0, 1 - start_inv.get(key_name, 0))

    # --- Battery economy ---------------------------------------------------
    battery_cost = sum(group["cost"] for group in active_sg)
    battery_total = battery_cost + battery_surplus
    if start_inv.get("Sentinel Battery Bundle"):
        raise ValueError("Sentinel Battery Bundle belongs to legacy rooms; use individual Sentinel Battery items")
    if start_inv.get("Sentinel Battery", 0) > battery_total:
        raise ValueError(f"Sentinel Battery starting inventory exceeds the {battery_total}-unit economy")
    base_pool["Sentinel Battery"] = max(
        0, battery_total - start_inv.get("Sentinel Battery", 0)
    )

    # --- Weapon Masteries (content scaling) & prerequisite mods ------------
    family_masteries: list[str] = []
    for mod_name, _location in ORDERED_MASTERY_CHALLENGES[:mastery_resource_family_count(n_normals)]:
        mastery_name = mod_name + " Mastery"
        family_masteries.append(mastery_name)
    requested_masteries = sorted(name for name in ALL_MASTERY_NAMES if start_inv.get(name))
    selected_masteries = family_masteries + [m for m in requested_masteries if m not in family_masteries]
    for mastery_name in selected_masteries:
        base_pool[mastery_name] = max(0, 1 - start_inv.get(mastery_name, 0))
        for dep in ITEM_DEPENDENCIES.get(mastery_name, ()):
            if dep == starting_weapon or dep not in item_data_table:
                continue
            if dep in ALL_MOD_NAMES:
                mandatory_mods.add(dep)
            base_pool[dep] = max(base_pool[dep], max(0, 1 - start_inv.get(dep, 0)))

    # --- Manually requested mod families -----------------------------------
    requested_mods = [mod for mod in ALL_MODS_ORDERED if start_inv.get(mod)]
    for mod in requested_mods:
        mandatory_mods.add(mod)
        base_pool[mod] = max(base_pool[mod], max(0, 1 - start_inv.get(mod, 0)))
        for dep in ITEM_DEPENDENCIES.get(mod, ()):
            if dep == starting_weapon or dep not in item_data_table:
                continue
            if dep in ALL_MOD_NAMES:
                mandatory_mods.add(dep)
            base_pool[dep] = max(base_pool[dep], max(0, 1 - start_inv.get(dep, 0)))

    # --- Mechanically required challenge mods ------------------------------
    for stage_id, mods in HARD_MOD_BY_STAGE.items():
        if stage_id in active_normal_ids:
            for mod in mods:
                mandatory_mods.add(mod)
                base_pool[mod] = max(base_pool[mod], max(0, 1 - start_inv.get(mod, 0)))

    # --- WUP economy -------------------------------------------------------
    active_family_count = len(family_masteries)
    requested_mastery_count = len(requested_masteries)
    effective_families = max(active_family_count, requested_mastery_count)
    if compact:
        wup_policy = 3 * effective_families
    else:
        # Full-length campaigns keep the integral 39-bundle / 117-point
        # normal-upgrade baseline even when Mastery Challenges are disabled.
        wup_policy = WEAPON_UPGRADE_POINTS_ITEM_COUNT
    base_pool[WEAPON_UPGRADE_POINTS_NAME] = max(0, wup_policy - start_inv.get(WEAPON_UPGRADE_POINTS_NAME, 0))

    if not compact and not lean:
        mod_quota = 12
        selected_mods = set(mandatory_mods)
        selected_mods.update(requested_mods)
        for mod in ALL_MODS_ORDERED:
            if len(selected_mods) >= mod_quota:
                break
            selected_mods.add(mod)
        for mod in selected_mods:
            base_pool[mod] = max(base_pool[mod], max(0, 1 - start_inv.get(mod, 0)))
        for rune in NORMAL_RUNES_ORDERED:
            base_pool[rune] = max(base_pool[rune], max(0, 1 - start_inv.get(rune, 0)))
        if use_dlc:
            for support in SUPPORT_RUNES_ORDERED:
                base_pool[support] = max(base_pool[support], max(0, 1 - start_inv.get(support, 0)))
        for stat in _CAPACITY_STATS:
            stat_name = f"Progressive {stat} Upgrade"
            requested = start_inv.get(stat_name, 0)
            base_pool[stat_name] = max(base_pool[stat_name], max(0, _CAPACITY_MAX_STAGES - requested))

    # --- Optional selection universes --------------------------------------
    for mod in ALL_MODS_ORDERED:
        if mod in mandatory_mods:
            optional_caps[mod] = 0
        else:
            optional_caps[mod] = max(0, 1 - start_inv.get(mod, 0) - base_pool.get(mod, 0))
    if compact or lean:
        for rune in NORMAL_RUNES_ORDERED:
            optional_caps[rune] = max(0, 1 - start_inv.get(rune, 0) - base_pool.get(rune, 0))
        if use_dlc:
            for support in SUPPORT_RUNES_ORDERED:
                optional_caps[support] = max(0, 1 - start_inv.get(support, 0) - base_pool.get(support, 0))
        for stat in _CAPACITY_STATS:
            stat_name = f"Progressive {stat} Upgrade"
            optional_caps[stat_name] = max(
                0, _CAPACITY_MAX_STAGES - start_inv.get(stat_name, 0) - base_pool.get(stat_name, 0)
            )

    for name, quantity in overrides.items():
        if quantity and ((name in SUPPORT_RUNE_NAMES and not use_dlc)
                         or (name in SPECIAL_WEAPON_POOL_COUNTS and name != special_name)):
            raise ValueError(f"Item Pool Overrides: {name} is unavailable in this campaign")
        base_pool[name] = max(0, quantity - start_inv.get(name, 0) - int(name == starting_weapon))
        optional_caps[name] = 0
    available = Counter(base_pool) + start_inv
    if starting_weapon:
        available[starting_weapon] += 1
    if not _option_value(options, "randomize_dash"):
        available["Dash"] += 1
    if not _option_value(options, "randomize_chainsaw"):
        available["Chainsaw"] += 1
    for name in list(available):
        for dependency in ITEM_DEPENDENCIES.get(name, ()):
            if available[dependency] > 0:
                continue
            if dependency in overrides:
                raise ValueError(f"Item Pool Overrides: {name} requires {dependency}")
            base_pool[dependency] = available[dependency] = 1
    required_mods = {mod for mod, _ in ORDERED_MASTERY_CHALLENGES[:active_masteries_count]}
    required_mods.update(mod for stage_id, mods in HARD_MOD_BY_STAGE.items() if stage_id in active_normal_ids for mod in mods)
    if set(active_normal_ids) & HOOK_TRAVERSAL_STAGES:
        required_mods.add("Meat Hook")
    for mod in required_mods:
        if available[mod] <= 0:
            raise ValueError(f"Item Pool Overrides: {mod} is required by active challenges")
    if available[WEAPON_UPGRADE_POINTS_NAME] < 3 * max(active_masteries_count, requested_mastery_count):
        raise ValueError("Item Pool Overrides: Weapon Upgrade Points do not cover active mastery challenges")

    # --- Baseline logical state (mirrors dynamic classification) -----------
    baseline: Counter[str] = Counter()
    for name, qty in start_inv.items():
        if name in item_data_table:
            baseline[name] += qty
    if starting_weapon:
        baseline[starting_weapon] += 1
    if not _option_value(options, "randomize_dash"):
        baseline["Dash"] = 1
    if not _option_value(options, "randomize_chainsaw"):
        baseline["Chainsaw"] = 1

    mastery_victory_active = (
        "Complete All Weapon Mastery Challenges" in set(
            getattr(getattr(options, "additional_victory_requirements", None), "value", ()) or ()
        )
        and effective_families > 0
    )
    wup_promoted = 0
    if mastery_victory_active:
        wup_promoted = min(3 * effective_families, base_pool.get(WEAPON_UPGRADE_POINTS_NAME, 0))
        baseline[WEAPON_UPGRADE_POINTS_NAME] += wup_promoted

    for name in list(base_pool) + list(optional_caps):
        qty = base_pool.get(name, 0)
        if qty <= 0 or not _item_is_progression(name) or name in COMBAT_BASELINE_NAMES:
            continue
        baseline[name] += qty

    # --- Activation budget --------------------------------------------------
    activatable: Counter[str] = Counter()
    for name in set(base_pool) | set(optional_caps):
        pool_copies = base_pool.get(name, 0) + optional_caps.get(name, 0)
        if pool_copies <= 0:
            continue
        in_baseline = 0
        if _item_is_progression(name) and name not in COMBAT_BASELINE_NAMES:
            in_baseline = base_pool.get(name, 0)
        budget = max(0, pool_copies - in_baseline)
        if budget > 0:
            activatable[name] = budget

    selection = ReadinessSelection(satisfied=True)
    if targets and (compact or lean or overrides):
        selection = select_readiness_items(
            base_items=baseline,
            targets=targets,
            additional=activatable,
            world_context=world_context,
            player=player,
        )
        pool.readiness_initial_deficit = selection.initial_deficit
        pool.readiness_final_deficit = selection.final_deficit
        pool.readiness_evaluations = selection.evaluations
        if not selection.satisfied:
            raise ValueError(f"Item Pool Overrides cannot satisfy campaign readiness (deficit {selection.final_deficit:g})")

    # --- Final concrete multiset -------------------------------------------
    used = selection.counts
    names = set(base_pool) | set(optional_caps) | set(used)
    for name in names:
        base_copies = base_pool.get(name, 0)
        in_baseline = 0
        if _item_is_progression(name) and name not in COMBAT_BASELINE_NAMES:
            in_baseline = base_copies
        pool_copies = max(base_copies, in_baseline + used.get(name, 0))
        pool_copies = min(pool_copies, base_copies + optional_caps.get(name, 0))
        if pool_copies > 0:
            pool.placement_counts[name] = pool_copies
    if placement_budget is not None and sum(pool.placement_counts.values()) > placement_budget:
        from .locations import location_data_table, optional_location_enabled
        from .logic import build_location_prerequisites, connection_requirement, required_item_names
        from .generated_content import CAMPAIGN_CONNECTIONS

        stage_ids = {target.stage_id for target in targets or ()} | set(active_normal_ids)
        regions = {region for stage in CAMPAIGN_STAGES if stage["id"] in stage_ids for region in stage["regions"]}
        mastery_locations = {name for _, name in ORDERED_MASTERY_CHALLENGES[:active_masteries_count]}
        active_locations = {name for name, data in location_data_table.items()
                            if data.code is not None and optional_location_enabled(name, options)
                            and (data.region in regions or data.region.startswith("Fortress of Doom"))
                            and (not name.endswith(" - Weapon Mastery Challenge") or name in mastery_locations)}
        active_regions = regions | {location_data_table[name].region for name in active_locations}
        requirements = build_location_prerequisites(
            active_locations, active_region_names=active_regions,
            randomize_chainsaw=bool(_option_value(options, "randomize_chainsaw")),
            randomize_dash=bool(_option_value(options, "randomize_dash")),
            special_weapon=special_name, logic_difficulty=_option_value(options, "logic_difficulty", 1),
            active_spend_groups=active_sg,
        )
        hard_items = set().union(*(required_item_names(req) for req in requirements.values()))
        for source, destination, _, condition in CAMPAIGN_CONNECTIONS:
            if source in active_regions and destination in active_regions:
                hard_items.update(required_item_names(connection_requirement(
                    condition, randomize_dash=bool(_option_value(options, "randomize_dash")))))
        if "Blood Punch" in hard_items:
            hard_items.add("Progressive Blood Punch")
        locked = set(overrides)
        if _option_value(options, "praetor_suit_upgrades_in_pool", -2) != -2:
            locked.update(suit_counts or {})
        candidates = (set(ALL_MOD_NAMES) | set(NORMAL_RUNE_NAMES) | set(SUPPORT_RUNE_NAMES)
                      | set(suit_perk_item_names) | {f"Progressive {stat} Upgrade" for stat in _CAPACITY_STATS}
                      | {"Progressive Blood Punch"}) - locked - hard_items

        def inventory_counts():
            counts = pool.placement_counts + start_inv
            if starting_weapon:
                counts[starting_weapon] += 1
            for name, option in (("Dash", "randomize_dash"), ("Chainsaw", "randomize_chainsaw")):
                if not _option_value(options, option):
                    counts[name] = max(1, counts[name])
            return counts

        while sum(pool.placement_counts.values()) > placement_budget:
            counts = inventory_counts()
            before_cr = evaluate_player_loadout_cr(FastState.from_counts(counts, player), player, world_context).total
            best = None
            for name in sorted(candidates):
                if pool.placement_counts[name] <= 0:
                    continue
                minimum = int(name.startswith("Progressive "))
                if counts[name] <= minimum:
                    continue
                if name in NORMAL_RUNE_NAMES and sum(counts[rune] for rune in NORMAL_RUNE_NAMES) <= (1 if lean else 2):
                    continue
                reduced = counts.copy()
                reduced[name] -= 1
                if any(reduced[parent] and any(reduced[dep] <= 0 for dep in deps)
                       for parent, deps in ITEM_DEPENDENCIES.items()):
                    continue
                state = FastState.from_counts(reduced, player)
                cr = evaluate_player_loadout_cr(state, player, world_context).total
                results = [evaluate_mission_readiness(state, player, target.stage_id, world_context,
                           context=target.context, player_cr=cr) for target in targets or ()]
                pool.readiness_evaluations += len(results)
                if not all(result.ready for result in results):
                    continue
                score = (before_cr - cr, -counts[name], name)
                if best is None or score < best:
                    best = score
            if best is None:
                break
            name = best[2]
            pool.placement_counts[name] -= 1
            pool.auto_adjustments[name] += 1
        state = FastState.from_counts(inventory_counts(), player)
        results = [evaluate_mission_readiness(state, player, target.stage_id, world_context,
                   context=target.context) for target in targets or ()]
        if results:
            pool.readiness_final_deficit = max(
                max(result.effective_cr - result.player_cr - result.allowance, result.preparation_deficit)
                if result.preparation_deficit > 0 else result.effective_cr - result.player_cr - result.allowance
                for result in results)
    for name in set(pool.placement_counts) | set(start_inv):
        data = item_data_table.get(name)
        if data is None:
            continue
        pool.total_counts[name] = pool.placement_counts.get(name, 0) + start_inv.get(name, 0)

    for name, qty in used.items():
        if qty > 0 and name not in mandatory_mods and name != WEAPON_UPGRADE_POINTS_NAME:
            pool.optional_selected[name] = min(qty, pool.placement_counts.get(name, 0))
    pool.auto_adjustments += Counter()

    return pool


def build_pool_candidate_counts(
    options,
    active_normal_ids,
    starting_weapon,
    active_sg,
    active_masteries_count,
    *,
    battery_surplus: int = 1,
    targets: Sequence[ReadinessTarget] | None = None,
    player: int = 1,
    world_context: Any = None,
) -> Counter:
    """Placement-view candidate pool consumed by the bootstrap solver.

    Production ``create_items`` consumes the semantic builder through
    ``plan['semantic_counts']``.
    """
    if targets is None and is_compact_campaign(active_normal_ids):
        provisional_plan: dict[str, Any] = {
            "sequence": [*active_normal_ids],
            "active_normal_mission_ids": list(active_normal_ids),
            "goal_stage": None,
            "stage_ids": list(active_normal_ids),
        }
        targets = derive_readiness_targets(options, provisional_plan)
    pool = build_semantic_counts(
        options,
        active_normal_ids=active_normal_ids,
        starting_weapon=starting_weapon,
        active_sg=active_sg,
        active_masteries_count=active_masteries_count,
        battery_surplus=battery_surplus,
        targets=targets,
        player=player,
        world_context=world_context,
    )
    return Counter(pool.placement_counts)
