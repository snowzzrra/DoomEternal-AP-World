"""Declarative, validated access rules for proven DOOM Eternal checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from BaseClasses import CollectionState

from .items import starting_weapon_item_names

MASTERY_SUFFIX = " - Weapon Mastery Challenge"

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
    "Meat Hook": "Super Shotgun",
}

MISSION_COMPLETION_WEAPON_THRESHOLDS: Mapping[str, int] = {
    "Hell on Earth": 1,
    "Exultia": 2,
    "Cultist Base": 4,
    "Doom Hunter Base": 5,
    "Super Gore Nest": 6,
    "ARC Complex": 7,
}
DEFAULT_MISSION_COMPLETION_WEAPON_THRESHOLD = 7
MISSION_CLEAR_EVENT_PREFIX = "Internal Mission Clear: "

FORTRESS_BATTERY_CONSUMER_LOCATIONS = frozenset({
    "Fortress of Doom - Praetor Suit",
    "Fortress of Doom - Sentinel Armor",
    "Fortress of Doom - Classic Marine Suit",
})


@dataclass(frozen=True)
class LocationRequirement:
    """Location access from direct item, combat, and battery requirements."""

    all_of: tuple[str, ...] = ()
    any_of: tuple[tuple[str, ...], ...] = ()
    combat_all_of: tuple[str, ...] = ()
    combat_any_of: tuple[str, ...] = ()
    battery_currency: int = 0
    normal_weapon_count: int = 0
    all_requirements: tuple["LocationRequirement", ...] = ()


COMBAT_CAPABILITIES: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "weak_point": (("Heavy Cannon", "Precision Bolt"), ("Ballista",), ("Combat Shotgun", "Sticky Bombs")),
    "flame_belch": (("Flame Belch",),),
    "frag_grenade": (("Frag Grenade",),),
    "plasma_rifle": (("Plasma Rifle",),),
    "ice_bomb": (("Ice Bomb",),),
    "blood_punch": (("Blood Punch",),),
}

def combat_capability_alternatives(capability: str) -> tuple[tuple[str, ...], ...]:
    if capability in COMBAT_CAPABILITIES:
        return COMBAT_CAPABILITIES[capability]
    if capability.startswith("mod:"):
        mod_name = capability.removeprefix("mod:")
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        if base_weapon:
            return ((base_weapon, mod_name),)
    raise ValueError(f"Unknown combat capability: {capability}")


def connection_requirement(
    condition: Mapping[str, object], *, randomize_first_battery: bool = False
) -> LocationRequirement:
    """Convert generated connection metadata into AP access logic."""
    capabilities = condition.get("soft_capabilities", ())
    if not isinstance(capabilities, (list, tuple)):
        raise ValueError("Generated connection soft_capabilities must be a sequence")
    first_battery_gate = "requires_first_battery" in capabilities
    combat_capabilities = tuple(
        capability for capability in capabilities if capability != "requires_first_battery"
    )
    return LocationRequirement(
        battery_currency=1 if first_battery_gate and randomize_first_battery else 0,
        combat_all_of=combat_capabilities,
    )


def mission_clear_event_name(mission_name: str) -> str:
    return f"{MISSION_CLEAR_EVENT_PREFIX}{mission_name}"


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


def build_location_prerequisites(
    location_names: set[str], *, randomize_chainsaw: bool = False
) -> dict[str, LocationRequirement]:
    mastery_locations = sorted(name for name in location_names if name.endswith(MASTERY_SUFFIX))
    table: dict[str, LocationRequirement] = {
        "Cultist Base - Mission Challenge - Armored Rain": LocationRequirement(
            combat_all_of=("flame_belch",)
        ),
        "Doom Hunter Base - Mission Challenge - Fire in the Hole": LocationRequirement(
            combat_all_of=("frag_grenade",)
        ),
        "ARC Complex - Mission Challenge - External Combustion": LocationRequirement(
            combat_all_of=("plasma_rifle",)
        ),
        "Taras Nabad - Mission Challenge - Keeping Cool": LocationRequirement(
            combat_all_of=("ice_bomb",)
        ),
        "Nekravol Part II - Mission Challenge - Punched by Blood": LocationRequirement(
            combat_all_of=("blood_punch",)
        ),
        "Urdak - Mission Challenge - Angel of Death": LocationRequirement(
            all_of=("Heavy Cannon", "Precision Bolt")
        ),
        "Mars Core - Mission Challenge - Big Ba-Da Boom": LocationRequirement(
            all_of=("BFG-9000",)
        ),
        "Nekravol - Mission Challenge - Die by the Sword": LocationRequirement(
            all_of=("The Crucible",)
        ),
    }
    for aggregate_name in sorted(
        name for name in location_names if name.endswith(" - All Mission Challenges Completed")
    ):
        mission_prefix = aggregate_name.removesuffix(" - All Mission Challenges Completed")
        children = sorted(
            name
            for name in location_names
            if name.startswith(f"{mission_prefix} - Mission Challenge - ")
        )
        child_requirements = [table.get(child, LocationRequirement()) for child in children]
        table[aggregate_name] = LocationRequirement(
            all_requirements=tuple(child_requirements),
        )
    for location_name in location_names:
        if location_name.endswith(" - Mission Complete"):
            mission_name = location_name.removesuffix(" - Mission Complete")
            if mission_name == "Urdak":
                table[location_name] = LocationRequirement(
                    all_of=("Blood Punch",),
                )
            elif mission_name == "Final Sin":
                table[location_name] = LocationRequirement()
            else:
                table[location_name] = LocationRequirement(
                    normal_weapon_count=MISSION_COMPLETION_WEAPON_THRESHOLDS.get(
                        mission_name,
                        DEFAULT_MISSION_COMPLETION_WEAPON_THRESHOLD,
                    )
                )
            if mission_name == "Hell on Earth" and randomize_chainsaw:
                table[location_name] = LocationRequirement(
                    all_of=("Chainsaw",),
                    normal_weapon_count=MISSION_COMPLETION_WEAPON_THRESHOLDS[mission_name],
                )
    for location_name in FORTRESS_BATTERY_CONSUMER_LOCATIONS & location_names:
        table[location_name] = LocationRequirement(battery_currency=2)
    for location_name in mastery_locations:
        mod_name = location_name.removesuffix(MASTERY_SUFFIX)
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        if base_weapon is None:
            continue
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
        _validate_requirement(requirement, location_name, item_names)


def _validate_requirement(
    requirement: LocationRequirement,
    location_name: str,
    item_names: set[str],
) -> None:
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
    if requirement.normal_weapon_count < 0:
        raise ValueError(f"Negative normal weapon requirement: {location_name}")
    if requirement.battery_currency and not {"Sentinel Battery", "Sentinel Battery Bundle"}.issubset(item_names):
        raise ValueError(f"Battery items are absent for {location_name}")
    for child in requirement.all_requirements:
        _validate_requirement(child, location_name, item_names)


def requirement_satisfied(requirement: LocationRequirement, state: CollectionState, player: int) -> bool:
    if not all(state.has(item_name, player) for item_name in requirement.all_of):
        return False
    if requirement.normal_weapon_count and sum(
        state.count(item_name, player) for item_name in starting_weapon_item_names
    ) < requirement.normal_weapon_count:
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
    if requirement.combat_any_of and not any(
        any(
            all(state.has(item_name, player) for item_name in alternative)
            for alternative in combat_capability_alternatives(capability)
        )
        for capability in requirement.combat_any_of
    ):
        return False
    return all(requirement_satisfied(child, state, player) for child in requirement.all_requirements)


def required_item_names(requirement: LocationRequirement) -> frozenset[str]:
    """Return direct and conjunctive combat items to exclude from own ruled location."""
    names = set(_requirement_item_names(requirement))
    for child in requirement.all_requirements:
        names.update(required_item_names(child))
    return frozenset(names)
