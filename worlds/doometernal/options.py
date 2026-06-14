from dataclasses import dataclass
from Options import Toggle, Choice, PerGameCommonOptions

class IncludeMasterLevels(Toggle):
    """Include Master Levels as checks in the pool."""
    display_name = "Include Master Levels"

class IncludeDLC(Toggle):
    """Include DLC (The Ancient Gods Part 1 and 2) as checks in the pool."""
    display_name = "Include DLC (The Ancient Gods)"

@dataclass
class DoomEternalOptions(PerGameCommonOptions):
    include_master_levels: IncludeMasterLevels
    include_dlc: IncludeDLC

# Ideas for future options:
# - Hard Mode (no checkpoints within levels, so if you die you have to start the level over)
# - Enemy Randomizer (enemies are shuffled around within each level, there is already a randomizer mod for this, so it should be possible to pull this off)
# - Horde Mode Checks
# - Actually using slayer gates and the "demons killed meter" for something, as they already give some rewards, and the Unmaykr is a perfect candidate for and end goal to the archipelago.
# - Adding to the above, maybe Slayer Gate Keys could be used as a way to gate progress in the game if the above option is checked.

