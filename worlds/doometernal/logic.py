"""Declarative, validated access rules for proven DOOM Eternal checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from BaseClasses import CollectionState

MASTERY_SUFFIX = " - Weapon Mastery Challenge"
MEAT_HOOK_MASTERY_LOCATION = "Meat Hook - Weapon Mastery Challenge"
MEAT_HOOK_VANILLA_SOURCE = "Cultist Base: scripted Super Shotgun/Meat Hook sequence"
MARS_BFG_VANILLA_SOURCE = "Mars Core: mandatory route BFG-9000 grant (inventory declaration 4701)"
NEKRAVOL_CRUCIBLE_VANILLA_SOURCE = "Nekravol: mandatory route Crucible grant (inventory declaration 4137)"
AUDITED_VANILLA_GRANT_SOURCES = {
    MEAT_HOOK_VANILLA_SOURCE: {
        "map": "Cultist Base",
        "grant": "mandatory scripted Super Shotgun/Meat Hook sequence",
    },
    MARS_BFG_VANILLA_SOURCE: {
        "map": "Mars Core",
        "grant": "mandatory route BFG-9000 grant 4701",
    },
    NEKRAVOL_CRUCIBLE_VANILLA_SOURCE: {
        "map": "Nekravol",
        "grant": "mandatory route Crucible grant 4137",
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
    "Mars Core - Mission Challenge - Big Ba-Da Boom": ExternalVanillaPrerequisite(
        kind="route_guaranteed_vanilla_grant",
        capability="BFG-9000",
        source=MARS_BFG_VANILLA_SOURCE,
        ap_pool_representation="randomized_copy_does_not_replace_route_grant",
        rationale="the current route grants vanilla BFG 4701 before the challenge",
    ),
    "Nekravol - Mission Challenge - Die by the Sword": ExternalVanillaPrerequisite(
        kind="route_guaranteed_vanilla_grant",
        capability="Crucible",
        source=NEKRAVOL_CRUCIBLE_VANILLA_SOURCE,
        ap_pool_representation="none",
        rationale="the current route grants vanilla Crucible 4137 before the challenge",
    ),
}


def build_location_prerequisites(location_names: set[str]) -> dict[str, LocationRequirement]:
    mastery_locations = sorted(name for name in location_names if name.endswith(MASTERY_SUFFIX))
    table: dict[str, LocationRequirement] = {
        "Cultist Base - Mission Challenge - Armored Rain": LocationRequirement(all_of=("Flame Belch",)),
        # This aggregate is the conjunction of its three native children. Only
        # Armored Rain currently has a proven mandatory inventory prerequisite.
        "Cultist Base - All Mission Challenges Completed": LocationRequirement(all_of=("Flame Belch",)),
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
        "Doom Hunter Base - Mission Challenge - Fire in the Hole": LocationRequirement(all_of=("Frag Grenade",)),
        "Doom Hunter Base - All Mission Challenges Completed": LocationRequirement(all_of=("Frag Grenade",)),
        "ARC Complex - Mission Challenge - External Combustion": LocationRequirement(all_of=("Plasma Rifle",)),
        "ARC Complex - All Mission Challenges Completed": LocationRequirement(all_of=("Plasma Rifle",)),
        "Taras Nabad - Mission Challenge - Keeping Cool": LocationRequirement(all_of=("Ice Bomb",)),
        "Taras Nabad - All Mission Challenges Completed": LocationRequirement(all_of=("Ice Bomb",)),
        "Nekravol Part II - Mission Challenge - Punched by Blood": LocationRequirement(all_of=("Blood Punch",)),
        "Nekravol Part II - All Mission Challenges Completed": LocationRequirement(all_of=("Blood Punch",)),
        "Urdak - Mission Challenge - Angel of Death": LocationRequirement(
            any_of=(
                ("Heavy Cannon", "Precision Bolt"),
                ("Ballista",),
                ("Sticky Bombs",),
            )
        ),
        "Urdak - All Mission Challenges Completed": LocationRequirement(
            any_of=(
                ("Heavy Cannon", "Precision Bolt"),
                ("Ballista",),
                ("Sticky Bombs",),
            )
        ),
        "Urdak - Mission Complete": LocationRequirement(all_of=("Blood Punch",)),
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
                f"Unknown logic item(s) for {location_name}: {sorted(set(requirement.all_of) - item_names)}"
            )
        if any(not alternative for alternative in requirement.any_of):
            raise ValueError(f"Empty any_of alternative: {location_name}")
        unknown_any = {item for alternative in requirement.any_of for item in alternative if item not in item_names}
        if unknown_any:
            raise ValueError(f"Unknown any_of item(s) for {location_name}: {sorted(unknown_any)}")
        if requirement.battery_currency < 0:
            raise ValueError(f"Negative Battery requirement: {location_name}")
        if requirement.battery_currency and not {"Sentinel Battery", "Sentinel Battery Bundle"}.issubset(item_names):
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
        if not isinstance(record, ExternalVanillaPrerequisite):
            raise ValueError(f"Unknown or unused external prerequisite metadata: {location_name}")
        expected = EXTERNAL_VANILLA_PREREQUISITES.get(location_name)
        if expected is None:
            raise ValueError(f"Unaudited external prerequisite location: {location_name}")
        if record != expected:
            raise ValueError(f"External prerequisite contract drift: {location_name}")
        source_evidence = AUDITED_VANILLA_GRANT_SOURCES.get(record.source)
        if source_evidence is None:
            raise ValueError(f"External prerequisite source is not audited: {record.source}")
        if record.kind == "mandatory_vanilla_grant" and record.capability not in item_names:
            raise ValueError(f"Unknown external capability: {record.capability}")
        if record.kind == "mandatory_vanilla_grant" and record.capability in active_pool_item_names:
            raise ValueError(f"External prerequisite cannot replace active AP item: {record.capability}")
        if location_name in prerequisite_table:
            raise ValueError(f"External prerequisite also has an AP access rule: {location_name}")


def requirement_satisfied(requirement: LocationRequirement, state: CollectionState, player: int) -> bool:
    if not all(state.has(item_name, player) for item_name in requirement.all_of):
        return False
    if (
        requirement.battery_currency
        and (state.count("Sentinel Battery", player) + 2 * state.count("Sentinel Battery Bundle", player))
        < requirement.battery_currency
    ):
        return False
    return not requirement.any_of or any(
        all(state.has(item_name, player) for item_name in alternative) for alternative in requirement.any_of
    )


def required_item_names(requirement: LocationRequirement) -> frozenset[str]:
    """Return every item which must be excluded from its own ruled location."""
    return frozenset(requirement.all_of).union(item for alternative in requirement.any_of for item in alternative)


# Audited checks with no proven mandatory item prerequisite. Keep this explicit
# so future audits do not silently turn absence of evidence into logic.
NO_RULE_PROVEN = frozenset(
    {
        "Cultist Base - Mission Challenge - Pull the Crystal",
        "Cultist Base - Mission Challenge - Master of Turrets",
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
