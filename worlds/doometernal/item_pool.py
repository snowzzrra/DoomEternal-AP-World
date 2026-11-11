from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from BaseClasses import CollectionState, Item, ItemClassification, Location, LocationProgressType
from Fill import FillError

from Options import OptionError

from .combat_rating import (
    ALL_MASTERY_NAMES,
    ALL_MOD_NAMES,
    AMMUNITION_BY_WEAPON,
    MOD_HOST,
    SUPPORT_RUNE_NAMES,
    WEAPON_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    HOOK_TRAVERSAL_STAGES,
    ReadinessSelection,
    ReadinessTarget,
    evaluate_mission_readiness,
    select_readiness_items,
)
from .generated_content import CAMPAIGN_STAGES
from .items import (
    SPECIAL_WEAPON_POOL_COUNTS,
    WEAPON_UPGRADE_POINTS_ITEM_COUNT,
    WEAPON_UPGRADE_POINTS_NAME,
    item_data_table,
    world_pool_weapon_item_names,
)
from .planner import (
    _CAPACITY_MAX_STAGES,
    _CAPACITY_STATS,
    ALL_MODS_ORDERED,
    COMBAT_BASELINE_NAMES,
    CORE_EQUIPMENT,
    HARD_MOD_BY_STAGE,
    ITEM_DEPENDENCIES,
    NORMAL_RUNES_ORDERED,
    ORDERED_MASTERY_CHALLENGES,
    STAGE_BY_ID,
    STAGE_SLAYER_GATE_KEYS,
    SUPPORT_RUNES_ORDERED,
    FastState,
    PoolConfigurationError,
    _deplete_starting_pool,
    _item_is_progression,
    _option_value,
    is_compact_campaign,
    mastery_resource_family_count,
    special_weapon_pool_count,
)
from .player_strings_generated import text as player_text


def _filler_weights(world) -> dict[str, int]:
    weights = {
        "Extra Life": 10,
        "Ammo Refill": 30 if world.options.randomize_chainsaw.value else 20,
        "Full Heal": 8,
        "Full Armor": 8,
        "Soulsphere": 5,
        "Berserk": 3,
        "Onslaught": 3,
        "Overdrive": 3,
        "Small Health": 10,
        "Small Armor": 1,
        "Large Health": 10,
        "Large Armor": 10,
        "Armor Shard": 5,
    }
    profile = world.options.resource_profile.current_option_name
    for name in ("Full Heal", "Full Armor", "Soulsphere"):
        if profile == "Generous":
            weights[name] *= 2
        elif profile == "Lean":
            weights[name] = max(1, weights[name] // 2)
    weights.update(world.options.filler_weights.value)
    return weights


def get_filler_item_name(world) -> str:
    weights = _filler_weights(world)
    if not any(weights.values()):
        raise OptionError(player_text("apworld.errors", "filler_replacement_weight"))
    return world.random.choices(list(weights), weights=list(weights.values()), k=1)[0]


def create_items(world) -> None:
    if hasattr(world, "_tracker_slot"):
        world._restore_tracker_starting()
        return
    start_inventory = world.effective_starting_inventory()
    plan = world.campaign_plan
    semantic_counts = plan.get("semantic_counts") or {}
    if not semantic_counts:
        raise ValueError(player_text("apworld.errors", "semantic_pool_unplanned"))
    pool_names: list[str] = []
    for name, quantity in sorted(semantic_counts.items()):
        pool_names.extend([name] * quantity)

    world.praetor_suit_upgrades_in_pool = plan["praetor_suit_upgrades_in_pool"]

    _precollect_equipment(world, pool_names, plan)
    _choose_early_arsenal(world, pool_names, start_inventory, plan)
    _pad_item_pool(world, pool_names)
    pool = [world.create_item(name) for name in pool_names]
    world.multiworld.itempool += pool
    from .classification import apply_dynamic_progression_classification

    apply_dynamic_progression_classification(world)
    _classify_preparation(world, pool, plan)


def _hold_preparation_items(world, pool, preparation):
    if not world.campaign_plan.get("opening_stage"):
        return
    remaining = preparation - _plando_preparation_counts(world, pool)
    for item in pool:
        if remaining[item.name] and item.name not in world.options.non_local_items.value:
            world.preparation_items.append(item)
            world.multiworld.itempool.remove(item)
            remaining[item.name] -= 1


def _plando_preparation_counts(world, pool):
    available = Counter(item.name for item in pool)
    planned = Counter()
    for block in world.options.plando_items:
        if not block.from_pool:
            continue
        if isinstance(block.items, dict):
            planned.update({name: available[name] if count is True else count for name, count in block.items.items()})
        else:
            planned.update(block.items)
    return planned


def get_pre_fill_items(world):
    return [item for item in world.preparation_items if item.location is None]


def _preparation_locations(world, state, regions):
    from .campaign import FORTRESS_BOOTSTRAP_LOCATIONS

    return [
        loc
        for loc in world.multiworld.get_locations(world.player)
        if loc.address is not None
        and loc.can_reach(state)
        and (loc.name in FORTRESS_BOOTSTRAP_LOCATIONS or loc.parent_region.name in regions)
    ]


def _placed_preparation(world, name, locations, state, credited):
    return next(
        (
            loc
            for loc in locations
            if loc not in credited
            and loc.item
            and loc.item.player == world.player
            and loc.item.name == name
            and loc.can_fill(state, loc.item, check_access=False)
        ),
        None,
    )


def pre_fill(world) -> None:
    plan = world.campaign_plan
    if hasattr(world, "_tracker_slot"):
        return
    world.preparation_placements = []
    if plan.get("unprepared_start_stages") and world.multiworld.players == 1:
        _prepare_solo_start(world)
    if not plan.get("opening_stage"):
        return
    from .native_enemy_safety import OPENING_REGIONS

    state = CollectionState(world.multiworld)
    credited = set()
    state.sweep_for_advancements()
    opening = OPENING_REGIONS[plan["opening_stage"]]
    for items, regions in ((plan["bootstrap_placed_items"], ()), (plan["opening_placed_items"], opening)):
        for name in items:
            _prepare_item(world, name, state, regions, credited)
    for item in world.get_pre_fill_items():
        _place_preparation(world, item, state, opening, credited)


def _prepare_solo_start(world):
    state = CollectionState(world.multiworld)
    state.sweep_for_advancements()
    base = FastState.from_counts(state.prog_items[world.player], world.player)
    pool = [item for item in world.multiworld.itempool if item.player == world.player and item.advancement]
    locations = [loc for loc in world.multiworld.get_unfilled_locations(world.player)
                 if loc.progress_type != LocationProgressType.EXCLUDED and loc.can_reach(state)]
    package = _solo_preparation_package(world, base, pool)
    if package is None or len(package) > len(locations):
        raise OptionError(player_text("apworld.errors", "starting_preparation_unavailable"))
    regions = {loc.parent_region.name for loc in locations}
    _place_solo_preparation(world, package, pool, state, regions)


def _place_solo_preparation(world, package, pool, state, regions):
    credited = set()
    for name in package:
        item = next(item for item in pool if item.name == name)
        pool.remove(item)
        world.multiworld.itempool.remove(item)
        _place_preparation(world, item, state, regions, credited)


def _solo_preparation_package(world, base, pool):
    from .campaign import _endurance_selection, _prune_preparation, _start_stage_readiness

    packages = []
    counts = Counter(item.name for item in pool)
    for stage in world.campaign_plan["starting_stages"]:
        initial = _start_stage_readiness(base, world.player, stage, world)
        selection = _endurance_selection(stage, world, base, counts, world.player, initial)
        if selection.satisfied:
            package = _prune_preparation(
                [step.item_name for step in selection.steps], base,
                lambda st, stage=stage: _start_stage_readiness(st, world.player, stage, world)
            )
            packages.append(package)
    return min(packages, key=len, default=None)


def _place_preparation(world, item, state, regions, credited):
    locations = [
        loc
        for loc in _preparation_locations(world, state, regions)
        if loc.item is None and loc.can_fill(state, item, check_access=False)
    ]
    if not locations:
        raise FillError(
            player_text("apworld.errors", "preparation_check_missing", item=repr(item.name), player=world.player)
        )
    location = world.placement_rng.choice(sorted(locations, key=lambda loc: loc.name))
    location.place_locked_item(item)
    credited.add(location)
    world.preparation_placements.append(location)
    state.sweep_for_advancements()


def _access_priorities(world):
    access_priority = {}
    if world.options.mission_order.value == 2 and world.enemies.get("balance_preset"):
        ranks = world.campaign_plan["enemy_progression_bands"]
        count = max(1, *ranks.values())
        for stage in world.campaign_plan["access_items"].values():
            if STAGE_BY_ID[stage]["kind"] == "master":
                continue
            access_priority[STAGE_BY_ID[stage]["name"] + " Access"] = ranks[
                stage
            ] / count + world.access_priority_rng.uniform(-0.6, 0.6)
    return access_priority


def fill_hook(
    world,
    progitempool: list[Item],
    usefulitempool: list[Item],
    filleritempool: list[Item],
    fill_locations: list[Location],
) -> None:
    excluded_count = sum(loc.progress_type == LocationProgressType.EXCLUDED for loc in fill_locations)
    if excluded_count > len(filleritempool):
        raise OptionError(player_text("apworld.errors", "excluded_room_capacity",
                                     excluded_count=excluded_count, filler_count=len(filleritempool)))
    arsenal = set(getattr(world, "frontloaded_arsenal", ()))
    access_priority = _access_priorities(world)

    def sort_key(item: Item) -> float:
        if item.player == world.player:
            if item.name in arsenal:
                return 1
            if item.name in access_priority:
                return 1.5 + access_priority[item.name]
            if "Battery" in item.name:
                return 3
        return 2

    progitempool.sort(key=sort_key)


def _precollect_equipment(world, pool_names, plan):
    if world.starting_weapon_name in pool_names:
        pool_names.remove(world.starting_weapon_name)
    world.multiworld.push_precollected(world.create_item(world.starting_weapon_name))
    for name in plan["bootstrap_inventory"]:
        world.multiworld.push_precollected(world.create_item(name))


def _choose_early_arsenal(world, pool_names, start_inventory, plan):
    world.frontloaded_arsenal = []
    if world.enemies["enabled"]:
        owned = (
            set(start_inventory)
            | set(plan["bootstrap_inventory"])
            | {world.starting_weapon_name}
        )
        ammunition = AMMUNITION_BY_WEAPON
        families = {ammunition[name] for name in owned if name in ammunition}
        for _ in range(2):
            candidates = sorted(set(pool_names) & set(WEAPON_NAMES) - owned)
            if not candidates:
                break
            diverse = [name for name in candidates if ammunition.get(name) not in families]
            weapon = world.item_pool_rng.choice(diverse or candidates)
            world.frontloaded_arsenal.append(weapon)
            owned.add(weapon)
            families.add(ammunition[weapon])
            _choose_early_mod(world, pool_names, weapon)


def _pad_item_pool(world, pool_names):
    locations_count = len(world.multiworld.get_unfilled_locations(world.player))
    amount_needed = locations_count - len(pool_names)
    if amount_needed < 0:
        raise OptionError(
            player_text(
                "apworld.errors", "item_pool_capacity", pool_count=len(pool_names), location_count=locations_count
            )
        )
    excluded_count = sum(
        loc.progress_type == LocationProgressType.EXCLUDED or loc.name in world.options.exclude_locations.value
        for loc in world.multiworld.get_unfilled_locations(world.player)
    )
    if world.multiworld.players == 1 and excluded_count > amount_needed:
        raise OptionError(player_text("apworld.errors", "excluded_pool_capacity"))
    _add_filler_and_traps(world, pool_names, amount_needed)


def _prepare_item(world, name, state, regions, credited):
    locations = _preparation_locations(world, state, regions)
    placed = _placed_preparation(world, name, locations, state, credited)
    if placed:
        credited.add(placed)
        world.preparation_placements.append(placed)
        return
    if name in world.options.non_local_items.value:
        early = world.multiworld.early_items[world.player]
        early[name] = max(early.get(name, 0), 1)
        state.collect(world.create_item(name), True)
        state.sweep_for_advancements()
        return
    item = next((item for item in world.get_pre_fill_items() if item.name == name), None)
    if item is None:
        raise FillError(player_text("apworld.errors", "preparation_copy_missing", item=repr(name), player=world.player))
    _place_preparation(world, item, state, regions, credited)


def _classify_preparation(world, pool, plan):
    preparation = Counter(plan.get("bootstrap_placed_items", ())) + Counter(plan.get("opening_placed_items", ()))
    for item in world.multiworld.itempool:
        if item.player == world.player and item.name in preparation:
            item.classification = ItemClassification.progression
    _hold_preparation_items(world, pool, preparation)
    for name, quantity in Counter(plan.get("bootstrap_placed_items", ())).items():
        if plan.get("opening_stage"):
            continue
        early = (
            world.multiworld.early_items
            if name in world.options.non_local_items.value
            else world.multiworld.local_early_items
        )[world.player]
        early[name] = max(early.get(name, 0), quantity)


def _choose_early_mod(world, pool_names, weapon):
    mods = sorted(name for name in pool_names if MOD_HOST.get(name) == weapon)
    if mods:
        mod = world.item_pool_rng.choice(mods)
        world.frontloaded_arsenal.append(mod)


def _add_excluded_fillers(world, pool_names, filler_weights, amount_needed, trap_count):
    excluded_count = sum(
        loc.progress_type == LocationProgressType.EXCLUDED or loc.name in world.options.exclude_locations.value
        for loc in world.multiworld.get_unfilled_locations(world.player)
    )
    count = min(amount_needed - trap_count, max(0, excluded_count - trap_count))
    weights = {
        name: weight for name, weight in filler_weights.items()
        if not item_data_table[name].classification & (ItemClassification.progression | ItemClassification.useful)
    }
    if not any(weights.values()):
        if count and world.multiworld.players == 1:
            raise OptionError(player_text("apworld.errors", "filler_excluded_weight"))
        return 0
    if count:
        pool_names.extend(world.item_pool_rng.choices(list(weights), weights=list(weights.values()), k=count))
    return count


def _add_filler_and_traps(world, pool_names, amount_needed):
    filler_weights = _filler_weights(world)
    enabled_traps, trap_weights = _trap_weights(world)
    trap_count = amount_needed * world.options.trap_percentage.value // 100 if enabled_traps else 0
    excluded_fillers = _add_excluded_fillers(world, pool_names, filler_weights, amount_needed, trap_count)
    if amount_needed > trap_count and not any(filler_weights.values()):
        raise OptionError(player_text("apworld.errors", "filler_residual_weight"))
    if amount_needed > trap_count + excluded_fillers:
        pool_names.extend(
            world.item_pool_rng.choices(
                list(filler_weights), weights=list(filler_weights.values()),
                k=amount_needed - trap_count - excluded_fillers
            )
        )
    if trap_count:
        pool_names.extend(
            world.item_pool_rng.choices(
                enabled_traps, weights=[trap_weights[name] for name in enabled_traps], k=trap_count
            )
        )


def _trap_weights(world):
    enabled_traps = sorted(world.options.enabled_traps.value)
    trap_weights = {name: world.options.trap_weights.value.get(name, 1) for name in enabled_traps}
    enabled_traps = [name for name in enabled_traps if trap_weights[name] > 0]
    return enabled_traps, trap_weights


@dataclass
class SemanticPool:
    total_counts: Counter[str] = field(default_factory=Counter)
    placement_counts: Counter[str] = field(default_factory=Counter)
    compact: bool = False
    optional_selected: Counter[str] = field(default_factory=Counter)
    readiness_initial_deficit: float = 0.0
    readiness_final_deficit: float = 0.0
    auto_adjustments: Counter[str] = field(default_factory=Counter)

    def counts_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.total_counts.items() if qty > 0}

    def placement_view(self) -> dict[str, int]:
        return {name: qty for name, qty in self.placement_counts.items() if qty > 0}


def build_semantic_counts(
    options,
    *,
    active_normal_ids: Sequence[str],
    starting_weapon: str | None,
    active_sg: Sequence[Mapping[str, Any]],
    active_masteries_count: int,
    battery_surplus: int,
    targets: Sequence[ReadinessTarget] | None = None,
    player: int = 1,
    world_context: Any = None,
    suit_counts: Mapping[str, int] | None = None,
    placement_budget: int | None = None,
) -> SemanticPool:
    builder = _SemanticPoolBuilder(
        options=options,
        active_normal_ids=active_normal_ids,
        starting_weapon=starting_weapon,
        active_sg=active_sg,
        active_masteries_count=active_masteries_count,
        battery_surplus=battery_surplus,
        targets=targets,
        player=player,
        world_context=world_context,
        suit_counts=suit_counts,
        placement_budget=placement_budget,
    )
    return builder.build()


class _SemanticPoolBuilder:
    def __init__(
        self,
        options,
        *,
        active_normal_ids: Sequence[str],
        starting_weapon: str | None,
        active_sg: Sequence[Mapping[str, Any]],
        active_masteries_count: int,
        battery_surplus: int,
        targets: Sequence[ReadinessTarget] | None = None,
        player: int = 1,
        world_context: Any = None,
        suit_counts: Mapping[str, int] | None = None,
        placement_budget: int | None = None,
    ):
        self.active_masteries_count = active_masteries_count
        self.active_normal_ids = active_normal_ids
        self.active_sg = active_sg
        self.battery_surplus = battery_surplus
        self.options = options
        self.placement_budget = placement_budget
        self.player = player
        self.starting_weapon = starting_weapon
        self.suit_counts = suit_counts
        self.targets = targets
        self.world_context = world_context

    def build(self):
        self._base_equipment()
        self._special_weapon()
        self._gate_keys()
        self._battery_economy()
        self._mastery_families()
        self._requested_mods()
        self._required_mods()
        self._upgrade_points()
        self._full_campaign_equipment()
        self._optional_equipment()
        self._apply_overrides()
        self._validate_dependencies()
        self._baseline()
        self._activation_budget()
        self._select_readiness()
        self._placement_counts()
        self._fit_budget()
        return self._result()

    def _base_equipment(self):
        self.from_pool = Counter(getattr(getattr(self.options, "start_inventory_from_pool", None), "value", {}))
        self.start_inv = Counter(self.options.start_inventory.value) + self.from_pool
        self.n_normals = len(self.active_normal_ids)
        self.compact = is_compact_campaign(self.active_normal_ids)
        profile = _option_value(self.options, "resource_profile", 0)
        self.lean = profile == 2
        self.overrides = dict(getattr(getattr(self.options, "item_pool_counts", None), "value", {}) or {})
        self.use_dlc = bool(_option_value(self.options, "use_dlc_content", 1))
        self.pool = SemanticPool(compact=self.compact)
        self.base_pool: Counter[str] = Counter()
        self.optional_caps: Counter[str] = Counter()
        self.mandatory_mods: set[str] = set()
        self._runes_and_capacities()
        if self.compact:
            mod_floor = min(12, max(6, 2 * self.n_normals)) if profile == 1 else 0 if self.lean else 6
            for mod in ALL_MODS_ORDERED[:mod_floor]:
                self.base_pool[mod] = 1
        self._weapons_and_capabilities()

    def _special_weapon(self):
        special_opt = getattr(self.options, "special_weapon", None)
        self.special_name = (
            "The Crucible"
            if not self.use_dlc
            else getattr(special_opt, "current_option_name", "Progressive Special Weapon")
        )
        special_policy = special_weapon_pool_count(self.special_name, use_dlc=self.use_dlc, n_normals=self.n_normals)
        self.base_pool[self.special_name] = special_policy

    def _gate_keys(self):
        for stage_id, key_name in STAGE_SLAYER_GATE_KEYS.items():
            if not self.options.include_slayer_gates.value:
                continue
            if stage_id not in self.active_normal_ids:
                continue
            self.base_pool[key_name] = 1

    def _battery_economy(self):
        battery_cost = sum(group["cost"] for group in self.active_sg)
        battery_total = battery_cost + self.battery_surplus
        if self.start_inv.get("Sentinel Battery Bundle"):
            raise PoolConfigurationError(player_text("apworld.errors", "legacy_battery_bundle"))
        if self.start_inv.get("Sentinel Battery", 0) > battery_total:
            raise PoolConfigurationError(
                player_text("apworld.errors", "starting_battery_economy", budget=battery_total)
            )
        self.base_pool["Sentinel Battery"] = battery_total

    def _mastery_families(self):
        self.family_masteries: list[str] = []
        family_count = self.active_masteries_count if self.compact else mastery_resource_family_count(self.n_normals)
        for mod_name, _location in ORDERED_MASTERY_CHALLENGES[:family_count]:
            mastery_name = mod_name + " Mastery"
            self.family_masteries.append(mastery_name)
        self.requested_masteries = sorted(name for name in ALL_MASTERY_NAMES if self.start_inv.get(name))
        selected_masteries = self.family_masteries + [
            m for m in self.requested_masteries if m not in self.family_masteries
        ]
        for mastery_name in selected_masteries:
            self.base_pool[mastery_name] = 1
            self._include_dependencies(mastery_name)

    def _requested_mods(self):
        self.requested_mods = [mod for mod in ALL_MODS_ORDERED if self.start_inv.get(mod)]
        for mod in self.requested_mods:
            self.mandatory_mods.add(mod)
            self.base_pool[mod] = max(self.base_pool[mod], 1)
            self._include_dependencies(mod)

    def _required_mods(self):
        for stage_id, mods in HARD_MOD_BY_STAGE.items():
            if stage_id in self.active_normal_ids:
                for mod in mods:
                    self.mandatory_mods.add(mod)
                    self.base_pool[mod] = max(self.base_pool[mod], 1)

    def _upgrade_points(self):
        active_family_count = len(self.family_masteries)
        self.requested_mastery_count = len(self.requested_masteries)
        self.effective_families = max(active_family_count, self.requested_mastery_count)
        if self.compact:
            wup_policy = 3 * self.effective_families
        else:
            wup_policy = WEAPON_UPGRADE_POINTS_ITEM_COUNT
        self.base_pool[WEAPON_UPGRADE_POINTS_NAME] = wup_policy

    def _full_campaign_equipment(self):
        if not self.compact and (not self.lean):
            mod_quota = 12
            selected_mods = set(self.mandatory_mods)
            selected_mods.update(self.requested_mods)
            for mod in ALL_MODS_ORDERED:
                if len(selected_mods) >= mod_quota:
                    break
                selected_mods.add(mod)
            for mod in selected_mods:
                self.base_pool[mod] = max(self.base_pool[mod], 1)

    def _optional_equipment(self):
        for mod in ALL_MODS_ORDERED:
            if mod in self.mandatory_mods:
                self.optional_caps[mod] = 0
            else:
                self.optional_caps[mod] = max(0, 1 - self.base_pool.get(mod, 0))

    def _apply_overrides(self):
        for name, quantity in self.overrides.items():
            if quantity and (
                (name in SUPPORT_RUNE_NAMES and (not self.use_dlc))
                or (name in SPECIAL_WEAPON_POOL_COUNTS and name != self.special_name)
            ):
                raise PoolConfigurationError(player_text("apworld.errors", "override_unavailable", item=name))
            self.base_pool[name] = max(0, quantity - int(name == self.starting_weapon))
            self.optional_caps[name] = 0
        _deplete_starting_pool(self.base_pool, self.from_pool)

    def _validate_dependencies(self):
        available = Counter(self.base_pool) + self.start_inv
        if self.starting_weapon:
            available[self.starting_weapon] += 1
        if not _option_value(self.options, "randomize_dash"):
            available["Dash"] += 1
        if not _option_value(self.options, "randomize_chainsaw"):
            available["Chainsaw"] += 1
        for name in list(available):
            for dependency in ITEM_DEPENDENCIES.get(name, ()):
                if available[dependency] > 0:
                    continue
                if dependency in self.overrides:
                    raise PoolConfigurationError(
                        player_text("apworld.errors", "override_dependency", item=name, dependency=dependency)
                    )
                self.base_pool[dependency] = available[dependency] = 1
        self._validate_required_equipment(available)

    def _baseline(self):
        self.baseline: Counter[str] = Counter()
        for name, qty in self.start_inv.items():
            if name in item_data_table:
                self.baseline[name] += qty
        if self.starting_weapon:
            self.baseline[self.starting_weapon] += 1
        if not _option_value(self.options, "randomize_dash"):
            self.baseline["Dash"] = 1
        if not _option_value(self.options, "randomize_chainsaw"):
            self.baseline["Chainsaw"] = 1
        self._mastery_progression_baseline()
        for name in list(self.base_pool) + list(self.optional_caps):
            qty = self.base_pool.get(name, 0)
            if qty <= 0 or not _item_is_progression(name) or name in COMBAT_BASELINE_NAMES:
                continue
            self.baseline[name] += qty

    def _activation_budget(self):
        self.activatable: Counter[str] = Counter()
        for name in set(self.base_pool) | set(self.optional_caps):
            self.pool_copies = self.base_pool.get(name, 0) + self.optional_caps.get(name, 0)
            if self.pool_copies <= 0:
                continue
            self.in_baseline = 0
            if _item_is_progression(name) and name not in COMBAT_BASELINE_NAMES:
                self.in_baseline = self.base_pool.get(name, 0)
            budget = max(0, self.pool_copies - self.in_baseline)
            if budget > 0:
                self.activatable[name] = budget

    def _select_readiness(self):
        self.selection = ReadinessSelection(satisfied=True)
        if self.targets and (self.compact or self.lean or self.overrides):
            self.selection = select_readiness_items(
                base_items=self.baseline,
                targets=self.targets,
                additional=self.activatable,
                world_context=self.world_context,
                player=self.player,
            )
            self.pool.readiness_initial_deficit = self.selection.initial_deficit
            self.pool.readiness_final_deficit = self.selection.final_deficit
            if not self.selection.satisfied:
                raise PoolConfigurationError(
                    player_text(
                        "apworld.errors", "override_readiness", deficit=format(self.selection.final_deficit, "g")
                    )
                )

    def _placement_counts(self):
        self.used = self.selection.counts
        names = set(self.base_pool) | set(self.optional_caps) | set(self.used)
        for name in names:
            base_copies = self.base_pool.get(name, 0)
            self.in_baseline = 0
            if _item_is_progression(name) and name not in COMBAT_BASELINE_NAMES:
                self.in_baseline = base_copies
            self.pool_copies = max(base_copies, self.in_baseline + self.used.get(name, 0))
            self.pool_copies = min(self.pool_copies, base_copies + self.optional_caps.get(name, 0))
            if self.pool_copies > 0:
                self.pool.placement_counts[name] = self.pool_copies

    def _fit_budget(self):
        if (
            self.placement_budget is not None
            and sum(self.pool.placement_counts.values()) + sum(self.from_pool.values()) > self.placement_budget
        ):
            candidates = self._budget_candidates()
            while sum(self.pool.placement_counts.values()) + sum(self.from_pool.values()) > self.placement_budget:
                counts = self._inventory_counts()
                before_cr = evaluate_player_loadout_cr(
                    FastState.from_counts(counts, self.player), self.player, self.world_context
                ).total
                best = None
                best = self._least_cost_removal(candidates, counts, before_cr)
                if best is None:
                    break
                name = best[2]
                self.pool.placement_counts[name] -= 1
                self.pool.auto_adjustments[name] += 1
            self._record_budget_readiness()

    def _result(self):
        for name in set(self.pool.placement_counts) | set(self.from_pool):
            self.data = item_data_table.get(name)
            if self.data is None:
                continue
            self.pool.total_counts[name] = self.pool.placement_counts.get(name, 0) + self.from_pool.get(name, 0)
        for name, qty in self.used.items():
            if qty > 0 and name not in self.mandatory_mods and (name != WEAPON_UPGRADE_POINTS_NAME):
                self.pool.optional_selected[name] = min(qty, self.pool.placement_counts.get(name, 0))
        self.pool.auto_adjustments += Counter()
        return self.pool

    def _runes_and_capacities(self):
        for name, quantity in (self.suit_counts or {}).items():
            self.base_pool[name] = quantity
        for name in (*NORMAL_RUNES_ORDERED, *(SUPPORT_RUNES_ORDERED if self.use_dlc else ())):
            self.base_pool[name] = 1
        for stat in _CAPACITY_STATS:
            name = f"Progressive {stat} Upgrade"
            self.base_pool[name] = _CAPACITY_MAX_STAGES

    def _weapons_and_capabilities(self):
        for weapon in world_pool_weapon_item_names:
            if weapon == self.starting_weapon:
                continue
            self.base_pool[weapon] = 1
        self.base_pool["The Unmaykr"] = 1
        for equipment in CORE_EQUIPMENT:
            quantity = 4 if equipment == "Progressive Blood Punch" else 1
            self.base_pool[equipment] = quantity
        self.base_pool["Meat Hook"] = 1
        self.mandatory_mods.add("Meat Hook")
        if _option_value(self.options, "randomize_chainsaw") or self.start_inv.get("Chainsaw"):
            self.base_pool["Chainsaw"] = 1
        if _option_value(self.options, "randomize_dash") or self.start_inv.get("Dash"):
            self.base_pool["Dash"] = 1

    def _include_dependencies(self, name):
        for dep in ITEM_DEPENDENCIES.get(name, ()):
            if dep == self.starting_weapon or dep not in item_data_table:
                continue
            if dep in ALL_MOD_NAMES:
                self.mandatory_mods.add(dep)
            self.base_pool[dep] = max(self.base_pool[dep], 1)


    def _validate_required_equipment(self, available):
        required_mods = {mod for mod, _ in ORDERED_MASTERY_CHALLENGES[: self.active_masteries_count]}
        required_mods.update(
            (mod for stage_id, mods in HARD_MOD_BY_STAGE.items() if stage_id in self.active_normal_ids for mod in mods)
        )
        if set(self.active_normal_ids) & HOOK_TRAVERSAL_STAGES:
            required_mods.add("Meat Hook")
        for mod in required_mods:
            if available[mod] <= 0:
                raise PoolConfigurationError(player_text("apworld.errors", "override_required_mod", mod=mod))
        if available[WEAPON_UPGRADE_POINTS_NAME] < 3 * max(self.active_masteries_count, self.requested_mastery_count):
            raise PoolConfigurationError(player_text("apworld.errors", "override_mastery_points"))

    def _mastery_progression_baseline(self):
        mastery_victory_active = (
            "Complete All Weapon Mastery Challenges"
            in set(getattr(getattr(self.options, "additional_victory_requirements", None), "value", ()) or ())
            and self.effective_families > 0
        )
        wup_promoted = 0
        if mastery_victory_active:
            wup_promoted = min(3 * self.effective_families, self.base_pool.get(WEAPON_UPGRADE_POINTS_NAME, 0))
            self.baseline[WEAPON_UPGRADE_POINTS_NAME] += wup_promoted

    def _budget_candidates(self):
        from .generated_content import CAMPAIGN_CONNECTIONS
        from .logic import build_location_prerequisites, connection_requirement, required_item_names

        active_locations, active_regions = self._budget_locations()
        requirements = build_location_prerequisites(
            active_locations,
            active_region_names=active_regions,
            special_weapon=self.special_name,
            logic_difficulty=_option_value(self.options, "logic_difficulty", 1),
            active_spend_groups=self.active_sg,
            enemy_plan=getattr(self.world_context, "enemy_plan", None),
        )
        hard_items = set().union(*(required_item_names(req) for req in requirements.values()))
        for source, destination, _, condition in CAMPAIGN_CONNECTIONS:
            if source in active_regions and destination in active_regions:
                hard_items.update(required_item_names(connection_requirement(condition)))
        if "Blood Punch" in hard_items:
            hard_items.add("Progressive Blood Punch")
        locked = set(self.overrides) | set(self.start_inv)
        if _option_value(self.options, "praetor_suit_upgrades_in_pool", -2) != -2:
            locked.update(self.suit_counts or {})
        return (set(ALL_MOD_NAMES) | set(ALL_MASTERY_NAMES) | {"Progressive Blood Punch"}) - locked - hard_items

    def _inventory_counts(self):
        counts = self.pool.placement_counts + self.start_inv
        if self.starting_weapon:
            counts[self.starting_weapon] += 1
        for name, option in (("Dash", "randomize_dash"), ("Chainsaw", "randomize_chainsaw")):
            if not _option_value(self.options, option):
                counts[name] = max(1, counts[name])
        return counts

    def _least_cost_removal(self, candidates, counts, before_cr):
        best = None
        for name in sorted(candidates):
            if self.pool.placement_counts[name] <= 0:
                continue
            reduced = self._removable_counts(name, counts)
            if reduced is None:
                continue
            state = FastState.from_counts(reduced, self.player)
            cr = evaluate_player_loadout_cr(state, self.player, self.world_context).total
            results = [
                evaluate_mission_readiness(
                    state,
                    self.player,
                    target.stage_id,
                    self.world_context,
                    context=target.context,
                    player_cr=cr,
                )
                for target in self.targets or ()
            ]
            if not all(result.ready for result in results):
                continue
            score = (before_cr - cr, -counts[name], name)
            if best is None or score < best:
                best = score
        return best

    def _removable_counts(self, name, counts):
        minimum = int(name.startswith("Progressive "))
        if counts[name] <= minimum:
            return None
        reduced = counts.copy()
        reduced[name] -= 1
        if any(
            (reduced[parent] and any((reduced[dep] <= 0 for dep in deps)) for parent, deps in ITEM_DEPENDENCIES.items())
        ):
            return None
        return reduced

    def _record_budget_readiness(self):
        state = FastState.from_counts(self._inventory_counts(), self.player)
        results = [
            evaluate_mission_readiness(state, self.player, target.stage_id, self.world_context, context=target.context)
            for target in self.targets or ()
        ]
        if results:
            self.pool.readiness_final_deficit = max(
                max(result.effective_cr - result.player_cr - result.allowance, result.preparation_deficit)
                if result.preparation_deficit > 0
                else result.effective_cr - result.player_cr - result.allowance
                for result in results
            )

    def _budget_locations(self):
        from .locations import location_data_table

        stage_ids = {target.stage_id for target in self.targets or ()} | set(self.active_normal_ids)
        regions = {region for stage in CAMPAIGN_STAGES if stage["id"] in stage_ids for region in stage["regions"]}
        mastery_locations = {name for _, name in ORDERED_MASTERY_CHALLENGES[: self.active_masteries_count]}
        active_locations = {
            name
            for name, data in location_data_table.items()
            if self._budget_location_enabled(name, data, regions, mastery_locations)
        }
        active_regions = regions | {location_data_table[name].region for name in active_locations}
        return active_locations, active_regions

    def _budget_location_enabled(self, name, data, regions, mastery_locations):
        from .locations import optional_location_enabled

        return (
            data.code is not None
            and optional_location_enabled(name, self.options)
            and (data.region in regions or data.region.startswith("Fortress of Doom") or name in mastery_locations)
            and (not name.endswith(" - Weapon Mastery Challenge") or name in mastery_locations)
        )
