"""Declarative, validated access rules for proven DOOM Eternal checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from BaseClasses import CollectionState

from .items import BASE_GATE_KEY_ITEM_NAMES, starting_weapon_item_names

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
}

MISSION_COMPLETION_WEAPON_THRESHOLDS: Mapping[str, int] = {
    "Hell on Earth": 1,
    "Exultia": 2,
    "Cultist Base": 4,
    "Doom Hunter Base": 5,
    "Super Gore Nest": 6,
    "ARC Complex": 7,
    "UAC Atlantica Facility": 6,
    "The Blood Swamps": 6,
    "The Holt": 7,
    "The World Spear": 6,
    "Reclaimed Earth": 6,
    "Immora": 7,
}
DEFAULT_MISSION_COMPLETION_WEAPON_THRESHOLD = 7
MISSION_CLEAR_EVENT_PREFIX = "Internal Mission Clear: "
VICTORY_REQUIREMENT_EVENT_PREFIX = "Internal Victory Requirement: "
GOAL_ENDPOINT_EVENT_PREFIX = "Internal Goal Endpoint: "

BASE_SLAYER_GATES: Mapping[str, tuple[str, str]] = {
    "Exultia - Slayer Gate Complete": ("Exultia - Hell - Ichor Expanse", "Exultia Slayer Gate Key"),
    "Cultist Base - Slayer Gate Complete": ("Cultist Base - Promenade of Culling", "Cultist Base Slayer Gate Key"),
    "Super Gore Nest - Slayer Gate Complete": ("Super Gore Nest - Upper Area - Vermilion Canal", "Super Gore Nest Slayer Gate Key"),
    "ARC Complex - Slayer Gate Complete": ("ARC Complex - Convention Parking", "ARC Complex Slayer Gate Key"),
    "Mars Core - Slayer Gate Complete": ("Mars Core - Hell - Temple of Sin", "Mars Core Slayer Gate Key"),
    "Taras Nabad - Slayer Gate Complete": ("Taras Nabad - City Outskirts", "Taras Nabad Slayer Gate Key"),
}
BASE_GATE_COMPLETE_NAMES = tuple(BASE_SLAYER_GATES)
TAG1_GATE_COMPLETE_NAMES = (
    "UAC Atlantica Facility - Slayer Gate Complete",
    "The Holt - Slayer Gate Complete",
)
BASE_MISSION_NAMES = frozenset({
    "Hell on Earth",
    "Exultia",
    "Cultist Base",
    "Doom Hunter Base",
    "Super Gore Nest",
    "ARC Complex",
    "Mars Core",
    "Sentinel Prime",
    "Taras Nabad",
    "Nekravol",
    "Nekravol Part II",
    "Urdak",
    "Final Sin",
})

DLC_REGION_NAMES = frozenset({
    "UAC Atlantica Facility",
    "The Blood Swamps",
    "The Holt",
    "The World Spear",
    "Reclaimed Earth",
    "Immora",
    "Immora - The Dark Lord",
})
DLC_MISSION_NAMES = frozenset(DLC_REGION_NAMES)
DLC_MISSION_LOCAL_PREFIXES = DLC_MISSION_NAMES | frozenset({"The Dark Lord"})
VICTORY_REQUIREMENT_NAMES = frozenset({
    "Complete All Enabled Missions",
    "Complete All Slayer Gates",
    "Complete All Escalation Encounters",
    "Complete All Secret Encounters",
    "Complete All Mission Challenges",
    "Complete All Weapon Mastery Challenges",
    "Acquire the Unmaykr",
})
GOAL_NAMES = frozenset({
    "Acquire the Unmaykr",
    "Kill the Icon of Sin",
    "Kill the Dark Lord",
    "Complete the Full Saga",
})
GOAL_ENDPOINT_LOCATIONS = {
    "Acquire the Unmaykr": "Fortress of Doom - Unmaykr Acquired",
    "Kill the Icon of Sin": "Final Sin - Mission Complete",
    "Kill the Dark Lord": "The Dark Lord - Defeated",
    "Complete the Full Saga": "The Dark Lord - Defeated",
}

GOAL_IMPLIED_UNMAYKR = frozenset({"Acquire the Unmaykr", "Complete the Full Saga"})

FULL_SAGA_TAG_MISSIONS = (
    "UAC Atlantica Facility",
    "The Blood Swamps",
    "The Holt",
    "The World Spear",
    "Reclaimed Earth",
    "Immora",
)
BASE_CAMPAIGN_MISSIONS = (
    "Hell on Earth",
    "Exultia",
    "Cultist Base",
    "Doom Hunter Base",
    "Super Gore Nest",
    "ARC Complex",
    "Mars Core",
    "Sentinel Prime",
    "Taras Nabad",
    "Nekravol",
    "Nekravol Part II",
    "Urdak",
    "Final Sin",
)
FULL_SAGA_MISSIONS = BASE_CAMPAIGN_MISSIONS + FULL_SAGA_TAG_MISSIONS
BASE_CAMPAIGN_MISSION_COUNT = len(BASE_CAMPAIGN_MISSIONS)
FULL_SAGA_MISSION_COUNT = len(FULL_SAGA_MISSIONS)

FORTRESS_BATTERY_CONSUMER_LOCATIONS = frozenset({
    "Fortress of Doom - Sentinel Crystal - Battery Room Lower East",
    "Fortress of Doom - Sentinel Crystal - Battery Room Lower West",
    "Fortress of Doom - Praetor Suit Token - Battery Room Upper East",
    "Fortress of Doom - Praetor Suit Token - Battery Room Upper West",
    "Fortress of Doom - Modbot - Battery Room Upper West",
    "Fortress of Doom - Modbot - Battery Room Upper East",
    "Fortress of Doom - Praetor Suit Token - Elevator Room West",
    "Fortress of Doom - Praetor Suit Token - Elevator Room East",
    "Fortress of Doom - All Runes Cheat Code",
    "Fortress of Doom - Fully Upgraded Suit Cheat Code",
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
    reachable_any_of: tuple[tuple[str, str], ...] = ()
    battery_currency: int = 0
    normal_weapon_count: int = 0
    custom_rule: Callable[[CollectionState, int], bool] | None = None
    all_requirements: tuple["LocationRequirement", ...] = ()


COMBAT_CAPABILITIES: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "weak_point": (("Heavy Cannon", "Precision Bolt"), ("Ballista",), ("Combat Shotgun", "Sticky Bombs")),
    "flame_belch": (("Flame Belch",),),
    "frag_grenade": (("Frag Grenade",),),
    "plasma_rifle": (("Plasma Rifle",),),
    "ice_bomb": (("Ice Bomb",),),
    "blood_punch": (("Blood Punch",),),
    "mod:Meat Hook": (("Super Shotgun",),),
    "anti_spirit": (("Plasma Rifle", "Microwave Beam"),),
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


def fortress_battery_consumer_cost(*, randomize_first_battery: bool = False) -> int:
    return len(FORTRESS_BATTERY_CONSUMER_LOCATIONS) * 2 + (1 if randomize_first_battery else 0)


def connection_requirement(
    condition: Mapping[str, object],
    *,
    randomize_first_battery: bool = False,
    randomize_dash: bool = False,
) -> LocationRequirement:
    """Convert generated connection metadata into AP access logic."""
    capabilities = condition.get("soft_capabilities", ())
    if not isinstance(capabilities, (list, tuple)):
        raise ValueError("Generated connection soft_capabilities must be a sequence")
    first_battery_gate = "requires_first_battery" in capabilities
    dash_gate = "requires_dash" in capabilities
    combat_capabilities = tuple(
        capability
        for capability in capabilities
        if capability not in {"requires_first_battery", "requires_dash", "requires_dlc_content"}
    )
    all_of: tuple[str, ...] = ("Dash",) if dash_gate and randomize_dash else ()
    return LocationRequirement(
        all_of=all_of,
        battery_currency=1 if first_battery_gate and randomize_first_battery else 0,
        combat_all_of=combat_capabilities,
    )


def dash_available(state: CollectionState, player: int, *, randomize_dash: bool) -> bool:
    """Dash is available via AP item when randomized, or via Exultia clear when vanilla."""
    if randomize_dash:
        return state.has("Dash", player)
    return state.has("Internal Mission Clear: Exultia", player)


def chainsaw_available(state: CollectionState, player: int, *, randomize_chainsaw: bool) -> bool:
    """Chainsaw is available via AP item when randomized, or via Hell on Earth clear when vanilla."""
    if randomize_chainsaw:
        return state.has("Chainsaw", player)
    return state.has("Internal Mission Clear: Hell on Earth", player)


def sentinel_hammer_available(state: CollectionState, player: int, *, special_weapon: str) -> bool:
    """Sentinel Hammer is available at stage >= 2 of Progressive Special Weapon or stage >= 1 of Progressive Sentinel Hammer."""
    if special_weapon == "Progressive Special Weapon":
        return state.count("Progressive Special Weapon", player) >= 2
    if special_weapon == "Progressive Sentinel Hammer":
        return state.count("Progressive Sentinel Hammer", player) >= 1
    return False


def ammo_resource_producer(
    state: CollectionState,
    player: int,
    *,
    randomize_chainsaw: bool,
    special_weapon: str,
) -> bool:
    """Persistent ammo-resource producer capability: Chainsaw or Sentinel Hammer."""
    return chainsaw_available(state, player, randomize_chainsaw=randomize_chainsaw) or sentinel_hammer_available(
        state, player, special_weapon=special_weapon
    )


def tag1_late_game_readiness_satisfied(
    state: CollectionState,
    player: int,
    *,
    randomize_dash: bool,
    randomize_chainsaw: bool,
    special_weapon: str,
) -> bool:
    """TAG1 Late Game readiness: 6 normal weapons, plasma rifle, weak point, blood punch, dash, ammo resource."""
    if sum(state.count(item_name, player) for item_name in starting_weapon_item_names) < 6:
        return False
    if not state.has("Plasma Rifle", player):
        return False
    if not any(
        all(state.has(item_name, player) for item_name in alternative)
        for alternative in COMBAT_CAPABILITIES["weak_point"]
    ):
        return False
    if not state.has("Blood Punch", player):
        return False
    if not dash_available(state, player, randomize_dash=randomize_dash):
        return False
    if not ammo_resource_producer(
        state, player, randomize_chainsaw=randomize_chainsaw, special_weapon=special_weapon
    ):
        return False
    return True


def tag2_very_late_game_readiness_satisfied(
    state: CollectionState,
    player: int,
    *,
    randomize_dash: bool,
    randomize_chainsaw: bool,
    special_weapon: str,
) -> bool:
    """TAG2 Very Late Game readiness: TAG1 core readiness + 7 normal weapons + Super Shotgun + Meat Hook."""
    if not tag1_late_game_readiness_satisfied(
        state,
        player,
        randomize_dash=randomize_dash,
        randomize_chainsaw=randomize_chainsaw,
        special_weapon=special_weapon,
    ):
        return False
    if sum(state.count(item_name, player) for item_name in starting_weapon_item_names) < 7:
        return False
    if not state.has("Super Shotgun", player):
        return False
    if not any(
        all(state.has(item_name, player) for item_name in alternative)
        for alternative in COMBAT_CAPABILITIES["mod:Meat Hook"]
    ):
        return False
    return True


def tag1_from_the_beginning_satisfied(
    state: CollectionState,
    player: int,
    *,
    randomize_dash: bool,
) -> bool:
    """From the Beginning TAG1 readiness: requires Dash capability (vanilla proof: Exultia clear)."""
    return dash_available(state, player, randomize_dash=randomize_dash)


def tag2_from_the_beginning_satisfied(
    state: CollectionState,
    player: int,
    *,
    randomize_dash: bool,
    randomize_chainsaw: bool,
    special_weapon: str,
) -> bool:
    """From the Beginning TAG2 readiness: requires Dash, Super Shotgun / Meat Hook, and ammo resource."""
    if not dash_available(state, player, randomize_dash=randomize_dash):
        return False
    if not state.has("Super Shotgun", player):
        return False
    if not any(
        all(state.has(item_name, player) for item_name in alternative)
        for alternative in COMBAT_CAPABILITIES["mod:Meat Hook"]
    ):
        return False
    if not ammo_resource_producer(
        state, player, randomize_chainsaw=randomize_chainsaw, special_weapon=special_weapon
    ):
        return False
    return True


def tag1_late_game_readiness(
    *,
    randomize_dash: bool = False,
    randomize_chainsaw: bool = False,
    special_weapon: str = "Progressive Special Weapon",
) -> LocationRequirement:
    """Capability-based late-game readiness for entering TAG1."""
    return LocationRequirement(
        normal_weapon_count=6,
        combat_all_of=("plasma_rifle", "weak_point", "blood_punch"),
        custom_rule=lambda state, player: (
            dash_available(state, player, randomize_dash=randomize_dash)
            and ammo_resource_producer(
                state, player, randomize_chainsaw=randomize_chainsaw, special_weapon=special_weapon
            )
        ),
    )


def tag2_very_late_game_readiness(
    *,
    randomize_dash: bool = False,
    randomize_chainsaw: bool = False,
    special_weapon: str = "Progressive Special Weapon",
) -> LocationRequirement:
    """Capability-based very-late-game readiness for entering the TAG2 route."""
    return LocationRequirement(
        all_of=("Super Shotgun",),
        normal_weapon_count=7,
        combat_all_of=("plasma_rifle", "weak_point", "blood_punch", "mod:Meat Hook"),
        custom_rule=lambda state, player: tag1_late_game_readiness_satisfied(
            state,
            player,
            randomize_dash=randomize_dash,
            randomize_chainsaw=randomize_chainsaw,
            special_weapon=special_weapon,
        ),
    )


def tag1_from_the_beginning_readiness(
    *,
    randomize_dash: bool = False,
) -> LocationRequirement:
    """From the Beginning readiness for entering TAG1: requires Dash capability."""
    return LocationRequirement(
        custom_rule=lambda state, player: dash_available(state, player, randomize_dash=randomize_dash),
    )


def tag2_from_the_beginning_readiness(
    *,
    randomize_dash: bool = False,
    randomize_chainsaw: bool = False,
    special_weapon: str = "Progressive Special Weapon",
) -> LocationRequirement:
    """From the Beginning readiness for entering TAG2: requires Dash, SSG/Meat Hook, and ammo resource."""
    return LocationRequirement(
        all_of=("Super Shotgun",),
        combat_all_of=("mod:Meat Hook",),
        custom_rule=lambda state, player: (
            dash_available(state, player, randomize_dash=randomize_dash)
            and ammo_resource_producer(
                state, player, randomize_chainsaw=randomize_chainsaw, special_weapon=special_weapon
            )
        ),
    )


def mission_clear_event_name(mission_name: str) -> str:
    return f"{MISSION_CLEAR_EVENT_PREFIX}{mission_name}"


def goal_endpoint_event_name(goal_name: str) -> str:
    if goal_name not in GOAL_NAMES:
        raise ValueError(f"Unknown goal: {goal_name}")
    return f"{GOAL_ENDPOINT_EVENT_PREFIX}{goal_name}"


def validate_goal_endpoint(
    goal_name: str,
    location_names: set[str],
    *,
    use_dlc_content: bool,
    include_dlc_missions: bool = True,
) -> None:
    if goal_name not in GOAL_NAMES:
        raise ValueError(f"Unknown goal: {goal_name}")
    if goal_name in {"Kill the Dark Lord", "Complete the Full Saga"} and (
        not use_dlc_content or not include_dlc_missions
    ):
        required = "Dark Lord" if goal_name == "Kill the Dark Lord" else "Dark Lord and Full Saga"
        raise ValueError(
            f"DOOM Eternal Goal '{goal_name}' requires DLC content and DLC missions for {required} content"
        )
    endpoint_location = GOAL_ENDPOINT_LOCATIONS.get(goal_name)
    if endpoint_location is not None and endpoint_location not in location_names:
        raise ValueError(
            f"DOOM Eternal Goal '{goal_name}' is unavailable: "
            f"required endpoint location '{endpoint_location}' is not in active catalog"
        )


def goal_endpoint_available(goal_name: str, location_names: set[str]) -> bool:
    endpoint_location = GOAL_ENDPOINT_LOCATIONS.get(goal_name)
    return endpoint_location is not None and endpoint_location in location_names


def victory_requirement_event_name(requirement_name: str) -> str:
    if requirement_name not in VICTORY_REQUIREMENT_NAMES:
        raise ValueError(f"Unknown victory requirement: {requirement_name}")
    return f"{VICTORY_REQUIREMENT_EVENT_PREFIX}{requirement_name}"


def victory_requirement_location_event_name(requirement_name: str, location_name: str) -> str:
    if requirement_name not in VICTORY_REQUIREMENT_NAMES:
        raise ValueError(f"Unknown victory requirement: {requirement_name}")
    return f"{VICTORY_REQUIREMENT_EVENT_PREFIX}{requirement_name}: {location_name}"


def catalog_has_dlc_content(location_names: set[str]) -> bool:
    """Return whether generated location catalog contains TAG mission content."""
    return any(is_dlc_mission_local_name(location_name) for location_name in location_names)


def is_dlc_mission_local_name(name: str) -> bool:
    """Return whether name belongs to TAG mission-local content."""
    return name.split(" - ", 1)[0] in DLC_MISSION_LOCAL_PREFIXES


def active_catalog_location_names(
    location_names: set[str],
    *,
    use_dlc_content: bool,
    include_dlc_missions: bool = True,
) -> set[str]:
    """Filter authored locations by independent DLC content and mission toggles."""
    if not use_dlc_content or not include_dlc_missions:
        return {name for name in location_names if not is_dlc_mission_local_name(name)}
    return set(location_names)


def goal_redundant_requirements(
    goal: str,
    location_names: set[str],
    *,
    use_dlc_content: bool,
    include_dlc_missions: bool = True,
) -> frozenset[str]:
    """Return victory requirements fully implied by the selected Goal."""
    if goal not in GOAL_NAMES:
        raise ValueError(f"Unknown goal: {goal}")
    redundant: set[str] = set()
    if goal in GOAL_IMPLIED_UNMAYKR:
        redundant.add("Acquire the Unmaykr")
        active_locations = active_catalog_location_names(
            location_names,
            use_dlc_content=use_dlc_content,
            include_dlc_missions=include_dlc_missions,
        )
        if (
            set(BASE_GATE_COMPLETE_NAMES) <= active_locations
            and not any(name in active_locations for name in TAG1_GATE_COMPLETE_NAMES)
        ):
            redundant.add("Complete All Slayer Gates")
    if goal == "Complete the Full Saga":
        redundant.add("Complete All Enabled Missions")
    return frozenset(redundant & VICTORY_REQUIREMENT_NAMES)


def validate_full_saga_catalog(
    location_names: set[str],
    *,
    include_dlc_missions: bool = True,
) -> None:
    """Fail closed unless exactly canonical 13/19 mission completions are active."""
    authored = {
        name.removesuffix(" - Mission Complete")
        for name in location_names
        if name.endswith(" - Mission Complete")
    }
    expected = set(FULL_SAGA_MISSIONS if include_dlc_missions else BASE_CAMPAIGN_MISSIONS)
    missing = sorted(expected - authored)
    if missing:
        raise ValueError(
            "DOOM Eternal Goal 'Complete the Full Saga' is unavailable: "
            f"the mission-complete catalog is incomplete ({len(authored)}/{len(expected)} "
            f"missions authored); missing: {', '.join(missing)}"
        )
    unexpected = sorted(authored - expected)
    if unexpected or len(authored) != len(expected):
        raise ValueError(
            "DOOM Eternal Goal 'Complete the Full Saga' is unavailable: "
            f"the mission-complete catalog must contain exactly {len(expected)} missions; "
            f"authored {len(authored)}"
            + (f"; unexpected: {', '.join(unexpected)}" if unexpected else "")
        )


def effective_victory_requirements(
    selected: set[str],
    location_names: set[str],
    *,
    use_dlc_content: bool,
    include_dlc_missions: bool = True,
    goal: str | None = None,
) -> frozenset[str]:
    """Drop requirements with no authored content or fully implied by the Goal."""
    if selected - VICTORY_REQUIREMENT_NAMES:
        raise ValueError(f"Unknown victory requirement(s): {sorted(selected - VICTORY_REQUIREMENT_NAMES)}")
    if goal is not None:
        selected = selected - goal_redundant_requirements(
            goal,
            location_names,
            use_dlc_content=use_dlc_content,
            include_dlc_missions=include_dlc_missions,
        )
    active_locations = active_catalog_location_names(
        location_names,
        use_dlc_content=use_dlc_content,
        include_dlc_missions=include_dlc_missions,
    )
    content_present = {
        "Complete All Enabled Missions": any(name.endswith(" - Mission Complete") for name in active_locations),
        "Complete All Slayer Gates": (
            not use_dlc_content
            or any(" - Slayer Gate Complete" in name for name in active_locations)
            or any(name in active_locations for name in BASE_GATE_COMPLETE_NAMES)
        ),
        "Complete All Escalation Encounters": any(" - Escalation Encounter Wave " in name for name in active_locations),
        "Complete All Secret Encounters": any(" - Secret Encounter - " in name for name in active_locations),
        "Complete All Mission Challenges": any(" - All Mission Challenges Completed" in name for name in active_locations),
        "Complete All Weapon Mastery Challenges": any(name.endswith(MASTERY_SUFFIX) for name in active_locations),
        "Acquire the Unmaykr": "Fortress of Doom - Unmaykr Acquired" in active_locations,
    }
    return frozenset(name for name in selected if content_present[name])


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
    location_names: set[str],
    *,
    randomize_chainsaw: bool = False,
    randomize_dash: bool = False,
    randomize_first_battery: bool = False,
    special_weapon: str = "The Crucible",
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
            all_of=(special_weapon,)
        ),
    }
    gate_complete_keys = {
        "Exultia - Slayer Gate Complete": "Exultia Slayer Gate Key",
        "Cultist Base - Slayer Gate Complete": "Cultist Base Slayer Gate Key",
        "Super Gore Nest - Slayer Gate Complete": "Super Gore Nest Slayer Gate Key",
        "ARC Complex - Slayer Gate Complete": "ARC Complex Slayer Gate Key",
        "Mars Core - Slayer Gate Complete": "Mars Core Slayer Gate Key",
        "Taras Nabad - Slayer Gate Complete": "Taras Nabad Slayer Gate Key",
        "UAC Atlantica Facility - Slayer Gate Complete": "UAC Atlantica Slayer Gate Key",
        "The Holt - Slayer Gate Complete": "The Holt Slayer Gate Key",
    }
    for loc_name, key_name in gate_complete_keys.items():
        if loc_name in location_names:
            table[loc_name] = LocationRequirement(all_of=(key_name,))
    if "Fortress of Doom - Unmaykr Acquired" in location_names:
        table["Fortress of Doom - Unmaykr Acquired"] = LocationRequirement(
            all_of=BASE_GATE_COMPLETE_NAMES,
        )
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
            all_of: tuple[str, ...] = ()
            combat_all_of: tuple[str, ...] = ()
            if mission_name == "Urdak":
                all_of = ("Blood Punch",)
                if randomize_dash:
                    all_of = (*all_of, "Dash")
            normal_weapon_count = MISSION_COMPLETION_WEAPON_THRESHOLDS.get(
                mission_name,
                DEFAULT_MISSION_COMPLETION_WEAPON_THRESHOLD,
            )
            table[location_name] = LocationRequirement(
                all_of=all_of,
                combat_all_of=combat_all_of,
                normal_weapon_count=normal_weapon_count,
            )
    battery_cost = fortress_battery_consumer_cost(randomize_first_battery=randomize_first_battery)
    for location_name in FORTRESS_BATTERY_CONSUMER_LOCATIONS & location_names:
        table[location_name] = LocationRequirement(battery_currency=battery_cost)
    for location_name in mastery_locations:
        mod_name = location_name.removesuffix(MASTERY_SUFFIX)
        base_weapon = MOD_BASE_WEAPON_REQUIREMENTS.get(mod_name)
        if base_weapon is None:
            continue
        reachable_any_of: tuple[tuple[str, str], ...] = ()
        if mod_name == "Full Auto":
            reachable_any_of = (("Region", "Doom Hunter Base - Station of Redemption"),)
        elif mod_name == "Lock-on Burst":
            reachable_any_of = (
                ("Location", "Cultist Base - Slayer Key - Giant Yellow Wall Route"),
                ("Region", "Doom Hunter Base - Station of Redemption"),
            )
        table[location_name] = LocationRequirement(
            combat_all_of=(f"mod:{mod_name}",),
            reachable_any_of=reachable_any_of,
        )
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
    if requirement.reachable_any_of and not any(
        state.can_reach(name, kind, player)
        for kind, name in requirement.reachable_any_of
    ):
        return False
    if requirement.custom_rule is not None and not requirement.custom_rule(state, player):
        return False
    return all(requirement_satisfied(child, state, player) for child in requirement.all_requirements)


def required_item_names(requirement: LocationRequirement) -> frozenset[str]:
    """Return direct and conjunctive combat items to exclude from own ruled location."""
    names = set(_requirement_item_names(requirement))
    for child in requirement.all_requirements:
        names.update(required_item_names(child))
    return frozenset(names)
