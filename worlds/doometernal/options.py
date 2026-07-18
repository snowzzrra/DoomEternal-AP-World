from dataclasses import dataclass
from Options import Toggle, DeathLinkMixin, PerGameCommonOptions


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

# Ideas for future options:
# - Hard Mode (no checkpoints within levels, so if you die you have to start the level over)
# - Enemy Randomizer (enemies are shuffled around within each level, there is already a randomizer mod for this, so it should be possible to pull this off)
# - Horde Mode Checks
# - Actually using slayer gates and the "demons killed meter" for something, as they already give some rewards, and the Unmaykr is a perfect candidate for and end goal to the archipelago.
# - Adding to the above, maybe Slayer Gate Keys could be used as a way to gate progress in the game if the above option is checked.
