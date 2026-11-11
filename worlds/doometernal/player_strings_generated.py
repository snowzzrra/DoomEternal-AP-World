# GENERATED from data/strings/en.json; regenerate in DoomEternal-AP-Mod:
# python -m tools.content.compile_player_strings
"""APWorld player text; no Mod checkout or runtime catalog is required."""

TEMPLATES = {
    ("apworld.errors", "battery_items_absent"): (
        "Battery items are absent for {location}"
    ),
    ("apworld.errors", "classification_budget_mismatch"): (
        "DOOM Eternal classification budget mismatch for '{item}'"
    ),
    ("apworld.errors", "custom_pool_minimum"): (
        "DOOM Eternal Custom Mission Pool requires at least {minimum} normal missions to fit the upgrade "
        "pool."
    ),
    ("apworld.errors", "dark_lord_requires_dlc"): (
        "DOOM Eternal Goal '{goal}' requires DLC content and DLC missions for Dark Lord content"
    ),
    ("apworld.errors", "empty_logic_alternative"): (
        "Empty any_of alternative: {location}"
    ),
    ("apworld.errors", "enemy_attribute_object"): (
        "enemy_{attribute} must be an object"
    ),
    ("apworld.errors", "enemy_boolean"): (
        "{option} must be a boolean"
    ),
    ("apworld.errors", "enemy_count_mode"): (
        "Enemy Count must be Auto or Multiplier"
    ),
    ("apworld.errors", "enemy_integer_range"): (
        "{option} must be an integer between {minimum} and {maximum}"
    ),
    ("apworld.errors", "enemy_inverted_range"): (
        "enemy_{attribute}.{species} minimum exceeds maximum"
    ),
    ("apworld.errors", "enemy_limit_label"): (
        "Special Enemy Limit {limit}"
    ),
    ("apworld.errors", "enemy_limits_object"): (
        "Special Enemy Limits must be an object"
    ),
    ("apworld.errors", "enemy_options_revision"): (
        "Unsupported enemy options revision"
    ),
    ("apworld.errors", "enemy_percentage_positive"): (
        "Enemy attribute percentages must be positive."
    ),
    ("apworld.errors", "enemy_range_bounds"): (
        "enemy_{attribute}.{species} needs both fixed bounds or all four Early/Late bounds"
    ),
    ("apworld.errors", "enemy_range_name_text"): (
        "enemy_{attribute} range names must be text"
    ),
    ("apworld.errors", "enemy_speed_range"): (
        "speed_percent must be an integer in 1..10000"
    ),
    ("apworld.errors", "enemy_speed_unqualified"): (
        "Speed changes are not qualified for {species}: {capability}; use 100%"
    ),
    ("apworld.errors", "enemy_unknown_range"): (
        "enemy_{attribute} has unknown range {range}"
    ),
    ("apworld.errors", "enemy_weight_label"): (
        "Enemy Weight {species}"
    ),
    ("apworld.errors", "enemy_weights_empty"): (
        "Enemy Weights exclude every eligible random combat species"
    ),
    ("apworld.errors", "enemy_weights_object"): (
        "Enemy Weights must be an object"
    ),
    ("apworld.errors", "excluded_pool_capacity"): (
        "Too many excluded locations for the DOOM Eternal upgrade pool. Exclude fewer locations, include more"
        " missions, or reduce Item Pool Counts."
    ),
    ("apworld.errors", "excluded_room_capacity"): (
        "The room has {excluded_count} excluded locations but only {filler_count} filler/trap items. Reduce "
        "Exclude Locations or increase non-useful Filler Weights / Trap Percentage."
    ),
    ("apworld.errors", "filler_excluded_weight"): (
        "Excluded locations require filler or traps. Give a positive Filler Weight to a non-useful item such "
        "as Full Heal, or increase Trap Percentage."
    ),
    ("apworld.errors", "filler_replacement_weight"): (
        "Filler Weights must leave a positive weight for replacement items"
    ),
    ("apworld.errors", "filler_residual_weight"): (
        "Filler Weights must leave a positive weight for residual locations"
    ),
    ("apworld.errors", "full_saga_incomplete"): (
        "DOOM Eternal Goal 'Complete the Full Saga' is unavailable: the mission-complete catalog is "
        "incomplete ({authored}/{expected} missions authored); missing: {missing}"
    ),
    ("apworld.errors", "full_saga_mission_count"): (
        "DOOM Eternal Goal 'Complete the Full Saga' is unavailable: the mission-complete catalog must contain"
        " exactly {expected} missions; authored {authored}{unexpected}"
    ),
    ("apworld.errors", "full_saga_mission_count_details"): (
        "; unexpected: {names}"
    ),
    ("apworld.errors", "full_saga_requires_dlc"): (
        "DOOM Eternal Goal '{goal}' requires DLC content and DLC missions for Dark Lord and Full Saga content"
    ),
    ("apworld.errors", "goal_endpoint_unavailable"): (
        "DOOM Eternal Goal '{goal}' is unavailable: required endpoint location '{location}' is not in active "
        "catalog"
    ),
    ("apworld.errors", "invalid_item_override"): (
        "{option}: invalid override {item}: {count}"
    ),
    ("apworld.errors", "invalid_logic_rule"): (
        "Invalid logic rule: {location}"
    ),
    ("apworld.errors", "invalid_soft_capabilities"): (
        "Generated connection soft_capabilities must be a sequence"
    ),
    ("apworld.errors", "inventory_chainsaw_disabled"): (
        "DOOM Eternal starting inventory Chainsaw unavailable when randomize_chainsaw is disabled"
    ),
    ("apworld.errors", "inventory_consumable"): (
        "{item} (consumable)"
    ),
    ("apworld.errors", "inventory_dash_disabled"): (
        "DOOM Eternal starting inventory Dash unavailable when randomize_dash is disabled"
    ),
    ("apworld.errors", "inventory_filler"): (
        "{item} (filler/consumable)"
    ),
    ("apworld.errors", "inventory_goal_item"): (
        "{item} (goal item)"
    ),
    ("apworld.errors", "inventory_invalid_item_quantity"): (
        "DOOM Eternal starting inventory has invalid quantity: {item}"
    ),
    ("apworld.errors", "inventory_invalid_quantity"): (
        "DOOM Eternal starting inventory has invalid quantity: {items}"
    ),
    ("apworld.errors", "inventory_maximum"): (
        "{item} (maximum {maximum})"
    ),
    ("apworld.errors", "inventory_not_persistent"): (
        "{item} (not in current persistent pool)"
    ),
    ("apworld.errors", "inventory_requires_dlc"): (
        "{item} (requires Use DLC Content ON)"
    ),
    ("apworld.errors", "inventory_special_weapon"): (
        "{item} (incompatible Special Weapon mode)"
    ),
    ("apworld.errors", "inventory_trap"): (
        "{item} (trap)"
    ),
    ("apworld.errors", "inventory_unavailable"): (
        "DOOM Eternal starting inventory item is not legal in current persistent pool: {items}"
    ),
    ("apworld.errors", "inventory_unsafe"): (
        "DOOM Eternal starting inventory cannot contain traps, filler/consumables, or Victory: {items}"
    ),
    ("apworld.errors", "item_pool_capacity"): (
        "DOOM Eternal item pool requires {pool_count} locations; only {location_count} enabled"
    ),
    ("apworld.errors", "item_pool_does_not_fit"): (
        "DOOM Eternal items do not fit the enabled checks; include more missions or checks, or reduce "
        "explicit Item Pool Overrides"
    ),
    ("apworld.errors", "kill_rewards_option_range"): (
        "Kill Rewards must be Auto or 1..2000"
    ),
    ("apworld.errors", "kill_rewards_range"): (
        "Kill Rewards must be Auto or 1..{maximum}"
    ),
    ("apworld.errors", "killsanity_access_mission"): (
        "Killsanity source access belongs to another mission: {source}"
    ),
    ("apworld.errors", "killsanity_inactive_mission"): (
        "Killsanity source references an inactive mission: {mission}"
    ),
    ("apworld.errors", "killsanity_unknown_items"): (
        "Killsanity source references unknown items: {source}"
    ),
    ("apworld.errors", "legacy_battery_bundle"): (
        "Sentinel Battery Bundle belongs to legacy rooms; use individual Sentinel Battery items"
    ),
    ("apworld.errors", "legacy_blood_punch"): (
        "Blood Punch belongs to legacy rooms; new seeds require Progressive Blood Punch (0..4)"
    ),
    ("apworld.errors", "master_level_count"): (
        "Master Level Count must be between 1 and {maximum} active Master Levels."
    ),
    ("apworld.errors", "master_levels_disabled"): (
        "{objective} requires Include Master Levels to be enabled."
    ),
    ("apworld.errors", "mastery_points_insufficient"): (
        "The active Weapon Mastery Challenges need more Weapon Upgrade Points"
    ),
    ("apworld.errors", "negative_battery_requirement"): (
        "Negative Battery requirement: {location}"
    ),
    ("apworld.errors", "negative_weapon_requirement"): (
        "Negative normal weapon requirement: {location}"
    ),
    ("apworld.errors", "opening_encounters_unavailable"): (
        "Starting mission has no verified opening encounters"
    ),
    ("apworld.errors", "override_dependency"): (
        "Item Pool Overrides: {item} requires {dependency}"
    ),
    ("apworld.errors", "override_mastery_points"): (
        "Item Pool Overrides: Weapon Upgrade Points do not cover active mastery challenges"
    ),
    ("apworld.errors", "override_readiness"): (
        "Item Pool Overrides cannot satisfy campaign readiness (deficit {deficit})"
    ),
    ("apworld.errors", "override_required_mod"): (
        "Item Pool Overrides: {mod} is required by active challenges"
    ),
    ("apworld.errors", "override_unavailable"): (
        "Item Pool Overrides: {item} is unavailable in this campaign"
    ),
    ("apworld.errors", "pool_excludes_requirements"): (
        "Item Pool Overrides exclude active requirements: {items}"
    ),
    ("apworld.errors", "preparation_check_missing"): (
        "DOOM Eternal preparation cannot place {item} for player {player}: no reachable opening check accepts"
        " it; review excluded locations, item rules and plando"
    ),
    ("apworld.errors", "preparation_copy_missing"): (
        "DOOM Eternal preparation cannot place {item} for player {player}: no held copy or reachable opening "
        "plando copy; review excluded locations, item rules and plando"
    ),
    ("apworld.errors", "progressive_opening_unavailable"): (
        "This mission pool has no verified opening for progressive enemizer without starting equipment"
    ),
    ("apworld.errors", "room_placement_missing"): (
        "Room placement is missing an item at {location}"
    ),
    ("apworld.errors", "semantic_pool_unplanned"): (
        "DOOM Eternal semantic item pool was not planned"
    ),
    ("apworld.errors", "starting_battery_economy"): (
        "Sentinel Battery starting inventory exceeds the {budget}-unit economy"
    ),
    ("apworld.errors", "starting_pool_copies"): (
        "DOOM Eternal start_inventory_from_pool '{item}' requests {quantity} copies; only {available} "
        "eligible pool copies are available"
    ),
    ("apworld.errors", "starting_preparation_unavailable"): (
        "DOOM Eternal cannot fit guaranteed combat preparation for a starting mission in this solo world. Add"
        " starting equipment with Start Inventory, include early Base missions, or lower Campaign Difficulty "
        "/ choose a more permissive Logic Difficulty."
    ),
    ("apworld.errors", "starting_weapon_unavailable"): (
        "Starting Weapon random selection has no eligible pool weapon"
    ),
    ("apworld.errors", "suit_count_maximum"): (
        "Praetor Suit upgrade count exceeds catalog maximum {maximum}"
    ),
    ("apworld.errors", "suit_pool_conflict"): (
        "Praetor Suit count conflicts with Item Pool Overrides"
    ),
    ("apworld.errors", "tracker_options_missing"): (
        "DOOM Eternal room has no complete tracker options; generate a room with UT support"
    ),
    ("apworld.errors", "unknown_alternative_items"): (
        "Unknown any_of item(s) for {location}: {items}"
    ),
    ("apworld.errors", "unknown_combat_capability"): (
        "Unknown combat capability: {capability}"
    ),
    ("apworld.errors", "unknown_combat_items"): (
        "Unknown combat capability item(s) for {location}: {items}"
    ),
    ("apworld.errors", "unknown_enemy_limit"): (
        "Unknown Special Enemy Limit: {limit}"
    ),
    ("apworld.errors", "unknown_enemy_preset"): (
        "Unknown Enemy Preset: {preset}"
    ),
    ("apworld.errors", "unknown_enemy_weight"): (
        "Unknown Enemy Weight: {species}"
    ),
    ("apworld.errors", "unknown_goal"): (
        "Unknown goal: {goal}"
    ),
    ("apworld.errors", "unknown_logic_items"): (
        "Unknown logic item(s) for {location}: {items}"
    ),
    ("apworld.errors", "unknown_logic_location"): (
        "Unknown logic location: {location}"
    ),
    ("apworld.errors", "unknown_mission_pool"): (
        "Unknown Mission Pool: {pool}"
    ),
    ("apworld.errors", "unknown_speed_species"): (
        "Unknown Speed species: {species}"
    ),
    ("apworld.errors", "unknown_stage_cr"): (
        "Unknown stage ID for Base CR: {stage}"
    ),
    ("apworld.errors", "unknown_suit_count"): (
        "Unknown Praetor Suit upgrade count: {count}"
    ),
    ("apworld.errors", "unknown_victory_requirement"): (
        "Unknown victory requirement: {requirement}"
    ),
    ("apworld.errors", "unknown_victory_requirements"): (
        "Unknown victory requirement(s): {requirements}"
    ),
    ("apworld.errors", "unmaykr_requires_base"): (
        "DOOM Eternal Goal 'Acquire the Unmaykr' requires Base Slayer Gates and cannot be generated with DLC "
        "Only."
    ),
    ("apworld.errors", "unmaykr_requires_gates"): (
        "Acquire the Unmaykr requires Include Slayer Gates; choose another Goal or enable Slayer Gates."
    ),
    ("apworld.errors", "unsupported_logic_difficulty"): (
        "Unsupported logic difficulty: {difficulty}. Supported: 0 (Relaxed), 1 (Standard), 2 (Expert)"
    ),
    ("apworld.errors", "upgrade_pool_does_not_fit"): (
        "DOOM Eternal upgrades do not fit the enabled checks; include more missions or checks, or reduce "
        "explicit Item Pool Overrides"
    ),
    ("apworld.notices", "resource_adjusted"): (
        "DOOM Eternal {profile} resource profile: Auto adjusted {original} to {actual} pool copies (budget "
        "{budget})."
    ),
    ("apworld.notices", "speed_fixed"): (
        "Speed is fixed at 100% (normal) in this build. Your chosen speed ranges are saved in your player "
        "file."
    ),
    ("apworld.notices", "speed_supported"): (
        "Speed changes affect: {species}. Other enemies move at normal speed."
    ),
    ("apworld.notices", "unprepared_start"): (
        "DOOM Eternal starting mission {mission} has no guaranteed combat preparation; keeping the configured"
        " loadout."
    ),
    ("apworld.readiness", "armor_source"): (
        "Flame Belch or Super Shotgun, Meat Hook and Meat Hook Mastery"
    ),
    ("apworld.settings", "client_directory"): (
        "Directory where the DOOM Eternal Archipelago client is installed."
    ),
    ("apworld.spoiler", "access_items"): (
        "  Access items: {items}"
    ),
    ("apworld.spoiler", "automatic_adjustments"): (
        "Automatic adjustments"
    ),
    ("apworld.spoiler", "combat"): (
        "  Combat {stage}: cost {original} -> {actual}; {waves} waves, peak cost {peak}"
    ),
    ("apworld.spoiler", "composition_bands"): (
        "Composition bands"
    ),
    ("apworld.spoiler", "early_delivery"): (
        "{item} (early delivery, {count})"
    ),
    ("apworld.spoiler", "enemy_preset"): (
        "  Enemy preset: {preset}"
    ),
    ("apworld.spoiler", "enemy_seed"): (
        "  Enemy generation seed: {seed}"
    ),
    ("apworld.spoiler", "goal"): (
        "  Goal: {goal}"
    ),
    ("apworld.spoiler", "item_location"): (
        "{item} at {location}"
    ),
    ("apworld.spoiler", "mission_order"): (
        "  Mission order: {order}"
    ),
    ("apworld.spoiler", "mission_selection"): (
        "  Mission selection: {requested} requested, {included} included; forced goal: {forced_goal}"
    ),
    ("apworld.spoiler", "none"): (
        "None"
    ),
    ("apworld.spoiler", "off"): (
        "Off"
    ),
    ("apworld.spoiler", "optional_resources"): (
        "Optional resources"
    ),
    ("apworld.spoiler", "planning_entries"): (
        "  {label}: {entries}"
    ),
    ("apworld.spoiler", "pool_counts"): (
        "Pool counts"
    ),
    ("apworld.spoiler", "preparation"): (
        "  Preparation: {preparation}"
    ),
    ("apworld.spoiler", "preparation_cr"): (
        "  Preparation CR: {initial} -> {final}; effective {effective}; overshoot {overshoot}"
    ),
    ("apworld.spoiler", "progression_bands"): (
        "Progression bands"
    ),
    ("apworld.spoiler", "readiness"): (
        "  Readiness deficit: {initial} -> {final}; resource budget: {budget}"
    ),
    ("apworld.spoiler", "safety_adjustment"): (
        "  Safety adjustment: {details}"
    ),
    ("apworld.spoiler", "sequence"): (
        "  Sequence: {sequence}"
    ),
    ("apworld.spoiler", "sequence_unlocks"): (
        "None (missions unlock in sequence)"
    ),
    ("apworld.spoiler", "starting_inventory"): (
        "{item} (starting inventory)"
    ),
    ("apworld.spoiler", "title"): (
        "DOOM Eternal - {player}"
    ),
    ("apworld.web", "tagline"): (
        "Rip and tear, until it is done."
    ),
    ("apworld.web", "tutorial_description"): (
        "A guide to installing and connecting DOOM Eternal for Archipelago."
    ),
    ("apworld.web", "tutorial_title"): (
        "DOOM Eternal Setup Guide"
    ),
    ("apworld.web", "world_description"): (
        "Doom Eternal Randomizer for Archipelago."
    ),
}


def text(category: str, key: str, **values: str | int) -> str:
    return TEMPLATES[category, key].format(**values)
