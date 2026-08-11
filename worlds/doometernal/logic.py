"""Declarative, validated access rules for proven DOOM Eternal checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from BaseClasses import CollectionState

from .items import normal_pool_weapon_item_names

MASTERY_SUFFIX = " - Weapon Mastery Challenge"
MEAT_HOOK_MASTERY_LOCATION = "Meat Hook - Weapon Mastery Challenge"

# Base weapons and mods are separate progression items in current pool. Mod
# requirements never imply a vanilla grant for a stripped or AP item.
MOD_BASE_WEAPON_REQUIREMENTS: Mapping[str, str] = {
    "Full Auto": "Combat Shotgun",
    "Sticky Bombs": "Combat Shotgun",
    "Precision Bolt": "Heavy Cannon",
    "Micro Missiles": "Heavy Cannon",
    "Heat Blast": "Plasma Rifle",
    "Microwave Beam": "Plasma Rifle",
    "Lock-on Burst": "Rocket Launcher",
    "Remote Detonate": "Rocket Launcher",
    "Destroyer Blade": "Ballista",
    "Arbalest": "Ballista",
    "Mobile Turret": "Chaingun",
    "Energy Shield": "Chaingun",
}


@dataclass(frozen=True)
class LocationRequirement:
    """Location access from direct item, combat, and battery requirements."""

    all_of: tuple[str, ...] = ()
    any_of: tuple[tuple[str, ...], ...] = ()
    combat_all_of: tuple[str, ...] = ()
    combat_any_of: tuple[str, ...] = ()
    battery_currency: int = 0


COMBAT_CAPABILITIES: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "weak_point": (("Heavy Cannon", "Precision Bolt"), ("Ballista",), ("Combat Shotgun", "Sticky Bombs")),
    "flame_belch": (("Flame Belch",),),
    "frag_grenade": (("Frag Grenade",),),
    "plasma_rifle": (("Plasma Rifle",),),
    "ice_bomb": (("Ice Bomb",),),
    "blood_punch": (("Blood Punch",),),
}

WEAPON_COVERAGE_PREFIX = "weapon_coverage_"
NORMAL_WEAPON_NAMES = frozenset(normal_pool_weapon_item_names)
def weapon_coverage_capability(required_count: int) -> str:
    if required_count < 1:
        raise ValueError("Weapon coverage threshold must be positive")
    return f"{WEAPON_COVERAGE_PREFIX}{required_count}"


def weapon_coverage_threshold(capability: str) -> int | None:
    if not capability.startswith(WEAPON_COVERAGE_PREFIX):
        return None
    raw_threshold = capability.removeprefix(WEAPON_COVERAGE_PREFIX)
    try:
        threshold = int(raw_threshold)
    except ValueError as error:
        raise ValueError(f"Invalid weapon coverage capability: {capability}") from error
    if threshold < 1:
        raise ValueError(f"Invalid weapon coverage capability: {capability}")
    return threshold


def weapon_coverage_satisfied(state: CollectionState, player: int, required_count: int) -> bool:
    if required_count < 1:
        raise ValueError("Weapon coverage threshold must be positive")
    return sum(state.has(name, player) for name in NORMAL_WEAPON_NAMES) >= required_count


def combat_capability_alternatives(capability: str) -> tuple[tuple[str, ...], ...]:
    if capability in COMBAT_CAPABILITIES:
        return COMBAT_CAPABILITIES[capability]
    if capability.startswith("mod:"):
        mod_name = capability.removeprefix("mod:")
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        if base_weapon:
            return ((base_weapon, mod_name),)
    raise ValueError(f"Unknown combat capability: {capability}")


def _requirement_item_names(requirement: LocationRequirement) -> frozenset[str]:
    names = set(requirement.all_of)
    # Only conjunctive requirements can make their own location inaccessible.
    # Alternatives remain gameplay choices, not placement bans.
    for capability in requirement.combat_all_of:
        names.update(
            item
            for alternative in combat_capability_alternatives(capability)
            for item in alternative
        )
    return frozenset(names)


def build_location_prerequisites(location_names: set[str]) -> dict[str, LocationRequirement]:
    mastery_locations = sorted(name for name in location_names if name.endswith(MASTERY_SUFFIX))
    table: dict[str, LocationRequirement] = {
        "Cultist Base - Mission Challenge - Armored Rain": LocationRequirement(
            combat_all_of=("flame_belch",)
        ),
        # This aggregate is the conjunction of its three native children. Only
        # Armored Rain currently has a proven mandatory inventory prerequisite.
        "Cultist Base - All Mission Challenges Completed": LocationRequirement(
            combat_all_of=("flame_belch",)
        ),
        "Fortress of Doom - Praetor Suit Token - Battery Room Upper East": LocationRequirement(battery_currency=2),
        "Fortress of Doom - Praetor Suit Token - Battery Room Upper West": LocationRequirement(battery_currency=3),
        "Fortress of Doom - Modbot - Battery Room Upper West": LocationRequirement(battery_currency=5),
        "Fortress of Doom - Modbot - Battery Room Upper East": LocationRequirement(battery_currency=7),
        "Fortress of Doom - Sentinel Crystal - Battery Room Lower East": LocationRequirement(battery_currency=9),
        "Fortress of Doom - Sentinel Crystal - Battery Room Lower West": LocationRequirement(battery_currency=11),
        "Fortress of Doom - Praetor Suit Token - Elevator Room West": LocationRequirement(battery_currency=12),
        "Fortress of Doom - Praetor Suit Token - Elevator Room East": LocationRequirement(battery_currency=13),
        "Fortress of Doom - All Runes Cheat Code": LocationRequirement(battery_currency=15),
        "Fortress of Doom - Fully Upgraded Suit Cheat Code": LocationRequirement(battery_currency=17),
        "Fortress of Doom - Praetor Suit": LocationRequirement(battery_currency=2),
        "Fortress of Doom - Sentinel Armor": LocationRequirement(battery_currency=4),
        "Fortress of Doom - Classic Marine Suit": LocationRequirement(battery_currency=6),
        "Doom Hunter Base - Mission Challenge - Fire in the Hole": LocationRequirement(
            combat_all_of=("frag_grenade",)
        ),
        "Doom Hunter Base - All Mission Challenges Completed": LocationRequirement(
            combat_all_of=("frag_grenade",)
        ),
        "ARC Complex - Mission Challenge - External Combustion": LocationRequirement(
            combat_all_of=("plasma_rifle",)
        ),
        "ARC Complex - All Mission Challenges Completed": LocationRequirement(
            combat_all_of=("plasma_rifle",)
        ),
        "Taras Nabad - Mission Challenge - Keeping Cool": LocationRequirement(
            combat_all_of=("ice_bomb",)
        ),
        "Taras Nabad - All Mission Challenges Completed": LocationRequirement(
            combat_all_of=("ice_bomb",)
        ),
        "Nekravol Part II - Mission Challenge - Punched by Blood": LocationRequirement(
            combat_all_of=("blood_punch",)
        ),
        "Nekravol Part II - All Mission Challenges Completed": LocationRequirement(
            combat_all_of=("blood_punch",)
        ),
        "Urdak - Mission Challenge - Angel of Death": LocationRequirement(
            combat_any_of=("weak_point",)
        ),
        "Urdak - All Mission Challenges Completed": LocationRequirement(
            combat_any_of=("weak_point",)
        ),
    }
    for location_name in mastery_locations:
        if location_name in NO_RULE_PROVEN:
            continue
        mod_name = location_name.removesuffix(MASTERY_SUFFIX)
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        if base_weapon is None:
            raise ValueError(f"No audited weapon/mod capability for mastery: {mod_name}")
        table[location_name] = LocationRequirement(combat_all_of=(f"mod:{mod_name}",))
    return table


def validate_location_prerequisites(
    table: Mapping[str, LocationRequirement],
    location_names: set[str],
    item_names: set[str],
) -> None:
    for location_name, requirement in table.items():
        if location_name not in location_names:
            raise ValueError(f"Unknown logic location: {location_name}")
        if not isinstance(requirement, LocationRequirement):
            raise ValueError(f"Invalid logic rule: {location_name}")
        if set(requirement.all_of) - item_names:
            raise ValueError(
                f"Unknown logic item(s) for {location_name}: {sorted(set(requirement.all_of) - item_names)}"
            )
        if any(not alternative for alternative in requirement.any_of):
            raise ValueError(f"Empty any_of alternative: {location_name}")
        unknown_any = {item for alternative in requirement.any_of for item in alternative if item not in item_names}
        if unknown_any:
            raise ValueError(f"Unknown any_of item(s) for {location_name}: {sorted(unknown_any)}")
        for capability in (*requirement.combat_all_of, *requirement.combat_any_of):
            alternatives = combat_capability_alternatives(capability)
            unknown_combat = {
                item for alternative in alternatives for item in alternative if item not in item_names
            }
            if unknown_combat:
                raise ValueError(
                    f"Unknown combat capability item(s) for {location_name}: {sorted(unknown_combat)}"
                )
        if requirement.battery_currency < 0:
            raise ValueError(f"Negative Battery requirement: {location_name}")
        if requirement.battery_currency and not {"Sentinel Battery", "Sentinel Battery Bundle"}.issubset(item_names):
            raise ValueError(f"Battery items are absent for {location_name}")


def requirement_satisfied(requirement: LocationRequirement, state: CollectionState, player: int) -> bool:
    if not all(state.has(item_name, player) for item_name in requirement.all_of):
        return False
    if (
        requirement.battery_currency
        and (state.count("Sentinel Battery", player) + 2 * state.count("Sentinel Battery Bundle", player))
        < requirement.battery_currency
    ):
        return False
    if requirement.any_of and not any(
        all(state.has(item_name, player) for item_name in alternative) for alternative in requirement.any_of
    ):
        return False
    if not all(
        any(
            all(state.has(item_name, player) for item_name in alternative)
            for alternative in combat_capability_alternatives(capability)
        )
        for capability in requirement.combat_all_of
    ):
        return False
    return not requirement.combat_any_of or any(
        any(
            all(state.has(item_name, player) for item_name in alternative)
            for alternative in combat_capability_alternatives(capability)
        )
        for capability in requirement.combat_any_of
    )


@dataclass(frozen=True)
class ConnectionRequirement:
    """Conservative, bypassable gameplay capability for a canonical transition."""

    soft_capabilities: tuple[str, ...] = ()


def connection_requirement_satisfied(
    requirement: ConnectionRequirement, state: CollectionState, player: int
) -> bool:
    return all(
        weapon_coverage_satisfied(state, player, threshold)
        if (threshold := weapon_coverage_threshold(capability)) is not None
        else any(
            all(state.has(item_name, player) for item_name in alternative)
            for alternative in combat_capability_alternatives(capability)
        )
        for capability in requirement.soft_capabilities
    )


def connection_requirement_from_metadata(metadata: Mapping[str, object]) -> ConnectionRequirement:
    if set(metadata) - {"soft_capabilities"}:
        raise ValueError(f"Unknown connection condition fields: {sorted(set(metadata) - {'soft_capabilities'})}")
    capabilities = metadata.get("soft_capabilities", ())
    if not isinstance(capabilities, (list, tuple)) or any(not isinstance(value, str) for value in capabilities):
        raise ValueError("Connection soft_capabilities must contain strings")
    for capability in capabilities:
        if weapon_coverage_threshold(capability) is None:
            combat_capability_alternatives(capability)
    return ConnectionRequirement(tuple(capabilities))


def required_item_names(requirement: LocationRequirement) -> frozenset[str]:
    """Return direct and conjunctive combat items to exclude from own ruled location."""
    return _requirement_item_names(requirement)


# Audited checks with no proven mandatory item prerequisite. Keep this explicit
# so future audits do not silently turn absence of evidence into logic.
NO_RULE_PROVEN = frozenset(
    {
        "Cultist Base - Mission Challenge - Pull the Crystal",
        "Cultist Base - Mission Challenge - Master of Turrets",
        MEAT_HOOK_MASTERY_LOCATION,
        "Doom Hunter Base - Mission Challenge - Musical Interlude",
        "Doom Hunter Base - Mission Challenge - Big Reveal",
        "ARC Complex - Mission Challenge - Rune Finder",
        "ARC Complex - Mission Challenge - Solitary Confinement",
        "Mars Core - Mission Challenge - Big Ba-Da Boom",
        "Mars Core - Mission Challenge - Disarmament",
        "Mars Core - Mission Challenge - Lock and Key",
        "Taras Nabad - Mission Challenge - Man Made Wiki",
        "Taras Nabad - Mission Challenge - Painkiller",
        "Nekravol - Mission Challenge - Die by the Sword",
        "Nekravol - Mission Challenge - Tricks and Traps",
        "Nekravol - Mission Challenge - Doom Hunt",
        "Nekravol Part II - Mission Challenge - Cut Down to Size",
        "Nekravol Part II - Mission Challenge - Resurrect No More",
        "Urdak - Mission Challenge - Accessories Not Included",
        "Urdak - Mission Challenge - Inflight Devastation",
    }
)
