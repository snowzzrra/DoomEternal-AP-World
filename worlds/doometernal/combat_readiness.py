"""
Implements the Combat Readiness solver model:
- Mission Base CR catalog (20 stages from Phase 7.2)
- Skill Allowances (0: 6, 1: 10, 2: 15, 3: 20 from Phase 7.5)
- Severe Soft Penalties:
    - Missing effective Microwave Beam at mandatory Spirit breakpoint: +15
    - Missing effective Sentinel Hammer at The Dark Lord: +15
- Effective Mission CR: min(100, Base CR + Soft Penalty)
- Readiness Condition: Player_CR + Skill_Allowance >= Effective_Mission_CR

Pure deterministic evaluation for Archipelago logical reachability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .combat_rating import evaluate_player_loadout_cr
from .logic import sentinel_hammer_available

if TYPE_CHECKING:
    from BaseClasses import CollectionState

# ── Frozen Phase 7.2 Mission Base CR Catalog ───────────────────
# Canonical P7.3 stage IDs -> integer Base CR (0..100)
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
    "e5m1_spear": 75,   # The World Spear
    "e5m2_earth": 77,   # Reclaimed Earth
    "e5m3_hell": 82,    # Immora
    "e5m4_boss": 80,    # The Dark Lord
}

# ── Frozen Phase 7.5 Skill Allowances ─────────────────────────
# CampaignDifficulty option value -> numerical CR allowance
SKILL_ALLOWANCES: dict[int, int] = {
    0: 6,   # I'm Too Young to Die
    1: 10,  # Hurt Me Plenty
    2: 15,  # Ultra-Violence (default)
    3: 20,  # Nightmare
}

# ── Frozen Phase 7.5 Severe Soft Penalties & Caps ──────────────
SPIRIT_PENALTY: int = 15
DARK_LORD_HAMMER_PENALTY: int = 15
MAX_EFFECTIVE_CR: int = 100

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

    @property
    def is_ready(self) -> bool:
        return self.ready


def get_mission_base_cr(stage_id: str) -> int:
    """Return the frozen Base CR for a canonical stage ID."""
    if stage_id not in MISSION_BASE_CR:
        raise KeyError(f"Unknown stage ID for Base CR: {stage_id}")
    return MISSION_BASE_CR[stage_id]


def get_skill_allowance(difficulty: int) -> int:
    """Return the frozen Skill Allowance for a CampaignDifficulty value (0..3)."""
    if difficulty not in SKILL_ALLOWANCES:
        raise ValueError(
            f"Unsupported campaign difficulty: {difficulty}. "
            f"Supported: 0 (ITYTD: 6), 1 (HMP: 10), 2 (UV: 15), 3 (Nightmare: 20)"
        )
    return SKILL_ALLOWANCES[difficulty]


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
    difficulty: int | None = None,
    special_weapon: str | None = None,
) -> tuple[int, str]:
    """Resolve difficulty and special weapon configuration."""
    if difficulty is None:
        if world is not None and hasattr(world, "options") and hasattr(world.options, "campaign_difficulty"):
            difficulty = int(world.options.campaign_difficulty.value)
        else:
            difficulty = 2  # default Ultra-Violence
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
    return difficulty, special_weapon


def evaluate_mission_readiness(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    difficulty: int | None = None,
    special_weapon: str | None = None,
    context: str = "base",
) -> ReadinessResult:
    """Evaluate readiness of a player for a given mission and context."""
    diff, sw = _resolve_readiness_options(world, difficulty, special_weapon)
    allowance = get_skill_allowance(diff)
    base_cr = get_mission_base_cr(stage_id)
    cr_result = evaluate_player_loadout_cr(state, player, world)
    player_cr = float(cr_result.total)

    soft_penalty = 0
    reason = ""
    if context == "spirit_breakpoint":
        if not has_effective_anti_spirit(state, player):
            soft_penalty = SPIRIT_PENALTY
            reason = "Missing effective Microwave Beam at mandatory Spirit breakpoint (+15 CR)"
    elif context == "dark_lord_defeated" or (stage_id == DARK_LORD_STAGE_ID and context == "boss"):
        if not has_effective_sentinel_hammer(state, player, special_weapon=sw):
            soft_penalty = DARK_LORD_HAMMER_PENALTY
            reason = "Missing effective Sentinel Hammer against The Dark Lord (+15 CR)"

    effective_cr = min(MAX_EFFECTIVE_CR, base_cr + soft_penalty)
    deficit = round(effective_cr - player_cr, 2)
    ready = deficit <= allowance

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
    )


def is_mission_ready(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    difficulty: int | None = None,
    special_weapon: str | None = None,
    context: str = "base",
) -> bool:
    """Return whether player is logically combat-ready for a mission."""
    return evaluate_mission_readiness(
        state, player, stage_id, world,
        difficulty=difficulty, special_weapon=special_weapon, context=context,
    ).ready


def is_spirit_breakpoint_ready(
    state: CollectionState,
    player: int,
    stage_id: str,
    world: Any | None = None,
    *,
    difficulty: int | None = None,
) -> bool:
    """Return whether player is logically combat-ready to cross a mandatory Spirit breakpoint."""
    return evaluate_mission_readiness(
        state, player, stage_id, world,
        difficulty=difficulty, context="spirit_breakpoint",
    ).ready


def is_dark_lord_defeated_ready(
    state: CollectionState,
    player: int,
    world: Any | None = None,
    *,
    difficulty: int | None = None,
    special_weapon: str | None = None,
) -> bool:
    """Return whether player is logically combat-ready to defeat The Dark Lord."""
    return evaluate_mission_readiness(
        state, player, DARK_LORD_STAGE_ID, world,
        difficulty=difficulty, special_weapon=special_weapon, context="dark_lord_defeated",
    ).ready
