from functools import partial

from BaseClasses import ItemClassification, LocationProgressType

from worlds.generic.Rules import add_item_rule, forbid_item, set_rule

from .campaign import (
    STAGE_BY_ID,
    completion_event,
)
from .items import (
    item_data_table,
)
from .logic import (
    FORTRESS_BATTERY_CONSUMER_LOCATIONS,
    MASTERY_SUFFIX,
    build_location_prerequisites,
    effective_victory_requirements,
    goal_endpoint_event_name,
    required_item_names,
    requirement_satisfied,
    validate_location_prerequisites,
    victory_requirement_location_event_name,
)


def set_rules(world) -> None:
    active_location_names = {
        location.name for location in world.multiworld.get_locations(world.player) if location.address is not None
    }
    active_battery_cost = sum(group["cost"] for group in world.active_spend_groups)

    prerequisite_table = build_location_prerequisites(
        active_location_names,
        active_region_names={region.name for region in world.multiworld.get_regions(world.player)},
        randomize_chainsaw=bool(world.options.randomize_chainsaw.value),
        randomize_dash=bool(world.options.randomize_dash.value),
        special_weapon=(
            "The Crucible"
            if not world.options.use_dlc_content.value
            else world.options.special_weapon.current_option_name
        ),
        active_battery_cost=active_battery_cost,
        logic_difficulty=world.options.logic_difficulty.value,
        active_spend_groups=world.active_spend_groups,
        enemy_plan=world.enemy_plan,
    )
    validate_location_prerequisites(
        prerequisite_table,
        active_location_names,
        set(item_data_table),
    )
    for location_name, requirement in prerequisite_table.items():
        location = world.multiworld.get_location(location_name, world.player)
        set_rule(
            location,
            partial(requirement_satisfied, requirement, player=world.player),
        )
        for item_name in required_item_names(requirement):
            forbid_item(location, item_name, world.player)

    for location_name in FORTRESS_BATTERY_CONSUMER_LOCATIONS & active_location_names:
        location = world.multiworld.get_location(location_name, world.player)
        forbid_item(location, "Sentinel Battery", world.player)
        forbid_item(location, "Sentinel Battery Bundle", world.player)

    _set_victory_rules(world, active_location_names)


def _set_victory_rules(world, active_location_names):
    effective_requirements = effective_victory_requirements(
        set(world.options.additional_victory_requirements.value),
        active_location_names,
        use_dlc_content=bool(world.options.use_dlc_content.value),
        include_dlc_missions=True,
        goal=world.options.goal.current_option_name,
    )
    mission_events = {completion_event(s["id"]) for s in world.campaign_plan["stages"] if s["kind"] != "master"}
    master_events = {completion_event(key) for key in world.campaign_plan["master_level_stage_ids"]}
    master_goal = world.options.goal.current_option_name == "Complete N Master Levels"
    required_events = set() if master_goal else {goal_endpoint_event_name(world.options.goal.current_option_name)}
    if "Complete all Master Levels" in effective_requirements:
        required_events.update(master_events)
    if "Complete All Included Missions" in effective_requirements:
        required_events.update(mission_events)
    if "Acquire the Unmaykr" in effective_requirements:
        required_events.add(goal_endpoint_event_name("Acquire the Unmaykr"))
    required_events.update(_additional_victory_events(world, active_location_names, effective_requirements))

    world.multiworld.completion_condition[world.player] = lambda state: _victory_satisfied(
        world, state, required_events, master_goal, master_events
    )


def _victory_satisfied(world, state, required_events, master_goal, master_events):
    return (
        _goal_stage_available(world, state)
        and (
            not master_goal
            or sum(state.has(event, world.player) for event in master_events) >= world.options.master_level_count.value
        )
        and all(state.has(event, world.player) for event in required_events)
    )


def _additional_victory_events(world, active_location_names, effective_requirements):
    events = set()
    for requirement_name in effective_requirements - {
        "Complete All Included Missions",
        "Acquire the Unmaykr",
        "Complete all Master Levels",
    }:
        suffix = {
            "Complete All Slayer Gates": " - Slayer Gate Complete",
            "Complete All Escalation Encounters": " - Escalation Encounter Wave ",
            "Complete All Secret Encounters": " - Secret Encounter - ",
            "Complete All Mission Challenges": " - All Mission Challenges Completed",
            "Complete All Weapon Mastery Challenges": MASTERY_SUFFIX,
        }[requirement_name]
        candidate_locations = active_location_names
        events.update(
            victory_requirement_location_event_name(requirement_name, location)
            for location in candidate_locations
            if (suffix in location if suffix.endswith(" - ") or suffix.endswith(" ") else location.endswith(suffix))
        )

    return events


def _goal_stage_available(world, state):
    goal_stage = world.campaign_plan["goal_stage"]
    if goal_stage is not None:
        ordinary_complete = all(
            state.has(completion_event(key), world.player)
            for key in world.campaign_plan["sequence"]
            if key != goal_stage
        )
        goal_access = world.campaign_plan["goal_as_item"] and state.has(
            STAGE_BY_ID[goal_stage]["name"] + " Access", world.player
        )
        if not (ordinary_complete or goal_access):
            return False
    return True


def generate_basic(world) -> None:
    if hasattr(world, "_tracker_slot"):
        return
    locations = [world.get_location(name) for group in world.active_spend_groups for name in group["locations"]]
    eligible = [loc for loc in locations if loc.progress_type != LocationProgressType.EXCLUDED]
    count = min(len(eligible), (len(locations) * world.options.useful_fortress_rewards.value + 99) // 100)
    chosen = set(world.random.sample(eligible, count))
    useful = ItemClassification.progression | ItemClassification.useful
    for location in locations:
        if location in chosen:
            add_item_rule(location, lambda item: bool(item.classification & useful))
        elif world.multiworld.players > 1:
            add_item_rule(location, lambda item: item.player != world.player or bool(item.classification & useful))
