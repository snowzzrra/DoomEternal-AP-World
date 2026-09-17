"""Canonical semantic pool planner and readiness package selector (Phase 7.8B).

This module is the single source of truth for:

- optional-item dependency closure (:data:`ITEM_DEPENDENCIES`),
- readiness target derivation for the active campaign,
- greedy dependency-aware optional selection driven by the production
  readiness evaluator (never by fixed per-category quotas),
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
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    WEAPON_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    DARK_LORD_STAGE_ID,
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
)

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}

READINESS_PLACEMENT_SLACK: float = 6.0

FULL_LENGTH_MIN_MISSIONS = 9

DLC_STAGE_IDS = frozenset({
    "e4m1_rig", "e4m2_swamp", "e4m3_mcity",
    "e5m1_spear", "e5m2_earth", "e5m3_hell", "e5m4_boss",
})

CORE_EQUIPMENT = ("Frag Grenade", "Blood Punch", "Flame Belch", "Ice Bomb")

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
    "Meat Hook Mastery": ("Super Shotgun",),
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

# Items the dynamic classifier demotes to ``useful`` before readiness
# evaluation (combat baseline); they only count once promoted.
COMBAT_BASELINE_NAMES = frozenset(WEAPON_NAMES) | frozenset(ALL_MOD_NAMES)

# Modules that are mechanically mandatory because an active challenge rule
# requires them conjunctively (owner: logic.build_location_prerequisites).
HARD_MOD_BY_STAGE: dict[str, tuple[str, ...]] = {
    "e3m3_maykr": ("Precision Bolt",),
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
        return self.prog_items[item_name]

    def has(self, item_name, player):
        return self.prog_items[item_name] > 0

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

    dlc_timing = getattr(options, "dlc_logic_timing", None)
    is_from_the_beginning = (dlc_timing is not None and getattr(dlc_timing, "value", 0) == 1)

    if order_val == "mission_access_as_items":
        active_ids = list(plan.get("active_normal_mission_ids", []))
        goal_stage = plan.get("goal_stage")
        if goal_stage and goal_stage not in active_ids and goal_stage in STAGE_BY_ID:
            active_ids.append(goal_stage)
        for s_id in active_ids:
            s_name = STAGE_BY_ID[s_id]["name"]
            if not (is_from_the_beginning and s_id in DLC_STAGE_IDS):
                add_target(s_id, "base", f"Mission: {s_name}")
            if s_id in spirit_stage_ids:
                add_target(s_id, "spirit_breakpoint", f"Spirit Breakpoint: {s_name}")
    else:
        sequence = plan.get("sequence", [])
        for s_id in sequence:
            s_name = STAGE_BY_ID[s_id]["name"]
            if not (is_from_the_beginning and s_id in DLC_STAGE_IDS):
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

    def counts_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.total_counts.items() if qty > 0}

    def placement_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.placement_counts.items() if qty > 0}


def is_compact_campaign(active_normal_ids: Sequence[str]) -> bool:
    return len(active_normal_ids) < FULL_LENGTH_MIN_MISSIONS


def special_weapon_pool_count(special_name: str, *, use_dlc: bool, n_normals: int) -> int:
    """Frozen special-weapon multiplicities, compact-aware (Phase 7.8B §2A/§R08)."""
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
) -> SemanticPool:
    """Build the concrete semantic multiset for the active campaign.

    Compact short worlds select optional families only when the production
    readiness evaluator proves they are needed. Full-length campaigns preserve
    the frozen legacy economies.
    """
    start_inv = Counter(options.start_inventory.value)
    n_normals = len(active_normal_ids)
    compact = is_compact_campaign(active_normal_ids)
    use_dlc = bool(_option_value(options, "use_dlc_content", 1))

    pool = SemanticPool(compact=compact)
    base_pool: Counter[str] = Counter()      # policy floor of pool copies
    optional_caps: Counter[str] = Counter()  # extra selectable copies beyond floor
    mandatory_mods: set[str] = set()

    # --- Weapons (guarantee: 7 normal + BFG-9000) -------------------------
    for weapon in world_pool_weapon_item_names:
        if weapon == starting_weapon:
            continue
        base_pool[weapon] = max(0, 1 - start_inv.get(weapon, 0))

    # --- Core equipment ---------------------------------------------------
    for equipment in CORE_EQUIPMENT:
        base_pool[equipment] = max(0, 1 - start_inv.get(equipment, 0))

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
        if stage_id not in active_normal_ids:
            continue
        if stage_id in ("e4m1_rig", "e4m3_mcity") and not use_dlc:
            continue
        base_pool[key_name] = max(0, 1 - start_inv.get(key_name, 0))

    # --- Battery economy ---------------------------------------------------
    sg_count = len(active_sg)
    if sg_count > 0:
        num_bundles = sg_count + battery_surplus
        base_pool["Sentinel Battery Bundle"] = max(0, num_bundles - start_inv.get("Sentinel Battery Bundle", 0))
    first_battery_random = bool(
        _option_value(options, "randomize_first_battery") and "e1m2_war" in active_normal_ids
    )
    single_policy = 1 if first_battery_random else 0
    base_pool["Sentinel Battery"] = max(0, single_policy - start_inv.get("Sentinel Battery", 0))

    # --- Weapon Masteries (content scaling) & prerequisite mods ------------
    family_masteries: list[str] = []
    for mod_name, _location in ORDERED_MASTERY_CHALLENGES[:active_masteries_count]:
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

    if compact:
        # Requested optional families are mandatory; the rest is selection-driven.
        for rune in NORMAL_RUNES_ORDERED:
            if start_inv.get(rune):
                base_pool[rune] = max(base_pool[rune], 1)
        if use_dlc:
            for support in SUPPORT_RUNES_ORDERED:
                if start_inv.get(support):
                    base_pool[support] = max(base_pool[support], 1)
        for stat in _CAPACITY_STATS:
            stat_name = f"Progressive {stat} Upgrade"
            requested = start_inv.get(stat_name, 0)
            if requested:
                base_pool[stat_name] = max(base_pool[stat_name], requested)
    else:
        # Full-length: preserve the frozen legacy optional families.
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
    if compact:
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

    # --- Baseline logical state (mirrors dynamic classification) -----------
    baseline: Counter[str] = Counter()
    for name, qty in start_inv.items():
        if name in item_data_table:
            baseline[name] += qty
    if starting_weapon:
        baseline[starting_weapon] += 1

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
    if compact and targets:
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
    for name in set(pool.placement_counts) | set(start_inv):
        data = item_data_table.get(name)
        if data is None:
            continue
        pool.total_counts[name] = pool.placement_counts.get(name, 0) + start_inv.get(name, 0)

    for name, qty in used.items():
        if qty > 0 and name not in mandatory_mods and name != WEAPON_UPGRADE_POINTS_NAME:
            pool.optional_selected[name] = qty

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

    Compatibility wrapper kept for existing callers/tests; the same builder
    feeds production ``create_items`` through ``plan['semantic_counts']``.
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
