from dataclasses import dataclass

from Options import DeathLinkMixin, PerGameCommonOptions, Toggle


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


@dataclass
class DoomEternalOptions(DeathLinkMixin, PerGameCommonOptions):
    randomize_chainsaw: RandomizeChainsaw
    randomize_dash: RandomizeDash
    randomize_first_battery: RandomizeFirstBattery
