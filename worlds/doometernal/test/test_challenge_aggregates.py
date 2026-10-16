from types import SimpleNamespace

from ..logic import build_location_prerequisites, requirement_satisfied


def test_aggregate_without_active_children_requires_same_mission_completion():
    complete = "Urdak - Mission Complete"
    aggregate = "Urdak - All Mission Challenges Completed"
    child = "Urdak - Mission Challenge - Angel of Death"
    reachable, owned = set(), set()
    state = SimpleNamespace(
        can_reach=lambda name, kind, player: kind == "Location" and name in reachable,
        has=lambda name, player: name in owned,
    )
    rule = build_location_prerequisites({complete, aggregate})[aggregate]
    assert not requirement_satisfied(rule, state, 1)
    reachable.add("Mars Core - Mission Complete")
    assert not requirement_satisfied(rule, state, 1)
    reachable.add(complete)
    assert requirement_satisfied(rule, state, 1)
    rule = build_location_prerequisites({complete, aggregate, child})[aggregate]
    assert not requirement_satisfied(rule, state, 1)
    reachable.clear()
    owned.update(("Heavy Cannon", "Precision Bolt"))
    assert requirement_satisfied(rule, state, 1)
