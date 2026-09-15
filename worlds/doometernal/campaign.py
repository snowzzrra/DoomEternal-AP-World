"""Seed-time unified campaign decisions, active content filtering, and structural CollectionState rules."""
from .generated_content import CAMPAIGN_STAGES
from .logic import goal_endpoint_event_name, mission_clear_event_name

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}
STAGE_BY_NAME = {stage["name"]: stage for stage in CAMPAIGN_STAGES}
REGION_STAGE = {region: stage["id"] for stage in CAMPAIGN_STAGES for region in stage["regions"]}

BASE_GATE_STAGE_IDS = (
    "e1m2_war",
    "e1m3_cult",
    "e2m1_nest",
    "e2m2_base",
    "e2m3_core",
    "e3m1_slayer",
)

STAGE_SLAYER_GATE_KEYS = {
    "e1m2_war": "Slayer Gate Key Exultia",
    "e1m3_cult": "Slayer Gate Key Cultist Base",
    "e2m1_nest": "Slayer Gate Key Super Gore Nest",
    "e2m2_base": "Slayer Gate Key ARC Complex",
    "e2m3_core": "Slayer Gate Key Mars Core",
    "e3m1_slayer": "Slayer Gate Key Taras Nabad",
    "e4m1_rig": "Slayer Gate Key UAC Atlantica Facility",
    "e4m3_mcity": "Slayer Gate Key The Holt",
}

FORTRESS_NON_CONSUMER_LOCATIONS = frozenset({
    "Fortress of Doom - Fortress of Doom Codex Entry",
    "Fortress of Doom - Flame Belch",
    "Fortress of Doom - Ice Bomb",
    "Fortress of Doom - Sentinel Crystal - Bridge Story Pickup",
    "Fortress of Doom - Praetor Suit Token - Story Suit Tutorial",
    "Fortress of Doom - Ballista",
})
FORTRESS_BOOTSTRAP_LOCATIONS = FORTRESS_NON_CONSUMER_LOCATIONS

FORTRESS_SPEND_GROUPS = (
    {
        "id": "SG_LOWER_EAST",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Crystal - Battery Room Lower East",),
    },
    {
        "id": "SG_LOWER_WEST",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Crystal - Battery Room Lower West",),
    },
    {
        "id": "SG_UPPER_EAST_MODBOT",
        "cost": 2,
        "locations": ("Fortress of Doom - Modbot - Battery Room Upper East",),
    },
    {
        "id": "SG_UPPER_WEST_MODBOT",
        "cost": 2,
        "locations": ("Fortress of Doom - Modbot - Battery Room Upper West",),
    },
    {
        "id": "SG_UPPER_EAST_PRAETOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Battery Room Upper East",),
    },
    {
        "id": "SG_UPPER_WEST_PRAETOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Battery Room Upper West",),
    },
    {
        "id": "SG_ELEVATOR_EAST",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Elevator Room East",),
    },
    {
        "id": "SG_ELEVATOR_WEST",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Elevator Room West",),
    },
    {
        "id": "SG_UPPER_SPIRE_CHEAT",
        "cost": 2,
        "locations": ("Fortress of Doom - Fully Upgraded Suit Cheat Code",),
    },
    {
        "id": "SG_SENTINEL_ARMOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Armor",),
    },
    {
        "id": "SG_CLASSIC_MARINE",
        "cost": 2,
        "locations": ("Fortress of Doom - Classic Marine Suit",),
    },
    {
        "id": "SG_PRAETOR_AND_RUNES",
        "cost": 2,
        "locations": (
            "Fortress of Doom - Praetor Suit",
            "Fortress of Doom - All Runes Cheat Code",
        ),
    },
)
SPEND_GROUP_BY_ID = {sg["id"]: sg for sg in FORTRESS_SPEND_GROUPS}

ORDERED_MASTERY_CHALLENGES = (
    ("Sticky Bombs", "Sticky Bombs - Weapon Mastery Challenge"),
    ("Precision Bolt", "Precision Bolt - Weapon Mastery Challenge"),
    ("Heat Blast", "Heat Blast - Weapon Mastery Challenge"),
    ("Remote Detonate", "Remote Detonate - Weapon Mastery Challenge"),
    ("Arbalest", "Arbalest - Weapon Mastery Challenge"),
    ("Energy Shield", "Energy Shield - Weapon Mastery Challenge"),
    ("Full Auto", "Full Auto - Weapon Mastery Challenge"),
    ("Micro Missiles", "Micro Missiles - Weapon Mastery Challenge"),
    ("Microwave Beam", "Microwave Beam - Weapon Mastery Challenge"),
    ("Lock-on Burst", "Lock-on Burst - Weapon Mastery Challenge"),
    ("Meat Hook", "Meat Hook - Weapon Mastery Challenge"),
    ("Destroyer Blade", "Destroyer Blade - Weapon Mastery Challenge"),
    ("Mobile Turret", "Mobile Turret - Weapon Mastery Challenge"),
)


def completion_event(stage_id):
    stage = STAGE_BY_ID[stage_id]
    return (goal_endpoint_event_name("Kill the Dark Lord") if stage["kind"] == "boss"
            else mission_clear_event_name(stage["name"]))


def get_short_world_scaling(
    active_normal_stage_ids: list[str],
    mission_location_count: int,
    mode: str,
    include_weapon_masteries: bool = True,
):
    n = len(active_normal_stage_ids)
    if n <= 3:
        if mission_location_count <= 28:
            active_sg = FORTRESS_SPEND_GROUPS[:1]
            active_masteries = 0
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        elif mission_location_count <= 36:
            active_sg = FORTRESS_SPEND_GROUPS[:2]
            active_masteries = 1
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        elif mission_location_count <= 50:
            active_sg = FORTRESS_SPEND_GROUPS[:3]
            active_masteries = 2
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        else:
            active_sg = FORTRESS_SPEND_GROUPS[:4]
            active_masteries = 2
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
    elif n <= 5:
        active_sg = FORTRESS_SPEND_GROUPS[:4]
        active_masteries = 3
        battery_surplus = 1
    elif n <= 8:
        active_sg = FORTRESS_SPEND_GROUPS[:8]
        active_masteries = 5
        battery_surplus = 1
    else:
        active_sg = FORTRESS_SPEND_GROUPS  # all 12
        active_masteries = 13
        battery_surplus = 1

    if not include_weapon_masteries:
        active_masteries = 0

    return active_sg, active_masteries, battery_surplus


def select_active_normal_missions(candidate_ids, requested_count, forced_ids, rng):
    candidates = sorted(candidate_ids)
    effective_count = len(candidates) if requested_count == "all" or requested_count == 0 else min(int(requested_count), len(candidates))
    effective_count = max(3, effective_count)
    if forced_ids:
        effective_count = max(effective_count, len(forced_ids))
    selected = sorted(forced_ids)
    rem = effective_count - len(selected)
    if rem > 0:
        pool = sorted(set(candidates) - set(forced_ids))
        selected.extend(rng.sample(pool, rem))
    return sorted(selected)


def make_plan(options, rng):
    pool_name = options.mission_pool.current_option_name
    goal_name = options.goal.current_option_name
    order_mode = options.mission_order.value  # 0: Vanilla, 1: RMO, 2: MAI

    # 1. Candidate resolution
    if pool_name == "Base":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["source"] == "base" and s["kind"] == "mission"]
        dark_lord_candidate = False
    elif pool_name == "Full Saga":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["kind"] == "mission"]
        dark_lord_candidate = True
    elif pool_name == "DLC Only":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["source"] in ("tag1", "tag2") and s["kind"] == "mission"]
        dark_lord_candidate = True
    elif pool_name == "Custom":
        custom_vals = set(options.custom_missions.value)
        candidate_normal_ids = [
            s["id"] for s in CAMPAIGN_STAGES
            if s["kind"] == "mission" and (s["name"] in custom_vals or s["id"] in custom_vals)
        ]
        dark_lord_candidate = bool(options.custom_dark_lord.value)
        if len(candidate_normal_ids) < 3:
            raise ValueError("DOOM Eternal Custom Mission Pool requires at least 3 normal missions.")
    else:
        raise ValueError(f"Unknown Mission Pool: {pool_name}")

    # 2. Auto-promote Use DLC Content if DLC missions or Dark Lord are present
    has_dlc = any(STAGE_BY_ID[s]["source"] in ("tag1", "tag2") for s in candidate_normal_ids) or dark_lord_candidate
    if has_dlc and not options.use_dlc_content.value:
        options.use_dlc_content.value = 1

    # 3. Goal normalization
    goal_forced_active = False
    forced_normal_ids = set()
    goal_stage = None

    if goal_name == "Kill the Icon of Sin":
        goal_stage = "e3m4_boss"
        if "e3m4_boss" not in candidate_normal_ids:
            candidate_normal_ids.append("e3m4_boss")
            candidate_normal_ids.sort()
            goal_forced_active = True
        forced_normal_ids.add("e3m4_boss")
    elif goal_name == "Kill the Dark Lord":
        goal_stage = "e5m4_boss"
        if not dark_lord_candidate:
            dark_lord_candidate = True
            goal_forced_active = True
    elif goal_name == "Acquire the Unmaykr":
        if pool_name == "DLC Only":
            raise ValueError("DOOM Eternal Goal 'Acquire the Unmaykr' requires Base Slayer Gates and cannot be generated with DLC Only.")
        for gate_id in BASE_GATE_STAGE_IDS:
            if gate_id not in candidate_normal_ids:
                candidate_normal_ids.append(gate_id)
                candidate_normal_ids.sort()
                goal_forced_active = True
            forced_normal_ids.add(gate_id)
    elif goal_name == "Complete the Full Saga":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["kind"] == "mission"]
        dark_lord_candidate = True
        final = options.full_saga_final_boss.value
        if order_mode == 0:
            final = 2
        elif final == 0:
            final = rng.choice((1, 2))
        goal_stage = "e3m4_boss" if final == 1 else "e5m4_boss"

    # 4. Mission Count & Active Normal Missions selection
    raw_count = options.mission_count.value
    if order_mode == 0:
        # Vanilla Order ignores count and uses all candidate missions in chronological order
        requested_count = "all" if raw_count == 0 else raw_count
        effective_count = len(candidate_normal_ids)
        active_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["id"] in candidate_normal_ids]
    else:
        if goal_name == "Complete the Full Saga":
            requested_count = "all"
            effective_count = len(candidate_normal_ids)
        elif raw_count == 0:
            requested_count = "all"
            effective_count = len(candidate_normal_ids)
        else:
            requested_count = raw_count
            effective_count = min(raw_count, len(candidate_normal_ids))
            effective_count = max(3, effective_count)

        if goal_name == "Acquire the Unmaykr":
            effective_count = max(6, effective_count)

        active_normal_ids = select_active_normal_missions(
            candidate_normal_ids,
            effective_count,
            forced_normal_ids,
            rng,
        )

    dark_lord_active = bool(dark_lord_candidate)
    active_stage_ids = list(active_normal_ids)
    if dark_lord_active:
        active_stage_ids.append("e5m4_boss")

    # 5. Order sequencing & starts
    ordinary = [s for s in active_normal_ids if s != goal_stage]
    if order_mode == 0:
        # Vanilla Order
        sequence = list(active_normal_ids)
        if dark_lord_active and "e5m4_boss" not in sequence:
            sequence.append("e5m4_boss")
        starts = [sequence[0]]
        access = []
        goal_as_item = False
    elif order_mode == 1:
        # Random Mission Order
        rng.shuffle(ordinary)
        if dark_lord_active and "e5m4_boss" != goal_stage:
            ordinary.append("e5m4_boss")
            rng.shuffle(ordinary)
        sequence = ordinary + ([goal_stage] if goal_stage else [])
        starts = [sequence[0]]
        access = []
        goal_as_item = False
    elif order_mode == 2:
        # Mission Access as Items
        rng.shuffle(ordinary)
        if dark_lord_active and "e5m4_boss" != goal_stage:
            ordinary.append("e5m4_boss")
            rng.shuffle(ordinary)
        eff_starts = min(options.starting_missions.value, len(ordinary))
        eff_starts = max(1, eff_starts)
        starts = ordinary[:eff_starts]
        goal_as_item = bool(goal_stage and options.goal_mission_as_item.value)
        access = [s for s in ordinary if s not in starts]
        if goal_as_item and goal_stage:
            access.append(goal_stage)
        sequence = ordinary + ([goal_stage] if goal_stage else [])

    # 6. Bootstrap inventory
    bootstrap_inventory = {}
    if not options.randomize_dash.value and any(key not in {"e1m1_intro", "e1m2_war"} for key in starts):
        bootstrap_inventory["Dash"] = 1

    return {
        "schema": 1,
        "mode": options.mission_order.current_option_name,
        "difficulty": options.campaign_difficulty.value,
        "sequence": sequence,
        "starting_stages": starts,
        "goal_stage": goal_stage,
        "goal_as_item": goal_as_item,
        "bootstrap_inventory": bootstrap_inventory,
        "access_items": {str(STAGE_BY_ID[stage]["access_id"]): stage for stage in access},
        "stages": [dict(STAGE_BY_ID[stage]) for stage in active_stage_ids],
        "stage_ids": active_stage_ids,
        "active_normal_missions": active_normal_ids,
        "active_normal_mission_ids": active_normal_ids,
        "dark_lord_active": dark_lord_active,
        "requested_mission_count": requested_count,
        "effective_mission_count": effective_count,
        "mission_pool": pool_name,
        "goal_forced_active": goal_forced_active,
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
