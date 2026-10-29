from collections import Counter

import pytest

from BaseClasses import CollectionState, PlandoItemBlock
from Fill import FillError, distribute_items_restrictive, distribute_planned_blocks
from Options import PlandoItems
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.doometernal import DoomEternalWorld
from worlds.doometernal.campaign import FORTRESS_BOOTSTRAP_LOCATIONS
from worlds.doometernal.logic import (
    MISSION_CLEAR_EVENT_PREFIX, VICTORY_REQUIREMENT_EVENT_PREFIX, goal_endpoint_event_name,
)
from worlds.generic.Rules import exclusion_rules

from . import bases


PREPARATION_OPTIONS = {
    'mission_pool': 'custom',
    'custom_missions': {'Hell on Earth', 'Exultia', 'Cultist Base',
                        'Super Gore Nest', 'Mars Core', 'Final Sin'},
    'mission_order': 'mission_access_as_items', 'starting_missions': 2,
    'campaign_difficulty': 'nightmare', 'enemy_randomizer': True,
    'enemy_preset': 'hells_vanguard', 'randomize_dash': False, 'randomize_chainsaw': False,
}


class TestVanilla(bases.DoomEternalTestBase):
    options = {'mission_order': 'vanilla_order', 'enemy_randomizer': False}


class TestRMO(bases.DoomEternalTestBase):
    options = {'mission_order': 'random_mission_order', 'enemy_randomizer': False}


class TestMAI(bases.DoomEternalTestBase):
    options = {'mission_order': 'mission_access_as_items', 'starting_missions': 2,
               'goal_mission_as_item': True, 'enemy_randomizer': False}


class TestCompactCampaign(bases.DoomEternalTestBase):
    options = {'mission_pool': 'base', 'mission_count': 6,
               'mission_order': 'random_mission_order', 'goal': 'kill_the_icon_of_sin',
               'enemy_randomizer': False}


class TestDLCCampaign(bases.DoomEternalTestBase):
    options = {'mission_pool': 'dlc_only', 'mission_count': 6,
               'mission_order': 'random_mission_order', 'goal': 'kill_the_dark_lord',
               'starting_weapon': 'combat_shotgun', 'start_inventory': bases.DLC_START_INVENTORY,
               'enemy_randomizer': False}

    def world_setup(self, seed=1077):
        self.multiworld = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=seed,
                                          options=self.options)
        self.world = self.multiworld.worlds[self.player]
        # setup_multiworld leaves explicit start inventory for the caller to precollect.
        for name, count in self.world.options.start_inventory.value.items():
            for _ in range(count):
                self.multiworld.push_precollected(self.world.create_item(name))
        call_all(self.multiworld, 'pre_fill')


class TestExtraObjectives(bases.DoomEternalTestBase):
    options = {
        'mission_pool': 'full_saga', 'mission_order': 'vanilla_order',
        'goal': 'kill_the_icon_of_sin', 'enemy_randomizer': False,
        'additional_victory_requirements': {
            'Complete All Included Missions', 'Complete All Slayer Gates',
            'Complete All Escalation Encounters', 'Complete All Secret Encounters',
            'Complete All Mission Challenges', 'Complete All Weapon Mastery Challenges',
            'Acquire the Unmaykr',
        },
    }


def physical_items(multiworld):
    held = [item for world in multiworld.worlds.values() for item in world.get_pre_fill_items()]
    return [item for item in multiworld.get_items() + held if item.code is not None]


def item_counts(items):
    return Counter((item.player, item.name, item.code, item.classification) for item in items)


def filled_item_counts(mw):
    return item_counts(loc.item for loc in mw.get_filled_locations() if loc.address is not None)


def fill(multiworld):
    distribute_items_restrictive(multiworld)
    call_all(multiworld, 'post_fill')
    call_all(multiworld, 'finalize_multiworld')


def place_preparation_item(mw, preparation):
    location = mw.get_location(min(FORTRESS_BOOTSTRAP_LOCATIONS), 1)
    item = next(item for item in mw.itempool if item.name in preparation)
    distribute_planned_blocks(mw, [PlandoItemBlock(
        player=1, from_pool=True, force=True, worlds={1}, items=[item.name],
        resolved_locations=[location], count={'min': 1, 'max': 1, 'target': 1},
    )])
    return location, item


def assert_preparation_available(mw, preparation):
    state = CollectionState(mw)
    state.sweep_for_advancements()
    for name, count in Counter(preparation).items():
        assert state.count(name, 1) >= count


def mission_entrances(mw):
    return [entrance for entrance in mw.get_entrances(1)
            if entrance.name.startswith('Mission Select: ')]


def assert_mission_access(state, item, entrances):
    without_access = state.copy()
    without_access.remove(item)
    blocked = 'Mission Select: ' + item.name.removesuffix(' Access')
    assert blocked in {entrance.name for entrance in entrances}
    for entrance in entrances:
        assert entrance.can_reach(without_access) == (entrance.name != blocked), item.name
    without_access.collect(item, prevent_sweep=True)
    assert all(entrance.can_reach(without_access) for entrance in entrances)


def state_with_filled_items(mw):
    state = CollectionState(mw)
    for location in mw.get_filled_locations():
        if location.address is not None:
            state.collect(location.item, prevent_sweep=True)
    return state


def extra_objectives(mw, goal):
    events = [location for location in mw.get_filled_locations()
              if location.address is None and location is not goal]
    objectives = [location for location in events
                  if location.name.startswith((MISSION_CLEAR_EVENT_PREFIX, VICTORY_REQUIREMENT_EVENT_PREFIX))
                  or location.name in {goal_endpoint_event_name('Acquire the Unmaykr'),
                                       goal_endpoint_event_name('Kill the Dark Lord')}]
    return events, objectives


def assert_objectives_reachable(state, objectives):
    for location in objectives:
        assert location.can_reach(state), location.name
        assert state.has(location.item.name, 1), location.name


def remote_advancement_locations(mw):
    return [location for location in mw.get_filled_locations()
            if location.item.advancement and location.item.player != location.player]


def collect_sphere_items(state, sphere):
    for location in sphere:
        before = state.prog_items[location.player].copy()
        state.collect(location.item, prevent_sweep=True, location=location)
        if location.item.player != location.player:
            assert state.prog_items[location.player] == before


@pytest.mark.parametrize('exclude_all', [False, True], ids=['one-check', 'all-checks'])
def test_excluded_preparation_locations_are_not_filled(exclude_all):
    mw = setup_multiworld(DoomEternalWorld, steps=gen_steps[:-1], seed=230001,
                          options=PREPARATION_OPTIONS)
    before = item_counts(physical_items(mw))
    assert mw.worlds[1].campaign_plan['bootstrap_placed_items']
    excluded = set(FORTRESS_BOOTSTRAP_LOCATIONS)
    if not exclude_all:
        excluded = {min(excluded)}
    exclusion_rules(mw, 1, excluded)
    try:
        call_all(mw, 'pre_fill')
    except FillError as error:
        assert 'excluded locations' in str(error)
    assert all(mw.get_location(name, 1).item is None for name in excluded)
    assert item_counts(physical_items(mw)) == before
    assert len(mw.itempool) + len(mw.worlds[1].get_pre_fill_items()) == len(mw.get_unfilled_locations())


def test_plando_preserves_preparation_and_item_conservation():
    mw = setup_multiworld(DoomEternalWorld, steps=gen_steps[:2], seed=230001,
                          options=PREPARATION_OPTIONS)
    preparation = mw.worlds[1].campaign_plan['bootstrap_placed_items']
    assert preparation
    mw.worlds[1].options.plando_items = PlandoItems.from_any([{
        'item': preparation[0], 'location': min(FORTRESS_BOOTSTRAP_LOCATIONS), 'from_pool': True,
    }])
    for step in gen_steps[2:-1]:
        call_all(mw, step)
    before = item_counts(physical_items(mw))
    location, item = place_preparation_item(mw, preparation)
    call_all(mw, 'pre_fill')
    assert location.item is item
    assert location.locked
    assert item_counts(physical_items(mw)) == before
    assert len(mw.itempool) == len(mw.get_unfilled_locations())
    assert_preparation_available(mw, preparation)
    fill(mw)
    assert location.item is item
    assert filled_item_counts(mw) == before
    assert mw.can_beat_game()


def test_access_items_gate_only_their_missions():
    mw = setup_multiworld(DoomEternalWorld, seed=230001, options=TestMAI.options)
    state = CollectionState(mw)
    items = physical_items(mw)
    for item in items:
        state.collect(item, prevent_sweep=True)
    entrances = mission_entrances(mw)
    access_items = [item for item in items if item.name.endswith(' Access')]
    assert access_items
    assert all(entrance.can_reach(state) for entrance in entrances)
    for item in access_items:
        assert_mission_access(state, item, entrances)


def test_extra_objectives_are_reachable_before_victory():
    mw = setup_multiworld(DoomEternalWorld, seed=230001, options=TestExtraObjectives.options)
    fill(mw)
    state = state_with_filled_items(mw)
    goal = mw.get_location(goal_endpoint_event_name(mw.worlds[1].options.goal.current_option_name), 1)
    events, objectives = extra_objectives(mw, goal)
    assert objectives
    assert not mw.has_beaten_game(state)
    state.sweep_for_advancements(events)
    assert_objectives_reachable(state, objectives)
    assert not mw.has_beaten_game(state)
    assert goal.can_reach(state)
    state.collect(goal.item, prevent_sweep=True, location=goal)
    assert mw.has_beaten_game(state)
    for location in objectives:
        missing_objective = state.copy()
        missing_objective.remove(location.item)
        assert not mw.has_beaten_game(missing_objective), location.name


def test_spheres_reach_goal_without_borrowing_foreign_slot_items():
    mw = setup_multiworld([DoomEternalWorld, DoomEternalWorld], seed=230001,
                          options=[TestCompactCampaign.options, {
                              **TestMAI.options, 'mission_pool': 'base', 'mission_count': 6,
                              'goal': 'kill_the_icon_of_sin',
                          }])
    fill(mw)
    remote = remote_advancement_locations(mw)
    assert remote
    state = CollectionState(mw)
    checked = set()
    for sphere in mw.get_spheres():
        assert sphere, 'Progression stopped before every location was reached'
        assert all(location.can_reach(state) for location in sphere)
        assert checked.isdisjoint(sphere)
        collect_sphere_items(state, sphere)
        checked.update(sphere)
    assert checked == set(mw.get_filled_locations())
    for player in mw.player_ids:
        assert mw.has_beaten_game(state, player)
