from random import Random
from typing import cast

from BaseClasses import CollectionState, ItemClassification

from ..generated_content import CAMPAIGN_CONNECTIONS, CAMPAIGN_REGIONS, LOCATION_ROWS
from ..items import item_data_table, suit_perk_item_names
from ..logic import (
    NO_RULE_PROVEN,
    build_location_prerequisites,
    combat_capability_alternatives,
    connection_requirement_from_metadata,
    connection_requirement_satisfied,
    required_item_names,
    requirement_satisfied,
    validate_location_prerequisites,
    weapon_coverage_capability,
    weapon_coverage_satisfied,
)
from ..locations import location_data_table
from ..options import (
    DeathLinkMode,
    PraetorSuitUpgradesInPool,
    resolve_praetor_suit_upgrade_count,
)


def test_praetor_option_uses_catalog_range_and_hidden_random_sentinel() -> None:
    maximum = len(suit_perk_item_names)
    assert PraetorSuitUpgradesInPool.range_start == 0
    assert PraetorSuitUpgradesInPool.range_end == maximum
    assert PraetorSuitUpgradesInPool.from_text("random").value == -1
    assert PraetorSuitUpgradesInPool.from_text(str(maximum)).value == maximum


def test_praetor_random_count_is_seeded_middle_biased_and_bounded() -> None:
    maximum = len(suit_perk_item_names)
    first = resolve_praetor_suit_upgrade_count(-1, Random(47), maximum)
    second = resolve_praetor_suit_upgrade_count(-1, Random(47), maximum)
    assert first == second
    assert max(1, maximum // 3) <= first <= min(maximum - 1, (2 * maximum + 2) // 3)
    assert [resolve_praetor_suit_upgrade_count(value, Random(1), maximum) for value in range(maximum + 1)] == list(
        range(maximum + 1)
    )


def test_pool_and_deathlink_contracts() -> None:
    assert item_data_table["Ammo Refill"].classification == ItemClassification.filler
    assert DeathLinkMode(DeathLinkMode.option_hardcore).current_key == "hardcore"
    assert DeathLinkMode(DeathLinkMode.option_extra_lives).current_key == "extra_lives"


def test_generated_topology_and_capability_rules_validate() -> None:
    assert "Fortress of Doom - Seventh Visit" in CAMPAIGN_REGIONS
    table = build_location_prerequisites(set(location_data_table))
    validate_location_prerequisites(table, set(location_data_table), set(item_data_table))
    assert "weak_point" in table["Urdak - Mission Challenge - Angel of Death"].combat_any_of


class FakeState:
    def __init__(self, *items: str, batteries: int = 0, bundles: int = 0) -> None:
        self.items = set(items)
        self.batteries = batteries
        self.bundles = bundles

    def has(self, name: str, player: int) -> bool:
        return name in self.items

    def count(self, name: str, player: int) -> int:
        return {"Sentinel Battery": self.batteries, "Sentinel Battery Bundle": self.bundles}.get(name, 0)


def test_topology_conditions_gate_only_documented_combat_stages() -> None:
    assert len(LOCATION_ROWS) == 369
    by_pair = {(source, destination): condition for source, destination, _, condition in CAMPAIGN_CONNECTIONS}
    assert by_pair[("Hell on Earth - Barges/Approach", "Hell on Earth - Council/Downtown")] == {}
    assert by_pair[("Exultia - Exultia", "Exultia - Hell")] == {}
    assert by_pair[("Cultist Base - Inner/Revenant", "Cultist Base - Prison/Train")] == {
        "soft_capabilities": ("weapon_coverage_2",)
    }
    assert by_pair[("Fortress of Doom - First Visit", "Exultia - Exultia")] == {}
    requirement = connection_requirement_from_metadata(by_pair[("Final Sin - Upper Towers", "Final Sin - Icon")])
    assert not connection_requirement_satisfied(requirement, cast(CollectionState, FakeState()), 1)
    assert by_pair[("Mars Core - Transit", "Mars Core - Surface/Portal")] == {
        "soft_capabilities": ("weapon_coverage_3",)
    }


def test_weapon_coverage_counts_distinct_normal_weapons() -> None:
    coverage_2 = connection_requirement_from_metadata(
        {"soft_capabilities": [weapon_coverage_capability(2)]}
    )
    coverage_3 = connection_requirement_from_metadata(
        {"soft_capabilities": [weapon_coverage_capability(3)]}
    )
    starting_weapon = cast(CollectionState, FakeState("Combat Shotgun"))
    two_weapons = cast(CollectionState, FakeState("Combat Shotgun", "Heavy Cannon"))
    three_weapons = cast(CollectionState, FakeState("Combat Shotgun", "Heavy Cannon", "Plasma Rifle"))

    assert not weapon_coverage_satisfied(starting_weapon, 1, 2)
    assert connection_requirement_satisfied(coverage_2, two_weapons, 1)
    assert not connection_requirement_satisfied(coverage_3, two_weapons, 1)
    assert connection_requirement_satisfied(coverage_3, three_weapons, 1)


def test_stripped_contracts_do_not_invent_weapon_grants_or_meathook_prerequisites() -> None:
    table = build_location_prerequisites(set(location_data_table))
    assert "Meat Hook - Weapon Mastery Challenge" not in table
    assert {
        "Mars Core - Mission Challenge - Big Ba-Da Boom",
        "Nekravol - Mission Challenge - Die by the Sword",
    }.issubset(NO_RULE_PROVEN)
    assert ("Combat Shotgun", "Sticky Bombs") in combat_capability_alternatives("weak_point")


def test_battery_currency_and_minimal_accessibility() -> None:
    battery_rule = build_location_prerequisites(set(location_data_table))[
        "Fortress of Doom - Praetor Suit Token - Battery Room Upper East"
    ]
    assert not requirement_satisfied(battery_rule, cast(CollectionState, FakeState()), 1)
    assert requirement_satisfied(battery_rule, cast(CollectionState, FakeState(batteries=2)), 1)
    assert requirement_satisfied(battery_rule, cast(CollectionState, FakeState(bundles=1)), 1)
    assert not connection_requirement_satisfied(
        connection_requirement_from_metadata({"soft_capabilities": ["weapon_coverage_2"]}), cast(CollectionState, FakeState()), 1
    )
    assert not connection_requirement_satisfied(
        connection_requirement_from_metadata({"soft_capabilities": ["weapon_coverage_2"]}),
        cast(CollectionState, FakeState("Combat Shotgun")),
        1,
    )
    assert connection_requirement_satisfied(
        connection_requirement_from_metadata({"soft_capabilities": ["weapon_coverage_2"]}),
        cast(CollectionState, FakeState("Combat Shotgun", "Heavy Cannon")),
        1,
    )
    assert not required_item_names(
        build_location_prerequisites(set(location_data_table))["Urdak - Mission Challenge - Angel of Death"]
    )
