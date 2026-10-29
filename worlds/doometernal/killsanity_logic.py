from BaseClasses import Region
from Options import OptionError

from .campaign import completion_event, REGION_STAGE
from .items import item_data_table
from .killsanity_plan import build_killsanity_plan
from .locations import DoomEternalLocation, KILL_REWARD_ID_BASE
from .slot_data_contract import MAX_KILL_REWARDS, catalog_tables


def expand_kill_rewards(interval, count, finite_supported_count):
    return [{"threshold": ordinal * interval, "location_id": KILL_REWARD_ID_BASE + ordinal,
             "finite_supported": ordinal <= finite_supported_count} for ordinal in range(1, count + 1)]


def build_kill_rewards(options, finite_sources, *, estimated_kills=None):
    try:
        plan = build_killsanity_plan(options, finite_sources, estimated_kills=estimated_kills)
        count = len(plan["milestones"])
        if count > MAX_KILL_REWARDS:
            raise ValueError(f"Kill Rewards must be Auto or 1..{MAX_KILL_REWARDS}")
        plan["milestones"] = expand_kill_rewards(plan["interval"], count, plan["finite_kills"] // plan["interval"])
        return plan
    except ValueError as error:
        raise OptionError(str(error)) from error


def restore_kill_rewards(kills, catalog):
    sources = catalog_tables(catalog)["finite_sources"]
    return dict(interval=kills.interval, maximum_milestones=kills.count,
        finite_kills=kills.finite_kills, estimated_kills=kills.estimated_kills,
        finite_sources=[{**sources[ref], "map_key": sources[ref]["stage_id"], "count": count}
                        for ref, count in kills.sources],
        milestones=expand_kill_rewards(kills.interval, kills.count, kills.finite_supported_count))


def _source_access(world, row, entrance):
    multiworld, player = world.multiworld, world.player
    if row["map_key"] not in world.campaign_plan["stage_ids"]:
        raise ValueError(f"Killsanity source references an inactive mission: {row['map_key']}")
    items = tuple(row.get("required_items", ()))
    if set(items) - item_data_table.keys():
        raise ValueError(f"Killsanity source references unknown items: {row['source_id']}")
    if "location" in row:
        target = multiworld.get_location(row["location"], player)
        access_region = target.parent_region
    elif "region" in row:
        target = access_region = multiworld.get_region(row["region"], player)
    else:
        event = completion_event(row["map_key"])
        return lambda state: all(state.has(item, player) for item in items) and state.has(event, player)
    if REGION_STAGE.get(access_region.name) != row["map_key"]:
        raise ValueError(f"Killsanity source access belongs to another mission: {row['source_id']}")
    multiworld.register_indirect_condition(access_region, entrance)
    return lambda state: all(state.has(item, player) for item in items) and target.can_reach(state)


def create_killsanity_locations(world):
    plan = world.killsanity_plan
    if not plan["milestones"]:
        return
    multiworld, player = world.multiworld, world.player
    region = Region("Killsanity", player, multiworld)
    multiworld.regions.append(region)
    entrance = multiworld.get_region("Menu", player).connect(region)
    sources = [(row, _source_access(world, row, entrance)) for row in plan["finite_sources"]]
    repeatable = [(completion_event(row["map_key"]), access) for row, access in sources if row["repeatable"]]
    for key in world.campaign_plan['stage_ids']:
        if not any(row['map_key'] == key for row, _ in sources):
            event = completion_event(key)
            repeatable.append((event, lambda state, event=event: state.has(event, player)))
    entrance.access_rule = lambda state: any(access(state) for _, access in sources) or any(
        state.has(event, player) and access(state) for event, access in repeatable)
    for ordinal, row in enumerate(plan["milestones"], 1):
        threshold = row["threshold"]
        location = DoomEternalLocation(player, f"Kill Reward {ordinal:04d}", row["location_id"], region)
        location.display_name = f"Killed {threshold} Enemies"
        if row["finite_supported"]:
            location.access_rule = lambda state, threshold=threshold: sum(
                source["count"] for source, access in sources if access(state)) >= threshold
        else:
            location.item_rule = lambda item: not item.advancement
            location.access_rule = lambda state: any(
                state.has(event, player) and access(state) for event, access in repeatable)
        region.locations.append(location)
