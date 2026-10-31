"""
To Test (Layer 1 - pure core of the recency score module, no DB):
- time_pressure(): t = 0, future last_encounter_time, upper bound, tier ordering, monotonic in t
- rel_interaction(): extremes, zero-passage guard, middle proportion
- hist_memory(): empty list, recency weighting, all-equal, single element
- rand_pick_new_words(): size cap, level exhaustion, "7-9" ordering, never skipping ahead,
  input dict left unchanged

NOTE: mem_score_list index 0 = MOST RECENT (the shell's query orders by timestamp desc).
"""

from datetime import datetime, timedelta

import pytest

from backend.generation import (
    hist_memory,
    rand_pick_new_words,
    rel_interaction,
    time_pressure,
)
from backend.schemas import StatusTier

# shared anchor for every datetime below
BASE_TIME = datetime(2026, 10, 1, 12, 0, 0)


# ---------------
# Time Pressure (time_pressure)
# ---------------
# A) Testing Scenarios
# --- Scenario 1: t = 0 (last encounter == now) ---
last_encounter_tp_1 = BASE_TIME
current_time_tp_1 = BASE_TIME
status_tier_tp_1 = StatusTier.LEARNING
expected_tp_1 = 0

# --- Scenario 2: last encounter is 2 days AFTER current time ---
last_encounter_tp_2 = BASE_TIME + timedelta(days=2)
current_time_tp_2 = BASE_TIME
status_tier_tp_2 = StatusTier.FAMILIAR
expected_tp_2 = 0

# --- Scenario 3: upper bound - very large t (1 year), slowest-rising tier ---
last_encounter_tp_3 = BASE_TIME
current_time_tp_3 = BASE_TIME + timedelta(days=365)
status_tier_tp_3 = StatusTier.LEARNING
expected_tp_3 = 1

# --- Scenario 4: tier ordering - same t (1 day) across all 4 tiers (non-parametrized) ---
last_encounter_tp_order = BASE_TIME
current_time_tp_order = BASE_TIME + timedelta(days=1)
tiers_tp_order = [
    StatusTier.LEARNING,
    StatusTier.FAMILIAR,
    StatusTier.SOLID,
    StatusTier.MASTERED,
]

# --- Scenario 5: monotonic in t - one tier, increasing current times (non-parametrized) ---
last_encounter_tp_mono = BASE_TIME
status_tier_tp_mono = StatusTier.SOLID
current_times_tp_mono = [
    BASE_TIME + timedelta(hours=1),
    BASE_TIME + timedelta(hours=12),
    BASE_TIME + timedelta(days=1),
    BASE_TIME + timedelta(days=3),
    BASE_TIME + timedelta(days=10),
]


# B) Parametrization
@pytest.mark.parametrize(
    "last_encounter_time, current_time, status_tier, expected",
    [
        pytest.param(
            last_encounter_tp_1,
            current_time_tp_1,
            status_tier_tp_1,
            expected_tp_1,
            id="t = 0",
        ),
        pytest.param(
            last_encounter_tp_2,
            current_time_tp_2,
            status_tier_tp_2,
            expected_tp_2,
            id="last encounter in future",
        ),
        pytest.param(
            last_encounter_tp_3,
            current_time_tp_3,
            status_tier_tp_3,
            expected_tp_3,
            id="upper bound (large t)",
        ),
    ],
)

# C) Function Call
def test_time_pressure(last_encounter_time, current_time, status_tier, expected):
    assert pytest.approx(expected) == time_pressure(
        last_encounter_time, current_time, status_tier
    )


def test_time_pressure_tier_ordering():
    time_pressures = []
    for status in tiers_tp_order:
        time_pressures.append(
            time_pressure(last_encounter_tp_order, current_time_tp_order, status)
        )

    for i in range(len(tiers_tp_order) - 1):
        assert time_pressures[i] > time_pressures[i + 1]


def test_time_pressure_monotonic():
    time_pressures = []
    for current_time in current_times_tp_mono:
        time_pressures.append(
            time_pressure(last_encounter_tp_mono, current_time, status_tier_tp_mono)
        )

    for i in range(len(current_times_tp_mono) - 1):
        assert time_pressures[i] < time_pressures[i + 1]


# ---------------
# Relative Interaction Pressure (rel_interaction)
# ---------------
# A) Testing Scenarios
# --- Scenario 1: zero appearances, nonzero passages ---
num_appearances_ri_1 = 0
num_passages_ri_1 = 10
expected_ri_1 = 1

# --- Scenario 2: appears in every passage ---
num_appearances_ri_2 = 10
num_passages_ri_2 = 10
expected_ri_2 = 0

# --- Scenario 3: zero passages total (guard) ---
num_appearances_ri_3 = 0
num_passages_ri_3 = 0
expected_ri_3 = 1

# --- Scenario 4: middle proportion ---
num_appearances_ri_4 = 3
num_passages_ri_4 = 10
expected_ri_4 = 0.7


# B) Parametrization
@pytest.mark.parametrize(
    "num_appearances, num_passages, expected",
    [
        pytest.param(
            num_appearances_ri_1,
            num_passages_ri_1,
            expected_ri_1,
            id="zero appearances",
        ),
        pytest.param(
            num_appearances_ri_2,
            num_passages_ri_2,
            expected_ri_2,
            id="in every passage",
        ),
        pytest.param(
            num_appearances_ri_3,
            num_passages_ri_3,
            expected_ri_3,
            id="zero passages",
        ),
        pytest.param(
            num_appearances_ri_4,
            num_passages_ri_4,
            expected_ri_4,
            id="middle proportion",
        ),
    ],
)

# C) Function Call
def test_rel_interaction(num_appearances, num_passages, expected):
    assert expected == rel_interaction(num_appearances, num_passages)


# ---------------
# Historical Memory (hist_memory)
# ---------------
# A) Testing Scenarios
# --- Scenario 1: empty list (no appearances yet) ---
mem_score_list_hm_1 = []
expected_hm_1 = 0.5

# --- Scenario 2: only the MOST RECENT appearance scored 1 ---
mem_score_list_hm_2 = [1.0, 0.0, 0.0, 0.0, 0.0]
expected_hm_2 = 0.7025226

# --- Scenario 3: only the OLDEST appearance scored 1 (mirror of scenario 2) ---
mem_score_list_hm_3 = [0.0, 0.0, 0.0, 0.0, 1.0]
expected_hm_3 = 0.87815326

# --- Scenario 4: all equal ---
mem_score_list_hm_4 = [0.6, 0.6, 0.6]
expected_hm_4 = 0.4

# --- Scenario 5: single element ---
mem_score_list_hm_5 = [0.7]
expected_hm_5 = 0.3

# --- Scenario 6: recency weighting, relative check (non-parametrized) ---
# reuses scenarios 2 & 3: recent-heavy vs. old-heavy
recent_heavy_hm = mem_score_list_hm_2
old_heavy_hm = mem_score_list_hm_3


# B) Parametrization
@pytest.mark.parametrize(
    "mem_score_list, expected",
    [
        pytest.param(mem_score_list_hm_1, expected_hm_1, id="empty list"),
        pytest.param(mem_score_list_hm_2, expected_hm_2, id="only most recent = 1"),
        pytest.param(mem_score_list_hm_3, expected_hm_3, id="only oldest = 1"),
        pytest.param(mem_score_list_hm_4, expected_hm_4, id="all equal"),
        pytest.param(mem_score_list_hm_5, expected_hm_5, id="single element"),
    ],
)

# C) Function Call
def test_hist_memory(mem_score_list, expected):
    assert pytest.approx(expected) == hist_memory(mem_score_list)


def test_hist_memory_recency_weighting():
    recent_score = hist_memory(recent_heavy_hm)
    old_score = hist_memory(old_heavy_hm)
    assert recent_score < old_score


# ---------------
# New Word Picker (rand_pick_new_words)
# ---------------
# NOTE: inputs chosen so outcomes are forced where possible (no patching `choice`).
# expected_size: exact len of the result
# expected_must_include: IDs that MUST be in the result (forced picks)
# expected_levels: every pick's level must be in this set

# A) Testing Scenarios
# --- Scenario 1: n < lowest level's size -> never skips ahead ---
num_new_words_rp_1 = 2
all_new_words_dict_rp_1 = {
    101: "1",
    102: "1",
    103: "1",
    104: "1",
    201: "2",
    202: "2",
    203: "2",
}
expected_size_rp_1 = 2
expected_must_include_rp_1 = []
expected_levels_rp_1 = ["1"]

# --- Scenario 2: n > whole pool -> capped at pool size ---
num_new_words_rp_2 = 5
all_new_words_dict_rp_2 = {101: "1", 102: "1", 201: "2"}
expected_size_rp_2 = 3
expected_must_include_rp_2 = [101, 102, 201]
expected_levels_rp_2 = ["1", "2"]

# --- Scenario 3: n = 0 ---
num_new_words_rp_3 = 0
all_new_words_dict_rp_3 = {101: "1", 102: "1", 201: "2"}
expected_size_rp_3 = 0
expected_must_include_rp_3 = []
expected_levels_rp_3 = []

# --- Scenario 4: empty pool, n > 0 ---
num_new_words_rp_4 = 3
all_new_words_dict_rp_4 = {}
expected_size_rp_4 = 0
expected_must_include_rp_4 = []
expected_levels_rp_4 = []

# --- Scenario 5: level "1" exhausted, level "2" has exactly ONE word -> fully forced ---
num_new_words_rp_5 = 3
all_new_words_dict_rp_5 = {
    101: "1",
    102: "1",
    201: "2",
    301: "3",
    302: "3",
}
expected_size_rp_5 = 3
expected_must_include_rp_5 = [101, 102, 201]
expected_levels_rp_5 = ["1", "2"]

# --- Scenario 6: "6" exhausted into "7-9" (real level labels, string ordering) ---
num_new_words_rp_6 = 3
all_new_words_dict_rp_6 = {
    7001: "7-9",
    7002: "7-9",
    7003: "7-9",
    601: "6",
    602: "6",
}
expected_size_rp_6 = 3
expected_must_include_rp_6 = [601, 602]
expected_levels_rp_6 = ["6", "7-9"]

# --- Scenario 7: input dict unchanged after call (non-parametrized) ---
num_new_words_rp_mut = 2
all_new_words_dict_rp_mut = {101: "1", 102: "1", 201: "2"}


# B) Parametrization
@pytest.mark.parametrize(
    "num_new_words, all_new_words_dict, expected_size, expected_must_include, expected_levels",
    [
        pytest.param(
            num_new_words_rp_1,
            all_new_words_dict_rp_1,
            expected_size_rp_1,
            expected_must_include_rp_1,
            expected_levels_rp_1,
            id="never skips ahead",
        ),
        pytest.param(
            num_new_words_rp_2,
            all_new_words_dict_rp_2,
            expected_size_rp_2,
            expected_must_include_rp_2,
            expected_levels_rp_2,
            id="n > pool",
        ),
        pytest.param(
            num_new_words_rp_3,
            all_new_words_dict_rp_3,
            expected_size_rp_3,
            expected_must_include_rp_3,
            expected_levels_rp_3,
            id="n = 0",
        ),
        pytest.param(
            num_new_words_rp_4,
            all_new_words_dict_rp_4,
            expected_size_rp_4,
            expected_must_include_rp_4,
            expected_levels_rp_4,
            id="empty pool",
        ),
        pytest.param(
            num_new_words_rp_5,
            all_new_words_dict_rp_5,
            expected_size_rp_5,
            expected_must_include_rp_5,
            expected_levels_rp_5,
            id="level exhausted (fully forced)",
        ),
        pytest.param(
            num_new_words_rp_6,
            all_new_words_dict_rp_6,
            expected_size_rp_6,
            expected_must_include_rp_6,
            expected_levels_rp_6,
            id="6 exhausted into 7-9",
        ),
    ],
)

# C) Function Call
def test_rand_pick_new_words(
    num_new_words,
    all_new_words_dict,
    expected_size,
    expected_must_include,
    expected_levels,
):
    new_words_set = rand_pick_new_words(num_new_words, all_new_words_dict)
    # check size
    assert len(new_words_set) == expected_size

    # check that all forced IDs are present
    assert set(expected_must_include) <= new_words_set

    # check all levels are present
    present_levels = set()
    for id in new_words_set:
        if all_new_words_dict[id] not in present_levels:
            present_levels.add(all_new_words_dict[id])

    assert set(expected_levels) == present_levels


def test_rand_pick_new_words_input_unchanged():
    cpy_dict = all_new_words_dict_rp_mut.copy()
    rand_pick_new_words(num_new_words_rp_mut, all_new_words_dict_rp_mut)
    assert cpy_dict == all_new_words_dict_rp_mut
