from dataclasses import dataclass

from Options import Choice, DeathLinkMixin, NamedRange, OptionSet, PerGameCommonOptions, Range, Toggle

from .items import SAFE_TRAP_NAMES, suit_perk_item_names


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


class UseDLCContent(Toggle):
    """Adds supported The Ancient Gods equipment and gameplay content to the randomizer, including the Sentinel Hammer and Support Runes. DLC missions are controlled separately."""

    display_name = "Use DLC Content"
    default = 1


class IncludeDLCMissions(Toggle):
    """Adds The Ancient Gods Part One and Part Two missions and their Archipelago locations. Disable this for the Base Campaign while keeping enabled DLC equipment and gameplay content in the randomizer."""

    display_name = "Include DLC Missions"
    default = 1


class DLCLogicTiming(_ExactLabelChoice):
    """Choose when The Ancient Gods can enter your Archipelago progression.

    Late Game — DLC mission paths enter logic once your inventory reaches their intended combat readiness.

    From the Beginning — Removes the extra late-game combat-readiness gate. DLC paths become logical as soon as their real traversal, equipment, and internal mission requirements are satisfied (vanilla Dash becomes available after Exultia; The World Spear requires Super Shotgun / Meat Hook traversal and a sustainable ammo-resource tool).

    This changes Archipelago progression only. It does not change DOOM Eternal's difficulty or hide missions from the campaign menus.
    """

    display_name = "DLC Logic Timing"
    option_late_game = 0
    option_from_the_beginning = 1
    default = option_late_game
    labels = {
        option_late_game: "Late Game",
        option_from_the_beginning: "From the Beginning",
    }


class Goal(_ExactLabelChoice):
    """Choose the main objective that wins your Archipelago world.

    Acquire the Unmaykr — Complete the six Base Campaign Slayer Gates and claim the Unmaykr from its case in the Fortress of Doom.

    Kill the Icon of Sin — Progress through the Base Campaign and defeat the Icon of Sin.

    Kill the Dark Lord — Progress through The Ancient Gods Part Two and defeat the Dark Lord.

    Complete the Full Saga — Complete all 19 Base Campaign, TAG1, and TAG2 missions, claim the Unmaykr, defeat the Icon of Sin, and defeat the Dark Lord.
    """

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
    "Complete All Enabled Missions",
    "Complete All Slayer Gates",
    "Complete All Escalation Encounters",
    "Complete All Secret Encounters",
    "Complete All Mission Challenges",
    "Complete All Weapon Mastery Challenges",
    "Acquire the Unmaykr",
})


class AdditionalVictoryRequirements(OptionSet):
    """Choose extra objectives that must also be completed before your Goal counts as victory. Hover an objective to see exactly what it requires."""

    display_name = "Additional Victory Requirements"
    valid_keys = VICTORY_REQUIREMENT_NAMES
    default = frozenset({
        "Complete All Enabled Missions",
        "Complete All Slayer Gates",
        "Complete All Escalation Encounters",
    })


class SpecialWeapon(_ExactLabelChoice):
    """Choose a three-stage Crucible-to-Hammer progression, a two-stage Sentinel Hammer progression, or one standalone Crucible stage."""

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


class EnhancedMeleeDamage(Toggle):
    """Increase the damage of normal punches, making melee a more useful close-range fallback."""

    display_name = "Enhanced Melee Damage"
    default = 0


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


class IncludeWeaponMasteryChallenges(Toggle):
    """Include the 13 Weapon Mastery Challenge locations."""

    display_name = "Include Weapon Mastery Challenges"
    default = 1


class RevealAPLocationsOnAutomap(Toggle):
    """Show Archipelago pickup locations on the DOOM Eternal Automap, making checks easier to find while exploring or replaying missions."""

    display_name = "Reveal AP Locations on Automap"
    default = 0


class TrapPercentage(Range):
    """Percentage of filler padding replaced by enabled traps."""

    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 10


class EnabledTraps(OptionSet):
    """Trap types eligible for filler-padding replacement."""

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
    use_dlc_content: UseDLCContent
    include_dlc_missions: IncludeDLCMissions
    dlc_logic_timing: DLCLogicTiming
    goal: Goal
    additional_victory_requirements: AdditionalVictoryRequirements
    special_weapon: SpecialWeapon
    enhanced_melee_damage: EnhancedMeleeDamage
    randomize_chainsaw: RandomizeChainsaw
    randomize_dash: RandomizeDash
    randomize_first_battery: RandomizeFirstBattery
    include_weapon_mastery_challenges: IncludeWeaponMasteryChallenges
    reveal_ap_locations_on_automap: RevealAPLocationsOnAutomap
    starting_weapon: StartingWeapon
    praetor_suit_upgrades_in_pool: PraetorSuitUpgradesInPool
    trap_percentage: TrapPercentage
    enabled_traps: EnabledTraps
