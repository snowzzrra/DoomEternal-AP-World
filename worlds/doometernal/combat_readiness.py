"""
Implements the Combat Readiness solver model:
- Mission Base CR catalog (20 stages)
- Logic preparation allowances: Relaxed 15, Standard 12, Expert 6
- Severe Soft Penalties:
    - Missing effective Microwave Beam at mandatory Spirit breakpoint: +15
    - Missing effective Sentinel Hammer at The Dark Lord: +15
- Effective Mission CR: min(100, Base CR + Soft Penalty)
- Readiness Condition: CR allowance, mechanical traversal and endurance preparation

Pure deterministic evaluation for Archipelago logical reachability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .combat_rating import evaluate_player_loadout_cr, NORMAL_RUNE_NAMES
from .logic import dash_available, sentinel_hammer_available

if TYPE_CHECKING:
    from BaseClasses import CollectionState
MISSION_BASE_CR: dict[str, int] = {
    "e1m1_intro": 12,   # Hell on Earth
    "e1m2_war": 25,     # Exultia
    "e1m3_cult": 42,    # Cultist Base
    "e1m4_boss": 50,    # Doom Hunter Base
    "e2m1_nest": 58,    # Super Gore Nest
    "e2m2_base": 63,    # ARC Complex
    "e2m3_core": 66,    # Mars Core
    "e2m4_boss": 55,    # Sentinel Prime
    "e3m1_slayer": 72,  # Taras Nabad
    "e3m2_hell": 68,    # Nekravol
    "e3m2_hell_b": 74,  # Nekravol Part II
    "e3m3_maykr": 82,   # Urdak
    "e3m4_boss": 87,    # Final Sin
    "e4m1_rig": 83,     # UAC Atlantica Facility
    "e4m2_swamp": 88,   # The Blood Swamps
    "e4m3_mcity": 94,   # The Holt
    "e5m1_spear": 86,   # The World Spear: provisional endurance comparison with Atlantica (83) / Blood Swamps (88)
    "e5m2_earth": 77,   # Reclaimed Earth
    "e5m3_hell": 82,    # Immora
    "e5m4_boss": 80,    # The Dark Lord
}
SKILL_ALLOWANCES: dict[int, int] = {
    0: 15,  # Relaxed
    1: 12,  # Standard
    2: 6,   # Expert
}
SPIRIT_PENALTY: int = 15
DARK_LORD_HAMMER_PENALTY: int = 15
MAX_EFFECTIVE_CR: int = 100

# Vanilla tiers anchor each seed's presentation independently of the player's inventory.
MISSION_SKULL_TIERS = {
    "e1m1_intro": 1, "e1m2_war": 1, "e1m3_cult": 2, "e1m4_boss": 2,
    "e2m1_nest": 2, "e2m2_base": 2, "e2m3_core": 2, "e2m4_boss": 2,
    "e3m1_slayer": 3, "e3m2_hell": 3, "e3m2_hell_b": 3, "e3m3_maykr": 3,
    "e3m4_boss": 4, "e4m1_rig": 4, "e4m2_swamp": 4, "e4m3_mcity": 4,
    "e5m1_spear": 4, "e5m2_earth": 3, "e5m3_hell": 3, "e5m4_boss": 3,
}
TRAVERSAL_DASH_STAGES = frozenset({
    "e3m3_maykr", "e4m1_rig", "e4m2_swamp", "e4m3_mcity",
    "e5m1_spear", "e5m2_earth", "e5m3_hell",
})
HOOK_TRAVERSAL_STAGES = frozenset({"e5m1_spear", "e5m2_earth", "e5m3_hell"})
ENDURANCE_STAGES = TRAVERSAL_DASH_STAGES | {"e3m1_slayer"}

# ── Breakpoint Topology Mapping ────────────────────────────────
# Region connection (source, destination) -> canonical stage ID
SPIRIT_BREAKPOINTS: dict[tuple[str, str], str] = {
    ("The Blood Swamps - Underworld Crossroad", "The Blood Swamps - Sunken Courtyard"): "e4m2_swamp",
    ("The Holt - Tranquility", "The Holt - Crimson Forest"): "e4m3_mcity",
    ("The World Spear - Sentinel Mountain - Mountain Ruins", "The World Spear - Sentinel Mountain - Nether Lake"): "e5m1_spear",
    ("Reclaimed Earth - Lockdown", "Reclaimed Earth - Gate of Divum"): "e5m2_earth",
    ("Immora - Immora Assault - Walls of Immora", "Immora - Immora Assault - Breach"): "e5m3_hell",
}

DARK_LORD_LOCATION: str = "The Dark Lord - Defeated"
DARK_LORD_STAGE_ID: str = "e5m4_boss"


@dataclass(frozen=True)
class ReadinessResult:
    """Diagnostic result for readiness evaluation."""
    stage_id: str
    player_cr: float
    mission_base_cr: int
    soft_penalty: int
    effective_cr: int
    allowance: int
    deficit: float
    ready: bool
    context: str = "base"
    reason: str = ""
    preparation_deficit: float = 0.0
    missing_requirements: tuple[str, ...] = ()

    @property
    def is_ready(self) -> bool:
        return self.ready


def get_mission_base_cr(stage_id: str, world: Any | None = None) -> int:
    """Apply the frozen change in combat cost to the mission's preparation rating."""
    if stage_id not in MISSION_BASE_CR:
        raise KeyError(f"Unknown stage ID for Base CR: {stage_id}")
    base = MISSION_BASE_CR[stage_id]
    costs = (getattr(world, "enemy_plan", None) or {}).get("combat_costs", {}).get(stage_id)
    if costs is None:
        return base
    import math
    profile = costs.get('campaign')
    if profile is not None:
        if (getattr(world, 'enemy_plan', None) or {}).get('revision', 0) >= 5 and profile.get('waves'):
            return get_mission_cr_range(stage_id, world)[1]
        bodies = max(1, profile['bodies'])
        pressure = (8 + 8 * math.log2(1 + profile['actual'] / bodies)
                    + 4 * math.log2(1 + profile['wave_p90'] / 10)
                    + 3 * math.log2(1 + profile['bodies'] / 100))
        floor = base if stage_id in {'e1m4_boss', 'e2m4_boss', 'e3m3_maykr', 'e3m4_boss', 'e4m3_mcity', 'e5m4_boss'} else 1
        return max(floor, min(MAX_EFFECTIVE_CR, round(pressure)))
    # Ten cost units per reference CR; doubling that budget adds twelve CR.
    factor = max(.25, 1 + (costs["actual"] - costs["original"]) / (10 * base))
    floor = base if stage_id in {"e1m4_boss", "e2m2_base", "e2m4_boss",
                                "e3m3_maykr", "e3m4_boss", "e4m3_mcity", "e5m4_boss"} else 1
    return max(floor, min(MAX_EFFECTIVE_CR, round(base + 12 * math.log2(factor))))


def get_mission_cr_range(stage_id, world):
    import math
    profile = (getattr(world, 'enemy_plan', None) or {}).get('combat_costs', {}).get(stage_id, {}).get('campaign', {})
    if not profile.get('waves'):
        value = get_mission_base_cr(stage_id, world)
        return value, value
    floor = MISSION_BASE_CR[stage_id] if stage_id in {'e1m4_boss', 'e2m4_boss', 'e3m3_maykr', 'e3m4_boss', 'e4m3_mcity', 'e5m4_boss'} else 1
    endurance = 3 * math.log2(1 + profile['bodies'] / 100)
    ratings = [max(floor, min(MAX_EFFECTIVE_CR, round(8 + endurance
        + 8 * math.log2(1 + wave['cost'] / max(1, wave['bodies']))
        + 4 * math.log2(1 + wave['cost'] / 10)))) for wave in profile['waves'] if wave['bodies']]
    return (min(ratings), max(ratings)) if ratings else (floor, floor)


def get_mission_effort_per_check(stage_id, world):
    profile = (getattr(world, 'enemy_plan', None) or {}).get('combat_costs', {}).get(stage_id, {}).get('campaign', {})
    if 'effort' not in profile:
        return 0.0
    from .generated_content import CAMPAIGN_STAGES, LOCATION_ROWS
    from .locations import optional_location_enabled
    regions = next(set(stage['regions']) for stage in CAMPAIGN_STAGES if stage['id'] == stage_id)
    options = getattr(world, 'options', None)
    checks = sum(code is not None and region in regions and (options is None or optional_location_enabled(name, options))
                 for name, code, region in LOCATION_ROWS)
    duration_weight = 1.5 if stage_id in {'e5m1_spear', 'e5m2_earth', 'e5m3_hell'} else 1.25 if stage_id.startswith('e4m') else 1
    return profile['effort'] * duration_weight / max(1, checks)


def get_mission_skull_tier(stage_id: str, world: Any | None = None) -> int:
    if (getattr(world, 'enemy_plan', None) or {}).get('revision', 0) >= 3:
        rating = get_mission_intrinsic_cr(stage_id, world)
        return 1 + sum(rating >= threshold for threshold in (35, 55, 75))
    change = get_mission_base_cr(stage_id, world) - MISSION_BASE_CR[stage_id]
    return max(1, min(4, MISSION_SKULL_TIERS[stage_id] + round(change / 15)))


def _enemy_counter_penalties(state, player, stage_id, world):
    from .logic import COMBAT_CAPABILITIES
    profile = (getattr(world, 'enemy_plan', None) or {}).get('combat_costs', {}).get(stage_id, {}).get('campaign', {})
    present = set(profile.get('species', ()))
    counters = (("spirit", 15, (("Plasma Rifle", "Microwave Beam"),)),
                ("blood_angel", 8, COMBAT_CAPABILITIES['weak_point']),
                ("stone_imp", 6, (("Combat Shotgun", "Full Auto"),)))
    return {species: penalty for species, penalty, alternatives in counters if species in present and not (
        state is not None and any(all(state.has(item, player) for item in alternative) for alternative in alternatives))}


def get_mission_intrinsic_cr(stage_id, world):
    return min(MAX_EFFECTIVE_CR, get_mission_base_cr(stage_id, world) + sum(_enemy_counter_penalties(None, 1, stage_id, world).values()))


def get_skill_allowance(logic_difficulty: int) -> int:
    """Return the preparation allowance for a LogicDifficulty value."""
    if logic_difficulty not in SKILL_ALLOWANCES:
        raise ValueError(
            f"Unsupported logic difficulty: {logic_difficulty}. "
            "Supported: 0 (Relaxed), 1 (Standard), 2 (Expert)"
        )
    return SKILL_ALLOWANCES[logic_difficulty]


def has_effective_anti_spirit(state: CollectionState, player: int) -> bool:
    """Check whether player possesses an effective anti-spirit capability (Plasma Rifle + Microwave Beam)."""
    return state.has("Plasma Rifle", player) and state.has("Microwave Beam", player)


def has_effective_sentinel_hammer(
    state: CollectionState,
    player: int,
    special_weapon: str = "Progressive Special Weapon",
) -> bool:
    """Check whether player possesses Sentinel Hammer capability."""
    return sentinel_hammer_available(state, player, special_weapon=special_weapon)


def _resolve_readiness_options(
    world: Any | None = None,
    logic_difficulty: int | None = None,
    special_weapon: str | None = None,
) -> tuple[int, str]:
    """Resolve logic difficulty and special weapon configuration."""
    if logic_difficulty is None:
        if world is not None and hasattr(world, "options") and hasattr(world.options, "logic_difficulty"):
            logic_difficulty = int(world.options.logic_difficulty.value)
        else:
            logic_difficulty = 1
    if special_weapon is None:
        if world is not None and hasattr(world, "options") and hasattr(world.options, "special_weapon"):
            opt = world.options.special_weapon
            if hasattr(opt, "current_option_name") and isinstance(opt.current_option_name, str):
                special_weapon = opt.current_option_name
            elif hasattr(opt, "value"):
                from .options import SpecialWeapon
                special_weapon = SpecialWeapon.labels.get(opt.value, "Progressive Special Weapon")
            else:
                special_weapon = "Progressive Special Weapon"
        else:
            special_weapon = "Progressive Special Weapon"
    return logic_difficulty, special_weapon


def evaluate_mission_readiness(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    logic_difficulty: int | None = None,
    special_weapon: str | None = None,
    context: str = "base",
    player_cr: float | None = None,
) -> ReadinessResult:
    """Evaluate readiness of a player for a given mission and context.

    ``player_cr`` may be supplied when the caller already evaluated the same
    state; it must be the exact ``evaluate_player_loadout_cr`` total.
    """
    diff, sw = _resolve_readiness_options(world, logic_difficulty, special_weapon)
    allowance = get_skill_allowance(diff)
    if stage_id == DARK_LORD_STAGE_ID and context == "base":
        context = "darklord"
    base_cr = get_mission_base_cr(stage_id, world)
    if player_cr is None:
        cr_result = evaluate_player_loadout_cr(state, player, world)
        player_cr = float(cr_result.total)
    else:
        player_cr = float(player_cr)

    penalties = _enemy_counter_penalties(state, player, stage_id, world)
    reason = ""
    if context == "spirit_breakpoint":
        enemy_plan = getattr(world, 'enemy_plan', None) or {}
        generated_species = enemy_plan.get('combat_costs', {}).get(stage_id, {}).get('campaign', {}).get('species', ())
        spirit_present = enemy_plan.get('revision', 0) < 4 or 'spirit' in generated_species
        if spirit_present and not has_effective_anti_spirit(state, player):
            penalties['spirit'] = SPIRIT_PENALTY
            reason = "Missing effective Microwave Beam at mandatory Spirit breakpoint (+15 CR)"
    elif context == "dark_lord_defeated" or (stage_id == DARK_LORD_STAGE_ID and context == "boss"):
        if not has_effective_sentinel_hammer(state, player, special_weapon=sw):
            penalties['dark_lord'] = DARK_LORD_HAMMER_PENALTY
            reason = "Missing effective Sentinel Hammer against The Dark Lord (+15 CR)"

    soft_penalty = sum(penalties.values())
    if soft_penalty and not reason:
        reason = f"Missing enemy counter preparation (+{soft_penalty} CR)"
    effective_cr = min(MAX_EFFECTIVE_CR, base_cr + soft_penalty)
    deficit = round(effective_cr - player_cr, 2)
    missing = []
    options = getattr(world, "options", None)
    randomize_dash = bool(getattr(getattr(options, "randomize_dash", None), "value", 0))
    if stage_id in TRAVERSAL_DASH_STAGES and not dash_available(state, player, randomize_dash=randomize_dash):
        missing.append("Dash")
    if stage_id in HOOK_TRAVERSAL_STAGES:
        missing.extend(name for name in ("Super Shotgun", "Meat Hook") if not state.has(name, player))
    enemy_plan = getattr(world, "enemy_plan", None) or {}
    has_supply = any(operation.get("reserve") for operation in
                     enemy_plan.get("maps", {}).get(stage_id, {}).get("operations", []))
    from .native_enemy_plan import AMMO_FODDER
    has_supply = has_supply or any(recipe.get('renewable') and
        any(body['species'] in AMMO_FODDER for body in recipe['bodies'])
        for recipe in enemy_plan.get('maps', {}).get(stage_id, {}).get('recipes', []))
    randomize_chainsaw = bool(getattr(getattr(options, "randomize_chainsaw", None), "value", 0))
    # The fixed Chainsaw pickup precedes the profiled Hell on Earth fights.
    if has_supply and randomize_chainsaw:
        from .logic import chainsaw_available
        if not chainsaw_available(state, player, randomize_chainsaw=True):
            missing.append("Chainsaw for ammunition supply")
    if stage_id in HOOK_TRAVERSAL_STAGES:
        from .logic import ammo_resource_producer
        if not ammo_resource_producer(state, player,
                randomize_chainsaw=bool(getattr(getattr(options, "randomize_chainsaw", None), "value", 0)), special_weapon=sw):
            missing.append("Ammo resource producer")
    preparation_deficit = float(len(missing))
    if stage_id in ENDURANCE_STAGES:
        # shortcut: capacity floors need comparative gameplay calibration.
        capacities = ("Progressive Health Upgrade", "Progressive Armor Upgrade", "Progressive Ammo Upgrade")
        preparation_deficit += sum(not state.has(name, player) for name in capacities)
        preparation_deficit += not any(state.has(name, player) for name in NORMAL_RUNE_NAMES)
        categories = evaluate_player_loadout_cr(state, player, world).categories
        preparation_deficit += sum(max(0.0, floor - categories[category]) for category, floor in
                                   (("Mobility", 4.0), ("Defense", 6.0), ("Sustain", 9.0)))
    ready = deficit <= allowance and preparation_deficit <= 0

    return ReadinessResult(
        stage_id=stage_id,
        player_cr=player_cr,
        mission_base_cr=base_cr,
        soft_penalty=soft_penalty,
        effective_cr=effective_cr,
        allowance=allowance,
        deficit=deficit,
        ready=ready,
        context=context,
        reason=reason,
        preparation_deficit=preparation_deficit,
        missing_requirements=tuple(missing),
    )


def is_mission_ready(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    logic_difficulty: int | None = None,
    special_weapon: str | None = None,
    context: str = "base",
) -> bool:
    """Return whether player is logically combat-ready for a mission."""
    return evaluate_mission_readiness(
        state,
        player,
        stage_id,
        world,
        logic_difficulty=logic_difficulty,
        special_weapon=special_weapon,
        context=context,
    ).ready


def is_spirit_breakpoint_ready(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    logic_difficulty: int | None = None,
) -> bool:
    """Return whether player is logically combat-ready to cross a mandatory Spirit breakpoint."""
    return evaluate_mission_readiness(
        state, player, stage_id, world,
        logic_difficulty=logic_difficulty, context="spirit_breakpoint",
    ).ready


def is_dark_lord_defeated_ready(
    state: CollectionState,
    player: int,
    world: Any | None = None,
    *,
    logic_difficulty: int | None = None,
    special_weapon: str | None = None,
) -> bool:
    """Return whether player is logically combat-ready to defeat The Dark Lord."""
    return evaluate_mission_readiness(
        state, player, DARK_LORD_STAGE_ID, world,
        logic_difficulty=logic_difficulty, special_weapon=special_weapon, context="dark_lord_defeated",
    ).ready
