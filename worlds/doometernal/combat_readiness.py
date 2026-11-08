"""Mission combat ratings, preparation requirements and readiness."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .combat_rating import NORMAL_RUNE_NAMES, evaluate_player_loadout_cr
from .generated_content import MASTER_LEVEL_COMBAT_PROFILES
from .logic import dash_available, sentinel_hammer_available
from .planner import ITEM_DEPENDENCIES, STAGE_BY_ID, FastState
from .player_strings_generated import text as player_text

if TYPE_CHECKING:
    from BaseClasses import CollectionState
READINESS_PLACEMENT_SLACK: float = 6.0


MISSION_BASE_CR: dict[str, int] = {
    "e1m1_intro": 12,
    "e1m2_war": 25,
    "e1m3_cult": 42,
    "e1m4_boss": 50,
    "e2m1_nest": 58,
    "e2m2_base": 63,
    "e2m3_core": 66,
    "e2m4_boss": 55,
    "e3m1_slayer": 72,
    "e3m2_hell": 68,
    "e3m2_hell_b": 74,
    "e3m3_maykr": 82,
    "e3m4_boss": 87,
    "e4m1_rig": 83,
    "e4m2_swamp": 88,
    "e4m3_mcity": 94,
    "e5m1_spear": 86,
    "e5m2_earth": 77,
    "e5m3_hell": 82,
    "e5m4_boss": 80,
}
SKILL_ALLOWANCES: dict[int, int] = {
    0: 15,
    1: 12,
    2: 6,
}
SPIRIT_PENALTY: int = 15
DARK_LORD_HAMMER_PENALTY: int = 15
MAX_EFFECTIVE_CR: int = 100


MISSION_SKULL_TIERS = {
    "e1m1_intro": 1,
    "e1m2_war": 1,
    "e1m3_cult": 2,
    "e1m4_boss": 2,
    "e2m1_nest": 2,
    "e2m2_base": 2,
    "e2m3_core": 2,
    "e2m4_boss": 2,
    "e3m1_slayer": 3,
    "e3m2_hell": 3,
    "e3m2_hell_b": 3,
    "e3m3_maykr": 3,
    "e3m4_boss": 4,
    "e4m1_rig": 4,
    "e4m2_swamp": 4,
    "e4m3_mcity": 4,
    "e5m1_spear": 4,
    "e5m2_earth": 3,
    "e5m3_hell": 3,
    "e5m4_boss": 3,
}
TRAVERSAL_DASH_STAGES = (
    frozenset(
        {
            "e3m3_maykr",
            "e4m1_rig",
            "e4m2_swamp",
            "e4m3_mcity",
            "e5m1_spear",
            "e5m2_earth",
            "e5m3_hell",
        }
    )
    | MASTER_LEVEL_COMBAT_PROFILES.keys()
)
HOOK_TRAVERSAL_STAGES = frozenset({"e5m1_spear", "e5m2_earth", "e5m3_hell", "ml_e5m1_spear"})
ENDURANCE_STAGES = TRAVERSAL_DASH_STAGES | {"e3m1_slayer"}


SPIRIT_BREAKPOINTS: dict[tuple[str, str], str] = {
    ("The Blood Swamps - Underworld Crossroad", "The Blood Swamps - Sunken Courtyard"): "e4m2_swamp",
    ("The Holt - Tranquility", "The Holt - Crimson Forest"): "e4m3_mcity",
    (
        "The World Spear - Sentinel Mountain - Mountain Ruins",
        "The World Spear - Sentinel Mountain - Nether Lake",
    ): "e5m1_spear",
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


def get_mission_base_cr(stage_id: str, world: Any | None = None) -> int:
    """Apply the frozen change in combat cost to the mission's preparation rating."""
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return frozen.cr_max
    if stage_id in MASTER_LEVEL_COMBAT_PROFILES:
        return get_mission_cr_range(stage_id, world)[1]
    if stage_id not in MISSION_BASE_CR:
        raise KeyError(player_text("apworld.errors", "unknown_stage_cr", stage=stage_id))
    base = MISSION_BASE_CR[stage_id]
    enemy_plan = getattr(world, "enemy_plan", None) or {}
    costs = enemy_plan.get("combat_costs", {}).get(stage_id)
    if costs is None:
        return base
    profile = costs.get("campaign")
    if profile is not None:
        if enemy_plan.get("revision", 0) >= 5 and profile.get("waves"):
            return get_mission_cr_range(stage_id, world)[1]
        return _campaign_pressure_cr(stage_id, base, profile)
    return _scaled_cost_cr(stage_id, base, costs)


def _scaled_cost_cr(stage_id, base, costs):
    import math

    # Ten cost units per reference CR; doubling that budget adds twelve CR.
    factor = max(0.25, 1 + (costs["actual"] - costs["original"]) / (10 * base))
    floor = (
        base
        if stage_id in {"e1m4_boss", "e2m2_base", "e2m4_boss", "e3m3_maykr", "e3m4_boss", "e4m3_mcity", "e5m4_boss"}
        else 1
    )
    return max(floor, min(MAX_EFFECTIVE_CR, round(base + 12 * math.log2(factor))))


def _campaign_pressure_cr(stage_id, base, profile):
    import math

    bodies = max(1, profile["bodies"])
    pressure = (
        8
        + 8 * math.log2(1 + profile["actual"] / bodies)
        + 4 * math.log2(1 + profile["wave_p90"] / 10)
        + 3 * math.log2(1 + profile["bodies"] / 100)
    )
    floor = base if stage_id in {"e1m4_boss", "e2m4_boss", "e3m3_maykr", "e3m4_boss", "e4m3_mcity", "e5m4_boss"} else 1
    return max(floor, min(MAX_EFFECTIVE_CR, round(pressure)))


def _opening_combat_profile(profile):
    waves = profile.get("opening_waves")
    if not waves:
        raise ValueError(player_text("apworld.errors", "opening_encounters_unavailable"))
    profile = {**profile, "waves": waves, "bodies": sum(wave["bodies"] for wave in waves)}
    if "opening_estimated_kills" in profile:
        profile["estimated_kills"] = profile["opening_estimated_kills"]
    return profile


def get_mission_cr_range(stage_id, world, *, opening=False):
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return (frozen.opening_cr_min, frozen.opening_cr_max) if opening else (frozen.cr_min, frozen.cr_max)

    profile = _combat_profile(stage_id, world)
    if opening:
        if getattr(world, "enemy_plan", None) is None:
            return 35, 35
        profile = _opening_combat_profile(profile)
    if not profile.get("waves"):
        value = get_mission_base_cr(stage_id, world)
        return value, value
    return _profile_cr_range(stage_id, profile, opening)


def get_mission_effort_per_check(stage_id, world):
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return frozen.effort_per_check_milli / 1000
    profile = _combat_profile(stage_id, world)
    if "effort" not in profile:
        return 0.0
    from .generated_content import CAMPAIGN_STAGES, LOCATION_ROWS
    from .locations import optional_location_enabled

    regions = next(set(stage["regions"]) for stage in CAMPAIGN_STAGES if stage["id"] == stage_id)
    options = getattr(world, "options", None)
    checks = sum(
        code is not None and region in regions and (options is None or optional_location_enabled(name, options))
        for name, code, region in LOCATION_ROWS
    )
    return profile["effort"] * _mission_duration_weight(stage_id) / max(1, checks)


def _mission_duration_weight(stage_id):
    return 1.5 if stage_id in {"e5m1_spear", "e5m2_earth", "e5m3_hell"} else 1.25 if stage_id.startswith("e4m") else 1


def get_mission_skull_tier(stage_id: str, world: Any | None = None) -> int:
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return frozen.skulls
    if stage_id in MASTER_LEVEL_COMBAT_PROFILES or (getattr(world, "enemy_plan", None) or {}).get("revision", 0) >= 3:
        rating = get_mission_intrinsic_cr(stage_id, world)
        return 1 + sum(rating >= threshold for threshold in (35, 55, 75))
    change = get_mission_base_cr(stage_id, world) - MISSION_BASE_CR[stage_id]
    return max(1, min(4, MISSION_SKULL_TIERS[stage_id] + round(change / 15)))


def _combat_profile(stage_id, world):
    if stage_id in MASTER_LEVEL_COMBAT_PROFILES:
        return MASTER_LEVEL_COMBAT_PROFILES[stage_id]
    return (getattr(world, "enemy_plan", None) or {}).get("combat_costs", {}).get(stage_id, {}).get("campaign", {})


def _stage_counter_ids(stage_id, world, opening):
    profile = _combat_profile(stage_id, world)
    present = set(profile.get("opening_species" if opening else "species", ()))
    enemy_plan = getattr(world, "enemy_plan", None) or {}
    if stage_id not in MASTER_LEVEL_COMBAT_PROFILES and enemy_plan.get("revision", 0) >= 13:
        present.difference_update({"spirit", "stone_imp"})
    field = "opening_counter_ids" if opening else "counter_ids"
    frozen = getattr(world, "stage_profiles", {}).get(stage_id)
    if frozen is not None:
        present = set(getattr(frozen, field))
    return present


def _enemy_counter_penalties(state, player, stage_id, world, *, opening=False):
    from .logic import COMBAT_CAPABILITIES

    present = _stage_counter_ids(stage_id, world, opening)
    counters = (
        ("spirit", 15, (("Plasma Rifle", "Microwave Beam"),)),
        ("blood_angel", 8, COMBAT_CAPABILITIES["weak_point"]),
        ("stone_imp", 6, (("Combat Shotgun", "Full Auto"),)),
    )
    return {
        species: penalty
        for species, penalty, alternatives in counters
        if species in present
        and not (
            state is not None
            and any(all(state.has(item, player) for item in alternative) for alternative in alternatives)
        )
    }


def get_mission_intrinsic_cr(stage_id, world):
    return min(
        MAX_EFFECTIVE_CR,
        get_mission_base_cr(stage_id, world) + sum(_enemy_counter_penalties(None, 1, stage_id, world).values()),
    )


def _native_chainsaw_before_combat(stage_id, world):
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return frozen.native_chainsaw_before_combat
    return (
        stage_id == "e1m1_intro"
        and (getattr(world, "enemy_plan", None) or {}).get("revision", 0) >= 13
        and not getattr(getattr(getattr(world, "options", None), "randomize_chainsaw", None), "value", 0)
    )


def _renewable_ammo(stage_id, world):
    frozen = (getattr(world, "stage_profiles", None) or {}).get(stage_id)
    if frozen is not None:
        return frozen.renewable_ammo
    if stage_id in MASTER_LEVEL_COMBAT_PROFILES:
        return MASTER_LEVEL_COMBAT_PROFILES[stage_id]["renewable_ammo"]
    from .native_enemy_plan import AMMO_FODDER

    stage = (getattr(world, "enemy_plan", None) or {}).get("maps", {}).get(stage_id, {})
    return any(operation.get("reserve") for operation in stage.get("operations", [])) or any(
        recipe.get("renewable") and any(body["species"] in AMMO_FODDER for body in recipe["bodies"])
        for recipe in stage.get("recipes", [])
    )


def _breakpoint_spirit_present(stage_id, world):
    if getattr(world, "stage_profiles", None):
        return world.enemy_plan is None or "spirit" in world.stage_profiles[stage_id].counter_ids
    enemy_plan = getattr(world, "enemy_plan", None) or {}
    if enemy_plan.get("revision", 0) >= 13:
        return False
    generated_species = enemy_plan.get("combat_costs", {}).get(stage_id, {}).get("campaign", {}).get("species", ())
    return enemy_plan.get("revision", 0) < 4 or "spirit" in generated_species


def get_skill_allowance(logic_difficulty: int, campaign_difficulty: int = 1) -> int:
    """Return the preparation allowance for a LogicDifficulty value."""
    if logic_difficulty not in SKILL_ALLOWANCES:
        raise ValueError(player_text("apworld.errors", "unsupported_logic_difficulty", difficulty=logic_difficulty))
    return max(0, SKILL_ALLOWANCES[logic_difficulty] - max(0, min(campaign_difficulty, 3) - 1) * 2)


def has_effective_anti_spirit(state: CollectionState, player: int) -> bool:
    """Check whether player possesses an effective anti-spirit capability (Plasma Rifle + Microwave Beam)."""
    return state.has("Plasma Rifle", player) and state.has("Microwave Beam", player)


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
    special_weapon = _resolve_special_weapon_option(world, special_weapon)
    return logic_difficulty, special_weapon


def _ammo_requirements(state, player, stage_id, world, options, sw):
    missing = []
    randomize_chainsaw = bool(getattr(getattr(options, "randomize_chainsaw", None), "value", 0))

    if _renewable_ammo(stage_id, world) and randomize_chainsaw:
        from .logic import chainsaw_available

        if not chainsaw_available(state, player, randomize_chainsaw=True):
            missing.append("Chainsaw for ammunition supply")
    if stage_id in HOOK_TRAVERSAL_STAGES:
        from .logic import ammo_resource_producer

        if not ammo_resource_producer(
            state,
            player,
            randomize_chainsaw=bool(getattr(getattr(options, "randomize_chainsaw", None), "value", 0)),
            special_weapon=sw,
        ):
            missing.append("Ammo resource producer")
    return missing


def _equipment_requirements(state, player, stage_id, world, context, sw):
    missing = []
    if stage_id in MASTER_LEVEL_COMBAT_PROFILES and "spirit" in _stage_counter_ids(stage_id, world, False):
        if not has_effective_anti_spirit(state, player):
            missing.append("Plasma Rifle and Microwave Beam")
    options = getattr(world, "options", None)
    randomize_dash = bool(getattr(getattr(options, "randomize_dash", None), "value", 0))
    if stage_id in TRAVERSAL_DASH_STAGES and not dash_available(state, player, randomize_dash=randomize_dash):
        missing.append("Dash")
    if stage_id in HOOK_TRAVERSAL_STAGES and context != "opening":
        missing.extend(name for name in ("Super Shotgun", "Meat Hook") if not state.has(name, player))
    missing.extend(_ammo_requirements(state, player, stage_id, world, options, sw))
    return missing


def _armor_requirements(state, player, stage_id, world, difficulty):
    plan = getattr(world, "campaign_plan", {})
    stages = plan.get("sequence", []) + plan.get("master_level_stage_ids", [])
    if difficulty >= 2 or stage_id not in stages or stages.index(stage_id) < len(stages) // 2:
        return []
    if state.has("Flame Belch", player) or all(
        state.has(name, player) for name in ("Super Shotgun", "Meat Hook", "Meat Hook Mastery")
    ):
        return []
    return [player_text("apworld.readiness", "armor_source")]


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
    """A supplied player_cr must match the loadout total for this state."""
    diff, sw = _resolve_readiness_options(world, logic_difficulty, special_weapon)
    campaign_difficulty = getattr(getattr(getattr(world, "options", None), "campaign_difficulty", None), "value", 1)
    allowance = get_skill_allowance(diff, campaign_difficulty)
    if stage_id == DARK_LORD_STAGE_ID and context == "base":
        context = "darklord"
    base_cr = get_mission_base_cr(stage_id, world)
    if context == "opening":
        base_cr = get_mission_cr_range(stage_id, world, opening=True)[1]
    native_chainsaw = _native_chainsaw_before_combat(stage_id, world)
    if player_cr is None or native_chainsaw:
        cr_result = evaluate_player_loadout_cr(state, player, world, native_chainsaw=native_chainsaw)
        player_cr = float(cr_result.total)
    else:
        player_cr = float(player_cr)

    soft_penalty, reason = _mission_counter_penalty(state, player, stage_id, world, context, sw)
    effective_cr = min(MAX_EFFECTIVE_CR, base_cr + soft_penalty)
    deficit = round(effective_cr - player_cr, 2)
    missing = _equipment_requirements(state, player, stage_id, world, context, sw)
    missing.extend(_armor_requirements(state, player, stage_id, world, diff))
    preparation_deficit = float(len(missing))
    preparation_deficit += _endurance_preparation_deficit(state, player, stage_id, world, context)
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
    plan = getattr(world, "campaign_plan", {}) or {}
    if stage_id in plan.get("unprepared_start_stages", ()):
        return True
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
        state,
        player,
        stage_id,
        world,
        logic_difficulty=logic_difficulty,
        context="spirit_breakpoint",
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
        state,
        player,
        DARK_LORD_STAGE_ID,
        world,
        logic_difficulty=logic_difficulty,
        special_weapon=special_weapon,
        context="dark_lord_defeated",
    ).ready


def _profile_cr_range(stage_id, profile, opening):
    import math

    floor = (
        MISSION_BASE_CR[stage_id]
        if not opening and stage_id in {"e1m4_boss", "e2m4_boss", "e3m3_maykr", "e3m4_boss", "e4m3_mcity", "e5m4_boss"}
        else 1
    )
    endurance = 3 * math.log2(1 + profile.get("estimated_kills", profile["bodies"]) / 100)
    ratings = [
        max(
            floor,
            min(
                MAX_EFFECTIVE_CR,
                round(
                    8
                    + endurance
                    + 8
                    * math.log2(
                        1 + wave.get("peak_cost", wave["cost"]) / max(1, wave.get("peak_bodies", wave["bodies"]))
                    )
                    + 4 * math.log2(1 + wave.get("peak_cost", wave["cost"]) / 10)
                ),
            ),
        )
        for wave in profile["waves"]
        if wave["bodies"]
    ]
    return (min(ratings), max(ratings)) if ratings else (floor, floor)


def _resolve_special_weapon_option(world, special_weapon):
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
    return special_weapon


def _mission_counter_penalty(state, player, stage_id, world, context, sw):
    penalties = _enemy_counter_penalties(state, player, stage_id, world, opening=context == "opening")
    reason = ""
    if context == "spirit_breakpoint":
        if _breakpoint_spirit_present(stage_id, world) and not has_effective_anti_spirit(state, player):
            penalties["spirit"] = SPIRIT_PENALTY
            reason = "Missing effective Microwave Beam at mandatory Spirit breakpoint (+15 CR)"
    elif context == "dark_lord_defeated" or (stage_id == DARK_LORD_STAGE_ID and context == "boss"):
        if not sentinel_hammer_available(state, player, special_weapon=sw):
            penalties["dark_lord"] = DARK_LORD_HAMMER_PENALTY
            reason = "Missing effective Sentinel Hammer against The Dark Lord (+15 CR)"

    soft_penalty = sum(penalties.values())
    if soft_penalty and not reason:
        reason = f"Missing enemy counter preparation (+{soft_penalty} CR)"
    return soft_penalty, reason


def _endurance_preparation_deficit(state, player, stage_id, world, context):
    preparation_deficit = 0.0
    enemies = getattr(world, "enemies", {})
    if stage_id in ENDURANCE_STAGES and context != "opening" and not enemies.get("balance_preset"):
        capacities = ("Progressive Health Upgrade", "Progressive Armor Upgrade", "Progressive Ammo Upgrade")
        preparation_deficit += sum(not state.has(name, player) for name in capacities)
        preparation_deficit += not any(state.has(name, player) for name in NORMAL_RUNE_NAMES)
        categories = evaluate_player_loadout_cr(state, player, world).categories
        preparation_deficit += sum(
            max(0.0, floor - categories[category])
            for category, floor in (("Mobility", 4.0), ("Defense", 6.0), ("Sustain", 9.0))
        )
    return preparation_deficit


@dataclass(frozen=True)
class ReadinessTarget:
    """Represents a logically required readiness target in the active campaign."""

    stage_id: str
    context: str = "base"
    description: str = ""


def derive_readiness_targets(options, plan: Mapping[str, Any]) -> list[ReadinessTarget]:
    plan = plan or {}
    targets = []
    seen = set()

    def add_target(stage_id, context="base", description=""):
        if context in {"base", "opening"} and stage_id in plan.get("unprepared_start_stages", ()):
            return
        key = (stage_id, context)
        if key not in seen:
            seen.add(key)
            targets.append(ReadinessTarget(stage_id, context, description))

    spirit_stages = set(SPIRIT_BREAKPOINTS.values())
    for stage_id in plan.get("sequence", []) + plan.get("master_level_stage_ids", []):
        name = STAGE_BY_ID[stage_id]["name"]
        add_target(stage_id, "base", f"Mission: {name}")
        if stage_id in spirit_stages:
            add_target(stage_id, "spirit_breakpoint", f"Spirit Breakpoint: {name}")
    if _requires_dark_lord_readiness(plan):
        add_target(DARK_LORD_STAGE_ID, "dark_lord_defeated", "Boss: The Dark Lord Defeated")
    return targets


@dataclass(frozen=True)
class SelectionStep:
    """One activated item copy inside a dependency-complete package."""

    item_name: str
    package_lead: str
    package_size: int
    is_dependency: bool
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


def select_readiness_items(
    *,
    base_items: Mapping[str, int],
    targets: Sequence[ReadinessTarget],
    additional: Mapping[str, int],
    world_context: Any,
    player: int = 1,
    slack: float = READINESS_PLACEMENT_SLACK,
) -> ReadinessSelection:
    if not targets:
        return ReadinessSelection(satisfied=True)
    builder = _ReadinessSelector(
        base_items=base_items,
        targets=targets,
        additional=additional,
        world_context=world_context,
        player=player,
        slack=slack,
    )
    return builder.build()


def _requires_dark_lord_readiness(plan):
    return (
        plan.get("goal_stage") == DARK_LORD_STAGE_ID
        or any(
            DARK_LORD_STAGE_ID in plan.get(key, ()) for key in ("active_normal_mission_ids", "stage_ids", "sequence")
        )
    )


def _reason_for_context(context: str) -> str:
    if context == "spirit_breakpoint":
        return "spirit_breakpoint"
    if context == "dark_lord_defeated":
        return "dark_lord_breakpoint"
    return "cr_readiness"


class _ReadinessSelector:
    def __init__(
        self,
        *,
        base_items: Mapping[str, int],
        targets: Sequence[ReadinessTarget],
        additional: Mapping[str, int],
        world_context: Any,
        player: int = 1,
        slack: float = READINESS_PLACEMENT_SLACK,
    ):
        self.additional = additional
        self.base_items = base_items
        self.player = player
        self.slack = slack
        self.targets = targets
        self.world_context = world_context

    def build(self):
        self._initialize()
        self._select()
        return self._result()

    def player_cr(self, st: FastState) -> float:
        key = tuple(sorted(st.prog_items.items()))
        cached = self.cr_cache.get(key)
        if cached is None:
            cached = float(evaluate_player_loadout_cr(st, self.player, self.world_context).total)
            self.cr_cache[key] = cached
        return cached

    def worst_deficit(self, st: FastState) -> tuple[float, ReadinessTarget | None]:
        key = tuple(sorted(st.prog_items.items()))
        cached = self.target_cache.get(key)
        if cached is not None:
            return cached
        cr = self.player_cr(st)
        worst = -999.0
        worst_target: ReadinessTarget | None = None
        for target in self.targets:
            result = evaluate_mission_readiness(
                st, self.player, target.stage_id, self.world_context, context=target.context, player_cr=cr
            )
            deficit = result.effective_cr - result.player_cr - result.allowance
            if result.preparation_deficit > 0:
                deficit = max(deficit, result.preparation_deficit)
            if deficit > worst:
                worst = deficit
                worst_target = target
        cached = (worst, worst_target)
        self.target_cache[key] = cached
        return cached

    def _initialize(self):
        self.selection = ReadinessSelection()
        self.state = FastState.from_counts(self.base_items, player=self.player)
        self.cr_cache: dict[tuple, float] = {}
        self.target_cache: dict[tuple, tuple[float, ReadinessTarget | None]] = {}

    def _select(self):
        self.current_deficit, self.current_worst = self.worst_deficit(self.state)
        self.selection.initial_deficit = self.current_deficit
        self.current_cr = self.player_cr(self.state)
        while self.current_deficit > -self.slack:
            best_lead, best_package, _, best_delta_cr = self._best_package()
            if best_lead is None:
                break
            reason = _reason_for_context(self.current_worst.context if self.current_worst is not None else "base")
            target_description = self.current_worst.description if self.current_worst is not None else ""
            for pkg_name in best_package:
                self.state.collect(pkg_name)
                self.selection.counts[pkg_name] += 1
                self.selection.steps.append(
                    SelectionStep(
                        item_name=pkg_name,
                        package_lead=best_lead,
                        package_size=len(best_package),
                        is_dependency=pkg_name != best_lead,
                        delta_cr=best_delta_cr,
                        target_description=target_description,
                        reason=reason,
                        dependency_closure=ITEM_DEPENDENCIES.get(pkg_name, ()),
                    )
                )
            self.current_cr = self.player_cr(self.state)
            self.current_deficit, self.current_worst = self.worst_deficit(self.state)

    def _result(self):
        self.selection.final_deficit = self.current_deficit
        self.selection.satisfied = self.current_deficit <= 0.0
        return self.selection

    def _best_package(self):
        best_lead: str | None = None
        best_package: tuple[str, ...] = ()
        best_delta_deficit = 0.0
        best_delta_cr = 0.0
        for cand_name in sorted(self.additional):
            if self.selection.counts[cand_name] >= self.additional[cand_name]:
                continue
            full_package = self._dependency_package(cand_name)
            if full_package is None:
                continue
            temp_state = self.state.copy()
            for pkg_name in full_package:
                temp_state.collect(pkg_name)
            new_max_def, _ = self.worst_deficit(temp_state)
            delta_def = self.current_deficit - new_max_def
            if delta_def <= 1e-06:
                continue
            new_cr = self.player_cr(temp_state)
            delta_cr = new_cr - self.current_cr
            is_better = _better_package(
                cand_name, full_package, delta_def, delta_cr, best_lead, best_package, best_delta_deficit, best_delta_cr
            )
            if is_better:
                best_lead = cand_name
                best_package = full_package
                best_delta_deficit = delta_def
                best_delta_cr = delta_cr
        return best_lead, best_package, best_delta_deficit, best_delta_cr

    def _dependency_package(self, cand_name):
        package_items: list[str] = []
        possible = True
        for dep in ITEM_DEPENDENCIES.get(cand_name, ()):
            if self.state.has(dep, self.player):
                continue
            if self.selection.counts[dep] < self.additional.get(dep, 0):
                package_items.append(dep)
            else:
                possible = False
                break
        if not possible:
            return None
        package_items.append(cand_name)
        return tuple(package_items)


def _better_package(
    cand_name, full_package, delta_def, delta_cr, best_lead, best_package, best_delta_deficit, best_delta_cr
):
    if best_lead is None or delta_def > best_delta_deficit + 1e-6:
        return True
    if not abs(delta_def - best_delta_deficit) <= 1e-6:
        return False
    if len(full_package) != len(best_package):
        return len(full_package) < len(best_package)
    if delta_cr > best_delta_cr + 1e-6:
        return True
    return abs(delta_cr - best_delta_cr) <= 1e-6 and cand_name < best_lead
