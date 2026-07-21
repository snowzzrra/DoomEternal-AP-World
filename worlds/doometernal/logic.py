"""Declarative, validated access rules for proven DOOM Eternal checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


MASTERY_SUFFIX = " - Weapon Mastery Challenge"
MEAT_HOOK_MASTERY_LOCATION = "Meat Hook - Weapon Mastery Challenge"
MEAT_HOOK_VANILLA_SOURCE = (
    "Cultist Base: scripted Super Shotgun/Meat Hook sequence"
)
AUDITED_VANILLA_GRANT_SOURCES = {
    MEAT_HOOK_VANILLA_SOURCE: {
        "map": "Cultist Base",
        "grant": "mandatory scripted Super Shotgun/Meat Hook sequence",
    },
}

# Delivery evidence: these base weapons and their mods are separate progression
# items in the current pool. Combat Shotgun is the starting weapon; Super
# Shotgun/Meat Hook remain vanilla-scripted, so neither gets an invented AP
# weapon requirement.
MOD_BASE_WEAPON_REQUIREMENTS: Mapping[str, str] = {
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
    all_of: tuple[str, ...] = ()
    any_of: tuple[tuple[str, ...], ...] = ()
    battery_currency: int = 0


@dataclass(frozen=True)
class ExternalVanillaPrerequisite:
    kind: str
    capability: str
    source: str
    ap_pool_representation: str
    rationale: str


EXTERNAL_VANILLA_PREREQUISITES: Mapping[str, ExternalVanillaPrerequisite] = {
    MEAT_HOOK_MASTERY_LOCATION: ExternalVanillaPrerequisite(
        kind="mandatory_vanilla_grant",
        capability="Meat Hook",
        source=MEAT_HOOK_VANILLA_SOURCE,
        ap_pool_representation="none",
        rationale="no AP self-lock surface",
    ),
}


def build_location_prerequisites(location_names: set[str]) -> dict[str, LocationRequirement]:
    mastery_locations = sorted(name for name in location_names if name.endswith(MASTERY_SUFFIX))
    table: dict[str, LocationRequirement] = {
        "Cultist Base - Mission Challenge - Armored Rain": LocationRequirement(
            all_of=("Flame Belch",)
        ),
        # This aggregate is the conjunction of its three native children. Only
        # Armored Rain currently has a proven mandatory inventory prerequisite.
        "Cultist Base - All Mission Challenges Completed": LocationRequirement(
            all_of=("Flame Belch",)
        ),
        "Fortress of Doom - Praetor Suit Token 2": LocationRequirement(battery_currency=2),
        "Fortress of Doom - Praetor Suit Token 3": LocationRequirement(battery_currency=3),
        "Fortress of Doom - Weapon Modbot 1": LocationRequirement(battery_currency=5),
        "Fortress of Doom - Weapon Modbot 2": LocationRequirement(battery_currency=7),
        "Fortress of Doom - Sentinel Crystal 2": LocationRequirement(battery_currency=9),
        "Fortress of Doom - Sentinel Crystal 3": LocationRequirement(battery_currency=11),
        "Fortress of Doom - Praetor Suit Token 4": LocationRequirement(battery_currency=12),
        "Fortress of Doom - Praetor Suit Token 5": LocationRequirement(battery_currency=13),
        "Fortress of Doom - All Runes Cheat Code": LocationRequirement(battery_currency=15),
        "Fortress of Doom - Fully Upgraded Suit Cheat Code": LocationRequirement(battery_currency=17),
        "Doom Hunter Base - Mission Challenge - Kill Two with One Grenade": LocationRequirement(
            all_of=("Frag Grenade",)
        ),
        "Doom Hunter Base - All Mission Challenges Completed": LocationRequirement(
            all_of=("Frag Grenade",)
        ),
    }
    for location_name in mastery_locations:
        if location_name in EXTERNAL_VANILLA_PREREQUISITES:
            continue
        mod_name = location_name.removesuffix(MASTERY_SUFFIX)
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        requirements = (base_weapon, mod_name) if base_weapon else (mod_name,)
        table[location_name] = LocationRequirement(all_of=requirements)
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
                f"Unknown logic item(s) for {location_name}: "
                f"{sorted(set(requirement.all_of) - item_names)}"
            )
        if any(not alternative for alternative in requirement.any_of):
            raise ValueError(f"Empty any_of alternative: {location_name}")
        unknown_any = {
            item for alternative in requirement.any_of for item in alternative
            if item not in item_names
        }
        if unknown_any:
            raise ValueError(f"Unknown any_of item(s) for {location_name}: {sorted(unknown_any)}")
        if requirement.battery_currency < 0:
            raise ValueError(f"Negative Battery requirement: {location_name}")
        if requirement.battery_currency and not {
            "Sentinel Battery", "Sentinel Battery Bundle"
        }.issubset(item_names):
            raise ValueError(f"Battery items are absent for {location_name}")


def validate_external_vanilla_prerequisites(
    metadata: Mapping[str, ExternalVanillaPrerequisite],
    prerequisite_table: Mapping[str, LocationRequirement],
    location_names: set[str],
    item_names: set[str],
    active_pool_item_names: set[str],
) -> None:
    for location_name, record in metadata.items():
        if location_name not in location_names:
            raise ValueError(f"Unknown external prerequisite location: {location_name}")
        if location_name != MEAT_HOOK_MASTERY_LOCATION:
            raise ValueError(f"Unaudited external prerequisite location: {location_name}")
        if not isinstance(record, ExternalVanillaPrerequisite):
            raise ValueError(f"Unknown or unused external prerequisite metadata: {location_name}")
        if record != EXTERNAL_VANILLA_PREREQUISITES[location_name]:
            raise ValueError(f"External prerequisite contract drift: {location_name}")
        source_evidence = AUDITED_VANILLA_GRANT_SOURCES.get(record.source)
        if source_evidence != {
            "map": "Cultist Base",
            "grant": "mandatory scripted Super Shotgun/Meat Hook sequence",
        }:
            raise ValueError(f"External prerequisite source is not audited: {record.source}")
        if record.capability not in item_names:
            raise ValueError(f"Unknown external capability: {record.capability}")
        if record.capability in active_pool_item_names:
            raise ValueError(
                f"External prerequisite cannot replace active AP item: {record.capability}"
            )
        if location_name in prerequisite_table:
            raise ValueError(f"External prerequisite also has an AP access rule: {location_name}")


def requirement_satisfied(requirement: LocationRequirement, state, player: int) -> bool:
    if not all(state.has(item_name, player) for item_name in requirement.all_of):
        return False
    if requirement.battery_currency and (
        state.count("Sentinel Battery", player)
        + 2 * state.count("Sentinel Battery Bundle", player)
    ) < requirement.battery_currency:
        return False
    return not requirement.any_of or any(
        all(state.has(item_name, player) for item_name in alternative)
        for alternative in requirement.any_of
    )


# Audited checks with no proven mandatory item prerequisite. Keep this explicit
# so future audits do not silently turn absence of evidence into logic.
NO_RULE_PROVEN = frozenset({
    "Cultist Base - Mission Challenge - Pull the Crystal",
    "Cultist Base - Mission Challenge - Master of Turrets",
    "Doom Hunter Base - Mission Challenge - Find the Album",
    "Doom Hunter Base - Mission Challenge - Map the Area",
})
