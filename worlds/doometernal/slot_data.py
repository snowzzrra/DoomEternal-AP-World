"""Serialize resolved world decisions for the room contract."""

from collections import Counter

from Options import OptionError

from .combat_readiness import (
    _enemy_counter_penalties, get_mission_cr_range, get_mission_effort_per_check,
    get_mission_skull_tier,
)
from .enemy_plan import ENEMY_DRAW_REVISION
from .generated_content import MASTERY_REQUIREMENT_COUNTS
from .items import item_name_to_id
from .killsanity_plan import build_resolved_killsanity
from .logic import effective_victory_requirements, goal_endpoint_event_name
from .native_enemy_plan import AMMO_FODDER, encode_native_recipes
from .options import DoomEternalOptions
from .slot_data_contract import (
    ContractError, StructureError, catalog_digest, catalog_tables, generation_fingerprint, load_slot_catalog,
    placement_digest, recipe_digest, validate_slot_data,
)
from .version import APWORLD_REVISION, BRIDGE_PROTOCOL, MANIFEST_SCHEMA_VERSION, ROOM_CONTRACT_REVISION


REQUIRED_CAPABILITIES = ["slot_data_v7"]


def _campaign(world):
    plan, options = world.campaign_plan, world.options
    locations = {location.name for location in world.multiworld.get_locations(world.player)}
    requirements = effective_victory_requirements(set(options.additional_victory_requirements.value), locations,
        use_dlc_content=bool(options.use_dlc_content.value), include_dlc_missions=True,
        goal=options.goal.current_option_name)
    economy = dict(plan["battery_economy"])
    economy["native_first_battery"] = bool(economy["native_first_battery"])
    return dict(mode=plan["mode"], sequence=list(plan["sequence"]),
        starting_stages=sorted(plan["starting_stages"]),
        unprepared_start_stages=sorted(plan.get("unprepared_start_stages", [])),
        opening_stage=plan.get("opening_stage"), goal_as_item=plan["goal_as_item"],
        active_masteries_count=plan["active_masteries_count"],
        master_level_stage_ids=sorted(plan.get("master_level_stage_ids", [])),
        access_items=sorted(map(int, plan["access_items"])),
        fixed_dash_completion_stage=plan["fixed_dash_completion_stage"],
        goal=dict(kind=options.goal.current_option_name, stage_id=plan["goal_stage"], count=0,
            endpoint_event=goal_endpoint_event_name(options.goal.current_option_name),
            additional_requirements=sorted(requirements)),
        fortress=dict(active_spend_group_ids=sorted(group["id"] for group in plan["active_spend_groups"]),
            phase_thresholds=list(plan["fortress_phase_thresholds"]), battery_economy=economy))


def _starting(world):
    owned = Counter(item.code for item in world.multiworld.precollected_items[world.player])
    return dict(items=sorted([code, count] for code, count in owned.items()),
                weapon_item_id=item_name_to_id[world.starting_weapon_name])


def _runtime(world):
    options = world.options
    names = ("use_dlc_content", "randomize_chainsaw", "randomize_dash", "enhanced_melee_damage",
             "easier_secret_encounters", "reveal_ap_locations_on_automap")
    return dict(difficulty=dict(engine=options.campaign_difficulty.value, death_policy="normal"),
        death_link=dict(enabled=bool(options.death_link.value),
            mode="hardcore" if options.death_link_mode.value else "soft"),
        **{name: bool(getattr(options, name).value) for name in names},
        randomize_first_battery=not bool(world.campaign_plan["battery_economy"]["native_first_battery"]),
        checks={name: bool(getattr(options, name).value) for name in
            ("include_slayer_gates", "include_secret_encounters", "include_weapon_mastery_challenges")},
        special_weapon=options.special_weapon.current_option_name if options.use_dlc_content.value else "The Crucible",
        mastery_requirement_counts=dict(MASTERY_REQUIREMENT_COUNTS[options.mastery_requirements.current_option_name]))


def _renewable_ammo(stage):
    return any(operation.get("reserve") for operation in stage.get("operations", [])) or any(
        recipe["renewable"] and any(body["species"] in AMMO_FODDER for body in recipe["bodies"])
        for recipe in stage.get("recipes", []))


def _stage_profile(world, stage_id):
    plan = world.enemy_plan or {}
    combat = plan.get("combat_costs", {}).get(stage_id, {}).get("campaign", {})
    opening = (None, None)
    if combat.get("opening_waves") or (world.enemy_plan is None
            and stage_id == world.campaign_plan.get("opening_stage")):
        opening = get_mission_cr_range(stage_id, world, opening=True)
    low, high = get_mission_cr_range(stage_id, world)
    return dict(cr_min=low, cr_max=high, opening_cr_min=opening[0], opening_cr_max=opening[1],
        counter_ids=sorted(_enemy_counter_penalties(None, world.player, stage_id, world)),
        opening_counter_ids=sorted(_enemy_counter_penalties(None, world.player, stage_id, world, opening=True)),
        renewable_ammo=bool(_renewable_ammo(plan.get("maps", {}).get(stage_id, {}))),
        native_chainsaw_before_combat=bool(stage_id == "e1m1_intro" and plan.get("revision", 0) >= 13
            and not world.options.randomize_chainsaw.value),
        skulls=get_mission_skull_tier(stage_id, world),
        effort_per_check_milli=round(get_mission_effort_per_check(stage_id, world) * 1000))


def _resolved_blocks(world, catalog):
    active = set(world.campaign_plan["stage_ids"])
    active.update(key for key, row in catalog_tables(catalog)["maps"].items() if row["stage_id"] is None)
    kills = world.killsanity_plan
    return dict(recipes=encode_native_recipes(world.enemy_plan, catalog, active_maps=active,
                    easier_secret_encounters=bool(world.options.easier_secret_encounters.value)),
        stage_profiles={stage: _stage_profile(world, stage) for stage in world.campaign_plan["stage_ids"]},
        killsanity=build_resolved_killsanity(dict(enabled=bool(world.options.killsanity.value),
            interval=world.options.kills_per_check.value, count=kills["maximum_milestones"] or "auto"),
            dict(finite_sources=kills["finite_sources"], estimated_kills=kills["estimated_kills"]), catalog))


def _tracker_options(world):
    options = world.options.as_dict(*DoomEternalOptions.__annotations__)
    options["start_inventory"] = dict(options["start_inventory"])
    options["start_inventory_from_pool"] = dict(options["start_inventory_from_pool"])
    return options


def _placements(world):
    rows = []
    for location in world.multiworld.get_locations(world.player):
        if location.address is None:
            continue
        if location.item is None:
            raise StructureError(f"Room placement is missing an item at {location.name}")
        rows.append([location.address, location.item.code, location.item.player])
    return rows


def build_slot_data(world):
    """Build plain JSON and validate it once before returning it to AP core."""
    try:
        catalog = load_slot_catalog()
        blocks = _resolved_blocks(world, catalog)
        placements = _placements(world)
        data = dict(identity=dict(schema=7,
                algorithm_revision=(world.enemy_plan or {}).get("revision", ENEMY_DRAW_REVISION),
                catalog_digest=catalog_digest(catalog), recipe_digest=recipe_digest(blocks["recipes"])),
            compatibility=dict(apworld_version=APWORLD_REVISION,
                minimum_client_version=APWORLD_REVISION,
                bridge_protocol=BRIDGE_PROTOCOL, manifest_schema_version=MANIFEST_SCHEMA_VERSION,
                mod_contract_revision=ROOM_CONTRACT_REVISION, required_capabilities=list(REQUIRED_CAPABILITIES)),
            campaign=_campaign(world), starting=_starting(world), runtime=_runtime(world), **blocks,
            tracker_options=_tracker_options(world),
            placement_digest=placement_digest(placements))
        data["native_generation_fingerprint"] = generation_fingerprint(data)
        validate_slot_data(data, catalog, placements=placements,
                           supported_capabilities=frozenset(REQUIRED_CAPABILITIES))
        return data
    except ContractError as error:
        raise OptionError(str(error)) from error
