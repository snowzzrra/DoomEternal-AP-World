from types import SimpleNamespace

import pytest

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


@pytest.mark.parametrize("mission,challenge", [
    ("Cultist Base", "Master of Turrets"),
    ("ARC Complex", "Solitary Confinement"),
    ("Mars Core", "Disarmament"),
])
def test_weakpoint_challenges_and_their_aggregate_require_a_suitable_weapon(mission, challenge):
    child = f"{mission} - Mission Challenge - {challenge}"
    aggregate = f"{mission} - All Mission Challenges Completed"
    rules = build_location_prerequisites({child, aggregate})
    owned = set()
    state = SimpleNamespace(has=lambda name, player: name in owned)
    for kit, expected in (((), False), (("Heavy Cannon",), False),
                          (("Heavy Cannon", "Precision Bolt"), True),
                          (("Ballista",), True), (("Combat Shotgun", "Sticky Bombs"), True)):
        owned.clear()
        owned.update(kit)
        assert requirement_satisfied(rules[child], state, 1) == expected
        assert requirement_satisfied(rules[aggregate], state, 1) == expected


@pytest.mark.parametrize("mod,weapon,species", [
    ("Full Auto", "Combat Shotgun", "pinky"),
    ("Lock-on Burst", "Rocket Launcher", "prowler"),
])
def test_generated_secret_encounter_targets_open_mastery_access(mod, weapon, species):
    from ..enemy_options import SPECIES_IDS, normalize_enemy_options
    from ..native_enemy_plan import build_native_recipes

    options = normalize_enemy_options({"enemy_count_mode": "multiplier", "enemy_count_multiplier": 100,
        "enemy_weights": {value: 100 if value == species else int(value == 'imp') for value in SPECIES_IDS}})
    plan = build_native_recipes(options, {"sequence": ["e3m3_maykr"]}, seed=71605)
    mastery = f"{mod} - Weapon Mastery Challenge"
    secret = "Urdak - Secret Encounter - Statue-Puzzle Upper Door"
    locations = {mastery, secret}
    regions = {"Doom Hunter Base - Station of Redemption"}
    owned, reachable = {weapon, mod}, {secret}
    state = SimpleNamespace(has=lambda name, player: name in owned,
                            can_reach=lambda name, kind, player: kind == "Location" and name in reachable,
                            count=lambda name, player: 3 if name == "Weapon Upgrade Points (3)" else 0)
    original = build_location_prerequisites(locations, active_region_names=regions)[mastery]
    assert not requirement_satisfied(original, state, 1)
    rule = build_location_prerequisites(locations, active_region_names=regions, enemy_plan=plan)[mastery]
    assert requirement_satisfied(rule, state, 1)
    reachable.clear()
    assert not requirement_satisfied(rule, state, 1)
    reachable.add(secret)
    owned.remove(mod)
    assert not requirement_satisfied(rule, state, 1)


def test_mastery_checks_require_points_for_every_active_mod():
    masteries = {"Sticky Bombs - Weapon Mastery Challenge", "Heat Blast - Weapon Mastery Challenge"}
    owned = {"Combat Shotgun", "Sticky Bombs", "Plasma Rifle", "Heat Blast"}
    bundles = 0
    state = SimpleNamespace(has=lambda name, player: name in owned,
                            count=lambda name, player: bundles if name == "Weapon Upgrade Points (3)" else 0)
    rules = build_location_prerequisites(masteries)
    for bundles, expected in ((0, False), (3, False), (5, False), (6, True)):
        assert all(requirement_satisfied(rules[name], state, 1) == expected for name in masteries)
