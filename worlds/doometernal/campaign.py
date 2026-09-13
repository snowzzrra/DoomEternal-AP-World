"""Seed-time unified campaign decisions and structural CollectionState rules."""
from .generated_content import CAMPAIGN_STAGES
from .logic import goal_endpoint_event_name, mission_clear_event_name

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}
REGION_STAGE = {region: stage["id"] for stage in CAMPAIGN_STAGES for region in stage["regions"]}


def completion_event(stage_id):
    stage = STAGE_BY_ID[stage_id]
    return (goal_endpoint_event_name("Kill the Dark Lord") if stage["kind"] == "boss"
            else mission_clear_event_name(stage["name"]))


def make_plan(options, rng):
    stages = [stage["id"] for stage in CAMPAIGN_STAGES
              if options.include_dlc_missions.value or stage["source"] == "base"]
    mode = options.mission_order.value
    goal_name = options.goal.current_option_name
    goal = {"Kill the Icon of Sin": "e3m4_boss", "Kill the Dark Lord": "e5m4_boss"}.get(goal_name)
    if goal_name == "Complete the Full Saga":
        final = options.full_saga_final_boss.value
        if mode == 0:
            final = 2
        elif final == 0:
            final = rng.choice((1, 2))
        goal = "e3m4_boss" if final == 1 else "e5m4_boss"
    ordinary = [stage for stage in stages if stage != goal]
    if mode != 0:
        rng.shuffle(ordinary)
    starts = ordinary[:options.starting_missions.value if mode == 2 else 1]
    goal_as_item = bool(mode == 2 and goal and options.goal_mission_as_item.value)
    bootstrap_inventory = {}
    if not options.randomize_dash.value and any(key not in {"e1m1_intro", "e1m2_war"} for key in starts):
        bootstrap_inventory["Dash"] = 1
    access = []
    if mode == 2:
        access = [stage for stage in ordinary if stage not in starts]
        if goal_as_item:
            access.append(goal)
    return {
        "schema": 1, "mode": options.mission_order.current_option_name,
        "difficulty": options.campaign_difficulty.value,
        "sequence": ordinary + ([goal] if goal else []), "starting_stages": starts,
        "goal_stage": goal, "goal_as_item": goal_as_item,
        "bootstrap_inventory": bootstrap_inventory,
        "access_items": {str(STAGE_BY_ID[stage]["access_id"]): stage for stage in access},
        "stages": [dict(STAGE_BY_ID[stage]) for stage in stages],
        "hub": {"id": "hub", "map": "game/hub/hub"},
    }


def stage_available(plan, stage_id, state, player):
    if state.has(completion_event(stage_id), player):
        return True
    if stage_id in plan["starting_stages"]:
        return True
    if str(STAGE_BY_ID[stage_id]["access_id"]) in plan["access_items"]:
        return state.has(STAGE_BY_ID[stage_id]["name"] + " Access", player)
    if stage_id == plan["goal_stage"]:
        predecessors = [stage for stage in plan["sequence"] if stage != stage_id]
    else:
        predecessors = plan["sequence"][:plan["sequence"].index(stage_id)]
    return all(state.has(completion_event(stage), player) for stage in predecessors)
