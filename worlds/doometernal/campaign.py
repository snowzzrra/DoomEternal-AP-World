"""Seed-time unified campaign decisions, active content filtering, and structural CollectionState rules."""

import itertools
import logging
from collections import Counter

from Options import OptionError

from .combat_rating import (
    ALL_MOD_NAMES,
    ITEM_CONTRIBUTIONS,
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    WEAPON_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    ENDURANCE_STAGES,
    MISSION_BASE_CR,
    SPIRIT_BREAKPOINTS,
    ReadinessTarget,
    derive_readiness_targets,
    evaluate_mission_readiness,
    get_mission_effort_per_check,
    get_mission_intrinsic_cr,
    select_readiness_items,
)
from .enemy_options import uses_protected_opening
from .fortress_economy import battery_surplus_limit
from .generated_content import (
    CAMPAIGN_STAGES,
    FORTRESS_POLICY,
    FORTRESS_SPEND_GROUPS,
    LOCATION_ROWS,
    RESOURCE_NEUTRAL_LOCATION_NAMES,
)
from .item_pool import build_semantic_counts
from .items import suit_perk_item_names
from .locations import location_data_table, optional_location_enabled
from .logic import CRUCIBLE_CHALLENGE, crucible_challenge_enabled, goal_endpoint_event_name, mission_clear_event_name
from .native_enemy_safety import OPENING_REGIONS
from .options import MissionCount, resolve_praetor_suit_upgrade_count
from .planner import (
    ITEM_DEPENDENCIES,
    STAGE_BY_ID,
    FastState,
    is_compact_campaign,
    mastery_resource_family_count,
)
from .player_strings_generated import text as player_text

REGION_STAGE = {region: stage["id"] for stage in CAMPAIGN_STAGES for region in stage["regions"]}


BASE_GATE_STAGE_IDS = (
    "e1m2_war",
    "e1m3_cult",
    "e2m1_nest",
    "e2m2_base",
    "e2m3_core",
    "e3m1_slayer",
)

FORTRESS_NON_CONSUMER_LOCATIONS = frozenset(
    {
        "Fortress of Doom - Fortress of Doom Codex Entry",
        "Fortress of Doom - Flame Belch",
        "Fortress of Doom - Ice Bomb",
        "Fortress of Doom - Sentinel Crystal - Bridge Story Pickup",
        "Fortress of Doom - Praetor Suit Token - Story Suit Tutorial",
        "Fortress of Doom - Ballista",
        "Fortress of Doom - Fully Upgraded Suit Cheat Code",
    }
)
FORTRESS_BOOTSTRAP_LOCATIONS = frozenset(
    name
    for name, _, region in LOCATION_ROWS
    if name in FORTRESS_NON_CONSUMER_LOCATIONS and region == "Fortress of Doom - First Visit"
)


def completion_event(stage_id):
    stage = STAGE_BY_ID[stage_id]
    return (
        goal_endpoint_event_name("Kill the Dark Lord")
        if stage["kind"] == "boss"
        else mission_clear_event_name(stage["name"])
    )


def get_short_world_scaling(
    active_normal_stage_ids: list[str],
    include_weapon_masteries: bool = True,
):
    n = len(active_normal_stage_ids)
    if n <= 3:
        active_sg = FORTRESS_SPEND_GROUPS[:3]
    elif n <= 5:
        active_sg = FORTRESS_SPEND_GROUPS[:4]
    elif n <= 8:
        active_sg = FORTRESS_SPEND_GROUPS[:8]
    else:
        active_sg = FORTRESS_SPEND_GROUPS
    active_masteries = mastery_resource_family_count(n) if include_weapon_masteries else 0

    cost = sum(group["cost"] for group in active_sg)
    surplus = battery_surplus_limit(cost, FORTRESS_POLICY["battery_surplus_percent"])
    return active_sg, active_masteries, surplus


def select_active_normal_missions(candidate_ids, effective_count, forced_ids, rng):
    candidates = sorted(candidate_ids)
    selected = sorted(forced_ids)
    rem = effective_count - len(selected)
    if rem > 0:
        pool = sorted(set(candidates) - set(forced_ids))
        selected.extend(rng.sample(pool, rem))
    return sorted(selected)


ITEM_DEPS = ITEM_DEPENDENCIES


def resolve_dependencies(package, base_state, player, pool_counts):
    """Ensure all dependencies for package are satisfied by base_state or package.
    Returns (valid, complete_package).
    """
    full = list(package)
    counts = Counter(full)
    added = True
    while added:
        added = False
        for dep in _missing_dependencies(full, base_state, player, counts):
            if pool_counts.get(dep, 0) <= counts[dep]:
                return False, ()
            full.append(dep)
            counts[dep] += 1
            added = True
    for it, req_qty in counts.items():
        if req_qty > pool_counts.get(it, 0):
            return False, ()
    return True, tuple(full)


SPIRIT_STAGE_IDS = frozenset(SPIRIT_BREAKPOINTS.values())


def _start_stage_readiness(state, player, stage_id, world_context):
    """Readiness for entry, traversal and mandatory encounters in the starting mission."""
    context = "dark_lord_defeated" if stage_id == "e5m4_boss" else "base"
    if (
        stage_id in OPENING_REGIONS
        and uses_protected_opening(getattr(world_context, "enemies", {}))
        and (
            getattr(world_context, "enemy_plan", None) is None
            or world_context.enemy_plan["campaign"].get("opening_stage") == stage_id
        )
    ):
        context = "opening"
    result = evaluate_mission_readiness(state, player, stage_id, world_context, context=context)
    if stage_id in SPIRIT_STAGE_IDS and context != "opening":
        breakpoint = evaluate_mission_readiness(state, player, stage_id, world_context, context="spirit_breakpoint")
        if breakpoint.deficit > result.deficit:
            result = breakpoint
    return result


def solve_stage_bootstrap(
    stage_id: str,
    world_context,
    base_state: FastState,
    pool_counts: Counter,
    *,
    capacity=None,
):
    """Compute minimal readiness bootstrap cost and items for stage_id."""
    player = base_state.player
    free_capacity = len(FORTRESS_BOOTSTRAP_LOCATIONS) if capacity is None else capacity

    def readiness(state):
        if capacity is None:
            return _start_stage_readiness(state, player, stage_id, world_context)
        return evaluate_mission_readiness(state, player, stage_id, world_context)

    res_0 = readiness(base_state)
    if res_0.ready:
        return {
            "stage_id": stage_id,
            "bootstrap_cost": 0,
            "placed_items": (),
            "initial_cr": res_0.player_cr,
            "final_cr": res_0.player_cr,
            "effective_cr": res_0.effective_cr,
            "overshoot": res_0.allowance - res_0.deficit,
        }

    if capacity is not None or (stage_id in ENDURANCE_STAGES and res_0.context != "opening"):
        return _greedy_bootstrap(stage_id, world_context, base_state, pool_counts, free_capacity, res_0, readiness)

    combat_pool = _bootstrap_combat_pool(pool_counts)
    best_zero = _exhaustive_bootstrap(combat_pool, base_state, player, world_context, res_0, free_capacity, readiness)
    if best_zero is not None:
        return {
            "stage_id": stage_id,
            "bootstrap_cost": 0,
            "placed_items": best_zero[2],
            "initial_cr": res_0.player_cr,
            "final_cr": best_zero[3],
            "effective_cr": best_zero[4],
            "overshoot": best_zero[1],
        }

    return {
        "stage_id": stage_id,
        "bootstrap_cost": 999,
        "placed_items": (),
        "initial_cr": res_0.player_cr,
        "final_cr": 0.0,
        "effective_cr": 0.0,
        "overshoot": 0.0,
    }


def _master_levels(options, goal_name):
    masters = [s["id"] for s in CAMPAIGN_STAGES if s["kind"] == "master"] if options.include_master_levels.value else []
    if goal_name == "Complete N Master Levels":
        if not masters:
            raise OptionError(player_text("apworld.errors", "master_levels_disabled", objective=goal_name))
        if not 1 <= options.master_level_count.value <= len(masters):
            raise OptionError(player_text("apworld.errors", "master_level_count", maximum=len(masters)))
    if "Complete all Master Levels" in options.additional_victory_requirements.value and not masters:
        raise OptionError(
            player_text("apworld.errors", "master_levels_disabled", objective="Complete all Master Levels")
        )

    return masters


def make_plan(options, rng, world=None, *, candidate=None):
    builder = _CampaignPlanner(options=options, rng=rng, world=world, candidate=candidate)
    return builder.build()


def stage_available(plan, stage_id, state, player):
    if state.has(completion_event(stage_id), player):
        return True
    if stage_id in plan["starting_stages"]:
        return True
    if str(STAGE_BY_ID[stage_id]["access_id"]) in plan["access_items"]:
        return state.has(STAGE_BY_ID[stage_id]["name"] + " Access", player)
    if stage_id == plan["goal_stage"] and plan["mode"] == "mission_access_as_items":
        predecessors = [stage for stage in plan["sequence"] if stage != stage_id]
    else:
        predecessors = plan["sequence"][: plan["sequence"].index(stage_id)]
    return all(state.has(completion_event(stage), player) for stage in predecessors)


class _CampaignPlanner:
    def __init__(self, options, rng, world=None, *, candidate=None):
        self.candidate = candidate
        self.options = options
        self.rng = rng
        self.world = world

    def build(self):
        self._resolve_candidates()
        self._resolve_goal()
        self._select_missions()
        self._count_mission_locations()
        self._starting_equipment()
        self._prepare_readiness()
        self._select_suits()
        self._fit_pool()
        self._select_start()
        self._bootstrap_inventory()
        self._access_items()
        self._enemy_bands()
        return self._result()

    def _resolve_candidates(self):
        self.pool_name = self.options.mission_pool.current_option_name
        self.goal_name = self.options.goal.current_option_name
        self.order_mode = self.options.mission_order.value
        if self.goal_name == "Acquire the Unmaykr" and (not self.options.include_slayer_gates.value):
            raise OptionError(player_text("apworld.errors", "unmaykr_requires_gates"))
        self.masters = _master_levels(self.options, self.goal_name)
        self._mission_candidates()

    def _resolve_goal(self):
        self.goal_forced_active = False
        self.forced_normal_ids = set()
        self.goal_stage = None
        if self.goal_name == "Kill the Icon of Sin":
            self.goal_stage = "e3m4_boss"
            if "e3m4_boss" not in self.candidate_normal_ids:
                self.candidate_normal_ids.append("e3m4_boss")
                self.candidate_normal_ids.sort()
                self.goal_forced_active = True
            self.forced_normal_ids.add("e3m4_boss")
        elif self.goal_name == "Kill the Dark Lord":
            self.goal_stage = "e5m4_boss"
            if not self.dark_lord_candidate:
                self.dark_lord_candidate = True
                self.goal_forced_active = True
        elif self.goal_name == "Acquire the Unmaykr":
            if self.pool_name == "DLC Only":
                raise OptionError(player_text("apworld.errors", "unmaykr_requires_base"))
            self._require_gate_missions()
        elif self.goal_name == "Complete the Full Saga":
            self._full_saga_goal()

    def _select_missions(self):
        raw_count = self.options.mission_count.value
        if self.order_mode == 0:
            self.requested_count = "all" if raw_count == 0 else raw_count
            self.effective_count = len(self.candidate_normal_ids)
            self.active_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["id"] in self.candidate_normal_ids]
        else:
            if self.goal_name == "Complete the Full Saga":
                self.requested_count = "all"
                self.effective_count = len(self.candidate_normal_ids)
            elif raw_count == 0:
                self.requested_count = "all"
                self.effective_count = len(self.candidate_normal_ids)
            else:
                self.requested_count = raw_count
                self.effective_count = min(raw_count, len(self.candidate_normal_ids))
                self.effective_count = max(MissionCount.range_start, self.effective_count)
            if self.goal_name == "Acquire the Unmaykr":
                self.effective_count = max(6, self.effective_count)
            self.active_normal_ids = select_active_normal_missions(
                self.candidate_normal_ids, self.effective_count, self.forced_normal_ids, self.rng
            )
        self.dark_lord_active = bool(self.dark_lord_candidate)
        self.active_stage_ids = list(self.active_normal_ids)
        if self.dark_lord_active:
            self.active_stage_ids.append("e5m4_boss")
        self.active_stage_ids.extend(self.masters)

    def _count_mission_locations(self):
        self.active_stage_set = set(self.active_stage_ids)
        vanilla_physical_locations = {
            "Hell on Earth - Chainsaw": self.options.randomize_chainsaw.value,
            "Exultia - Dash": self.options.randomize_dash.value,
        }
        self.mission_loc_count = 0
        self.resource_mission_locations = 0
        for loc_name, loc_data in location_data_table.items():
            stage_id = REGION_STAGE.get(loc_data.region)
            if stage_id in self.active_stage_set:
                if not optional_location_enabled(loc_name, self.options):
                    continue
                if loc_name in vanilla_physical_locations and (not vanilla_physical_locations[loc_name]):
                    continue
                self.mission_loc_count += 1
                self.resource_mission_locations += int(loc_name not in RESOURCE_NEUTRAL_LOCATION_NAMES)
        self.active_sg, self.active_masteries_count, self.battery_surplus = get_short_world_scaling(
            self.active_normal_ids, bool(self.options.include_weapon_mastery_challenges.value)
        )

    def _starting_equipment(self):
        self.start_inventory = Counter(self.options.start_inventory.value) + Counter(
            getattr(getattr(self.options, "start_inventory_from_pool", None), "value", {})
        )
        self.starting_weapon = self.options.starting_weapon.selected_weapon_name
        if self.starting_weapon is None:
            eligible_weapons = [
                w
                for w in (
                    "Combat Shotgun",
                    "Heavy Cannon",
                    "Plasma Rifle",
                    "Rocket Launcher",
                    "Super Shotgun",
                    "Ballista",
                    "Chaingun",
                )
                if not self.start_inventory.get(w, 0)
            ]
            self.starting_weapon = self.rng.choice(eligible_weapons or ["Combat Shotgun"])

    def get_candidate_base_state(self, s_id: str) -> FastState:
        candidate_items = list(self.base_items)
        if not self.options.randomize_dash.value and s_id not in {"e1m1_intro", "e1m2_war"}:
            candidate_items.append("Dash")
        if not self.options.randomize_chainsaw.value and s_id != "e1m1_intro":
            candidate_items.append("Chainsaw")
        return FastState(candidate_items, player=self.player)

    def _prepare_readiness(self):
        self.player = getattr(self.world, "player", 1)
        self.base_items = []
        for name, qty in self.start_inventory.items():
            self.base_items.extend([name] * qty)
        self.base_items.append(self.starting_weapon)
        if self.options.reveal_ap_locations_on_automap.value:
            self.base_items.append("Fortress of Doom - Automap Pod Offline")

        class MinimalWorldContext:
            def __init__(self, opts, plyr):
                self.options = opts
                self.player = plyr

        self.world_context = self.world if self.world is not None else MinimalWorldContext(self.options, self.player)
        self.enemies = getattr(self.world_context, "enemies", {})
        self.vanilla_curve = self.enemies.get("revision", 0) >= 7 and self.enemies.get("balance_preset")
        self.use_opening = uses_protected_opening(self.enemies)
        self._provisional_campaign()
        self._account_special_challenge()

    def _select_suits(self):
        suit_option = self.options.praetor_suit_upgrades_in_pool.value
        self.profile = self.options.resource_profile.current_option_name
        effective_suit_count = (
            len(suit_perk_item_names)
            if suit_option == -2
            else resolve_praetor_suit_upgrade_count(suit_option, self.rng)
        )
        overrides = self.options.item_pool_counts.value
        requested_suits = {name for name in suit_perk_item_names if self.start_inventory.get(name)}
        explicit_suits = {name for name in suit_perk_item_names if overrides.get(name, 0) > 0}
        fixed_suits = requested_suits | explicit_suits
        suit_count = max(effective_suit_count, len(fixed_suits))
        candidates = [name for name in suit_perk_item_names if name not in fixed_suits and overrides.get(name, 1) > 0]
        self._validate_suit_selection(
            suit_option, explicit_suits, requested_suits, effective_suit_count, candidates, suit_count, fixed_suits
        )
        self.chosen_suits = fixed_suits | set(
            self.rng.sample(candidates, min(len(candidates), suit_count - len(fixed_suits)))
        )

    def evaluate_start_stage(self, s_id: str):
        return solve_stage_bootstrap(s_id, self.world_context, self.get_candidate_base_state(s_id), self.pool_counts)

    def _fit_pool(self):
        while True:
            hub_location_count = len(
                FORTRESS_NON_CONSUMER_LOCATIONS | {name for group in self.active_sg for name in group["locations"]}
            ) + int(set(BASE_GATE_STAGE_IDS).issubset(self.active_stage_set))
            self.resource_budget = self.resource_mission_locations + hub_location_count + self.active_masteries_count
            self.semantic_pool = build_semantic_counts(
                self.options,
                active_normal_ids=self.active_normal_ids,
                starting_weapon=self.starting_weapon,
                active_sg=self.active_sg,
                active_masteries_count=self.active_masteries_count,
                battery_surplus=self.battery_surplus,
                targets=self.readiness_targets,
                player=self.player,
                world_context=self.world_context,
                suit_counts={name: 1 for name in sorted(self.chosen_suits)},
                placement_budget=max(0, self.resource_budget - self.access_count),
            )
            shortfall = sum(self.semantic_pool.total_counts.values()) - max(0, self.resource_budget - self.access_count)
            if shortfall <= 0:
                break
            self._reduce_fortress_pool(shortfall)
        self._record_pool()

    def _select_start(self):
        if self.candidate is not None and self.order_mode != 2:
            self._reuse_start()
        elif self.order_mode == 0:
            self.sequence = self.provisional_sequence
            self.starts = [self.sequence[0]]
            self.chosen_start = self.sequence[0]
            self.chosen_result = self.evaluate_start_stage(self.chosen_start)
            self.access = []
            self.goal_as_item = False
        else:
            self._choose_start()
            if self.order_mode == 1:
                self._random_order()
            else:
                self._access_order()

    def _bootstrap_inventory(self):
        self.unprepared_start = self.chosen_result["bootstrap_cost"] >= 999
        if self.unprepared_start:
            initial = _start_stage_readiness(
                self.get_candidate_base_state(self.chosen_start), self.player, self.chosen_start, self.world_context
            )
            self.chosen_result = {
                **self.chosen_result,
                "bootstrap_cost": 0,
                "placed_items": (),
                "final_cr": initial.player_cr,
                "effective_cr": initial.effective_cr,
                "overshoot": initial.allowance - initial.deficit,
            }
            logging.info(player_text("apworld.notices", "unprepared_start", mission=self.chosen_start))
        self._fixed_equipment()

    def _access_items(self):
        self.semantic_counts = dict(self.semantic_pool.counts_view())
        self.semantic_placement_counts = dict(self.semantic_pool.placement_view())
        self.access.extend(self.masters)
        for stage in self.access:
            access_name = STAGE_BY_ID[stage]["name"] + " Access"
            self.semantic_counts[access_name] = self.semantic_counts.get(access_name, 0) + 1
            self.semantic_placement_counts[access_name] = self.semantic_placement_counts.get(access_name, 0) + 1

    def _enemy_bands(self):
        if self.order_mode == 2:
            ranked = [stage for stage in self.sequence if stage not in self.starts and stage != self.goal_stage]
            ranked = self._rank_enemy_stages(ranked)
            if self.goal_stage:
                ranked.append(self.goal_stage)
            self.enemy_bands = {stage: 0 for stage in self.starts}
            self.enemy_bands.update({stage: index + 1 for index, stage in enumerate(ranked)})
        else:
            self.enemy_bands = {stage: index for index, stage in enumerate(self.sequence)}

    def _result(self):
        return {
            "schema": 1,
            **(
                {"opening_stage": self.chosen_start}
                if self.chosen_start in OPENING_REGIONS and self.use_opening
                else {}
            ),
            **(
                {"composition_bands": dict(self.candidate["composition_bands"])}
                if self.candidate and "composition_bands" in self.candidate
                else {}
            ),
            "mode": self.options.mission_order.current_option_name,
            "difficulty": min(self.options.campaign_difficulty.value, 3),
            "logic_difficulty": self.options.logic_difficulty.current_option_name,
            "sequence": self.sequence,
            "master_level_stage_ids": self.masters,
            "enemy_progression_bands": self.enemy_bands,
            "starting_stages": self.starts,
            **({"unprepared_start_stages": [self.chosen_start]} if self.unprepared_start else {}),
            "starting_weapon": self.starting_weapon,
            "goal_stage": self.goal_stage,
            "goal_as_item": self.goal_as_item,
            "access_items": {str(STAGE_BY_ID[stage]["access_id"]): stage for stage in self.access},
            "stages": [dict(STAGE_BY_ID[stage]) for stage in self.active_stage_ids],
            "stage_ids": self.active_stage_ids,
            "active_normal_missions": self.active_normal_ids,
            "active_normal_mission_ids": self.active_normal_ids,
            "dark_lord_active": self.dark_lord_active,
            "requested_mission_count": self.requested_count,
            "effective_mission_count": self.effective_count,
            "mission_pool": self.pool_name,
            "goal_forced_active": self.goal_forced_active,
            "compact_short_world": self.semantic_pool.compact,
            "semantic_counts": self.semantic_counts,
            "praetor_suit_upgrades_in_pool": len(self.chosen_suits),
            "semantic_placement_counts": self.semantic_placement_counts,
            "resource_permanent_budget": self.resource_budget,
            "resource_auto_adjustments": dict(sorted(self.semantic_pool.auto_adjustments.items())),
            "readiness_selection": dict(sorted(self.semantic_pool.optional_selected.items())),
            "readiness_initial_deficit": round(self.semantic_pool.readiness_initial_deficit, 2),
            "readiness_final_deficit": round(self.semantic_pool.readiness_final_deficit, 2),
            "hub": {"id": "hub", "map": "game/hub/hub"},
            **self._fortress_metadata(),
            **self._preparation_metadata(),
        }

    def _mission_candidates(self):
        if self.pool_name == "Base":
            self.candidate_normal_ids = _mission_ids({"base"})
            self.dark_lord_candidate = False
        elif self.pool_name == "Full Saga":
            self.candidate_normal_ids = _mission_ids()
            self.dark_lord_candidate = True
        elif self.pool_name == "DLC Only":
            self.candidate_normal_ids = _mission_ids({"tag1", "tag2"})
            self.dark_lord_candidate = True
        elif self.pool_name == "Custom":
            self._custom_candidates()
        else:
            raise OptionError(player_text("apworld.errors", "unknown_mission_pool", pool=self.pool_name))

    def _custom_candidates(self):
        custom_vals = set(self.options.custom_missions.value)
        self.candidate_normal_ids = [
            s["id"]
            for s in CAMPAIGN_STAGES
            if s["kind"] == "mission" and (s["name"] in custom_vals or s["id"] in custom_vals)
        ]
        self.dark_lord_candidate = bool(self.options.custom_dark_lord.value)
        if len(self.candidate_normal_ids) < MissionCount.range_start:
            raise OptionError(player_text("apworld.errors", "custom_pool_minimum", minimum=MissionCount.range_start))

    def _require_gate_missions(self):
        for gate_id in BASE_GATE_STAGE_IDS:
            if gate_id not in self.candidate_normal_ids:
                self.candidate_normal_ids.append(gate_id)
                self.candidate_normal_ids.sort()
                self.goal_forced_active = True
            self.forced_normal_ids.add(gate_id)

    def _full_saga_goal(self):
        self.candidate_normal_ids = _mission_ids()
        self.dark_lord_candidate = True
        final = self.options.full_saga_final_boss.value
        if self.order_mode == 0:
            final = 2
        elif final == 0:
            final = self.rng.choice((1, 2))
        self.goal_stage = "e3m4_boss" if final == 1 else "e5m4_boss"

    def _provisional_campaign(self):
        self.ordinary = [s for s in self.active_normal_ids if s != self.goal_stage]
        if self.dark_lord_active and "e5m4_boss" != self.goal_stage and ("e5m4_boss" not in self.ordinary):
            self.ordinary.append("e5m4_boss")
        self.provisional_sequence = list(self.active_normal_ids)
        if self.dark_lord_active and "e5m4_boss" not in self.provisional_sequence:
            self.provisional_sequence.append("e5m4_boss")
        if self.order_mode == 0 and self.goal_stage:
            self.provisional_sequence.remove(self.goal_stage)
            self.provisional_sequence.append(self.goal_stage)
        provisional_plan = {
            "sequence": self.provisional_sequence,
            "master_level_stage_ids": self.masters,
            "active_normal_mission_ids": list(self.active_normal_ids),
            "goal_stage": self.goal_stage,
            "stage_ids": list(self.active_stage_ids),
        }
        self.world_context.campaign_plan = provisional_plan
        self.readiness_targets = derive_readiness_targets(self.options, provisional_plan)

    def _account_special_challenge(self):
        special_weapon = (
            self.options.special_weapon.current_option_name if self.options.use_dlc_content.value else "The Crucible"
        )
        if not crucible_challenge_enabled(special_weapon) and CRUCIBLE_CHALLENGE in location_data_table:
            if REGION_STAGE.get(location_data_table[CRUCIBLE_CHALLENGE].region) in self.active_stage_set:
                self.mission_loc_count -= 1
                self.resource_mission_locations -= 1
        self.eff_starts = max(1, min(self.options.starting_missions.value, len(self.ordinary)))
        self.access_count = (
            len(self.ordinary)
            - self.eff_starts
            + int(bool(self.goal_stage and self.options.goal_mission_as_item.value))
            if self.order_mode == 2
            else 0
        ) + len(self.masters)

    def _validate_suit_selection(
        self, suit_option, explicit_suits, requested_suits, effective_suit_count, candidates, suit_count, fixed_suits
    ):
        if suit_option >= 0 and (
            len(explicit_suits | requested_suits) > max(effective_suit_count, len(requested_suits))
            or len(candidates) < suit_count - len(fixed_suits)
        ):
            raise OptionError(player_text("apworld.errors", "suit_pool_conflict"))

    def _record_pool(self):
        self.chosen_suits = {name for name in self.chosen_suits if self.semantic_pool.total_counts.get(name, 0)}
        if self.semantic_pool.auto_adjustments:
            actual = sum(self.semantic_pool.placement_counts.values())
            logging.info(
                player_text(
                    "apworld.notices",
                    "resource_adjusted",
                    profile=self.profile,
                    original=actual + sum(self.semantic_pool.auto_adjustments.values()),
                    actual=actual,
                    budget=max(0, self.resource_budget - self.access_count),
                )
            )
        self.pool_counts = Counter(self.semantic_pool.placement_counts)

    def _reduce_fortress_pool(self, shortfall):
        if not is_compact_campaign(self.active_normal_ids):
            raise OptionError(player_text("apworld.errors", "item_pool_does_not_fit"))
        if self.battery_surplus:
            self.battery_surplus = max(0, self.battery_surplus - shortfall)
        elif self.active_sg and sum(group["cost"] for group in self.active_sg[:-1]) >= self.start_inventory.get(
            "Sentinel Battery", 0
        ):
            self.active_sg = self.active_sg[:-1]
        elif self.active_masteries_count:
            self.active_masteries_count -= 1
        else:
            raise OptionError(player_text("apworld.errors", "upgrade_pool_does_not_fit"))

    def _reuse_start(self):
        self.sequence = list(self.candidate["sequence"])
        self.starts = list(self.candidate["starting_stages"])
        self.chosen_start = self.candidate["bootstrap_stage"]
        self.chosen_result = self.evaluate_start_stage(self.chosen_start)
        if (
            self.order_mode == 1
            and (not self.vanilla_curve)
            and ((getattr(self.world_context, "enemy_plan", None) or {}).get("revision", 0) >= 3)
        ):
            self._rank_random_order()
        self.access = list(self.candidate["access_items"].values())
        self.goal_as_item = self.candidate["goal_as_item"]

    def _rank_random_order(self):
        bands = self.candidate["composition_bands"]
        import math

        ranked = sorted(
            self.ordinary,
            key=lambda stage: (
                get_mission_intrinsic_cr(stage, self.world_context)
                + min(12, 3 * math.log2(1 + get_mission_effort_per_check(stage, self.world_context))),
                bands[stage],
            ),
        )
        results = {
            stage: self.evaluate_start_stage(stage) for stage in ranked if STAGE_BY_ID[stage]["kind"] == "mission"
        }
        self.chosen_start = next(
            (stage for stage in results if results[stage]["bootstrap_cost"] < 999), next(iter(results))
        )
        self.chosen_result = results[self.chosen_start]
        self.sequence = (
            [self.chosen_start]
            + [stage for stage in ranked if stage != self.chosen_start]
            + ([self.goal_stage] if self.goal_stage else [])
        )
        self.starts = [self.chosen_start]

    def _choose_start(self):
        candidate_results = self._start_candidates()
        if not candidate_results:
            raise OptionError(player_text("apworld.errors", "progressive_opening_unavailable"))
        min_cost = min(result["bootstrap_cost"] for result in candidate_results.values())
        tied_candidates = [s for s in candidate_results if candidate_results[s]["bootstrap_cost"] == min_cost]
        tied_candidates = self._opening_check_candidates(tied_candidates)
        min_intrinsic_cr = min(MISSION_BASE_CR[s] for s in tied_candidates)
        headroom_candidates = sorted(
            s
            for s in tied_candidates
            if (self.order_mode == 2 and (not self.vanilla_curve)) or MISSION_BASE_CR[s] == min_intrinsic_cr
        )
        self.chosen_start = self.rng.choice(headroom_candidates)
        self.chosen_result = candidate_results[self.chosen_start]

    def _random_order(self):
        rem_ordinary = [s for s in self.ordinary if s != self.chosen_start]
        self.rng.shuffle(rem_ordinary)
        opening = [self.chosen_start]
        while rem_ordinary and len(opening) < 4:
            eligible = [stage for stage in rem_ordinary if MISSION_BASE_CR[stage] <= 63]
            stage = eligible[0] if eligible else min(rem_ordinary, key=MISSION_BASE_CR.__getitem__)
            opening.append(stage)
            rem_ordinary.remove(stage)
        self.sequence = opening + rem_ordinary + ([self.goal_stage] if self.goal_stage else [])
        self.starts = [self.chosen_start]
        self.access = []
        self.goal_as_item = False

    def _access_order(self):
        rem_ordinary = [s for s in self.ordinary if s != self.chosen_start]
        self.rng.shuffle(rem_ordinary)
        if self.use_opening:
            rem_ordinary.sort(key=lambda stage: stage not in OPENING_REGIONS)
        self.starts = [self.chosen_start] + rem_ordinary[: self.eff_starts - 1]
        other_stages = rem_ordinary[self.eff_starts - 1 :]
        self.access = list(other_stages)
        self.goal_as_item = bool(self.goal_stage and self.options.goal_mission_as_item.value)
        if self.goal_as_item and self.goal_stage:
            self.access.append(self.goal_stage)
        self.sequence = self.starts + other_stages + ([self.goal_stage] if self.goal_stage else [])

    def _opening_check_candidates(self, tied_candidates):
        if self.use_opening and self.order_mode == 2 and (self.candidate is None):
            checks = {
                stage: sum(
                    (
                        code is not None
                        and region in OPENING_REGIONS.get(stage, ())
                        and optional_location_enabled(name, self.options)
                        for name, code, region in LOCATION_ROWS
                    )
                )
                for stage in tied_candidates
            }
            minimum = min(8, sorted(checks.values())[len(checks) // 2])
            tied_candidates = [stage for stage in tied_candidates if checks[stage] >= minimum]
        return tied_candidates

    def _start_candidates(self):
        return {
            s_id: self.evaluate_start_stage(s_id)
            for s_id in self.ordinary
            if STAGE_BY_ID[s_id]["kind"] == "mission"
            and (not self.use_opening or self.start_inventory or s_id in OPENING_REGIONS)
            and (
                self.candidate is None
                or not self.candidate.get("opening_stage")
                or s_id == self.candidate["opening_stage"]
            )
        }

    def _fixed_equipment(self):
        self.bootstrap_inventory = {}
        if not self.options.randomize_dash.value and any(key not in {"e1m1_intro", "e1m2_war"} for key in self.starts):
            self.bootstrap_inventory["Dash"] = 1
        if not self.options.randomize_chainsaw.value and any(key != "e1m1_intro" for key in self.starts):
            self.bootstrap_inventory["Chainsaw"] = 1

    def _rank_enemy_stages(self, ranked):
        if self.vanilla_curve:
            order = {stage["id"]: index for index, stage in enumerate(CAMPAIGN_STAGES)}
            ranked.sort(key=order.__getitem__)
        elif self.candidate is not None and self.enemies.get("balance_preset"):
            ranked.sort(key=self.candidate["enemy_progression_bands"].__getitem__)
        elif self.enemies.get("balance_preset"):
            self.rng.shuffle(ranked)
        else:
            ranked.sort(key=lambda stage: (MISSION_BASE_CR[stage], stage))
        return ranked

    def _preparation_metadata(self):
        return {
            "bootstrap_inventory": self.bootstrap_inventory,
            "fixed_dash_completion_stage": None
            if self.options.randomize_dash.value or "Dash" in self.bootstrap_inventory
            else self.sequence[0],
            "bootstrap_stage": self.chosen_start,
            "bootstrap_placed_items": list(self.chosen_result["placed_items"]),
            "bootstrap_initial_cr": self.chosen_result["initial_cr"],
            "bootstrap_final_cr": self.chosen_result["final_cr"],
            "bootstrap_effective_cr": self.chosen_result["effective_cr"],
            "bootstrap_overshoot": self.chosen_result["overshoot"],
        }

    def _fortress_metadata(self):
        return {
            "active_spend_groups": self.active_sg,
            "active_masteries_count": self.active_masteries_count,
            "battery_surplus": self.battery_surplus,
            "battery_economy": {
                "cost": sum(group["cost"] for group in self.active_sg),
                "surplus": self.battery_surplus,
                "total": sum(group["cost"] for group in self.active_sg) + self.battery_surplus,
                "surplus_percent": FORTRESS_POLICY["battery_surplus_percent"],
                "native_first_battery": 0,
            },
            "fortress_phase_thresholds": [
                (
                    count * len([key for key in self.sequence if key != self.goal_stage])
                    + FORTRESS_POLICY["phase_completion_denominator"]
                    - 1
                )
                // FORTRESS_POLICY["phase_completion_denominator"]
                for count in FORTRESS_POLICY["phase_completion_weights"]
            ],
        }


def _missing_dependencies(package, state, player, counts):
    for name in list(package):
        for dependency in ITEM_DEPS.get(name, ()):
            if not state.has(dependency, player) and counts[dependency] == 0:
                yield dependency


def _greedy_bootstrap(stage_id, world_context, base_state, pool_counts, free_capacity, res_0, readiness):
    player = base_state.player
    # shortcut: greedy pruning can reject a legal package in a constrained pool.
    selection = _endurance_selection(stage_id, world_context, base_state, pool_counts, player, res_0)
    package = [step.item_name for step in selection.steps]
    if selection.satisfied:
        package = _prune_preparation(package, base_state, readiness)
    package = tuple(package)
    if selection.satisfied and len(package) <= free_capacity:
        state = base_state.copy()
        for name in package:
            state.collect(name)
        final = readiness(state)
        return {
            "stage_id": stage_id,
            "bootstrap_cost": 0,
            "placed_items": package,
            "initial_cr": res_0.player_cr,
            "final_cr": final.player_cr,
            "effective_cr": final.effective_cr,
            "overshoot": final.allowance - final.deficit,
        }
    return {
        "stage_id": stage_id,
        "bootstrap_cost": 999,
        "placed_items": (),
        "initial_cr": res_0.player_cr,
        "final_cr": 0.0,
        "effective_cr": 0.0,
        "overshoot": 0.0,
    }


def _bootstrap_combat_pool(pool_counts):
    return {
        name: cnt
        for name, cnt in pool_counts.items()
        if cnt > 0
        and (
            name in WEAPON_NAMES
            or name in ALL_MOD_NAMES
            or name in ITEM_CONTRIBUTIONS
            or name in NORMAL_RUNE_NAMES
            or name in SUPPORT_RUNE_NAMES
            or name in {"Chainsaw", "The Crucible", "Sentinel Hammer", "Progressive Special Weapon"}
        )
    }


def _prune_preparation(package, base_state, readiness):
    for name in tuple(package):
        reduced = package.copy()
        reduced.remove(name)
        state = base_state.copy()
        for item in reduced:
            state.collect(item)
        if readiness(state).ready:
            package = reduced
    return package


def _search_bootstrap(
    primary_candidates,
    combat_pool,
    free_capacity,
    base_state,
    player,
    world_context,
    res_0,
    resolve_cached,
    eval_pkg,
    preference,
):
    best_zero = None
    target_cr = res_0.effective_cr - res_0.allowance
    upper_state = base_state.copy()
    for item, count in combat_pool.items():
        for _ in range(count):
            upper_state.collect(item)
    max_total_cr = evaluate_player_loadout_cr(upper_state, player, world_context).total
    if target_cr <= max_total_cr:
        for k in range(1, free_capacity + 1):
            best_zero = _best_bootstrap_size(
                primary_candidates, k, combat_pool, free_capacity, resolve_cached, eval_pkg, preference, best_zero
            )
            if best_zero is not None and best_zero[0] == k:
                break
    return best_zero


def _exhaustive_bootstrap(combat_pool, base_state, player, world_context, res_0, free_capacity, readiness):
    primary_candidates = sorted(combat_pool)

    eval_cache: dict[tuple, tuple] = {}
    dep_cache: dict[tuple, tuple] = {}

    def eval_pkg(pkg):
        key = tuple(sorted(pkg))
        cached = eval_cache.get(key)
        if cached is not None:
            return cached
        st = base_state.copy()
        for it in pkg:
            st.collect(it)
        r = readiness(st)
        cr = r.player_cr
        result = (r, cr)
        eval_cache[key] = result
        return result

    def resolve_cached(package, count_pool):
        key = (tuple(package), tuple(sorted(count_pool.items())))
        cached = dep_cache.get(key)
        if cached is None:
            cached = resolve_dependencies(package, base_state, player, count_pool)
            dep_cache[key] = cached
        return cached

    def preference(package):
        weapons = (
            sum(name in WEAPON_NAMES for name in package[2])
            if getattr(world_context, "enemies", {}).get("enabled")
            else 0
        )
        return package[0], -weapons, package[1], package[2]

    return _search_bootstrap(
        primary_candidates,
        combat_pool,
        free_capacity,
        base_state,
        player,
        world_context,
        res_0,
        resolve_cached,
        eval_pkg,
        preference,
    )


def _endurance_selection(stage_id, world_context, base_state, pool_counts, player, res_0):
    opening = (
        res_0.context == "opening"
        and getattr(world_context, "enemies", {}).get("revision", 0) >= 7
        and getattr(world_context, "enemies", {}).get("balance_preset")
    )
    targets = [ReadinessTarget(stage_id, "opening" if opening else "base", "Starting endurance mission")]
    if stage_id in SPIRIT_STAGE_IDS and not opening:
        targets.append(ReadinessTarget(stage_id, "spirit_breakpoint", "Starting Spirit breakpoint"))
    return select_readiness_items(
        base_items=base_state.prog_items,
        targets=targets,
        additional=pool_counts,
        world_context=world_context,
        player=player,
        slack=0,
    )


def _best_bootstrap_size(
    primary_candidates, k, combat_pool, free_capacity, resolve_cached, eval_pkg, preference, best_zero
):
    for combo in itertools.combinations_with_replacement(primary_candidates, k):
        valid, full = resolve_cached(combo, combat_pool)
        if not valid or len(full) > free_capacity:
            continue
        r, cr = eval_pkg(full)
        if r.ready:
            overshoot = r.allowance - r.deficit
            cand = (len(full), overshoot, tuple(sorted(full)), cr, r.effective_cr)
            if best_zero is None or preference(cand) < preference(best_zero):
                best_zero = cand
    return best_zero


def _mission_ids(sources=None):
    return [
        stage["id"]
        for stage in CAMPAIGN_STAGES
        if stage["kind"] == "mission" and (sources is None or stage["source"] in sources)
    ]
