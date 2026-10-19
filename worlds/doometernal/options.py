from dataclasses import dataclass

from Options import (
    Accessibility as APAccessibility, Choice, DeathLink as APDeathLink, DeathLinkMixin,
    NamedRange, OptionDict, OptionSet, PerGameCommonOptions, ProgressionBalancing as APProgressionBalancing,
    Range, Toggle,
)

from .generated_content import CAMPAIGN_STAGES
from .enemy_options import SPECIES_IDS
from .items import FILLER_WEIGHT_NAMES, POOL_ITEM_LIMITS, SAFE_TRAP_NAMES, suit_perk_item_names


class _ExactLabelChoice(Choice):
    """Choice whose public labels are part of the APWorld contract."""

    labels: dict[int, str] = {}

    @classmethod
    def get_option_name(cls, value: int) -> str:
        return cls.labels[value]

    @classmethod
    def from_text(cls, text: str):
        normalized = text.strip().casefold()
        for value, label in cls.labels.items():
            if normalized == label.casefold():
                return cls(value)
        return super().from_text(text)


class Accessibility(APAccessibility):
    """Choose how much of your world Archipelago makes reachable.

    Full: Make every item and location reachable.
    Minimal: Make the items needed to finish your goal reachable.
    """


class ProgressionBalancing(APProgressionBalancing):
    """Help players in a multiworld find useful items at a similar pace.

    Disabled: Use the initial item placement.
    Normal: Move important items earlier for players who fall behind.
    Extreme: Give the strongest preference to earlier important items.
    0..99: Higher values give more help to players who fall behind.
    """


class DeathLink(APDeathLink):
    """Share deaths with other players who enable Death Link.

    On: Your deaths affect them, and their deaths affect you.
    Off: Keep deaths within your game.
    """


class UseDLCContent(Toggle):
    """Add The Ancient Gods weapons, Support Runes and enemy types to your campaign.

    On: Include DLC equipment and enemies.
    Off: Use equipment and enemies from the base game."""

    display_name = "Use DLC Content"
    default = 1


class MissionPool(_ExactLabelChoice):
    """Choose which missions can appear in your campaign.

    Base: The 13 base game missions.
    Full Saga: The base game, both DLC campaigns and The Dark Lord.
    DLC Only: The six DLC missions and The Dark Lord.
    Custom: Pick missions with Custom Missions and Custom Dark Lord."""

    display_name = "Mission Pool"
    option_base = 0
    option_full_saga = 1
    option_dlc_only = 2
    option_custom = 3
    default = option_full_saga
    labels = {
        option_base: "Base",
        option_full_saga: "Full Saga",
        option_dlc_only: "DLC Only",
        option_custom: "Custom",
    }


class CustomMissions(OptionSet):
    """Pick the missions you want when Mission Pool is Custom.

    Select a mission to add it to the choices for your campaign. Clear it to leave it out."""

    display_name = "Custom Missions"
    valid_keys = frozenset(stage["name"] for stage in CAMPAIGN_STAGES if stage["kind"] == "mission") | frozenset(
        stage["id"] for stage in CAMPAIGN_STAGES if stage["kind"] == "mission"
    )
    default = frozenset(stage["name"] for stage in CAMPAIGN_STAGES if stage["kind"] == "mission")


class CustomDarkLord(Toggle):
    """Add The Dark Lord to your choices when Mission Pool is Custom.

    On: Include the final battle with Davoth.
    Off: Build the campaign from your Custom Missions selection."""

    display_name = "Custom Dark Lord"
    default = 1


class MissionCount(NamedRange):
    """Choose how many missions to play in Random Mission Order or Mission Access as Items.

    All: Use every mission in your selected pool.
    3..19: Randomly choose that many missions from the pool.
    The Dark Lord is an additional boss stage. Vanilla Order uses the whole selected pool."""

    display_name = "Mission Count"
    range_start = 3
    range_end = 19
    special_range_names = {"all": 0}
    default = 0

    @classmethod
    def get_option_name(cls, value: int) -> str:
        if value == cls.special_range_names["all"]:
            return "All"
        return super().get_option_name(value)


class MissionOrder(_ExactLabelChoice):
    """Choose how you unlock missions.

    Vanilla Order: Play missions in their original order.
    Random Mission Order: Play a shuffled sequence, unlocking the next mission as you progress.
    Mission Access as Items: Find an Access item to unlock each mission.
    You can replay completed missions through the Fortress of Doom."""
    display_name = "Mission Order"
    option_vanilla_order = 0
    option_random_mission_order = 1
    option_mission_access_as_items = 2
    default = option_random_mission_order
    labels = {0: "Vanilla Order", 1: "Random Mission Order", 2: "Mission Access as Items"}


class StartingMissions(Range):
    """Choose how many missions are open at the start in Mission Access as Items.

    1: Start with one mission. 2 or 3: Start with that many choices."""
    display_name = "Starting Missions"
    range_start = 1
    range_end = 3
    default = 1


class FullSagaFinalBoss(_ExactLabelChoice):
    """Choose the last boss for the Complete the Full Saga goal.

    Random: Let the seed choose between the Icon of Sin and Davoth.
    Icon of Sin: End with the Icon of Sin.
    Davoth / The Dark Lord: End with Davoth.
    Vanilla Order ends with Davoth."""
    display_name = "Full Saga Final Boss"
    option_randomized = 0
    option_icon_of_sin = 1
    option_davoth = 2
    default = 0
    labels = {0: "Random", 1: "Icon of Sin", 2: "Davoth / The Dark Lord"}


class GoalMissionAsItem(Toggle):
    """Unlock your goal's boss mission by finding its Access item in Mission Access as Items.

    On: Find the boss mission's Access item to enter it.
    Off: Unlock the boss mission after completing the other missions.
    Extra victory objectives still need to be completed."""
    display_name = "Goal Mission as Item"


class Goal(_ExactLabelChoice):
    """Choose what you need to do to win.

    Acquire the Unmaykr: Beat the six base game Slayer Gates and collect the Unmaykr in the Fortress.
    Kill the Icon of Sin: Defeat the base game's final boss.
    Kill the Dark Lord: Defeat Davoth, the final boss of The Ancient Gods Part Two.
    Complete the Full Saga: Include the base game and both DLC campaigns, with your chosen boss as the finale.
    Victory Requirements adds extra objectives to your goal."""

    display_name = "Goal"
    option_acquire_the_unmaykr = 0
    option_kill_the_icon_of_sin = 1
    option_kill_the_dark_lord = 2
    option_complete_the_full_saga = 3
    default = option_acquire_the_unmaykr
    labels = {
        option_acquire_the_unmaykr: "Acquire the Unmaykr",
        option_kill_the_icon_of_sin: "Kill the Icon of Sin",
        option_kill_the_dark_lord: "Kill the Dark Lord",
        option_complete_the_full_saga: "Complete the Full Saga",
    }


VICTORY_REQUIREMENT_NAMES = frozenset({
    "Complete All Included Missions",
    "Complete All Slayer Gates",
    "Complete All Escalation Encounters",
    "Complete All Secret Encounters",
    "Complete All Mission Challenges",
    "Complete All Weapon Mastery Challenges",
    "Acquire the Unmaykr",
})


class AdditionalVictoryRequirements(OptionSet):
    """Choose extra tasks to finish before you win. An empty selection uses just your Goal.

    Complete All Included Missions: Finish every mission in your campaign.
    Complete All Slayer Gates: Beat every included Slayer Gate.
    Complete All Escalation Encounters: Beat both waves of every included Escalation Encounter.
    Complete All Secret Encounters: Beat every included timed Secret Encounter.
    Complete All Mission Challenges: Finish the Mission Challenges in each included mission.
    Complete All Weapon Mastery Challenges: Finish every included weapon mastery challenge.
    Acquire the Unmaykr: Collect the Unmaykr from its case in the Fortress."""

    display_name = "Additional Victory Requirements"
    valid_keys = VICTORY_REQUIREMENT_NAMES
    def __init__(self, value, random_str=None):
        super().__init__({"Complete All Included Missions" if key == "Complete All Enabled Missions" else key
                         for key in value}, random_str)
    default = frozenset()


class SpecialWeapon(_ExactLabelChoice):
    """Choose which special weapon upgrades you can find.

    Progressive Special Weapon: Unlock the Crucible, then the Sentinel Hammer, then a fully upgraded Hammer.
    Progressive Sentinel Hammer: Unlock the Hammer, then a fully upgraded Hammer.
    The Crucible: Find the Crucible as a single item."""

    display_name = "Special Weapon"
    option_progressive_special_weapon = 0
    option_progressive_sentinel_hammer = 1
    option_the_crucible = 2
    default = option_progressive_special_weapon
    labels = {
        option_progressive_special_weapon: "Progressive Special Weapon",
        option_progressive_sentinel_hammer: "Progressive Sentinel Hammer",
        option_the_crucible: "The Crucible",
    }


class DeathLinkMode(_ExactLabelChoice):
    """Choose how deaths shared through Death Link affect you.

    Soft: Extra Lives or Saving Throw can save you from the shared death.
    Hardcore: A shared death kills you even if you have Extra Lives or Saving Throw."""

    display_name = "DeathLink Mode"
    option_soft = 0
    option_hardcore = 1
    default = option_soft
    labels = {
        option_soft: "Soft",
        option_hardcore: "Hardcore",
    }


class EnhancedMeleeDamage(Toggle):
    """Make normal punches deal more damage, giving you another way to fight at close range.

    On: Use stronger punches. Off: Use normal punch damage."""

    display_name = "Enhanced Melee Damage"
    default = 0


class RandomizeChainsaw(Toggle):
    """Choose where you find the Chainsaw.

    On: Find it among the shuffled Archipelago items.
    Off: Pick it up in its usual place in Hell on Earth."""

    display_name = "Randomize Chainsaw"
    default = 0


class RandomizeDash(Toggle):
    """Choose where you find Dash.

    On: Find it among the shuffled Archipelago items.
    Off: Unlock it during mission progression.
    Playing before you find Dash can require bunny hopping or Ballista boosting."""

    display_name = "Randomize Dash"
    default = 0


class IncludeSlayerGates(Toggle):
    """Earn Archipelago items by completing Slayer Gates and find their keys among shuffled items.

    On: Add Slayer Gate rewards and keys. Off: Use the campaign's other rewards.
    The Acquire the Unmaykr goal requires Slayer Gates."""

    display_name = "Include Slayer Gates"
    default = 1


class IncludeSecretEncounters(Toggle):
    """Earn Archipelago items by completing the optional timed Secret Encounters.

    On: Add a reward for each included Secret Encounter. Off: Use the campaign's other rewards."""

    display_name = "Include Secret Encounters"
    default = 1


class IncludeWeaponMasteryChallenges(Toggle):
    """Earn Archipelago items by completing the 13 weapon mastery challenges.

    On: Add mastery challenge rewards. Off: Use the campaign's other rewards."""

    display_name = "Include Weapon Mastery Challenges"
    default = 1


class EasierSecretEncounters(Toggle):
    """Give yourself 50% more time to finish Secret Encounters.

    On: A 30-second encounter gives you 45 seconds. Off: Use the usual time limits."""

    display_name = "Easier Secret Encounters"
    default = 0


class EnemyRandomizer(Toggle):
    """Randomize the enemies you fight and vary their health, damage and size.

    On: Use randomized enemies. Off: Fight the game's original enemies with their usual stats."""

    display_name = "Enemy Randomizer"
    default = 1


class EnemyPreset(_ExactLabelChoice):
    """Choose a starting setup for enemy randomization. You can adjust its settings afterward.

    UAC Patrol: Gentler fights with more weak enemies.
    Sentinel Training: Light combat with a gradual increase in difficulty.
    Slayer's Path: A balanced mix that gets tougher as you progress.
    Hell's Vanguard: Harder fights with more heavy enemies.
    Icon's Wrath: Very hard fights with strong enemies and more special enemies together.
    Gore Nest: Swarms of weaker enemies.
    Gladiator's Gauntlet: Smaller groups of tougher enemies.
    Cultist Chaos: A wide mix of enemy types and stats.
    Oops! All Imps: Replace enemies with large groups of Imps.
    Piñata Party: Favor Maykr Drones, Lost Souls and Buff Totems.
    Custom: Use your own enemy settings."""

    display_name = "Enemy Preset"
    option_uac_patrol = 0
    option_sentinel_training = 1
    option_slayers_path = 2
    option_hells_vanguard = 3
    option_icons_wrath = 4
    option_gore_nest = 5
    option_gladiators_gauntlet = 6
    option_cultist_chaos = 7
    option_oops_all_imps = 8
    option_pinata_party = 9
    option_custom = 10
    default = option_slayers_path
    labels = {
        option_uac_patrol: "UAC Patrol — Gentle",
        option_sentinel_training: "Sentinel Training — Light",
        option_slayers_path: "Slayer’s Path — Balanced",
        option_hells_vanguard: "Hell’s Vanguard — Intense",
        option_icons_wrath: "Icon’s Wrath — Extreme",
        option_gore_nest: "Gore Nest — Swarm",
        option_gladiators_gauntlet: "Gladiator’s Gauntlet — Elite",
        option_cultist_chaos: "Cultist Chaos — Chaotic",
        option_oops_all_imps: "Oops! All Imps",
        option_pinata_party: "Piñata Party",
        option_custom: "Custom",
    }


class ProgressiveDifficulty(Toggle):
    """Make randomized fights grow harder as you progress through the campaign.

    On: Use the early settings at the start and move toward the late settings as you progress.
    Off: Use the early settings throughout the campaign."""

    display_name = "Progressive Difficulty"
    default = 1


class _EnemyRecipeRange(NamedRange):
    range_start = 1
    range_end = 10000
    special_range_names = {"auto": -1}
    default = -1


class EnemyIntensityEarly(_EnemyRecipeRange):
    """Choose how tough randomized fights should be near the start when Enemy Count is Auto.

    100%: Aim for normal enemy strength. Lower values make fights easier; higher values make them harder.
    Auto: Use the selected enemy preset."""

    display_name = "Early Intensity"


class EnemyIntensityLate(_EnemyRecipeRange):
    """Choose how tough randomized fights should become near the end when Enemy Count is Auto.

    100%: Aim for normal enemy strength. Lower values make fights easier; higher values make them harder.
    Auto: Use the selected enemy preset."""

    display_name = "Late Intensity"


class EnemyDensity(_EnemyRecipeRange):
    """Choose between crowds of weaker enemies and smaller groups of stronger enemies when Enemy Count is Auto.

    100%: Use a balanced group size. Higher values favor crowds; lower values favor fewer, tougher enemies.
    Auto: Use the selected enemy preset."""

    display_name = "Density"


class EnemyVariety(_EnemyRecipeRange):
    """Choose how many different enemy types you tend to face in the same fight.

    0: Favor groups of the same enemy type.
    100: Favor a broad mix of enemy types. Values in between blend the two.
    Auto: Use the selected enemy preset."""

    display_name = "Variety"
    range_start = 0
    range_end = 100


class EnemyCountMode(_ExactLabelChoice):
    """Choose how to decide the number of randomized enemies in a fight.

    Preset: Use the selected enemy preset's count setting.
    Auto: Use Intensity and Density to choose between more weak enemies and fewer strong enemies.
    Multiplier: Multiply the fight's original enemy count using Enemy Count Multiplier.
    Crowded fights can split into extra waves."""

    display_name = "Enemy Count"
    option_preset = 0
    option_auto = 1
    option_multiplier = 2
    default = option_preset
    labels = {option_preset: "Preset", option_auto: "Auto", option_multiplier: "Multiplier"}


class EnemyCountMultiplier(_EnemyRecipeRange):
    """Choose how many enemies to request when Enemy Count is Multiplier.

    100%: Keep the original count. 200%: Request twice as many. 500%: Request five times as many.
    Auto: Use the selected enemy preset. The fight's available space can limit the result."""

    display_name = "Enemy Count Multiplier"


class EnemySizeVariationChance(_EnemyRecipeRange):
    """Choose the chance for an enemy to appear at half size or double size.

    0%: Use normal size. 100%: Give every enemy a chance split equally between half size and double size.
    Auto: Use the selected enemy preset. Size Ranges lets you choose other sizes."""

    display_name = "Size Variation Chance"
    range_start = 0
    range_end = 100


class Killsanity(Toggle):
    """Earn an Archipelago reward after every Kills per Check enemy deaths.

    Every enemy death counts, including enemies spawned by traps, respawns and replayed missions.
    On: Add kill rewards. Off: Use the campaign's other rewards."""

    display_name = "Killsanity"
    default = 0


class KillsPerCheck(Range):
    """Send one check at each multiple of this many enemy deaths.

    For example, 100 gives rewards at 100, 200, 300 kills and so on."""

    display_name = "Kills per Check"
    range_start = 1
    range_end = 2147483647
    default = 100


class KillsanityMaximumMilestones(NamedRange):
    """Choose how many kill rewards to add to your campaign.

    Auto: Divide estimated campaign kills plus 10% by Kills per Check, round down, and cap at 50 rewards.
    1..65,535: Add that many kill rewards. Kills per Check sets the gap between rewards."""

    display_name = "Kill Rewards"
    range_start = 1
    range_end = 65535
    special_range_names = {"auto": -1}
    default = -1


class RevealAPLocationsOnAutomap(Toggle):
    """Show Archipelago pickup locations on the DOOM Eternal Automap, making checks easier to find while exploring or replaying missions.

    On: Show the markers. Off: Explore with the usual Automap markers."""

    display_name = "Reveal AP Locations on Automap"
    default = 0


class TrapPercentage(Range):
    """Choose the percentage of extra item rewards that become traps.

    0%: Fill them with helpful consumables. 100%: Fill them with your selected traps.
    Values in between mix consumables and traps."""

    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 10


class EnabledTraps(OptionSet):
    """Pick the traps that other players can send you.

    Enemy traps spawn the named enemy near you, from an Imp to an Arch-vile.
    Cueball Trap spawns an explosive Cueball.
    Ammo Drain Trap reduces your regular ammo. Fuel Drain Trap reduces Chainsaw fuel.
    BFG Drain Trap reduces BFG ammo. Clear all entries to use helpful consumables instead."""

    display_name = "Enabled Traps"
    valid_keys = SAFE_TRAP_NAMES
    default = SAFE_TRAP_NAMES


# Starting Weapon option values are public and stable.
_STARTING_WEAPON_OPTION_NAMES = {
    1: "Heavy Cannon",
    2: "Plasma Rifle",
    3: "Rocket Launcher",
    4: "Ballista",
    5: "Chaingun",
    6: "Combat Shotgun",
    7: "Super Shotgun",
}


class CampaignDifficulty(Choice):
    """Choose the game's combat difficulty for your campaign.

    I'm Too Young to Die: The easiest fights, with more room for mistakes.
    Hurt Me Plenty: A moderate challenge.
    Ultra-Violence: Tough fights that reward good weapon use and movement.
    Nightmare: The hardest setting, with aggressive enemies and punishing damage."""

    display_name = "Campaign Difficulty"
    option_im_too_young_to_die = 0
    option_hurt_me_plenty = 1
    option_ultra_violence = 2
    option_nightmare = 3
    default = 2


class ResourceProfile(_ExactLabelChoice):
    """Choose how many upgrades, spare resources and recovery items you can find.

    Balanced: A varied supply suited to your campaign's length and fights.
    Generous: More alternatives and recovery items.
    Lean: Fewer spare upgrades and recovery items.
    Item Pool Overrides lets you choose exact amounts for individual items."""

    display_name = "Resource Profile"
    option_balanced = 0
    option_generous = 1
    option_lean = 2
    default = option_balanced
    labels = {option_balanced: "Balanced", option_generous: "Generous", option_lean: "Lean"}


class _BoundedItemDict(OptionDict):
    entry_limits = {}

    def __init__(self, value):
        for name, count in value.items():
            if name not in self.entry_limits or type(count) is not int or not 0 <= count <= self.entry_limits[name]:
                raise ValueError(f"{self.display_name}: invalid override {name!r}: {count!r}")
        super().__init__(value)


_ENEMY_NAMES = {
    species: {"archvile": "Arch-vile", "blood_angel": "Blood Maykr", "zombie_maykr": "Maykr Drone",
              "chaingun_soldier": "Riot Soldier", "zombie_t1_screecher": "Screecher Zombie",
              "zombie_tier_1": "Zombie", "zombie_tier_3": "Mecha Zombie"}.get(
                  species, species.replace("_", " ").title())
    for species in SPECIES_IDS
}
_ENEMY_RANGE_LABELS = {"minimum": "Minimum", "maximum": "Maximum",
                       "early_minimum": "Early Minimum", "early_maximum": "Early Maximum",
                       "late_minimum": "Late Minimum", "late_maximum": "Late Maximum"}


class EnemyWeights(_BoundedItemDict):
    """Choose how often each enemy type appears.

    Higher weights make an enemy more common. A weight of 20 is twice as likely as 10.
    Zero leaves that type out of random picks. Empty entries use the selected preset.
    Some fights keep special enemies or add weak enemies for ammo and health."""

    display_name = "Bestiary Weights"
    entry_limits = {species: 10000 for species in SPECIES_IDS}
    entry_labels = _ENEMY_NAMES
    default = {}


class _EnemyAttributeRanges(_BoundedItemDict):
    entry_limits = {field: 10000 for field in _ENEMY_RANGE_LABELS}
    entry_limits.update({f"{species}.{field}": 10000 for species in SPECIES_IDS for field in _ENEMY_RANGE_LABELS})
    entry_labels = {**_ENEMY_RANGE_LABELS, **{
        f"{species}.{field}": f"{label} — {_ENEMY_RANGE_LABELS[field]}"
        for species, label in _ENEMY_NAMES.items() for field in _ENEMY_RANGE_LABELS}}
    entry_minimum = 1
    default = {}

    def __init__(self, value):
        super().__init__(value)
        if 0 in self.value.values():
            raise ValueError("Enemy attribute percentages must be positive.")


class EnemyHealth(_EnemyAttributeRanges):
    """Choose enemy health as a percentage of its usual value: 50% is half health, 100% is normal, 200% is double.

    Minimum and Maximum: Pick each enemy's health between these values.
    Early Minimum/Maximum and Late Minimum/Maximum: Gradually change that range as you progress.
    Set both ends equal for a fixed value. Choose an enemy type to give it its own range.
    Empty entries use the selected preset. YAML example: imp.minimum: 50 and imp.maximum: 100."""

    display_name = "Health Ranges"


class EnemyDamage(_EnemyAttributeRanges):
    """Choose enemy damage as a percentage of its usual value: 50% is half damage, 100% is normal, 200% is double.

    Minimum and Maximum: Pick each enemy's damage between these values.
    Early Minimum/Maximum and Late Minimum/Maximum: Gradually change that range as you progress.
    Set both ends equal for a fixed value. Choose an enemy type to give it its own range.
    Empty entries use the selected preset."""

    display_name = "Damage Ranges"


class EnemySpeed(_EnemyAttributeRanges):
    """Choose how fast enemies move and attack: 100% is normal speed.

    Minimum and Maximum set a range. Early and Late values change the range as you progress.
    Choose an enemy type to give it its own range. Empty entries use the selected preset."""

    display_name = "Speed Ranges"


class EnemySize(_EnemyAttributeRanges):
    """Choose enemy size as a percentage: 50% is half size, 100% is normal, 200% is double.

    Minimum and Maximum set a range. Early and Late values change the range as you progress.
    Set both ends equal for a fixed size. Choose an enemy type to give it its own range.
    An enemy's Size Range takes priority over Size Variation Chance. Available space can limit its size."""

    display_name = "Size Ranges"


class EnemySpecialLimits(_BoundedItemDict):
    """Choose how many special enemies can fight you at the same time.

    Marauder, Arch-vile and Spirit: Set the limit for that enemy type.
    Combined Specials: Set the total limit for those three types together.
    Numbers stay fixed throughout the campaign. Empty entries use the preset and grow with Progressive Difficulty.
    Zero blocks random additions of that type.
    Some fights keep their special enemies."""

    display_name = "Special Enemy Limits"
    entry_limits = {"marauder": 2147483647, "archvile": 2147483647,
                    "spirit": 2147483647, "combined_special": 2147483647}
    entry_labels = {"marauder": "Marauder", "archvile": "Arch-vile",
                    "spirit": "Spirit", "combined_special": "Combined Specials"}
    default = {}


class ItemPoolCounts(_BoundedItemDict):
    """Choose exact amounts of individual upgrades and permanent items to place in your campaign.

    Zero leaves the item out. Positive numbers add that many copies, up to the item's upgrade limit.
    Empty entries use Resource Profile. Required challenge items can raise the amount."""

    display_name = "Item Pool Overrides"
    entry_limits = POOL_ITEM_LIMITS


class FillerWeights(_BoundedItemDict):
    """Choose how often you find each helpful consumable in extra reward slots.

    Higher weights make an item more common. A weight of 20 is twice as likely as 10.
    Zero leaves an item out. Empty entries use Resource Profile."""

    display_name = "Filler Weights"
    entry_limits = {name: 10000 for name in FILLER_WEIGHT_NAMES}


class TrapWeights(_BoundedItemDict):
    """Choose how often each selected trap appears.

    Higher weights make a trap more common. A weight of 20 is twice as likely as 10.
    Zero leaves a trap out. Empty entries give traps equal weight."""

    display_name = "Trap Weights"
    entry_limits = {name: 10000 for name in SAFE_TRAP_NAMES}


class MasteryRequirements(_ExactLabelChoice):
    """Choose how many times you need to repeat an action to finish a weapon mastery challenge.

    Original: Use the game's usual targets.
    Half: Require half as many repetitions, rounded up.
    Quarter: Require a quarter as many repetitions, rounded up.
    Every challenge requires at least one repetition."""

    display_name = "Mastery Requirements"
    option_original = 0
    option_half = 1
    option_quarter = 2
    default = option_half
    labels = {option_original: "Original", option_half: "Half", option_quarter: "Quarter"}


class LogicDifficulty(_ExactLabelChoice):
    """Choose how much equipment Archipelago expects you to have before a fight.

    Relaxed: Let you attempt fights with less equipment.
    Standard: Expect a balanced set of weapons and upgrades.
    Expert: Wait for a stronger set of weapons and upgrades before expecting you to clear a fight."""

    display_name = "Logic Difficulty"
    option_relaxed = 0
    option_standard = 1
    option_expert = 2
    default = option_standard
    labels = {option_relaxed: "Relaxed", option_standard: "Standard", option_expert: "Expert"}


class StartingWeapon(Choice):
    """Choose the weapon you have when you start.

    Random: Let the seed choose your starting weapon.
    Combat Shotgun: A close-range shotgun. Super Shotgun: A powerful double-barrel shotgun.
    Heavy Cannon: Accurate rifle fire. Plasma Rifle: Rapid energy fire, useful against shields.
    Rocket Launcher: Explosive splash damage. Ballista: Heavy precision shots.
    Chaingun: Sustained rapid fire."""

    display_name = "Starting Weapon"
    option_random_weapon = 0
    locals().update({
        f"option_{name.lower().replace(' ', '_').replace('-', '_')}": index
        for index, name in _STARTING_WEAPON_OPTION_NAMES.items()
    })
    default = 6

    @classmethod
    def from_text(cls, text: str):
        # keep the random starting weapon tied to the seed.
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
    """Choose how many individual Praetor Suit upgrades you can find.

    Auto: Use your campaign's length and Resource Profile.
    Random: Let the seed choose a moderate amount.
    0: Leave suit upgrades out. A positive number adds exactly that many; the maximum includes them all."""

    display_name = "Praetor Suit Upgrades in Pool"
    range_start = 0
    range_end = len(suit_perk_item_names)
    default = -2
    special_range_names = {"random": -1, "auto": -2}

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
    accessibility: Accessibility
    progression_balancing: ProgressionBalancing
    death_link: DeathLink
    use_dlc_content: UseDLCContent
    mission_pool: MissionPool
    custom_missions: CustomMissions
    custom_dark_lord: CustomDarkLord
    mission_count: MissionCount
    mission_order: MissionOrder
    campaign_difficulty: CampaignDifficulty
    logic_difficulty: LogicDifficulty
    mastery_requirements: MasteryRequirements
    resource_profile: ResourceProfile
    item_pool_counts: ItemPoolCounts
    filler_weights: FillerWeights
    trap_weights: TrapWeights
    starting_missions: StartingMissions
    full_saga_final_boss: FullSagaFinalBoss
    goal_mission_as_item: GoalMissionAsItem
    goal: Goal
    additional_victory_requirements: AdditionalVictoryRequirements
    special_weapon: SpecialWeapon
    death_link_mode: DeathLinkMode
    enhanced_melee_damage: EnhancedMeleeDamage
    randomize_chainsaw: RandomizeChainsaw
    randomize_dash: RandomizeDash
    include_slayer_gates: IncludeSlayerGates
    include_secret_encounters: IncludeSecretEncounters
    easier_secret_encounters: EasierSecretEncounters
    enemy_randomizer: EnemyRandomizer
    enemy_preset: EnemyPreset
    enemy_intensity_early: EnemyIntensityEarly
    enemy_intensity_late: EnemyIntensityLate
    enemy_density: EnemyDensity
    enemy_variety: EnemyVariety
    progressive_difficulty: ProgressiveDifficulty
    enemy_count_mode: EnemyCountMode
    enemy_count_multiplier: EnemyCountMultiplier
    enemy_size_variation_chance: EnemySizeVariationChance
    enemy_weights: EnemyWeights
    enemy_health: EnemyHealth
    enemy_damage: EnemyDamage
    enemy_speed: EnemySpeed
    enemy_size: EnemySize
    enemy_special_limits: EnemySpecialLimits
    killsanity: Killsanity
    kills_per_check: KillsPerCheck
    killsanity_maximum_milestones: KillsanityMaximumMilestones
    include_weapon_mastery_challenges: IncludeWeaponMasteryChallenges
    reveal_ap_locations_on_automap: RevealAPLocationsOnAutomap
    starting_weapon: StartingWeapon
    praetor_suit_upgrades_in_pool: PraetorSuitUpgradesInPool
    trap_percentage: TrapPercentage
    enabled_traps: EnabledTraps
