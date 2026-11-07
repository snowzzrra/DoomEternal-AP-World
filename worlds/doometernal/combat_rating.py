"""Player Loadout Combat Rating.

Evaluates CR from logical item ownership in a CollectionState,
**not** from live game state.  No solver, no difficulty gating,
no fill changes.  Pure read-only query.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Any

from .logic import chainsaw_available, dash_available

if TYPE_CHECKING:
    from BaseClasses import CollectionState

CATEGORY_CAPS: dict[str, float] = {
    "Arsenal": 35.0,
    "Enhancements": 10.0,
    "Sustain": 20.0,
    "Defense": 15.0,
    "Mobility": 10.0,
    "Control / Utility": 10.0,
}

AMMUNITION_BY_WEAPON = {
    "Combat Shotgun": "shells",
    "Super Shotgun": "shells",
    "Heavy Cannon": "bullets",
    "Chaingun": "bullets",
    "Plasma Rifle": "cells",
    "Ballista": "cells",
    "Rocket Launcher": "rockets",
}

WEAPON_BASE: dict[str, float] = {
    "Ballista": 8.0,
    "Super Shotgun": 10.0,
    "Rocket Launcher": 10.0,
    "Heavy Cannon": 8.0,
    "Plasma Rifle": 7.0,
    "Combat Shotgun": 6.0,
    "Chaingun": 4.0,
}
WEAPON_NAMES = frozenset(WEAPON_BASE)


WEAPON_MULTIPLIERS = (1.00, 0.95, 0.85, 0.70, 0.55, 0.40, 0.30)

BREADTH_BONUS = (0.0, 0.0, 2.0, 5.0, 8.0, 10.0, 11.0, 12.0)

MOD_HOST: dict[str, str] = {
    "Sticky Bombs": "Combat Shotgun",
    "Full Auto": "Combat Shotgun",
    "Precision Bolt": "Heavy Cannon",
    "Micro Missiles": "Heavy Cannon",
    "Heat Blast": "Plasma Rifle",
    "Microwave Beam": "Plasma Rifle",
    "Remote Detonate": "Rocket Launcher",
    "Lock-on Burst": "Rocket Launcher",
    "Arbalest": "Ballista",
    "Destroyer Blade": "Ballista",
    "Energy Shield": "Chaingun",
    "Mobile Turret": "Chaingun",
}
ALL_MOD_NAMES = frozenset(MOD_HOST)

MASTERY_HOST: dict[str, tuple[str, ...]] = {
    "Sticky Bombs Mastery": ("Combat Shotgun", "Sticky Bombs"),
    "Full Auto Mastery": ("Combat Shotgun", "Full Auto"),
    "Precision Bolt Mastery": ("Heavy Cannon", "Precision Bolt"),
    "Micro Missiles Mastery": ("Heavy Cannon", "Micro Missiles"),
    "Heat Blast Mastery": ("Plasma Rifle", "Heat Blast"),
    "Microwave Beam Mastery": ("Plasma Rifle", "Microwave Beam"),
    "Remote Detonate Mastery": ("Rocket Launcher", "Remote Detonate"),
    "Lock-on Burst Mastery": ("Rocket Launcher", "Lock-on Burst"),
    "Arbalest Mastery": ("Ballista", "Arbalest"),
    "Destroyer Blade Mastery": ("Ballista", "Destroyer Blade"),
    "Energy Shield Mastery": ("Chaingun", "Energy Shield"),
    "Mobile Turret Mastery": ("Chaingun", "Mobile Turret"),
    "Meat Hook Mastery": ("Super Shotgun", "Meat Hook"),
}
ALL_MASTERY_NAMES = frozenset(MASTERY_HOST)

_Contrib = tuple[str, float, tuple[str, ...]]


def _flat(*pairs: tuple[str, float], deps: tuple[str, ...] = ()) -> list[_Contrib]:
    return [(cat, val, deps) for cat, val in pairs]


def _mod_contribs(host: str, enhancement: float, control: float = 0.0) -> list[_Contrib]:
    deps = (host,)
    result = [("Enhancements", enhancement, deps)]
    if control:
        result.append(("Control / Utility", control, deps))
    return result


def _mastery_contribs(
    deps: tuple[str, ...], enhancement: float = 0, control: float = 0, defense: float = 0, sustain: float = 0
) -> list[_Contrib]:
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
    "Chainsaw": _flat(("Sustain", 7), ("Control / Utility", 1)),
    "Flame Belch": _flat(("Sustain", 7), ("Control / Utility", 1)),
    "Ice Bomb": _flat(("Defense", 3), ("Control / Utility", 4)),
    "Frag Grenade": _flat(("Enhancements", 2), ("Control / Utility", 2)),
    "Blood Punch": _flat(("Enhancements", 2), ("Control / Utility", 1)),
    "Dash": _flat(("Mobility", 4), ("Defense", 2)),
    "Ammo Refill": [],
    "Faster Ledge Grab": _flat(("Mobility", 1)),
    "Reduced Hazard Damage": _flat(("Defense", 1)),
    "Reduced Self Damage": _flat(("Defense", 1)),
    "Respawning Barrels": _flat(("Sustain", 1)),
    "Ammo from Barrels": _flat(("Sustain", 2)),
    "Powerup Extender": _flat(("Defense", 1)),
    "Faster Dash Recharge": _flat(("Mobility", 2.5), ("Defense", 0.5), deps=("Dash",)),
    "Dash Refill on Glory Kill": _flat(("Mobility", 1), deps=("Dash",)),
    "Frag Grenade Cooldown": _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Frag Grenade Concussive Blast": _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Frag Grenade Cluster Bombs": _flat(("Enhancements", 1), deps=("Frag Grenade",)),
    "Second Frag Grenade": _flat(("Control / Utility", 1), deps=("Frag Grenade",)),
    "Ice Bomb Cooldown": _flat(("Control / Utility", 1), deps=("Ice Bomb",)),
    "Extended Ice Bomb Duration": _flat(("Control / Utility", 1), deps=("Ice Bomb",)),
    "Health from Frozen Demons": _flat(("Sustain", 1), deps=("Ice Bomb",)),
    "Frozen Melee Shatter": _flat(("Control / Utility", 1), deps=("Ice Bomb",)),
    "Sticky Bombs": _mod_contribs("Combat Shotgun", 4, 2),
    "Full Auto": _mod_contribs("Combat Shotgun", 2, 1),
    "Precision Bolt": _mod_contribs("Heavy Cannon", 6, 1),
    "Micro Missiles": _mod_contribs("Heavy Cannon", 2, 1),
    "Heat Blast": _mod_contribs("Plasma Rifle", 2, 1),
    "Microwave Beam": _mod_contribs("Plasma Rifle", 1, 2),
    "Remote Detonate": _mod_contribs("Rocket Launcher", 2, 1),
    "Lock-on Burst": _mod_contribs("Rocket Launcher", 6, 1),
    "Arbalest": _mod_contribs("Ballista", 3, 1),
    "Destroyer Blade": _mod_contribs("Ballista", 5, 2),
    "Energy Shield": [
        ("Enhancements", 1, ("Chaingun",)),
        ("Defense", 7, ("Chaingun",)),
        ("Control / Utility", 2, ("Chaingun",)),
    ],
    "Mobile Turret": _mod_contribs("Chaingun", 2, 1),
    "Sticky Bombs Mastery": _mastery_contribs(("Combat Shotgun", "Sticky Bombs"), enhancement=1),
    "Full Auto Mastery": _mastery_contribs(("Combat Shotgun", "Full Auto"), enhancement=1),
    "Precision Bolt Mastery": _mastery_contribs(("Heavy Cannon", "Precision Bolt"), enhancement=2),
    "Micro Missiles Mastery": _mastery_contribs(("Heavy Cannon", "Micro Missiles"), enhancement=1),
    "Heat Blast Mastery": _mastery_contribs(("Plasma Rifle", "Heat Blast"), enhancement=1),
    "Microwave Beam Mastery": _mastery_contribs(("Plasma Rifle", "Microwave Beam"), control=1),
    "Remote Detonate Mastery": _mastery_contribs(("Rocket Launcher", "Remote Detonate"), enhancement=1),
    "Lock-on Burst Mastery": _mastery_contribs(("Rocket Launcher", "Lock-on Burst"), enhancement=2),
    "Arbalest Mastery": _mastery_contribs(("Ballista", "Arbalest"), enhancement=1),
    "Destroyer Blade Mastery": _mastery_contribs(("Ballista", "Destroyer Blade"), enhancement=2),
    "Energy Shield Mastery": _mastery_contribs(("Chaingun", "Energy Shield"), defense=1),
    "Mobile Turret Mastery": _mastery_contribs(("Chaingun", "Mobile Turret"), enhancement=1),
    "Meat Hook Mastery": _mastery_contribs(("Super Shotgun", "Meat Hook"), sustain=7),
    "Meat Hook": [],
    "Savagery": [],
    "Chrono Strike": [],
}

NORMAL_RUNE_CONTRIBS: dict[str, list[_Contrib]] = {
    "Savagery": [],
    "Seek and Destroy": _flat(("Enhancements", 1), ("Control / Utility", 2)),
    "Blood Fueled": _flat(("Mobility", 3)),
    "Air Control": _flat(("Mobility", 6)),
    "Dazed and Confused": _flat(("Control / Utility", 2)),
    "Saving Throw": _flat(("Defense", 5)),
    "Chrono Strike": [],
    "Equipment Fiend": _flat(("Sustain", 4), ("Control / Utility", 2)),
    "Punch and Reave": _flat(("Sustain", 3), ("Control / Utility", 1)),
}
NORMAL_RUNE_NAMES = frozenset(NORMAL_RUNE_CONTRIBS)

SUPPORT_RUNE_CONTRIBS: dict[str, list[_Contrib]] = {
    "Break Blast": _flat(("Enhancements", 1), ("Control / Utility", 1)),
    "Desperate Punch": _flat(("Enhancements", 1), ("Control / Utility", 1)),
    "Take Back": _flat(("Defense", 1), ("Control / Utility", 1)),
}
SUPPORT_RUNE_NAMES = frozenset(SUPPORT_RUNE_CONTRIBS)


HEALTH_CR_PER_STAGE = 3.50
ARMOR_CR_PER_STAGE = 3.00
AMMO_CR_PER_STAGE = 3.50


WUP_ENHANCEMENT_PER_COPY = 0.25
WUP_ENHANCEMENT_CAP = 4.0


FASTER_WEAPON_SWAP_RATIO = 0.25
FASTER_WEAPON_SWAP_CAP = 8.0


def _normal_arsenal(weapons: tuple[str, ...]) -> float:
    """Diminishing-return Arsenal from sorted weapon list."""
    total = sum(WEAPON_BASE[w] * WEAPON_MULTIPLIERS[i] for i, w in enumerate(weapons[: len(WEAPON_MULTIPLIERS)]))
    families = {AMMUNITION_BY_WEAPON[weapon] for weapon in weapons}
    total += BREADTH_BONUS[min(len(families), len(BREADTH_BONUS) - 1)]
    return total


def _special_variants(mode: str, stage: int) -> tuple[tuple[str, int], ...]:
    """Evaluate the equipped Crucible and Hammer as separate alternatives."""
    if mode == "none" or stage <= 0:
        return (("none", 0),)
    if mode == "progressive_special" and stage >= 2:
        return (("progressive_special", stage), ("crucible", 1))
    return ((mode, stage),)


def _apply_special(mode: str, stage: int, raw: dict[str, float]) -> None:
    if (mode == "crucible" and stage >= 1) or (mode == "progressive_special" and stage == 1):
        raw["Arsenal"] += 9
        raw["Control / Utility"] += 1
    elif mode == "progressive_special" and stage >= 2:
        _apply_hammer(raw, stage >= 3)
    elif mode == "progressive_hammer" and stage >= 1:
        _apply_hammer(raw, stage >= 2)


def _apply_hammer(raw, upgraded):
    raw["Arsenal"] += 7
    raw["Sustain"] += 7
    raw["Defense"] += 2
    raw["Control / Utility"] += 6
    if upgraded:
        raw["Arsenal"] += 2


@dataclass(frozen=True)
class PlayerLoadoutCR:
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

    weapons = tuple(
        sorted(
            (n for n in owned if n in WEAPON_BASE),
            key=lambda n: WEAPON_BASE[n],
            reverse=True,
        )
    )
    normal_arsenal = _normal_arsenal(weapons)
    raw["Arsenal"] += normal_arsenal

    if "Ballista" in weapons:
        raw["Mobility"] += 1.5

    if "Super Shotgun" in weapons and "Meat Hook" in owned:
        raw["Mobility"] += 2

    raw["Defense"] += health_stages * HEALTH_CR_PER_STAGE
    raw["Defense"] += armor_stages * ARMOR_CR_PER_STAGE
    raw["Sustain"] += ammo_stages * AMMO_CR_PER_STAGE

    raw["Enhancements"] += min(WUP_ENHANCEMENT_CAP, max(0, wup_count) * WUP_ENHANCEMENT_PER_COPY)

    _apply_item_contributions(raw, owned)

    _apply_rune_contributions(raw, owned, selected_runes, selected_support)
    if "Faster Weapon Swap" in owned and weapons:
        effective_arsenal = min(normal_arsenal, CATEGORY_CAPS["Arsenal"])
        bonus = min(FASTER_WEAPON_SWAP_CAP, FASTER_WEAPON_SWAP_RATIO * effective_arsenal)
        raw["Enhancements"] += bonus

    return _best_special_loadout(raw, special_mode, special_stage, selected_runes, selected_support)


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
    """Maximize CR; break ties by rune names, then prefer no support rune."""
    owned = set(items)
    normal_owned = sorted(owned & NORMAL_RUNE_NAMES)
    support_owned = sorted(owned & SUPPORT_RUNE_NAMES)

    rune_combos = [
        combo for count in range(min(3, len(normal_owned)) + 1) for combo in combinations(normal_owned, count)
    ]
    support_candidates: list[str | None] = [None, *support_owned]

    best = None
    for runes in rune_combos:
        for support in support_candidates:
            result = _evaluate_with_rune_selection(
                owned,
                runes,
                support,
                health_stages=health_stages,
                armor_stages=armor_stages,
                ammo_stages=ammo_stages,
                wup_count=wup_count,
                special_mode=special_mode,
                special_stage=special_stage,
            )
            if best is None or (
                -result["final"],
                result["selected_runes"],
                "" if result["selected_support"] is None else result["selected_support"],
            ) < (
                -best["final"],
                best["selected_runes"],
                "" if best["selected_support"] is None else best["selected_support"],
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


_SPECIAL_ITEM_NAMES = frozenset(
    {
        "The Crucible",
        "Sentinel Hammer",
        "Progressive Special Weapon",
        "Progressive Sentinel Hammer",
    }
)


CR_RELEVANT_ITEMS: frozenset[str] = (
    WEAPON_NAMES
    | ALL_MOD_NAMES
    | ALL_MASTERY_NAMES
    | NORMAL_RUNE_NAMES
    | SUPPORT_RUNE_NAMES
    | frozenset(ITEM_CONTRIBUTIONS)
    | _SPECIAL_ITEM_NAMES
    | {
        "Faster Weapon Swap",
        "Progressive Health Upgrade",
        "Progressive Armor Upgrade",
        "Progressive Ammo Upgrade",
        "Weapon Upgrade Points (3)",
    }
)


def _resolve_special_from_state(
    state: CollectionState,
    player: int,
    *,
    special_weapon_option: str,
    use_dlc: bool,
) -> tuple[str, int]:
    if not use_dlc:
        count = state.count("The Crucible", player)
        return ("crucible", min(count, 1))

    if special_weapon_option == "Progressive Special Weapon":
        count = state.count("Progressive Special Weapon", player)
        return ("progressive_special", min(count, 3))
    if special_weapon_option == "Progressive Sentinel Hammer":
        count = state.count("Progressive Sentinel Hammer", player)
        return ("progressive_hammer", min(count, 2))

    count = state.count("The Crucible", player)
    return ("crucible", min(count, 1))


def evaluate_player_loadout_cr(
    state: CollectionState,
    player: int,
    world_context: Any = None,
    *,
    special_weapon_option: str | None = None,
    use_dlc: bool | None = None,
    randomize_chainsaw: bool | None = None,
    randomize_dash: bool | None = None,
    native_chainsaw: bool = False,
) -> PlayerLoadoutCR:
    """Read logical ownership and resolve option overrides before rating the loadout."""
    special_weapon_option, use_dlc, randomize_chainsaw, randomize_dash = _resolve_loadout_options(
        world_context, special_weapon_option, use_dlc, randomize_chainsaw, randomize_dash
    )

    owned = _owned_combat_items(state, player, randomize_dash, randomize_chainsaw, native_chainsaw)

    health_stages = state.count("Progressive Health Upgrade", player)
    armor_stages = state.count("Progressive Armor Upgrade", player)
    ammo_stages = state.count("Progressive Ammo Upgrade", player)

    wup_count = state.count("Weapon Upgrade Points (3)", player)

    special_mode, special_stage = _resolve_special_from_state(
        state,
        player,
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


evaluate_player_cr = evaluate_player_loadout_cr
rate_collection_state = evaluate_player_loadout_cr


def _apply_item_contributions(raw, owned):
    for name in owned:
        if name in NORMAL_RUNE_NAMES or name in SUPPORT_RUNE_NAMES:
            continue
        _apply_contributions(raw, owned, ITEM_CONTRIBUTIONS.get(name, []))


def _apply_rune_contributions(raw, owned, selected_runes, selected_support):
    for name in selected_runes:
        if name == "Equipment Fiend" and not owned.intersection({"Flame Belch", "Ice Bomb", "Frag Grenade"}):
            continue
        if name == "Punch and Reave" and "Blood Punch" not in owned:
            continue
        _apply_contributions(raw, owned, NORMAL_RUNE_CONTRIBS[name])

    _apply_support_contribution(raw, owned, selected_support)


def _best_special_loadout(raw, special_mode, special_stage, selected_runes, selected_support):
    best: dict[str, object] | None = None
    for variant_mode, variant_stage in _special_variants(special_mode, special_stage):
        raw_variant = dict(raw)
        _apply_special(variant_mode, variant_stage, raw_variant)
        capped_variant = {cat: min(val, CATEGORY_CAPS[cat]) for cat, val in raw_variant.items()}
        capped_variant["Arsenal"] = min(
            capped_variant["Arsenal"], 10 + capped_variant["Defense"] + min(10, capped_variant["Sustain"])
        )
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


def _resolve_loadout_options(world_context, special_weapon_option, use_dlc, randomize_chainsaw, randomize_dash):
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

    randomize_chainsaw, randomize_dash = _resolve_randomized_capabilities(opts, randomize_chainsaw, randomize_dash)
    return special_weapon_option, use_dlc, randomize_chainsaw, randomize_dash


def _owned_combat_items(state, player, randomize_dash, randomize_chainsaw, native_chainsaw):
    owned: set[str] = set()
    for name in CR_RELEVANT_ITEMS:
        if name in _SPECIAL_ITEM_NAMES:
            continue
        if name in (
            "Progressive Health Upgrade",
            "Progressive Armor Upgrade",
            "Progressive Ammo Upgrade",
            "Weapon Upgrade Points (3)",
        ):
            continue
        if state.has(name, player):
            owned.add(name)

    if dash_available(state, player, randomize_dash=randomize_dash):
        owned.add("Dash")

    if (
        native_chainsaw
        or state.has("Chainsaw", player)
        or chainsaw_available(state, player, randomize_chainsaw=randomize_chainsaw)
    ):
        owned.add("Chainsaw")
    return owned


def _apply_support_contribution(raw, owned, selected_support):
    if selected_support is not None:
        _apply_contributions(raw, owned, SUPPORT_RUNE_CONTRIBS[selected_support])


def _resolve_randomized_capabilities(opts, randomize_chainsaw, randomize_dash):
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
    return randomize_chainsaw, randomize_dash


def _apply_contributions(raw, owned, contributions):
    for category, value, dependencies in contributions:
        if all(dependency in owned for dependency in dependencies):
            raw[category] += value
