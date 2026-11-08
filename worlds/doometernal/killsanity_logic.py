from BaseClasses import LocationProgressType, Region

from Options import OptionError

from .campaign import completion_event
from .killsanity_plan import build_killsanity_plan, restore_campaign_kill_budget
from .locations import KILL_REWARD_ID_BASE, DoomEternalLocation
from .slot_data_contract import catalog_tables


def expand_kill_rewards(interval, count, finite_supported_count):
    return [
        {
            "threshold": ordinal * interval,
            "location_id": KILL_REWARD_ID_BASE + ordinal,
            "finite_supported": ordinal <= finite_supported_count,
        }
        for ordinal in range(1, count + 1)
    ]


def build_kill_rewards(options, finite_sources, *, estimated_kills=None):
    try:
        return build_killsanity_plan(options, finite_sources, estimated_kills=estimated_kills)
    except ValueError as error:
        raise OptionError(str(error)) from error


def restore_kill_rewards(data, catalog, campaign):
    kills = data.killsanity
    sources = catalog_tables(catalog)["finite_sources"]
    budget = (restore_campaign_kill_budget(campaign, data.recipes, catalog, revision=data.identity.algorithm_revision)
              if kills.count else {"stage_estimates": {}})
    return {
        "interval": kills.interval,
        "maximum_milestones": kills.count,
        "finite_kills": kills.finite_kills,
        "estimated_kills": kills.estimated_kills,
        "stage_estimates": budget["stage_estimates"],
        "finite_sources": [
            {**sources[ref], "map_key": sources[ref]["stage_id"], "count": count} for ref, count in kills.sources
        ],
        "milestones": expand_kill_rewards(kills.interval, kills.count, kills.finite_supported_count),
    }


def create_killsanity_locations(world):
    plan = world.killsanity_plan
    if not plan["milestones"]:
        return
    multiworld, player = world.multiworld, world.player
    region = Region("Killsanity", player, multiworld)
    multiworld.regions.append(region)
    entrance = multiworld.get_region("Menu", player).connect(region)
    stages = [(multiworld.get_location(completion_event(key), player), plan["stage_estimates"].get(key, 0))
              for key in world.campaign_plan["stage_ids"]]
    for target, _ in stages:
        multiworld.register_indirect_condition(target.parent_region, entrance)
    entrance.access_rule = lambda state: any(target.can_reach(state) for target, _ in stages)
    _create_kill_milestones(plan, player, region, stages)


def _create_kill_milestones(plan, player, region, stages):
    logical_budget = sum(count for _, count in stages) * 110
    for ordinal, row in enumerate(plan["milestones"], 1):
        threshold = row["threshold"]
        location = DoomEternalLocation(player, f"Kill Reward {ordinal:04d}", row["location_id"], region)
        location.display_name = f"Killed {threshold} Enemies"
        if threshold * 100 > logical_budget:
            location.progress_type = LocationProgressType.EXCLUDED
            location.item_rule = lambda item: not (item.advancement or item.useful)
            location.access_rule = lambda state: all(target.can_reach(state) for target, _ in stages)
        else:
            if not row["finite_supported"]:
                location.item_rule = lambda item: not item.advancement
            location.access_rule = (
                lambda state, threshold=threshold: sum(count for target, count in stages if target.can_reach(state))
                * 110 >= threshold * 100
            )
        region.locations.append(location)
