from functools import partial

from BaseClasses import ItemClassification, Region

from worlds.generic.Rules import add_rule, set_rule

from .campaign import (
    BASE_GATE_STAGE_IDS,
    FORTRESS_NON_CONSUMER_LOCATIONS,
    REGION_STAGE,
    STAGE_BY_ID,
    completion_event,
    stage_available,
)
from .combat_readiness import (
    SPIRIT_BREAKPOINTS,
    is_mission_ready,
    is_spirit_breakpoint_ready,
)
from .generated_content import (
    CAMPAIGN_CONNECTIONS,
)
from .items import (
    DoomEternalItem,
)
from .locations import (
    DoomEternalLocation,
    location_data_table,
    optional_location_enabled,
)
from .logic import (
    CRUCIBLE_CHALLENGE,
    GOAL_ENDPOINT_LOCATIONS,
    MASTERY_SUFFIX,
    connection_requirement,
    crucible_challenge_enabled,
    goal_endpoint_available,
    goal_endpoint_event_name,
    mission_clear_event_name,
    requirement_satisfied,
    victory_requirement_location_event_name,
)
from .planner import ORDERED_MASTERY_CHALLENGES


def create_regions(world) -> None:
    catalog_locations = _catalog_locations(world)
    plan = world.campaign_plan
    active_normal_ids = plan["active_normal_mission_ids"]
    active_stage_ids = set(plan["stage_ids"])

    vanilla_physical_locations = {
        "Hell on Earth - Chainsaw": world.options.randomize_chainsaw.value,
        "Exultia - Dash": world.options.randomize_dash.value,
    }

    active_sg = plan["active_spend_groups"]
    active_masteries_count = plan["active_masteries_count"]
    battery_surplus = plan["battery_surplus"]
    world.active_spend_groups = active_sg
    world.active_masteries_count = active_masteries_count
    world.battery_surplus = battery_surplus

    active_hub_locations = _hub_locations(world, active_normal_ids, active_sg)

    active_mastery_locations = {loc for _, loc in ORDERED_MASTERY_CHALLENGES[:active_masteries_count]}

    hub = _create_region_nodes(world, active_masteries_count, active_stage_ids)
    player, multiworld = world.player, world.multiworld
    _create_catalog_locations(
        world,
        catalog_locations,
        active_hub_locations,
        active_mastery_locations,
        active_stage_ids,
        vanilla_physical_locations,
    )
    if plan.get("fixed_dash_completion_stage") == "e1m2_war":
        region = multiworld.get_region(catalog_locations["Exultia - Dash"].region, player)
        region.add_event("Fixed Dash Acquisition", "Dash", location_type=DoomEternalLocation, item_type=DoomEternalItem)

    _create_completion_events(world, plan, multiworld, player)
    _create_victory_events(world, multiworld, player)
    _create_goal_events(world, plan, multiworld, player)
    regions = _connect_missions(world, hub, plan, multiworld, player)
    ordinary = [key for key in plan["sequence"] if key != plan["goal_stage"]]
    visits = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh")
    for index, visit in enumerate(visits):
        threshold = 0 if index == 0 else plan["fortress_phase_thresholds"][index]
        entrance = hub.connect(regions[f"Fortress of Doom - {visit} Visit"], f"Fortress phase: {visit}")
        entrance.access_rule = (
            lambda state, count=threshold: sum(state.has(completion_event(key), player) for key in ordinary) >= count
        )

    from .killsanity_logic import create_killsanity_locations

    create_killsanity_locations(world)


def _create_region_nodes(world, active_masteries_count, active_stage_ids):
    player, multiworld = world.player, world.multiworld
    menu = Region("Menu", player, multiworld)
    multiworld.regions.append(menu)
    hub = Region("Fortress of Doom", player, multiworld)
    multiworld.regions.append(hub)
    menu.connect(hub, "Campaign: Fortress")

    for visit in ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"):
        multiworld.regions.append(Region(f"Fortress of Doom - {visit} Visit", player, multiworld))

    if active_masteries_count > 0:
        wm_region = Region("Weapon Masteries", player, multiworld)
        multiworld.regions.append(wm_region)
        menu.connect(wm_region, "Menu to Weapon Masteries")

    for stage_id in active_stage_ids:
        stage = STAGE_BY_ID[stage_id]
        for reg_name in stage["regions"]:
            multiworld.regions.append(Region(reg_name, player, multiworld))
    return hub


def _create_catalog_locations(
    world,
    catalog_locations,
    active_hub_locations,
    active_mastery_locations,
    active_stage_ids,
    vanilla_physical_locations,
):
    player, multiworld = world.player, world.multiworld

    for loc_name, loc_data in catalog_locations.items():
        reg_name = loc_data.region
        if not _location_active(
            world,
            loc_name,
            reg_name,
            active_hub_locations,
            active_mastery_locations,
            active_stage_ids,
            vanilla_physical_locations,
        ):
            continue
        region = multiworld.get_region(reg_name, player)
        location = DoomEternalLocation(player, loc_name, loc_data.code, region)
        region.locations.append(location)


def _create_completion_events(world, plan, multiworld, player):
    for s in plan["stages"]:
        if s["kind"] in {"mission", "master"}:
            mission_name = s["name"]
            mission_location = f"{mission_name} - Mission Complete"
            try:
                public_location = multiworld.get_location(mission_location, player)
            except KeyError:
                continue
            region = public_location.parent_region
            event_name = mission_clear_event_name(mission_name)
            event_item = region.add_event(
                event_name,
                event_name,
                rule=lambda state, public_location=public_location: public_location.can_reach(state),
                location_type=DoomEternalLocation,
                item_type=DoomEternalItem,
            )
            event_item.classification = ItemClassification.progression_skip_balancing
            if plan.get("fixed_dash_completion_stage") == s["id"] and s["id"] != "e1m2_war":
                dash = region.add_event(
                    "Fixed Dash Acquisition",
                    "Dash",
                    rule=lambda state, public_location=public_location: public_location.can_reach(state),
                    location_type=DoomEternalLocation,
                    item_type=DoomEternalItem,
                )
                dash.classification = ItemClassification.progression_skip_balancing


def _create_victory_events(world, multiworld, player):
    requirement_location_suffixes = {
        "Complete All Slayer Gates": " - Slayer Gate Complete",
        "Complete All Escalation Encounters": " - Escalation Encounter Wave ",
        "Complete All Secret Encounters": " - Secret Encounter - ",
        "Complete All Mission Challenges": " - All Mission Challenges Completed",
        "Complete All Weapon Mastery Challenges": MASTERY_SUFFIX,
    }
    for location in list(multiworld.get_locations(player)):
        location_name = location.name
        for requirement_name, suffix in requirement_location_suffixes.items():
            if (
                suffix in location_name
                if suffix.endswith(" - ") or suffix.endswith(" ")
                else location_name.endswith(suffix)
            ):
                region = location.parent_region
                event_name = victory_requirement_location_event_name(requirement_name, location_name)
                event_item = region.add_event(
                    event_name,
                    event_name,
                    rule=lambda state, loc=location: loc.can_reach(state),
                    location_type=DoomEternalLocation,
                    item_type=DoomEternalItem,
                )
                event_item.classification = ItemClassification.progression_skip_balancing


def _create_goal_events(world, plan, multiworld, player):
    active_location_names = {loc.name for loc in multiworld.get_locations(player)}
    for endpoint_goal, default_location_name in GOAL_ENDPOINT_LOCATIONS.items():
        endpoint_location_name = default_location_name
        if endpoint_goal == "Complete the Full Saga" and world.options.goal.current_option_name == endpoint_goal:
            endpoint_location_name = GOAL_ENDPOINT_LOCATIONS[
                "Kill the Icon of Sin" if plan["goal_stage"] == "e3m4_boss" else "Kill the Dark Lord"
            ]
        if not goal_endpoint_available(endpoint_goal, active_location_names):
            continue
        goal_location = multiworld.get_location(endpoint_location_name, player)
        goal_region = goal_location.parent_region
        goal_event_name = goal_endpoint_event_name(endpoint_goal)
        goal_event = goal_region.add_event(
            goal_event_name,
            goal_event_name,
            rule=lambda state, goal_location=goal_location: goal_location.can_reach(state),
            location_type=DoomEternalLocation,
            item_type=DoomEternalItem,
        )
        goal_event.classification = ItemClassification.progression_skip_balancing


def _connect_missions(world, hub, plan, multiworld, player):
    regions = {region.name: region for region in multiworld.get_regions(player)}
    for stage_id in [*plan["sequence"], *plan["master_level_stage_ids"]]:
        stage = STAGE_BY_ID[stage_id]
        entrance = hub.connect(regions[stage["entry_region"]], "Mission Select: " + stage["name"])
        entrance.access_rule = lambda state, key=stage_id: stage_available(
            plan, key, state, player
        ) and is_mission_ready(
            state, player, key, world, context="opening" if key == plan.get("opening_stage") else "base"
        )

    _connect_stage_regions(world, regions, plan, player)
    return regions


def _connect_stage_regions(world, regions, plan, player):
    for source_name, destination_name, entrance_name, condition in CAMPAIGN_CONNECTIONS:
        if source_name not in regions or destination_name not in regions:
            continue
        if not _same_stage_connection(source_name, destination_name):
            continue
        entrance = regions[source_name].connect(regions[destination_name], entrance_name)
        requirement = connection_requirement(
            condition,
            randomize_dash=bool(world.options.randomize_dash.value),
        )
        set_rule(entrance, partial(requirement_satisfied, requirement, player=player))
        from .native_enemy_safety import OPENING_REGIONS

        opening = OPENING_REGIONS.get(plan.get("opening_stage"), ())
        if source_name in opening and destination_name not in opening:
            add_rule(entrance, lambda state, key=plan["opening_stage"]: is_mission_ready(state, player, key, world))
        conn_key = (source_name, destination_name)
        if conn_key in SPIRIT_BREAKPOINTS:
            bp_stage_id = SPIRIT_BREAKPOINTS[conn_key]
            add_rule(
                entrance,
                lambda state, s_id=bp_stage_id: is_spirit_breakpoint_ready(state, player, s_id, world),
            )
    return regions


def _catalog_locations(world):
    dlc_enabled = bool(world.options.use_dlc_content.value)
    special_weapon = world.options.special_weapon.current_option_name if dlc_enabled else "The Crucible"
    return {
        name: data
        for name, data in location_data_table.items()
        if (name != CRUCIBLE_CHALLENGE or crucible_challenge_enabled(special_weapon))
        and optional_location_enabled(name, world.options)
    }


def _hub_locations(world, active_normal_ids, active_sg):
    has_unmaykr_check = bool(world.options.include_slayer_gates.value) and set(BASE_GATE_STAGE_IDS).issubset(
        set(active_normal_ids)
    )
    active_fortress_consumer_locs = {loc for sg in active_sg for loc in sg["locations"]}
    return (
        FORTRESS_NON_CONSUMER_LOCATIONS
        | active_fortress_consumer_locs
        | ({"Fortress of Doom - Unmaykr Acquired"} if has_unmaykr_check else set())
    )


def _location_active(
    world,
    loc_name,
    reg_name,
    active_hub_locations,
    active_mastery_locations,
    active_stage_ids,
    vanilla_physical_locations,
):
    if "Fortress of Doom" in reg_name:
        if loc_name not in active_hub_locations:
            return False
    elif reg_name == "Weapon Masteries":
        if loc_name not in active_mastery_locations:
            return False
    else:
        stage_id = REGION_STAGE.get(reg_name)
        if stage_id not in active_stage_ids:
            return False
        if loc_name in vanilla_physical_locations and not vanilla_physical_locations[loc_name]:
            return False
    return True


def _same_stage_connection(source_name, destination_name):
    source_stage = REGION_STAGE.get(source_name)
    if (source_stage is None or source_stage != REGION_STAGE.get(destination_name)) and not (
        source_name == "Menu" and destination_name == "Weapon Masteries"
    ):
        return False
    return True
