"""Campaign equipment policy and planning state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from BaseClasses import ItemClassification

from .combat_rating import (
    ALL_MOD_NAMES,
    ITEM_CONTRIBUTIONS,
    SUPPORT_RUNE_NAMES,
    WEAPON_NAMES,
)
from .generated_content import CAMPAIGN_STAGES
from .items import (
    SPECIAL_WEAPON_POOL_COUNTS,
    item_data_table,
    suit_perk_item_names,
)
from .logic import MOD_BASE_WEAPON_REQUIREMENTS
from .player_strings_generated import text as player_text

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}


FULL_LENGTH_MIN_MISSIONS = 9

CORE_EQUIPMENT = ("Frag Grenade", "Progressive Blood Punch", "Flame Belch", "Ice Bomb")

NORMAL_RUNES_ORDERED = (
    "Savagery",
    "Seek and Destroy",
    "Blood Fueled",
    "Air Control",
    "Dazed and Confused",
    "Saving Throw",
    "Chrono Strike",
    "Equipment Fiend",
    "Punch and Reave",
)

SUPPORT_RUNES_ORDERED = tuple(sorted(SUPPORT_RUNE_NAMES))

PRIMARY_BASE_MODS = (
    "Sticky Bombs",
    "Precision Bolt",
    "Microwave Beam",
    "Remote Detonate",
    "Arbalest",
    "Energy Shield",
)
SECONDARY_MODS = (
    "Full Auto",
    "Micro Missiles",
    "Heat Blast",
    "Lock-on Burst",
    "Destroyer Blade",
    "Mobile Turret",
)
ALL_MODS_ORDERED = PRIMARY_BASE_MODS + SECONDARY_MODS

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


ITEM_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    **{f"{mod} Mastery": (weapon, mod) for mod, weapon in MOD_BASE_WEAPON_REQUIREMENTS.items()},
    "Meat Hook": ("Super Shotgun",),
    "Faster Dash Recharge": ("Dash",),
    **{mod: (weapon,) for mod, weapon in MOD_BASE_WEAPON_REQUIREMENTS.items() if mod != "Meat Hook"},
}
ITEM_DEPENDENCIES.update(
    {
        name: tuple(dict.fromkeys(dep for _, _, deps in contributions for dep in deps))
        for name, contributions in ITEM_CONTRIBUTIONS.items()
        if name in suit_perk_item_names
    }
)


COMBAT_BASELINE_NAMES = frozenset(WEAPON_NAMES) | frozenset(ALL_MOD_NAMES)


HARD_MOD_BY_STAGE: dict[str, tuple[str, ...]] = {
    "e3m3_maykr": ("Precision Bolt",),
    "e4m3_mcity": ("Microwave Beam",),
}

_CAPACITY_STATS = ("Health", "Armor", "Ammo")
_CAPACITY_MAX_STAGES = 4


class FastState:
    """Minimal CollectionState-compatible state used by planner/solver."""

    __slots__ = ("player", "prog_items")

    def __init__(self, items=None, player=1):
        self.prog_items = Counter(items or ())
        self.player = player

    @classmethod
    def from_counts(cls, counts: Mapping[str, int], player: int = 1) -> FastState:
        state = cls(player=player)
        state.prog_items = Counter({name: qty for name, qty in counts.items() if qty})
        return state

    def count(self, item_name, player):
        return self.prog_items[item_name] + (
            self.prog_items["Progressive Blood Punch"] if item_name == "Blood Punch" else 0
        )

    def has(self, item_name, player):
        return self.count(item_name, player) > 0

    def copy(self):
        st = FastState(player=self.player)
        st.prog_items = Counter(self.prog_items)
        return st

    def collect(self, item_name):
        self.prog_items[item_name] += 1


def _item_is_progression(name: str) -> bool:
    data = item_data_table.get(name)
    return bool(data is not None and data.classification & ItemClassification.progression)


def _option_value(options, attribute: str, default: int = 0) -> int:
    """Read an option value, tolerating lightweight option mocks."""
    option = getattr(options, attribute, None)
    return int(getattr(option, "value", default))


class PoolConfigurationError(ValueError):
    pass


def is_compact_campaign(active_normal_ids: Sequence[str]) -> bool:
    return len(active_normal_ids) < FULL_LENGTH_MIN_MISSIONS


def mastery_resource_family_count(normal_mission_count: int) -> int:
    if normal_mission_count <= 3:
        return 2
    if normal_mission_count <= 5:
        return 3
    if normal_mission_count <= 8:
        return 5
    return 13


def special_weapon_pool_count(special_name: str, *, use_dlc: bool, n_normals: int) -> int:
    """Special-weapon multiplicities for full and compact campaigns."""
    if use_dlc and special_name.startswith("Progressive"):
        if n_normals >= FULL_LENGTH_MIN_MISSIONS:
            return SPECIAL_WEAPON_POOL_COUNTS[special_name]

        return 2 if special_name == "Progressive Special Weapon" else 1
    return SPECIAL_WEAPON_POOL_COUNTS.get(special_name, 1)


def _deplete_starting_pool(counts, requested):
    for name, quantity in requested.items():
        if quantity > counts.get(name, 0):
            raise PoolConfigurationError(
                player_text(
                    "apworld.errors",
                    "starting_pool_copies",
                    item=name,
                    quantity=quantity,
                    available=counts.get(name, 0),
                )
            )
        counts[name] -= quantity
