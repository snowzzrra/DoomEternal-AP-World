from dataclasses import dataclass

from Options import Choice, DeathLinkMixin, NamedRange, PerGameCommonOptions, Toggle

from .items import suit_perk_item_names


class RandomizeChainsaw(Toggle):
    """
    Randomize the Chainsaw. If false, the Chainsaw will always be found at its
    vanilla location in Hell on Earth.
    """

    display_name = "Randomize Chainsaw"
    default = 0


class RandomizeDash(Toggle):
    """Shuffle the Dash pickup into the item pool."""

    display_name = "Randomize Dash"
    default = 0


class RandomizeFirstBattery(Toggle):
    """
    When enabled, the mandatory first Sentinel Battery is shuffled into the
    item pool instead of being locked to its Exultia pickup.
    """

    display_name = "Randomize First Sentinel Battery"
    default = 0


class StartWithAutomap(Toggle):
    """Start with the Automap available."""

    display_name = "Start With Automap"
    default = 0


class DeathLinkMode(Choice):
    """Select DeathLink behavior for this slot. Soft is the safe default and dispatches each received DeathLink once; Hardcore retries until confirmed."""

    display_name = "DeathLink Mode"
    option_soft = 0
    option_hardcore = 1
    default = option_soft


# Keep existing public values stable; new weapons append at next value.
_STARTING_WEAPON_OPTION_NAMES = {
    1: "Heavy Cannon",
    2: "Plasma Rifle",
    3: "Rocket Launcher",
    4: "Ballista",
    5: "Chaingun",
    6: "Combat Shotgun",
    7: "Super Shotgun",
}


class StartingWeapon(Choice):
    """Choose the weapon you start with. Random selects one eligible weapon when the seed is generated. That weapon belongs to your starting inventory."""

    display_name = "Starting Weapon"
    option_random_weapon = 0
    locals().update({
        f"option_{name.lower().replace(' ', '_').replace('-', '_')}": index
        for index, name in _STARTING_WEAPON_OPTION_NAMES.items()
    })
    default = 6

    @classmethod
    def from_text(cls, text: str):
        # Choice normally resolves "random" before generation using global RNG.
        # Preserve it as this option's seeded random mode instead.
        if text.lower() == "random":
            return cls(cls.option_random_weapon)
        return super().from_text(text)

    @classmethod
    def get_option_name(cls, value: int) -> str:
        return "Random" if value == cls.option_random_weapon else super().get_option_name(value)

    @property
    def selected_weapon_name(self) -> str | None:
        return _STARTING_WEAPON_OPTION_NAMES.get(self.value)


class PraetorSuitUpgradesInPool(NamedRange):
    """Number of individual Praetor Suit upgrades placed in the item pool.

    ``Random`` is resolved from the seeded world RNG. Its bounded, middle-biased
    range avoids both empty and nearly-complete upgrade sets while explicit
    values remain available across the full catalog range.
    """

    display_name = "Praetor Suit Upgrades in Pool"
    range_start = 0
    range_end = len(suit_perk_item_names)
    default = 6
    special_range_names = {"random": -1}

    @classmethod
    def get_option_name(cls, value: int) -> str:
        if value == cls.special_range_names["random"]:
            return "Random"
        return super().get_option_name(value)


def resolve_praetor_suit_upgrade_count(option_value: int, rng, maximum: int = len(suit_perk_item_names)) -> int:
    if option_value >= 0:
        if option_value > maximum:
            raise ValueError(f"Praetor Suit upgrade count exceeds catalog maximum {maximum}")
        return option_value
    if option_value != PraetorSuitUpgradesInPool.special_range_names["random"]:
        raise ValueError(f"Unknown Praetor Suit upgrade count: {option_value}")
    lower = max(1, maximum // 3)
    upper = min(maximum - 1, (2 * maximum + 2) // 3)
    candidates = list(range(lower, upper + 1))
    weights = [maximum + 1 - abs(2 * value - maximum) for value in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


@dataclass
class DoomEternalOptions(DeathLinkMixin, PerGameCommonOptions):
    randomize_chainsaw: RandomizeChainsaw
    randomize_dash: RandomizeDash
    randomize_first_battery: RandomizeFirstBattery
    start_with_automap: StartWithAutomap
    death_link_mode: DeathLinkMode
    starting_weapon: StartingWeapon
    praetor_suit_upgrades_in_pool: PraetorSuitUpgradesInPool
