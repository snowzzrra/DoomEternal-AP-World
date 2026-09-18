"""Player Loadout Combat Rating.

Evaluates CR from logical item ownership in a CollectionState,
**not** from live game state.  No solver, no difficulty gating,
no fill changes.  Pure read-only query.
"""
from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from BaseClasses import CollectionState

CATEGORY_CAPS: dict[str, float] = {
    "Arsenal":          35.0,
    "Enhancements":     10.0,
    "Sustain":          20.0,
    "Defense":          15.0,
    "Mobility":         10.0,
    "Control / Utility": 10.0,
}

WEAPON_BASE: dict[str, float] = {
    "Ballista":         12.0,
    "Super Shotgun":    10.0,
    "Rocket Launcher":  10.0,
    "Heavy Cannon":      8.0,
    "Plasma Rifle":      7.0,
    "Combat Shotgun":    6.0,
    "Chaingun":          5.0,
}
WEAPON_NAMES = frozenset(WEAPON_BASE)

# Diminishing-return multipliers for sorted (desc) weapons
WEAPON_MULTIPLIERS = (1.00, 0.95, 0.85, 0.70, 0.55, 0.40, 0.30)
# Breadth bonus by weapon count (0..7)
BREADTH_BONUS = (0.0, 0.0, 2.0, 5.0, 8.0, 10.0, 11.0, 12.0)

MOD_HOST: dict[str, str] = {
    "Sticky Bombs":     "Combat Shotgun",
    "Full Auto":        "Combat Shotgun",
    "Precision Bolt":   "Heavy Cannon",
    "Micro Missiles":   "Heavy Cannon",
    "Heat Blast":       "Plasma Rifle",
    "Microwave Beam":   "Plasma Rifle",
    "Remote Detonate":  "Rocket Launcher",
    "Lock-on Burst":    "Rocket Launcher",
    "Arbalest":         "Ballista",
    "Destroyer Blade":  "Ballista",
    "Energy Shield":    "Chaingun",
    "Mobile Turret":    "Chaingun",
}
ALL_MOD_NAMES = frozenset(MOD_HOST)

MASTERY_HOST: dict[str, tuple[str, ...]] = {
    "Sticky Bombs Mastery":     ("Combat Shotgun", "Sticky Bombs"),
    "Full Auto Mastery":        ("Combat Shotgun", "Full Auto"),
    "Precision Bolt Mastery":   ("Heavy Cannon", "Precision Bolt"),
    "Micro Missiles Mastery":   ("Heavy Cannon", "Micro Missiles"),
    "Heat Blast Mastery":       ("Plasma Rifle", "Heat Blast"),
    "Microwave Beam Mastery":   ("Plasma Rifle", "Microwave Beam"),
    "Remote Detonate Mastery":  ("Rocket Launcher", "Remote Detonate"),
    "Lock-on Burst Mastery":    ("Rocket Launcher", "Lock-on Burst"),
    "Arbalest Mastery":         ("Ballista", "Arbalest"),
    "Destroyer Blade Mastery":  ("Ballista", "Destroyer Blade"),
    "Energy Shield Mastery":    ("Chaingun", "Energy Shield"),
    "Mobile Turret Mastery":    ("Chaingun", "Mobile Turret"),
    "Meat Hook Mastery":        ("Super Shotgun", "Meat Hook"),
}
ALL_MASTERY_NAMES = frozenset(MASTERY_HOST)

_Contrib = tuple[str, float, tuple[str, ...]]  # (category, value, deps)

def _flat(*pairs: tuple[str, float], deps: tuple[str, ...] = ()) -> list[_Contrib]:
    return [(cat, val, deps) for cat, val in pairs]

def _mod_contribs(host: str, enhancement: float, control: float = 0.0) -> list[_Contrib]:
    deps = (host,)
    result = [(f"Enhancements", enhancement, deps)]
    if control:
        result.append(("Control / Utility", control, deps))
    return result

def _mastery_contribs(deps: tuple[str, ...], enhancement: float = 0, control: float = 0, defense: float = 0, sustain: float = 0) -> list[_Contrib]:
    result: list[_Contrib] = []
    if enhancement:
        result.append(("Enhancements", enhancement, deps))
    if control:
        result.append(("Control / Utility", control, deps))
    if defense:
        result.append(("Defense", defense, deps))
    if sustain:
        result.append(("Sustain", sustain, deps))
    return result

ITEM_CONTRIBUTIONS: dict[str, list[_Contrib]] = {
    # Equipment & tools
    "Chainsaw":                 _flat(("Sustain", 7), ("Control / Utility", 1)),
    "Flame Belch":              _flat(("Sustain", 7), ("Control / Utility", 1)),
    "Ice Bomb":                 _flat(("Defense", 3), ("Control / Utility", 4)),
    "Frag Grenade":             _flat(("Enhancements", 2), ("Control / Utility", 2)),
    "Blood Punch":              _flat(("Enhancements", 2), ("Control / Utility", 1)),
    "Dash":                     _flat(("Mobility", 4), ("Defense", 2)),
    "Ammo Refill":              _flat(("Sustain", 2)),

    # Suit perks (no dependency)
    "Faster Ledge Grab":        _flat(("Mobility", 1)),
    "Reduced Hazard Damage":    _flat(("Defense", 1)),
    "Reduced Self Damage":      _flat(("Defense", 1)),
    "Respawning Barrels":       _flat(("Sustain", 1)),
    "Ammo from Barrels":        _flat(("Sustain", 2)),
    "Powerup Extender":         _flat(("Defense", 1)),

    # Suit perks WITH dependencies
    "Faster Dash Recharge":     _flat(("Mobility", 2.5), ("Defense", 0.5), deps=("Dash",)),
    "Dash Refill on Glory Kill": _flat(("Mobility", 1), deps=("Dash",)),
    "Frag Grenade Cooldown":    _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Frag Grenade Concussive Blast": _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Frag Grenade Cluster Bombs": _flat(("Enhancements", 1), deps=("Frag Grenade",)),
    "Second Frag Grenade":      _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Ice Bomb Cooldown":        _flat(("Control / Utility", 1), deps=("Ice Bomb",)),
    "Extended Ice Bomb Duration": _flat(("Control / Utility", 1), deps=("Ice Bomb",)),
    "Health from Frozen Demons": _flat(("Sustain", 1), deps=("Ice Bomb",)),
    "Frozen Melee Shatter":     _flat(("Control / Utility", 1), deps=("Ice Bomb",)),

    # Mods (host weapon dependency)
    "Sticky Bombs":             _mod_contribs("Combat Shotgun", 4, 2),
    "Full Auto":                _mod_contribs("Combat Shotgun", 2, 1),
    "Precision Bolt":           _mod_contribs("Heavy Cannon", 6, 1),
    "Micro Missiles":           _mod_contribs("Heavy Cannon", 2, 1),
    "Heat Blast":               _mod_contribs("Plasma Rifle", 2, 1),
    "Microwave Beam":           _mod_contribs("Plasma Rifle", 1, 2),
    "Remote Detonate":          _mod_contribs("Rocket Launcher", 2, 1),
    "Lock-on Burst":            _mod_contribs("Rocket Launcher", 6, 1),
    "Arbalest":                 _mod_contribs("Ballista", 3, 1),
    "Destroyer Blade":          _mod_contribs("Ballista", 5, 2),
    "Energy Shield":            [("Enhancements", 1, ("Chaingun",)),
                                 ("Defense", 7, ("Chaingun",)),
                                 ("Control / Utility", 2, ("Chaingun",))],
    "Mobile Turret":            _mod_contribs("Chaingun", 2, 1),

    # Masteries (host weapon + base mod dependency)
    "Sticky Bombs Mastery":     _mastery_contribs(("Combat Shotgun", "Sticky Bombs"), enhancement=1),
    "Full Auto Mastery":        _mastery_contribs(("Combat Shotgun", "Full Auto"), enhancement=1),
    "Precision Bolt Mastery":   _mastery_contribs(("Heavy Cannon", "Precision Bolt"), enhancement=2),
    "Micro Missiles Mastery":   _mastery_contribs(("Heavy Cannon", "Micro Missiles"), enhancement=1),
    "Heat Blast Mastery":       _mastery_contribs(("Plasma Rifle", "Heat Blast"), enhancement=1),
    "Microwave Beam Mastery":   _mastery_contribs(("Plasma Rifle", "Microwave Beam"), control=1),
    "Remote Detonate Mastery":  _mastery_contribs(("Rocket Launcher", "Remote Detonate"), enhancement=1),
    "Lock-on Burst Mastery":    _mastery_contribs(("Rocket Launcher", "Lock-on Burst"), enhancement=2),
    "Arbalest Mastery":         _mastery_contribs(("Ballista", "Arbalest"), enhancement=1),
    "Destroyer Blade Mastery":  _mastery_contribs(("Ballista", "Destroyer Blade"), enhancement=2),
    "Energy Shield Mastery":    _mastery_contribs(("Chaingun", "Energy Shield"), defense=1),
    "Mobile Turret Mastery":    _mastery_contribs(("Chaingun", "Mobile Turret"), enhancement=1),
    "Meat Hook Mastery":        _mastery_contribs(("Super Shotgun", "Meat Hook"), sustain=7),

    # Zero-CR items (cataloged but no contribution)
    "Meat Hook":                [],
    "Savagery":                 [],
    "Chrono Strike":            [],
}

NORMAL_RUNE_CONTRIBS: dict[str, list[_Contrib]] = {
    "Savagery":         [],
    "Seek and Destroy": _flat(("Enhancements", 1), ("Control / Utility", 2)),
    "Blood Fueled":     _flat(("Mobility", 1)),
    "Air Control":      _flat(("Mobility", 6)),
    "Dazed and Confused": _flat(("Control / Utility", 1)),
    "Saving Throw":     _flat(("Defense", 5)),
    "Chrono Strike":    [],
    "Equipment Fiend":  _flat(("Sustain", 2), ("Control / Utility", 2)),
    "Punch and Reave":  _flat(("Sustain", 1), ("Control / Utility", 1)),
}
NORMAL_RUNE_NAMES = frozenset(NORMAL_RUNE_CONTRIBS)

SUPPORT_RUNE_CONTRIBS: dict[str, list[_Contrib]] = {
    "Break Blast":      _flat(("Enhancements", 1), ("Control / Utility", 1)),
    "Desperate Punch":  _flat(("Enhancements", 1), ("Control / Utility", 1)),
    "Take Back":        _flat(("Defense", 1), ("Control / Utility", 1)),
}
SUPPORT_RUNE_NAMES = frozenset(SUPPORT_RUNE_CONTRIBS)

# ── Progressive capacities ────────────────────────────────────
# CR per stage (1-indexed, up to 4 each)
HEALTH_CR_PER_STAGE = 1.75   # Defense
ARMOR_CR_PER_STAGE  = 1.50   # Defense
AMMO_CR_PER_STAGE   = 1.75   # Sustain

# ── WUP ───────────────────────────────────────────────────────
WUP_ENHANCEMENT_PER_COPY = 0.25
WUP_ENHANCEMENT_CAP      = 4.0

# ── Faster Weapon Swap ────────────────────────────────────────
FASTER_WEAPON_SWAP_RATIO = 0.15
FASTER_WEAPON_SWAP_CAP   = 6.0

# ── Special weapon modes ──────────────────────────────────────
# Crucible standalone: Arsenal +9, Control +1
# Progressive Special Weapon:
#   stage 1: Crucible (A+9, C+1)
#   stage 2: Crucible retained, Hammer active (A+7, S+7, D+2, C+6)
#   stage 3: stage 2 + A+2
# Progressive Sentinel Hammer:
#   stage 1: Hammer (A+7, S+7, D+2, C+6)
#   stage 2: Hammer + upgrade A+2


# ═══════════════════════════════════════════════════════════════
# Core evaluator
# ═══════════════════════════════════════════════════════════════

def _normal_arsenal(weapons: tuple[str, ...]) -> float:
    """Diminishing-return Arsenal from sorted weapon list."""
    total = sum(
        WEAPON_BASE[w] * WEAPON_MULTIPLIERS[i]
        for i, w in enumerate(weapons[:len(WEAPON_MULTIPLIERS)])
    )
    total += BREADTH_BONUS[min(len(weapons), len(BREADTH_BONUS) - 1)]
    return total


def _special_variants(mode: str, stage: int) -> tuple[tuple[str, int], ...]:
    """Mutually exclusive equipped Special Weapon alternatives.

    Progressive Special Weapon keeps the Crucible selectable at stage >= 2,
    so both the retained Crucible and the Hammer are valid equipped choices;
    only the best alternative may be counted, never their sum.
    """
    if mode == "none" or stage <= 0:
        return (("none", 0),)
    if mode == "progressive_special" and stage >= 2:
        return (("progressive_special", stage), ("crucible", 1))
    return ((mode, stage),)


def _apply_special(mode: str, stage: int, raw: dict[str, float]) -> None:
    """Add special-weapon contributions to raw category totals."""
    if mode == "none":
        return
    elif mode == "crucible":
        if stage >= 1:
            raw["Arsenal"] += 9
            raw["Control / Utility"] += 1
    elif mode == "progressive_special":
        if stage == 1:
            raw["Arsenal"] += 9
            raw["Control / Utility"] += 1
        elif stage >= 2:
            # Hammer becomes selectable; Crucible retained
            raw["Arsenal"] += 7
            raw["Sustain"] += 7
            raw["Defense"] += 2
            raw["Control / Utility"] += 6
            if stage >= 3:
                raw["Arsenal"] += 2  # Hammer upgrade
    elif mode == "progressive_hammer":
        if stage >= 1:
            raw["Arsenal"] += 7
            raw["Sustain"] += 7
            raw["Defense"] += 2
            raw["Control / Utility"] += 6
            if stage >= 2:
                raw["Arsenal"] += 2  # upgrade


from dataclasses import dataclass
from typing import Any

from .logic import chainsaw_available, dash_available


@dataclass(frozen=True)
class PlayerLoadoutCR:
    """Evaluated Player Loadout Combat Rating result (P7.4)."""
    total: float
    categories: dict[str, float]
    raw_categories: dict[str, float]
    selected_runes: tuple[str, ...] = ()
    selected_support: str | None = None

    @property
    def total_cr(self) -> float:
        return self.total

    @property
    def final(self) -> float:
        return self.total

    @property
    def capped(self) -> dict[str, float]:
        return self.categories

    @property
    def raw(self) -> dict[str, float]:
        return self.raw_categories

    def __getitem__(self, key: str) -> Any:
        if key in ("final", "total", "total_cr"):
            return self.total
        if key in ("capped", "categories"):
            return self.categories
        if key in ("raw", "raw_categories"):
            return self.raw_categories
        if key == "selected_runes":
            return self.selected_runes
        if key == "selected_support":
            return self.selected_support
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


def _evaluate_with_rune_selection(
    owned: set[str],
    selected_runes: tuple[str, ...],
    selected_support: str | None,
    *,
    health_stages: int,
    armor_stages: int,
    ammo_stages: int,
    wup_count: int,
    special_mode: str,
    special_stage: int,
) -> dict[str, object]:
    """Evaluate CR for a specific rune/support selection."""
    raw: dict[str, float] = {cat: 0.0 for cat in CATEGORY_CAPS}

    # 1. Normal weapon Arsenal (diminishing returns + breadth)
    weapons = tuple(sorted(
        (n for n in owned if n in WEAPON_BASE),
        key=lambda n: WEAPON_BASE[n],
        reverse=True,
    ))
    normal_arsenal = _normal_arsenal(weapons)
    raw["Arsenal"] += normal_arsenal

    # Ballista soft Mobility
    if "Ballista" in weapons:
        raw["Mobility"] += 1.5
    # SSG explicit Meat Hook Mobility
    if "Super Shotgun" in weapons and "Meat Hook" in owned:
        raw["Mobility"] += 2

    # 2. Progressive capacities
    raw["Defense"] += health_stages * HEALTH_CR_PER_STAGE
    raw["Defense"] += armor_stages * ARMOR_CR_PER_STAGE
    raw["Sustain"] += ammo_stages * AMMO_CR_PER_STAGE

    # 3. WUP
    raw["Enhancements"] += min(WUP_ENHANCEMENT_CAP, max(0, wup_count) * WUP_ENHANCEMENT_PER_COPY)

    # 4. Non-rune item contributions (equipment, mods, masteries, suit perks)
    for name in owned:
        if name in NORMAL_RUNE_NAMES or name in SUPPORT_RUNE_NAMES:
            continue
        for cat, val, deps in ITEM_CONTRIBUTIONS.get(name, []):
            if all(dep in owned for dep in deps):
                raw[cat] += val

    # 5. Selected normal runes
    for name in selected_runes:
        for cat, val, deps in NORMAL_RUNE_CONTRIBS[name]:
            if all(dep in owned for dep in deps):
                raw[cat] += val

    # 6. Selected support rune
    if selected_support is not None:
        for cat, val, deps in SUPPORT_RUNE_CONTRIBS[selected_support]:
            if all(dep in owned for dep in deps):
                raw[cat] += val

    # 7. Faster Weapon Swap: +15% of normal Arsenal (capped normal) → Enhancement
    if "Faster Weapon Swap" in owned and weapons:
        effective_arsenal = min(normal_arsenal, CATEGORY_CAPS["Arsenal"])
        bonus = min(FASTER_WEAPON_SWAP_CAP, FASTER_WEAPON_SWAP_RATIO * effective_arsenal)
        raw["Enhancements"] += bonus

    # 8. Special weapon: evaluate the best OWNED equipped alternative after
    #    every category cap. Alternatives are never summed.
    best: dict[str, object] | None = None
    for variant_mode, variant_stage in _special_variants(special_mode, special_stage):
        raw_variant = dict(raw)
        _apply_special(variant_mode, variant_stage, raw_variant)
        capped_variant = {cat: min(val, CATEGORY_CAPS[cat]) for cat, val in raw_variant.items()}
        final_variant = round(sum(capped_variant.values()), 2)
        candidate = {
            "raw": raw_variant,
            "capped": capped_variant,
            "final": final_variant,
            "selected_runes": selected_runes,
            "selected_support": selected_support,
        }
        if best is None or final_variant > best["final"]:
            best = candidate

    assert best is not None
    return best


def rate_items(
    items: set[str] | frozenset[str],
    *,
    health_stages: int = 0,
    armor_stages: int = 0,
    ammo_stages: int = 0,
    wup_count: int = 0,
    special_mode: str = "none",
    special_stage: int = 0,
) -> PlayerLoadoutCR:
    """Evaluate CR from a set of owned item names, optimizing rune slots.

    Rune selection: try all combinations of up to 3 owned normal runes
    and best-1 support rune.  Pick the combination with maximum final CR.
    Ties: lexicographically smallest rune tuple, then no support before
    named support.
    """
    owned = set(items)
    normal_owned = sorted(owned & NORMAL_RUNE_NAMES)
    support_owned = sorted(owned & SUPPORT_RUNE_NAMES)

    # Generate all candidate rune selections
    rune_combos = [
        combo
        for count in range(min(3, len(normal_owned)) + 1)
        for combo in combinations(normal_owned, count)
    ]
    support_candidates: list[str | None] = [None] + support_owned

    best = None
    for runes in rune_combos:
        for support in support_candidates:
            result = _evaluate_with_rune_selection(
                owned, runes, support,
                health_stages=health_stages,
                armor_stages=armor_stages,
                ammo_stages=ammo_stages,
                wup_count=wup_count,
                special_mode=special_mode,
                special_stage=special_stage,
            )
            if best is None or (
                -result["final"], result["selected_runes"],
                "" if result["selected_support"] is None else result["selected_support"]
            ) < (
                -best["final"], best["selected_runes"],
                "" if best["selected_support"] is None else best["selected_support"]
            ):
                best = result

    assert best is not None
    return PlayerLoadoutCR(
        total=best["final"],
        categories=best["capped"],
        raw_categories=best["raw"],
        selected_runes=best["selected_runes"],
        selected_support=best["selected_support"],
    )


# ═══════════════════════════════════════════════════════════════
# CollectionState evaluator
# ═══════════════════════════════════════════════════════════════

# Items that map to special_mode/stage logic, not to ITEM_CONTRIBUTIONS
_SPECIAL_ITEM_NAMES = frozenset({
    "The Crucible",
    "Sentinel Hammer",
    "Progressive Special Weapon",
    "Progressive Sentinel Hammer",
})

# All item names the CR engine recognizes
CR_RELEVANT_ITEMS: frozenset[str] = (
    WEAPON_NAMES
    | ALL_MOD_NAMES
    | ALL_MASTERY_NAMES
    | NORMAL_RUNE_NAMES
    | SUPPORT_RUNE_NAMES
    | frozenset(ITEM_CONTRIBUTIONS)  # includes equipment, suit perks
    | _SPECIAL_ITEM_NAMES
    | {"Faster Weapon Swap", "Progressive Health Upgrade",
       "Progressive Armor Upgrade", "Progressive Ammo Upgrade",
       "Weapon Upgrade Points (3)"}
)


def _resolve_special_from_state(
    state: "CollectionState",
    player: int,
    *,
    special_weapon_option: str,
    use_dlc: bool,
) -> tuple[str, int]:
    """Determine special_mode and special_stage from CollectionState.

    Args:
        special_weapon_option: One of "Progressive Special Weapon",
            "Progressive Sentinel Hammer", "The Crucible".
        use_dlc: Whether DLC content is enabled.

    Returns:
        (mode, stage) for ``rate_items``.
    """
    if not use_dlc:
        # Non-DLC: standalone Crucible
        count = state.count("The Crucible", player)
        return ("crucible", min(count, 1))

    if special_weapon_option == "Progressive Special Weapon":
        count = state.count("Progressive Special Weapon", player)
        return ("progressive_special", min(count, 3))
    elif special_weapon_option == "Progressive Sentinel Hammer":
        count = state.count("Progressive Sentinel Hammer", player)
        return ("progressive_hammer", min(count, 2))
    else:
        # Standalone Crucible even with DLC
        count = state.count("The Crucible", player)
        return ("crucible", min(count, 1))


def evaluate_player_loadout_cr(
    state: "CollectionState",
    player: int,
    world_context: Any = None,
    *,
    special_weapon_option: str | None = None,
    use_dlc: bool | None = None,
    randomize_chainsaw: bool | None = None,
    randomize_dash: bool | None = None,
) -> PlayerLoadoutCR:
    """Evaluate Player Loadout CR from an AP CollectionState.

    This is the primary production integration point for the APWorld (P7.4).
    It reads logical item ownership from the CollectionState and returns
    a PlayerLoadoutCR with total, categories, raw_categories, and selected rune identity.

    Args:
        state: AP CollectionState to evaluate.
        player: AP player number.
        world_context: Optional World or Options instance to auto-extract options.
        special_weapon_option: Override for configured special weapon mode.
        use_dlc: Override for whether DLC content is enabled.
        randomize_chainsaw: Override for whether Chainsaw is randomized.
        randomize_dash: Override for whether Dash is randomized.

    Returns:
        PlayerLoadoutCR dataclass supporting both attribute and dict-like access.
    """
    opts = getattr(world_context, "options", world_context)
    if special_weapon_option is None:
        if hasattr(opts, "special_weapon"):
            special_weapon_option = opts.special_weapon.current_option_name
        else:
            special_weapon_option = "Progressive Special Weapon"

    if use_dlc is None:
        if hasattr(opts, "use_dlc_content"):
            use_dlc = bool(opts.use_dlc_content.value)
        else:
            use_dlc = True

    if randomize_chainsaw is None:
        if hasattr(opts, "randomize_chainsaw"):
            randomize_chainsaw = bool(opts.randomize_chainsaw.value)
        else:
            randomize_chainsaw = False

    if randomize_dash is None:
        if hasattr(opts, "randomize_dash"):
            randomize_dash = bool(opts.randomize_dash.value)
        else:
            randomize_dash = False

    # Collect all CR-relevant items the player logically owns
    owned: set[str] = set()
    for name in CR_RELEVANT_ITEMS:
        if name in _SPECIAL_ITEM_NAMES:
            continue  # handled separately
        if name in ("Progressive Health Upgrade", "Progressive Armor Upgrade",
                     "Progressive Ammo Upgrade", "Weapon Upgrade Points (3)"):
            continue  # counted separately below
        if state.has(name, player):
            owned.add(name)

    # Dash availability via logic
    if dash_available(state, player, randomize_dash=randomize_dash):
        owned.add("Dash")

    # Chainsaw availability via logic
    if state.has("Chainsaw", player) or chainsaw_available(state, player, randomize_chainsaw=randomize_chainsaw):
        owned.add("Chainsaw")

    # Progressive capacities
    health_stages = state.count("Progressive Health Upgrade", player)
    armor_stages = state.count("Progressive Armor Upgrade", player)
    ammo_stages = state.count("Progressive Ammo Upgrade", player)

    # WUP count (each item = 3 points, but CR uses per-copy 0.25)
    wup_count = state.count("Weapon Upgrade Points (3)", player)

    # Special weapon
    special_mode, special_stage = _resolve_special_from_state(
        state, player,
        special_weapon_option=special_weapon_option,
        use_dlc=use_dlc,
    )

    return rate_items(
        owned,
        health_stages=min(health_stages, 4),
        armor_stages=min(armor_stages, 4),
        ammo_stages=min(ammo_stages, 4),
        wup_count=min(wup_count, 39),
        special_mode=special_mode,
        special_stage=special_stage,
    )


# Canonical API aliases
evaluate_player_cr = evaluate_player_loadout_cr
rate_collection_state = evaluate_player_loadout_cr

