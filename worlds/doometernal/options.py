from dataclasses import dataclass

from Options import Choice, DeathLinkMixin, PerGameCommonOptions, Toggle


class RandomizeChainsaw(Toggle):
    """
    Randomize the Chainsaw. If false, the Chainsaw will always be found at its
    vanilla location in Hell on Earth.
    """

    display_name = "Randomize Chainsaw"
    default = 0


class RandomizeDash(Toggle):
    """
    Randomize the Dash pickup. Dash is not required by the current PTB logic
    because it is not technically mandatory until Khan Maykr, so enabling this
    option can place it anywhere allowed by that logic.
    """

    display_name = "Randomize Dash"
    default = 0


class RandomizeFirstBattery(Toggle):
    """
    When enabled, the mandatory first Sentinel Battery is shuffled into the
    item pool instead of being locked to its Exultia pickup.
    """

    display_name = "Randomize First Sentinel Battery"
    default = 0


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
    """Choose the weapon you start with. Random selects one eligible weapon when the seed is generated. The selected weapon is removed from the item pool."""

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


@dataclass
class DoomEternalOptions(DeathLinkMixin, PerGameCommonOptions):
    randomize_chainsaw: RandomizeChainsaw
    randomize_dash: RandomizeDash
    randomize_first_battery: RandomizeFirstBattery
    starting_weapon: StartingWeapon
