"""Seed-time unified campaign decisions, active content filtering, and structural CollectionState rules."""
from collections import Counter
from dataclasses import replace
import itertools
from .generated_content import CAMPAIGN_STAGES
from .logic import goal_endpoint_event_name, mission_clear_event_name
from .locations import location_data_table
from .combat_rating import (
    WEAPON_NAMES,
    ALL_MOD_NAMES,
    ITEM_CONTRIBUTIONS,
    NORMAL_RUNE_NAMES,
    SUPPORT_RUNE_NAMES,
    evaluate_player_loadout_cr,
)
from .combat_readiness import (
    evaluate_mission_readiness,
    is_mission_ready,
    MISSION_BASE_CR,
    SPIRIT_BREAKPOINTS,
)

STAGE_BY_ID = {stage["id"]: stage for stage in CAMPAIGN_STAGES}
STAGE_BY_NAME = {stage["name"]: stage for stage in CAMPAIGN_STAGES}
REGION_STAGE = {region: stage["id"] for stage in CAMPAIGN_STAGES for region in stage["regions"]}

BASE_GATE_STAGE_IDS = (
    "e1m2_war",
    "e1m3_cult",
    "e2m1_nest",
    "e2m2_base",
    "e2m3_core",
    "e3m1_slayer",
)

STAGE_SLAYER_GATE_KEYS = {
    "e1m2_war": "Slayer Gate Key Exultia",
    "e1m3_cult": "Slayer Gate Key Cultist Base",
    "e2m1_nest": "Slayer Gate Key Super Gore Nest",
    "e2m2_base": "Slayer Gate Key ARC Complex",
    "e2m3_core": "Slayer Gate Key Mars Core",
    "e3m1_slayer": "Slayer Gate Key Taras Nabad",
    "e4m1_rig": "Slayer Gate Key UAC Atlantica Facility",
    "e4m3_mcity": "Slayer Gate Key The Holt",
}

FORTRESS_NON_CONSUMER_LOCATIONS = frozenset({
    "Fortress of Doom - Fortress of Doom Codex Entry",
    "Fortress of Doom - Flame Belch",
    "Fortress of Doom - Ice Bomb",
    "Fortress of Doom - Sentinel Crystal - Bridge Story Pickup",
    "Fortress of Doom - Praetor Suit Token - Story Suit Tutorial",
    "Fortress of Doom - Ballista",
})
FORTRESS_BOOTSTRAP_LOCATIONS = FORTRESS_NON_CONSUMER_LOCATIONS

FORTRESS_SPEND_GROUPS = (
    {
        "id": "SG_LOWER_EAST",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Crystal - Battery Room Lower East",),
    },
    {
        "id": "SG_LOWER_WEST",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Crystal - Battery Room Lower West",),
    },
    {
        "id": "SG_UPPER_EAST_MODBOT",
        "cost": 2,
        "locations": ("Fortress of Doom - Modbot - Battery Room Upper East",),
    },
    {
        "id": "SG_UPPER_WEST_MODBOT",
        "cost": 2,
        "locations": ("Fortress of Doom - Modbot - Battery Room Upper West",),
    },
    {
        "id": "SG_UPPER_EAST_PRAETOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Battery Room Upper East",),
    },
    {
        "id": "SG_UPPER_WEST_PRAETOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Battery Room Upper West",),
    },
    {
        "id": "SG_ELEVATOR_EAST",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Elevator Room East",),
    },
    {
        "id": "SG_ELEVATOR_WEST",
        "cost": 2,
        "locations": ("Fortress of Doom - Praetor Suit Token - Elevator Room West",),
    },
    {
        "id": "SG_UPPER_SPIRE_CHEAT",
        "cost": 2,
        "locations": ("Fortress of Doom - Fully Upgraded Suit Cheat Code",),
    },
    {
        "id": "SG_SENTINEL_ARMOR",
        "cost": 2,
        "locations": ("Fortress of Doom - Sentinel Armor",),
    },
    {
        "id": "SG_CLASSIC_MARINE",
        "cost": 2,
        "locations": ("Fortress of Doom - Classic Marine Suit",),
    },
    {
        "id": "SG_PRAETOR_AND_RUNES",
        "cost": 2,
        "locations": (
            "Fortress of Doom - Praetor Suit",
            "Fortress of Doom - All Runes Cheat Code",
        ),
    },
)
SPEND_GROUP_BY_ID = {sg["id"]: sg for sg in FORTRESS_SPEND_GROUPS}

ORDERED_MASTERY_CHALLENGES = (
    ("Sticky Bombs", "Sticky Bombs - Weapon Mastery Challenge"),
    ("Precision Bolt", "Precision Bolt - Weapon Mastery Challenge"),
    ("Heat Blast", "Heat Blast - Weapon Mastery Challenge"),
    ("Remote Detonate", "Remote Detonate - Weapon Mastery Challenge"),
    ("Arbalest", "Arbalest - Weapon Mastery Challenge"),
    ("Energy Shield", "Energy Shield - Weapon Mastery Challenge"),
    ("Full Auto", "Full Auto - Weapon Mastery Challenge"),
    ("Micro Missiles", "Micro Missiles - Weapon Mastery Challenge"),
    ("Microwave Beam", "Microwave Beam - Weapon Mastery Challenge"),
    ("Lock-on Burst", "Lock-on Burst - Weapon Mastery Challenge"),
    ("Meat Hook", "Meat Hook - Weapon Mastery Challenge"),
    ("Destroyer Blade", "Destroyer Blade - Weapon Mastery Challenge"),
    ("Mobile Turret", "Mobile Turret - Weapon Mastery Challenge"),
)


def completion_event(stage_id):
    stage = STAGE_BY_ID[stage_id]
    return (goal_endpoint_event_name("Kill the Dark Lord") if stage["kind"] == "boss"
            else mission_clear_event_name(stage["name"]))


def get_short_world_scaling(
    active_normal_stage_ids: list[str],
    mission_location_count: int,
    mode: str,
    include_weapon_masteries: bool = True,
):
    n = len(active_normal_stage_ids)
    if n <= 3:
        if mission_location_count <= 28:
            active_sg = FORTRESS_SPEND_GROUPS[:1]
            active_masteries = 0
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        elif mission_location_count <= 36:
            active_sg = FORTRESS_SPEND_GROUPS[:2]
            active_masteries = 1
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        elif mission_location_count <= 50:
            active_sg = FORTRESS_SPEND_GROUPS[:3]
            active_masteries = 2
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
        else:
            active_sg = FORTRESS_SPEND_GROUPS[:4]
            active_masteries = 2
            battery_surplus = 0 if mode.startswith("MAI") or mode == "Mission Access as Items" else 1
    elif n <= 5:
        active_sg = FORTRESS_SPEND_GROUPS[:4]
        active_masteries = 3
        battery_surplus = 1
    elif n <= 8:
        active_sg = FORTRESS_SPEND_GROUPS[:8]
        active_masteries = 5
        battery_surplus = 1
    else:
        active_sg = FORTRESS_SPEND_GROUPS  # all 12
        active_masteries = 13
        battery_surplus = 1

    if not include_weapon_masteries:
        active_masteries = 0

    return active_sg, active_masteries, battery_surplus


def select_active_normal_missions(candidate_ids, requested_count, forced_ids, rng):
    candidates = sorted(candidate_ids)
    effective_count = len(candidates) if requested_count == "all" or requested_count == 0 else min(int(requested_count), len(candidates))
    effective_count = max(3, effective_count)
    if forced_ids:
        effective_count = max(effective_count, len(forced_ids))
    selected = sorted(forced_ids)
    rem = effective_count - len(selected)
    if rem > 0:
        pool = sorted(set(candidates) - set(forced_ids))
        selected.extend(rng.sample(pool, rem))
    return sorted(selected)


ITEM_DEPS = {
    "Sticky Bombs": ("Combat Shotgun",),
    "Full Auto": ("Combat Shotgun",),
    "Precision Bolt": ("Heavy Cannon",),
    "Micro Missiles": ("Heavy Cannon",),
    "Heat Blast": ("Plasma Rifle",),
    "Microwave Beam": ("Plasma Rifle",),
    "Remote Detonate": ("Rocket Launcher",),
    "Lock-on Burst": ("Rocket Launcher",),
    "Arbalest": ("Ballista",),
    "Destroyer Blade": ("Ballista",),
    "Mobile Turret": ("Chaingun",),
    "Energy Shield": ("Chaingun",),
    "Meat Hook": ("Super Shotgun",),
    "Faster Dash Recharge": ("Dash",),
}


class FastState:
    __slots__ = ('prog_items', 'player')

    def __init__(self, items=None, player=1):
        self.prog_items = Counter(items or ())
        self.player = player

    def count(self, item_name, player):
        return self.prog_items[item_name]

    def has(self, item_name, player):
        return self.prog_items[item_name] > 0

    def copy(self):
        st = FastState(player=self.player)
        st.prog_items = Counter(self.prog_items)
        return st

    def collect(self, item_name):
        self.prog_items[item_name] += 1


def resolve_dependencies(package, base_state, player, pool_counts):
    """Ensure all dependencies for package are satisfied by base_state or package.
    Returns (valid, complete_package).
    """
    full = list(package)
    counts = Counter(full)
    added = True
    while added:
        added = False
        for it in list(full):
            for dep in ITEM_DEPS.get(it, ()):
                if not base_state.has(dep, player) and counts[dep] == 0:
                    if pool_counts.get(dep, 0) > counts[dep]:
                        full.append(dep)
                        counts[dep] += 1
                        added = True
                    else:
                        return False, ()
    for it, req_qty in counts.items():
        if req_qty > pool_counts.get(it, 0):
            return False, ()
    return True, tuple(full)


SPIRIT_STAGE_IDS = frozenset(SPIRIT_BREAKPOINTS.values())

DLC_STAGE_IDS = frozenset({
    "e4m1_rig", "e4m2_swamp", "e4m3_mcity",
    "e5m1_spear", "e5m2_earth", "e5m3_hell", "e5m4_boss",
})


def _start_stage_readiness(state, player, stage_id, world_context):
    """Readiness required to choose stage_id as a starting mission.

    A starting-stage bootstrap must cover every mandatory gate the player has to
    pass to complete the start mission and reach progression, not only the
    mission-root entrance:
    - mission-root readiness (base CR, or Dark Lord readiness),
    - the mandatory Spirit breakpoint when the stage has one,
    - from_the_beginning traversal requirements (Dash and, for TAG2 stages,
      Super Shotgun + ammo-resource producer).
    """
    context = "dark_lord_defeated" if stage_id == "e5m4_boss" else "base"
    result = evaluate_mission_readiness(state, player, stage_id, world_context, context=context)
    if stage_id in SPIRIT_STAGE_IDS:
        breakpoint = evaluate_mission_readiness(
            state, player, stage_id, world_context, context="spirit_breakpoint"
        )
        if breakpoint.deficit > result.deficit:
            result = breakpoint
    if context == "base" and stage_id in DLC_STAGE_IDS:
        timing = getattr(getattr(world_context, "options", None), "dlc_logic_timing", None)
        if timing is not None and getattr(timing, "value", 0) == 1:
            if not is_mission_ready(state, player, stage_id, world_context, context="base"):
                result = replace(result, ready=False)
    return result


def solve_stage_bootstrap(
    stage_id: str,
    world_context,
    base_state: FastState,
    pool_counts: Counter,
    active_sg_count: int = 4,
):
    """Compute minimal readiness bootstrap cost and items for stage_id."""
    player = base_state.player
    res_0 = _start_stage_readiness(base_state, player, stage_id, world_context)
    if res_0.ready:
        return {
            "stage_id": stage_id,
            "bootstrap_cost": 0,
            "bootstrap_items": (),
            "placed_items": (),
            "initial_cr": res_0.player_cr,
            "final_cr": res_0.player_cr,
            "effective_cr": res_0.effective_cr,
            "overshoot": res_0.allowance - res_0.deficit,
        }

    # Available items in pool that contribute to CR or capacity
    combat_pool = {
        name: cnt for name, cnt in pool_counts.items()
        if cnt > 0 and (
            name in WEAPON_NAMES
            or name in ALL_MOD_NAMES
            or name in ITEM_CONTRIBUTIONS
            or name in NORMAL_RUNE_NAMES
            or name in SUPPORT_RUNE_NAMES
            or name in {"The Crucible", "Sentinel Hammer", "Progressive Special Weapon"}
        )
    }
    battery_pool_count = pool_counts.get("Sentinel Battery Bundle", 0)

    # Categories
    all_weapons = []
    for w in ["Super Shotgun", "Ballista", "Chaingun", "Rocket Launcher", "Plasma Rifle", "Heavy Cannon",
              "The Crucible", "Sentinel Hammer", "Progressive Special Weapon", "Combat Shotgun"]:
        cnt = combat_pool.get(w, 0)
        if cnt > 0:
            if "Progressive" in w:
                all_weapons.extend([w] * min(cnt, 2))
            else:
                all_weapons.append(w)
    all_mods = [
        m for m in ["Energy Shield", "Lock-on Burst", "Arbalest", "Precision Bolt", "Microwave Beam",
                    "Sticky Bombs", "Mobile Turret", "Heat Blast", "Remote Detonate", "Full Auto",
                    "Micro Missiles", "Destroyer Blade", "Meat Hook"]
        if combat_pool.get(m, 0) > 0
    ]
    all_equip = [
        e for e in ["Dash", "Chainsaw", "Ice Bomb", "Flame Belch", "Frag Grenade", "Blood Punch"]
        if combat_pool.get(e, 0) > 0
    ]

    primary_candidates = all_weapons + all_mods + all_equip

    def eval_pkg(pkg):
        st = base_state.copy()
        for it in pkg:
            st.collect(it)
        r = _start_stage_readiness(st, player, stage_id, world_context)
        cr = evaluate_player_loadout_cr(st, player, world_context).total
        return r, cr

    def iter_placed_combos(k, candidates, max_capacity):
        other_cands = [c for c in candidates if c not in all_weapons]
        max_w = min(k, len(all_weapons), 3)
        min_w = 2 if k >= 4 else (1 if k >= 2 else 0)
        for n_w in range(max_w, min_w - 1, -1):
            for w_combo in itertools.combinations(all_weapons, n_w):
                rem_k = k - n_w
                if rem_k <= len(other_cands):
                    for other_combo in itertools.combinations(other_cands, rem_k):
                        yield w_combo + other_combo

    # 1. Search for B = 0 (up to 6 placed items in free Fortress checks)
    best_zero = None
    target_cr = res_0.effective_cr - res_0.allowance
    if target_cr <= 77.5:
        for k in range(1, 7):
            for combo in iter_placed_combos(k, primary_candidates, 6):
                valid, full = resolve_dependencies(combo, base_state, player, combat_pool)
                if not valid or len(full) > 6:
                    continue
                r, cr = eval_pkg(full)
                if r.ready:
                    overshoot = r.allowance - r.deficit
                    cand = (len(full), overshoot, tuple(sorted(full)), cr, r.effective_cr)
                    if best_zero is None or cand < best_zero:
                        best_zero = cand
            if best_zero is not None and best_zero[0] == k:
                break

    if best_zero is not None:
        return {
            "stage_id": stage_id,
            "bootstrap_cost": 0,
            "bootstrap_items": (),
            "placed_items": best_zero[2],
            "initial_cr": res_0.player_cr,
            "final_cr": best_zero[3],
            "effective_cr": best_zero[4],
            "overshoot": best_zero[1],
        }

    # 2. Search for B > 0 (minimal bootstrap)
    for B in range(1, 6):
        best_b = None
        for b_bat in range(min(B, battery_pool_count, active_sg_count) + 1):
            b_combat = B - b_bat
            bat_pkg = ("Sentinel Battery Bundle",) * b_bat
            extra_capacity = min(b_bat, active_sg_count)
            placed_capacity = 6 + extra_capacity

            combat_boot_pool = all_weapons + all_mods + all_equip
            boot_combos = [()] if b_combat == 0 else itertools.combinations(combat_boot_pool, b_combat)

            for c_boot in boot_combos:
                boot_pkg = bat_pkg + c_boot
                valid_b, full_boot = resolve_dependencies(boot_pkg, base_state, player, pool_counts)
                if not valid_b or len(full_boot) != B:
                    continue

                rem_pool = Counter(pool_counts)
                for it in full_boot:
                    rem_pool[it] -= 1

                placed_cands = [c for c in primary_candidates if rem_pool[c] > 0]

                ranked_placed = [
                    c for c in [
                        "Dash", "Super Shotgun", "Ballista", "Chaingun", "Progressive Special Weapon",
                        "The Crucible", "Sentinel Hammer",
                        "Energy Shield", "Flame Belch", "Ice Bomb", "Blood Punch", "Destroyer Blade",
                        "Arbalest", "Lock-on Burst", "Rocket Launcher", "Plasma Rifle", "Microwave Beam",
                        "Precision Bolt", "Sticky Bombs", "Mobile Turret", "Heat Blast", "Remote Detonate",
                        "Chainsaw",
                    ] if rem_pool[c] > 0
                ]
                placed_sample = tuple(ranked_placed[:placed_capacity])
                valid_p, full_p = resolve_dependencies(placed_sample, base_state, player, rem_pool)
                if valid_p and len(full_p) <= placed_capacity:
                    full_total = full_boot + full_p
                    r, cr = eval_pkg(full_total)
                    if r.ready:
                        overshoot = r.allowance - r.deficit
                        best_b = (overshoot, len(full_total), full_boot, tuple(sorted(full_p)), cr, r.effective_cr)
                        break
            if best_b is not None:
                break

        if best_b is not None:
            return {
                "stage_id": stage_id,
                "bootstrap_cost": B,
                "bootstrap_items": best_b[2],
                "placed_items": best_b[3],
                "initial_cr": res_0.player_cr,
                "final_cr": best_b[4],
                "effective_cr": best_b[5],
                "overshoot": best_b[0],
            }

    return {
        "stage_id": stage_id,
        "bootstrap_cost": 999,
        "bootstrap_items": (),
        "placed_items": (),
        "initial_cr": res_0.player_cr,
        "final_cr": 0.0,
        "effective_cr": 0.0,
        "overshoot": 0.0,
    }


def build_pool_candidate_counts(options, active_normal_ids, starting_weapon, active_sg, active_masteries_count):
    n_normals = len(active_normal_ids)
    start_inv = options.start_inventory.value
    counts = Counter()

    world_pool_weapons = [
        "Combat Shotgun", "Heavy Cannon", "Plasma Rifle",
        "Rocket Launcher", "Super Shotgun", "Ballista", "Chaingun"
    ]
    for w in world_pool_weapons:
        if w != starting_weapon:
            counts[w] = 1 - min(1, start_inv.get(w, 0))

    for eq in ("Frag Grenade", "Blood Punch", "Flame Belch", "Ice Bomb"):
        counts[eq] = 1 - min(1, start_inv.get(eq, 0))

    if options.randomize_chainsaw.value:
        counts["Chainsaw"] = 1 - min(1, start_inv.get("Chainsaw", 0))
    if options.randomize_dash.value:
        counts["Dash"] = 1 - min(1, start_inv.get("Dash", 0))

    dlc_enabled = bool(options.use_dlc_content.value)
    spec_name = "The Crucible" if not dlc_enabled else options.special_weapon.current_option_name
    spec_count = 2 if dlc_enabled and "Progressive" in spec_name else 1
    counts[spec_name] = max(1, spec_count - min(spec_count, start_inv.get(spec_name, 0)))

    PRIMARY_BASE_MODS = [
        "Sticky Bombs", "Precision Bolt", "Microwave Beam",
        "Remote Detonate", "Arbalest", "Energy Shield",
    ]
    SECONDARY_MODS = [
        "Full Auto", "Micro Missiles", "Heat Blast",
        "Lock-on Burst", "Destroyer Blade", "Mobile Turret",
    ]
    ALL_MODS = PRIMARY_BASE_MODS + SECONDARY_MODS
    mod_quota = 6 if n_normals <= 3 else (8 if n_normals <= 5 else (10 if n_normals <= 8 else 12))
    for m in ALL_MODS[:mod_quota]:
        counts[m] = 1 - min(1, start_inv.get(m, 0))

    sg_count = len(active_sg)
    if sg_count > 0:
        counts["Sentinel Battery Bundle"] = max(1, sg_count)

    NORMAL_RUNES = [
        "Savagery", "Seek and Destroy", "Blood Fueled",
        "Air Control", "Dazed and Confused", "Saving Throw",
        "Chrono Strike", "Equipment Fiend", "Punch and Reave",
    ]
    rune_quota = 3 if n_normals <= 3 else (5 if n_normals <= 5 else (7 if n_normals <= 8 else 9))
    for r in NORMAL_RUNES[:rune_quota]:
        counts[r] = 1 - min(1, start_inv.get(r, 0))

    if dlc_enabled:
        SUPPORT_RUNES = ["Desperate Punch", "Take Back", "Break Through"]
        sup_quota = 1 if n_normals <= 3 else (2 if n_normals <= 8 else 3)
        for s in SUPPORT_RUNES[:sup_quota]:
            counts[s] = 1 - min(1, start_inv.get(s, 0))

    cap_count = 1 if n_normals <= 3 else (2 if n_normals <= 5 else (3 if n_normals <= 8 else 4))
    for stat in ("Health", "Armor", "Ammo"):
        counts[f"Progressive {stat} Upgrade"] = max(1, cap_count - start_inv.get(f"Progressive {stat} Upgrade", 0))

    return counts


def make_plan(options, rng, world=None):
    pool_name = options.mission_pool.current_option_name
    goal_name = options.goal.current_option_name
    order_mode = options.mission_order.value  # 0: Vanilla, 1: RMO, 2: MAI

    # 1. Candidate resolution
    if pool_name == "Base":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["source"] == "base" and s["kind"] == "mission"]
        dark_lord_candidate = False
    elif pool_name == "Full Saga":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["kind"] == "mission"]
        dark_lord_candidate = True
    elif pool_name == "DLC Only":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["source"] in ("tag1", "tag2") and s["kind"] == "mission"]
        dark_lord_candidate = True
    elif pool_name == "Custom":
        custom_vals = set(options.custom_missions.value)
        candidate_normal_ids = [
            s["id"] for s in CAMPAIGN_STAGES
            if s["kind"] == "mission" and (s["name"] in custom_vals or s["id"] in custom_vals)
        ]
        dark_lord_candidate = bool(options.custom_dark_lord.value)
        if len(candidate_normal_ids) < 3:
            raise ValueError("DOOM Eternal Custom Mission Pool requires at least 3 normal missions.")
    else:
        raise ValueError(f"Unknown Mission Pool: {pool_name}")

    # 2. Auto-promote Use DLC Content if DLC missions or Dark Lord are present
    has_dlc = any(STAGE_BY_ID[s]["source"] in ("tag1", "tag2") for s in candidate_normal_ids) or dark_lord_candidate
    if has_dlc and not options.use_dlc_content.value:
        options.use_dlc_content.value = 1

    # 3. Goal normalization
    goal_forced_active = False
    forced_normal_ids = set()
    goal_stage = None

    if goal_name == "Kill the Icon of Sin":
        goal_stage = "e3m4_boss"
        if "e3m4_boss" not in candidate_normal_ids:
            candidate_normal_ids.append("e3m4_boss")
            candidate_normal_ids.sort()
            goal_forced_active = True
        forced_normal_ids.add("e3m4_boss")
    elif goal_name == "Kill the Dark Lord":
        goal_stage = "e5m4_boss"
        if not dark_lord_candidate:
            dark_lord_candidate = True
            goal_forced_active = True
    elif goal_name == "Acquire the Unmaykr":
        if pool_name == "DLC Only":
            raise ValueError("DOOM Eternal Goal 'Acquire the Unmaykr' requires Base Slayer Gates and cannot be generated with DLC Only.")
        for gate_id in BASE_GATE_STAGE_IDS:
            if gate_id not in candidate_normal_ids:
                candidate_normal_ids.append(gate_id)
                candidate_normal_ids.sort()
                goal_forced_active = True
            forced_normal_ids.add(gate_id)
    elif goal_name == "Complete the Full Saga":
        candidate_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["kind"] == "mission"]
        dark_lord_candidate = True
        final = options.full_saga_final_boss.value
        if order_mode == 0:
            final = 2
        elif final == 0:
            final = rng.choice((1, 2))
        goal_stage = "e3m4_boss" if final == 1 else "e5m4_boss"

    # 4. Mission Count & Active Normal Missions selection
    raw_count = options.mission_count.value
    if order_mode == 0:
        # Vanilla Order ignores count and uses all candidate missions in chronological order
        requested_count = "all" if raw_count == 0 else raw_count
        effective_count = len(candidate_normal_ids)
        active_normal_ids = [s["id"] for s in CAMPAIGN_STAGES if s["id"] in candidate_normal_ids]
    else:
        if goal_name == "Complete the Full Saga":
            requested_count = "all"
            effective_count = len(candidate_normal_ids)
        elif raw_count == 0:
            requested_count = "all"
            effective_count = len(candidate_normal_ids)
        else:
            requested_count = raw_count
            effective_count = min(raw_count, len(candidate_normal_ids))
            effective_count = max(3, effective_count)

        if goal_name == "Acquire the Unmaykr":
            effective_count = max(6, effective_count)

        active_normal_ids = select_active_normal_missions(
            candidate_normal_ids,
            effective_count,
            forced_normal_ids,
            rng,
        )

    dark_lord_active = bool(dark_lord_candidate)
    active_stage_ids = list(active_normal_ids)
    if dark_lord_active:
        active_stage_ids.append("e5m4_boss")

    # Short-world scaling parameters
    active_stage_set = set(active_stage_ids)
    vanilla_physical_locations = {
        "Hell on Earth - Chainsaw": options.randomize_chainsaw.value,
        "Exultia - Dash": options.randomize_dash.value,
        "Exultia - Sentinel Battery - King Novik Return Path": options.randomize_first_battery.value,
    }
    mission_loc_count = 0
    for loc_name, loc_data in location_data_table.items():
        stage_id = REGION_STAGE.get(loc_data.region)
        if stage_id in active_stage_set:
            if loc_name in vanilla_physical_locations and not vanilla_physical_locations[loc_name]:
                continue
            mission_loc_count += 1

    active_sg, active_masteries_count, battery_surplus = get_short_world_scaling(
        active_normal_ids,
        mission_loc_count,
        options.mission_order.current_option_name,
        bool(options.include_weapon_mastery_challenges.value),
    )

    # Resolve generated starting weapon
    starting_weapon = options.starting_weapon.selected_weapon_name
    if starting_weapon is None:
        eligible_weapons = [
            w for w in (
                "Combat Shotgun", "Heavy Cannon", "Plasma Rifle",
                "Rocket Launcher", "Super Shotgun", "Ballista", "Chaingun"
            )
            if not options.start_inventory.value.get(w, 0)
        ]
        starting_weapon = rng.choice(eligible_weapons or ["Combat Shotgun"])

    # Build base items for bootstrap evaluation
    player = getattr(world, "player", 1)
    base_items = []
    for name, qty in options.start_inventory.value.items():
        base_items.extend([name] * qty)
    base_items.append(starting_weapon)
    if options.reveal_ap_locations_on_automap.value:
        base_items.append("Fortress of Doom - Automap Pod Offline")

    def get_candidate_base_state(s_id: str) -> FastState:
        candidate_items = list(base_items)
        if not options.randomize_dash.value and s_id not in {"e1m1_intro", "e1m2_war"}:
            candidate_items.append("Dash")
        if not options.randomize_chainsaw.value and s_id != "e1m1_intro":
            candidate_items.append("Chainsaw")
        return FastState(candidate_items, player=player)

    pool_counts = build_pool_candidate_counts(
        options, active_normal_ids, starting_weapon, active_sg, active_masteries_count
    )

    class MinimalWorldContext:
        def __init__(self, opts, plyr):
            self.options = opts
            self.player = plyr

    world_context = world if world is not None else MinimalWorldContext(options, player)

    # 5. Order sequencing & starts (Readiness-Aware, Phase 7.7c §4 & §5)
    ordinary = [s for s in active_normal_ids if s != goal_stage]
    if dark_lord_active and "e5m4_boss" != goal_stage and "e5m4_boss" not in ordinary:
        ordinary.append("e5m4_boss")

    # Evaluate bootstrap for candidate starts
    candidate_results = {}
    for s_id in ordinary:
        candidate_results[s_id] = solve_stage_bootstrap(
            s_id, world_context, get_candidate_base_state(s_id), pool_counts, len(active_sg)
        )

    if order_mode == 0:
        # Vanilla Order
        sequence = list(active_normal_ids)
        if dark_lord_active and "e5m4_boss" not in sequence:
            sequence.append("e5m4_boss")
        starts = [sequence[0]]
        chosen_start = sequence[0]
        chosen_result = candidate_results.get(
            chosen_start,
            solve_stage_bootstrap(chosen_start, world_context, get_candidate_base_state(chosen_start), pool_counts, len(active_sg))
        )
        access = []
        goal_as_item = False
    elif order_mode == 1:
        # Random Mission Order (§4)
        min_cost = min(candidate_results[s]["bootstrap_cost"] for s in ordinary)
        tied_candidates = [s for s in ordinary if candidate_results[s]["bootstrap_cost"] == min_cost]
        min_effective_cr = min(candidate_results[s]["effective_cr"] for s in tied_candidates)
        headroom_candidates = sorted(s for s in tied_candidates if candidate_results[s]["effective_cr"] == min_effective_cr)
        chosen_start = rng.choice(headroom_candidates)
        chosen_result = candidate_results[chosen_start]

        rem_ordinary = [s for s in ordinary if s != chosen_start]
        rng.shuffle(rem_ordinary)
        sequence = [chosen_start] + rem_ordinary + ([goal_stage] if goal_stage else [])
        starts = [chosen_start]
        access = []
        goal_as_item = False
    elif order_mode == 2:
        # Mission Access as Items (§5)
        min_cost = min(candidate_results[s]["bootstrap_cost"] for s in ordinary)
        tied_candidates = [s for s in ordinary if candidate_results[s]["bootstrap_cost"] == min_cost]
        min_effective_cr = min(candidate_results[s]["effective_cr"] for s in tied_candidates)
        headroom_candidates = sorted(s for s in tied_candidates if candidate_results[s]["effective_cr"] == min_effective_cr)
        chosen_start = rng.choice(headroom_candidates)
        chosen_result = candidate_results[chosen_start]

        eff_starts = min(options.starting_missions.value, len(ordinary))
        eff_starts = max(1, eff_starts)
        rem_ordinary = [s for s in ordinary if s != chosen_start]
        rng.shuffle(rem_ordinary)

        starts = [chosen_start] + rem_ordinary[:eff_starts - 1]
        other_stages = rem_ordinary[eff_starts - 1:]
        access = list(other_stages)
        goal_as_item = bool(goal_stage and options.goal_mission_as_item.value)
        if goal_as_item and goal_stage:
            access.append(goal_stage)
        sequence = starts + other_stages + ([goal_stage] if goal_stage else [])

    # 6. Bootstrap inventory
    bootstrap_inventory = {}
    if not options.randomize_dash.value and any(key not in {"e1m1_intro", "e1m2_war"} for key in starts):
        bootstrap_inventory["Dash"] = 1
    if not options.randomize_chainsaw.value and any(key != "e1m1_intro" for key in starts):
        bootstrap_inventory["Chainsaw"] = 1

    bootstrap_cost = chosen_result["bootstrap_cost"]
    readiness_bootstrap_items = list(chosen_result["bootstrap_items"])
    battery_bootstrap_items = [it for it in readiness_bootstrap_items if it == "Sentinel Battery Bundle"]
    combat_bootstrap_items = [it for it in readiness_bootstrap_items if it != "Sentinel Battery Bundle"]

    return {
        "schema": 1,
        "mode": options.mission_order.current_option_name,
        "difficulty": options.campaign_difficulty.value,
        "sequence": sequence,
        "starting_stages": starts,
        "starting_weapon": starting_weapon,
        "goal_stage": goal_stage,
        "goal_as_item": goal_as_item,
        "bootstrap_inventory": bootstrap_inventory,
        "bootstrap_cost": bootstrap_cost,
        "readiness_bootstrap_items": readiness_bootstrap_items,
        "battery_bootstrap_items": battery_bootstrap_items,
        "combat_bootstrap_items": combat_bootstrap_items,
        "bootstrap_stage": chosen_start,
        "bootstrap_placed_items": list(chosen_result["placed_items"]),
        "bootstrap_initial_cr": chosen_result["initial_cr"],
        "bootstrap_final_cr": chosen_result["final_cr"],
        "bootstrap_effective_cr": chosen_result["effective_cr"],
        "bootstrap_overshoot": chosen_result["overshoot"],
        "active_spend_groups": active_sg,
        "active_masteries_count": active_masteries_count,
        "battery_surplus": battery_surplus,
        "access_items": {str(STAGE_BY_ID[stage]["access_id"]): stage for stage in access},
        "stages": [dict(STAGE_BY_ID[stage]) for stage in active_stage_ids],
        "stage_ids": active_stage_ids,
        "active_normal_missions": active_normal_ids,
        "active_normal_mission_ids": active_normal_ids,
        "dark_lord_active": dark_lord_active,
        "requested_mission_count": requested_count,
        "effective_mission_count": effective_count,
        "mission_pool": pool_name,
        "goal_forced_active": goal_forced_active,
        "hub": {"id": "hub", "map": "game/hub/hub"},
    }


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
        predecessors = plan["sequence"][:plan["sequence"].index(stage_id)]
    return all(state.has(completion_event(stage), player) for stage in predecessors)
