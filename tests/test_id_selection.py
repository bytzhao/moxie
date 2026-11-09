"""
To Test (Layer 2 - DB shell of the ID selection / recency score module):
- seed_claude_triples(): ID -> ClaudeVocabTriple mapping, empty input, shared chars/pinyin, unknown IDs
- get_new_words(): learning-count cap, allowance vs. frontier_max caps, tier filtering (decoys)
- get_elligible_ids(): ranking, no new words left, new words fill frontier, memory scores (last 10, correct order),
brand-new user (partition is implicitly checked w/ ID set match)
- compute_recency_scores(): one hand-traced scenario - every component + total per word,
  zero-appearance branch, NOT_ENCOUNTERED exclusion

NOTE: every test runs against a fresh in-memory DB from conftest.py's scratch_s_maker, seeded with
TOY_HSK_VOCAB (via data/seed.py's seed_hsk_vocab) + one user. Per-scenario UserVocab / Passages /
Appearances rows are seeded inside each test.
NOTE: row tuples below omit user_id (single-user PoC) - the seeding helper fills it in.

TODO (known-untested, deliberately):
- user isolation (a second user's rows leaking into counts / pools / appearances)
- the 50-passage cap in compute_recency_scores' rel. interaction query
"""

from datetime import datetime, timedelta
from math import exp
from statistics import mean

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.generation import (
    IdNotFoundError,
    compute_recency_scores,
    get_elligible_ids,
    get_new_words,
    seed_claude_triples,
)
from backend.models import Appearances, HskVocabulary, Passages, PassageState, UserVocab
from backend.schemas import ClaudeVocabTriple, RecencyScore, StatusTier
from data.hsk_vocab import HskEntry

# shared anchor for every datetime below (also passed as current_time)
BASE_TIME = datetime(2026, 10, 1, 12, 0, 0)

# ---------------
# Toy HSK Baseline (seeded by the fixture for EVERY test)
# ---------------
# Shape matches HSK_VOCAB: word -> tuple of HskEntry(pinyin, level, pos, traditional).
# vocab_ids come from autoincrement in INSERTION ORDER (dict order, then entry order) in a fresh DB,
# so the ID constants below depend on that order - don't reorder this dict without updating them.
# Every entry has a non-blank, distinct pos so dedupe_senses() never collapses anything.
TOY_HSK_VOCAB = {
    # --- named words (vocab_id 1-14) ---
    "我": (HskEntry("wo3", "1", "Pron", "我"),),  # 1
    "是": (HskEntry("shi4", "1", "V", "是"),),  # 2
    "事": (HskEntry("shi4", "2", "N", "事"),),  # 3  (same pinyin as 是)
    "长": (
        HskEntry("chang2", "2", "Adj", "長"),
        HskEntry("zhang3", "3", "V", "長"),
    ),  # 4, 5
    "会": (HskEntry("hui4", "1", "V", "會"), HskEntry("hui4", "3", "N", "會")),  # 6, 7
    "猫": (HskEntry("mao1", "2", "N", "貓"),),  # 8
    "学生": (HskEntry("xue2sheng5", "1", "N", "學生"),),  # 9
    "图书馆": (HskEntry("tu2shu1guan3", "2", "N", "圖書館"),),  # 10
    "发展": (HskEntry("fa1zhan3", "4", "V", "發展"),),  # 11
    "研究": (HskEntry("yan2jiu1", "5", "V", "研究"),),  # 12
    "起源": (HskEntry("qi3yuan2", "6", "N", "起源"),),  # 13
    "一一": (HskEntry("yi1yi1", "7-9", "Adv", "一一"),),  # 14
    # --- learning filler: 30 placeholder words, all level "3" (vocab_id 15-44) ---
    **{f"L{n:02d}": (HskEntry("-", "3", "Filler", f"L{n:02d}"),) for n in range(1, 31)},
    # --- not-encountered pool: 4 @ level "1", 4 @ level "2", 4 @ level "4" (vocab_id 45-56) ---
    **{f"N{n:02d}": (HskEntry("-", "1", "Pool", f"N{n:02d}"),) for n in range(1, 5)},
    **{f"N{n:02d}": (HskEntry("-", "2", "Pool", f"N{n:02d}"),) for n in range(5, 9)},
    **{f"N{n:02d}": (HskEntry("-", "4", "Pool", f"N{n:02d}"),) for n in range(9, 13)},
    # --- tier decoys: 4 words, all level "1" (vocab_id 57-60) ---
    **{f"D{n}": (HskEntry("-", "1", "Decoy", f"D{n}"),) for n in range(1, 5)},
}

LEARNING_FILLER_IDS = list(range(15, 45))  # 30 IDs, level "3"
NE_L1_IDS = list(range(45, 49))  # level "1"
NE_L2_IDS = list(range(49, 53))  # level "2"
NE_L4_IDS = list(range(53, 57))  # level "4"
DECOY_IDS = list(range(57, 61))  # level "1"


# fixture that wraps/returns toy dictionary
@pytest.fixture
def toy_vocab_dict():
    return TOY_HSK_VOCAB


# ---------------
# Row Builders (raw data only)
# ---------------
# UserVocab row:   (vocab_id, status_tier, points, last_encounter_time)
# Passages row:    (passage_id, state, answer_key)
# Appearances row: (vocab_id, passage_id, memory_score, timestamp)
def _uv_rows(ids, tier, last_encounter_time=BASE_TIME):
    """Same tier + last encounter for a batch of IDs."""
    return [(vid, tier, 0, last_encounter_time) for vid in ids]


# decoys: lowest level ("1") but NOT not-encountered -> must never be picked as new words.
# the LEARNING decoy (60) also counts toward the learning count.
DECOY_UV_ROWS = [
    (57, StatusTier.FAMILIAR, 0, BASE_TIME),
    (58, StatusTier.SOLID, 0, BASE_TIME),
    (59, StatusTier.MASTERED, 0, BASE_TIME),
    (60, StatusTier.LEARNING, 0, BASE_TIME),
]


def seed_rows_helper(
    scratch_s_maker: sessionmaker,
    user_vocab_rows: list,
    passage_rows: list,
    appearance_rows: list,
    user_id: int = 1,
):
    """Takes a list of UserVocab, Passage, and Appearances rows to seed using provided sessionmaker."""
    with scratch_s_maker() as session:
        user_vocabs = [
            UserVocab(
                user_id=user_id,
                vocab_id=vid,
                status_tier=tier,
                points=pts,
                last_encounter_time=time,
            )
            for vid, tier, pts, time in user_vocab_rows
        ]

        passages = [
            Passages(passage_id=pid, user_id=user_id, state=state, answer_key=answer)
            for pid, state, answer in passage_rows
        ]

        appearances = [
            Appearances(
                vocab_id=vid,
                user_id=user_id,
                passage_id=pid,
                memory_score=mscore,
                timestamp=time,
            )
            for vid, pid, mscore, time in appearance_rows
        ]

        session.add_all(passages + user_vocabs)
        session.flush()
        session.add_all(appearances)
        session.commit()


# ---------------
# Claude Triples (seed_claude_triples)
# ---------------
# A) Testing Scenarios
# --- Scenario 1: unique IDs, distinct chars + pinyin ---
id_set_sct_1 = {1, 8, 10}
expected_sct_1 = {
    1: ClaudeVocabTriple("我", "wo3", "Pron"),
    8: ClaudeVocabTriple("猫", "mao1", "N"),
    10: ClaudeVocabTriple("图书馆", "tu2shu1guan3", "N"),
}

# --- Scenario 2: empty input ---
id_set_sct_2 = set()
expected_sct_2 = {}

# --- Scenario 3: shared chars (长 4/5, 会 6/7), shared pinyin across chars (是 2 / 事 3),
#     and shared chars AND pinyin (会 6/7, differ only on sense) ---
id_set_sct_3 = {2, 3, 4, 5, 6, 7}
expected_sct_3 = {
    2: ClaudeVocabTriple("是", "shi4", "V"),
    3: ClaudeVocabTriple("事", "shi4", "N"),
    4: ClaudeVocabTriple("长", "chang2", "Adj"),
    5: ClaudeVocabTriple("长", "zhang3", "V"),
    6: ClaudeVocabTriple("会", "hui4", "V"),
    7: ClaudeVocabTriple("会", "hui4", "N"),
}

# --- Scenario 4: one known ID + one ID not in HskVocabulary (non-parametrized, raises) ---
id_set_sct_4 = {1, 999}


# B) Parametrization
@pytest.mark.parametrize(
    "id_set, expected",
    [
        pytest.param(id_set_sct_1, expected_sct_1, id="unique IDs"),
        pytest.param(id_set_sct_2, expected_sct_2, id="empty input"),
        pytest.param(id_set_sct_3, expected_sct_3, id="shared chars / pinyin"),
    ],
)

# C) Function Call
def test_seed_claude_triples(scratch_s_maker, id_set, expected):
    assert expected == seed_claude_triples(id_set, scratch_s_maker)


def test_seed_claude_triples_unknown_id(scratch_s_maker):
    with pytest.raises(IdNotFoundError) as e:
        seed_claude_triples(id_set_sct_4, scratch_s_maker)
    assert e.value.unknown_id == 999


# ---------------
# New Words (get_new_words)
# ---------------
# NOTE: every scenario's not-encountered pool is NE_L2_IDS + NE_L4_IDS (levels "2" and "4"),
# while DECOY_UV_ROWS sit at level "1" and the learning filler at level "3" - so a broken tier
# filter would pick a decoy/filler before any legit word.
# expected_size / expected_must_include / expected_levels: same meaning as test_rand_pick_new_words.
NE_POOL_UV_ROWS = _uv_rows(NE_L2_IDS + NE_L4_IDS, StatusTier.NOT_ENCOUNTERED)

# A) Testing Scenarios
# --- Scenario 1a: learning count exactly AT the cap (24 filler + LEARNING decoy = 25) ---
user_vocab_rows_gnw_1a = (
    _uv_rows(LEARNING_FILLER_IDS[:24], StatusTier.LEARNING)
    + DECOY_UV_ROWS
    + NE_POOL_UV_ROWS
)
frontier_max_gnw_1a = 5
expected_size_gnw_1a = 0
expected_must_include_gnw_1a = None
expected_levels_gnw_1a = None

# --- Scenario 1b: learning count OVER the cap (25 filler + LEARNING decoy = 26) ---
user_vocab_rows_gnw_1b = (
    _uv_rows(LEARNING_FILLER_IDS[:25], StatusTier.LEARNING)
    + DECOY_UV_ROWS
    + NE_POOL_UV_ROWS
)
frontier_max_gnw_1b = 5
expected_size_gnw_1b = 0
expected_must_include_gnw_1b = None
expected_levels_gnw_1b = None

# --- Scenario 2: allowance GREATER than frontier_max (10 filler + LEARNING decoy = 11 learning) ---
user_vocab_rows_gnw_2 = (
    _uv_rows(LEARNING_FILLER_IDS[:10], StatusTier.LEARNING)
    + DECOY_UV_ROWS
    + NE_POOL_UV_ROWS
)
frontier_max_gnw_2 = 5
expected_size_gnw_2 = 5
expected_must_include_gnw_2 = NE_L2_IDS
expected_levels_gnw_2 = ["2", "4"]

# --- Scenario 3: allowance SMALLER than frontier_max (22 filler + LEARNING decoy = 23 learning) ---
user_vocab_rows_gnw_3 = (
    _uv_rows(LEARNING_FILLER_IDS[:22], StatusTier.LEARNING)
    + DECOY_UV_ROWS
    + NE_POOL_UV_ROWS
)
frontier_max_gnw_3 = 5
expected_size_gnw_3 = 2
expected_must_include_gnw_3 = []
expected_levels_gnw_3 = ["2"]


# B) Parametrization
@pytest.mark.parametrize(
    "user_vocab_rows, frontier_max, expected_size, expected_must_include, expected_levels",
    [
        pytest.param(
            user_vocab_rows_gnw_1a,
            frontier_max_gnw_1a,
            expected_size_gnw_1a,
            expected_must_include_gnw_1a,
            expected_levels_gnw_1a,
            id="learning count at cap",
        ),
        pytest.param(
            user_vocab_rows_gnw_1b,
            frontier_max_gnw_1b,
            expected_size_gnw_1b,
            expected_must_include_gnw_1b,
            expected_levels_gnw_1b,
            id="learning count over cap",
        ),
        pytest.param(
            user_vocab_rows_gnw_2,
            frontier_max_gnw_2,
            expected_size_gnw_2,
            expected_must_include_gnw_2,
            expected_levels_gnw_2,
            id="allowance > frontier_max",
        ),
        pytest.param(
            user_vocab_rows_gnw_3,
            frontier_max_gnw_3,
            expected_size_gnw_3,
            expected_must_include_gnw_3,
            expected_levels_gnw_3,
            id="allowance < frontier_max",
        ),
    ],
)

# C) Function Call
def test_get_new_words(
    scratch_s_maker,
    user_vocab_rows,
    frontier_max,
    expected_size,
    expected_must_include,
    expected_levels,
):
    # add the rows using scratch_s_maker
    seed_rows_helper(scratch_s_maker, user_vocab_rows, [], [])

    new_words_set = get_new_words(1, frontier_max, scratch_s_maker)

    assert expected_size == len(new_words_set)

    # if length isn't 0, check must-include and expected levels
    if expected_size != 0:
        assert set(expected_must_include) <= new_words_set

        present_levels = set()

        # find present levels for all IDs
        with scratch_s_maker() as session:
            for id in new_words_set:
                hsk_level_query = (
                    select(HskVocabulary.hsk_level)
                    .select_from(HskVocabulary)
                    .where(HskVocabulary.vocab_id == id)
                )
                level = session.scalar(hsk_level_query)
                present_levels.add(level)

        assert set(expected_levels) == present_levels


# ---------------
# ID Selection (get_elligible_ids)
# ---------------
# NOTE: every scenario's new-word pool is sized/leveled so get_new_words' picks are FORCED,
# so all three expected ID sets can be exact.

# shared "urgent" vs. "calm" encountered words for the ranking-based scenarios (A, B)
# - urgent (1, 2, 4): FAMILIAR, last seen 30 days ago, 1 appearance (oldest passage), memory 0.0
# - calm   (6, 8, 9): FAMILIAR, last seen 1 hour ago, appears in all 5 passages, memory 1.0
URGENT_IDS = [1, 2, 4]
CALM_IDS = [6, 8, 9]
RANK_PASSAGE_TIMES = {
    1: BASE_TIME - timedelta(days=30),
    2: BASE_TIME - timedelta(days=4),
    3: BASE_TIME - timedelta(days=3),
    4: BASE_TIME - timedelta(days=2),
    5: BASE_TIME - timedelta(hours=1),
}
RANK_PASSAGE_ROWS = [(pid, PassageState.GRADED, "") for pid in RANK_PASSAGE_TIMES]
RANK_UV_ROWS = _uv_rows(
    URGENT_IDS, StatusTier.FAMILIAR, RANK_PASSAGE_TIMES[1]
) + _uv_rows(CALM_IDS, StatusTier.FAMILIAR, RANK_PASSAGE_TIMES[5])
RANK_APPEARANCE_ROWS = [(vid, 1, 0.0, RANK_PASSAGE_TIMES[1]) for vid in URGENT_IDS] + [
    (vid, pid, 1.0, ts) for vid in CALM_IDS for pid, ts in RANK_PASSAGE_TIMES.items()
]

# A) Testing Scenarios
# --- Scenario A: ranking - 2 new words (exactly 2 not-encountered left), 3 open frontier slots ---
user_vocab_rows_gei_a = RANK_UV_ROWS + _uv_rows(
    NE_L1_IDS[:2], StatusTier.NOT_ENCOUNTERED
)
passage_rows_gei_a = RANK_PASSAGE_ROWS
appearance_rows_gei_a = RANK_APPEARANCE_ROWS
frontier_max_gei_a = 5
expected_new_ids_gei_a = [45, 46]
expected_frontier_ids_gei_a = [45, 46, 1, 2, 4]
expected_other_ids_gei_a = [6, 8, 9]

# --- Scenario B: no new words left (zero not-encountered rows) ---
user_vocab_rows_gei_b = RANK_UV_ROWS
passage_rows_gei_b = RANK_PASSAGE_ROWS
appearance_rows_gei_b = RANK_APPEARANCE_ROWS
frontier_max_gei_b = 3
expected_new_ids_gei_b = []
expected_frontier_ids_gei_b = [1, 2, 4]
expected_other_ids_gei_b = [6, 8, 9]

# --- Scenario C: new words fill the frontier completely ---
# pool = 4 @ level "1" + 4 @ level "2" (pool > frontier_max); 3 encountered words, no passages yet
user_vocab_rows_gei_c = _uv_rows(
    NE_L1_IDS + NE_L2_IDS, StatusTier.NOT_ENCOUNTERED
) + _uv_rows([1, 2, 4], StatusTier.FAMILIAR)
passage_rows_gei_c = []
appearance_rows_gei_c = []
frontier_max_gei_c = 4
expected_new_ids_gei_c = [45, 46, 47, 48]
expected_frontier_ids_gei_c = [45, 46, 47, 48]
expected_other_ids_gei_c = [1, 2, 4]

# --- Scenario D: memory scores - last 10, correct order ---
# X (10) and Y (11): identical tier, last encounter, and appearances (all 12 passages);
# only the memory HISTORY differs:
# - X: 6 oldest scores 1.0, 6 most recent 0.0
# - Y: 6 oldest scores 0.0, 6 most recent 1.0
# taking the OLDEST 10, or weighting them oldest-first, flips which of X / Y wins the slot.
# no new words, 1 frontier slot
MEM_PASSAGE_TIMES = {pid: BASE_TIME - timedelta(days=13 - pid) for pid in range(1, 13)}
user_vocab_rows_gei_d = _uv_rows([10, 11], StatusTier.FAMILIAR, MEM_PASSAGE_TIMES[12])
passage_rows_gei_d = [(pid, PassageState.GRADED, "") for pid in MEM_PASSAGE_TIMES]
appearance_rows_gei_d = [
    (10, pid, 1.0 if pid <= 6 else 0.0, ts) for pid, ts in MEM_PASSAGE_TIMES.items()
] + [(11, pid, 0.0 if pid <= 6 else 1.0, ts) for pid, ts in MEM_PASSAGE_TIMES.items()]
frontier_max_gei_d = 1
expected_new_ids_gei_d = []
expected_frontier_ids_gei_d = [10]
expected_other_ids_gei_d = [11]

# --- Scenario E: brand-new user - zero encountered words, zero passages / appearances ---
# pool = 4 @ level "1" + 1 @ level "2" (exactly frontier_max words)
user_vocab_rows_gei_e = _uv_rows(NE_L1_IDS + NE_L2_IDS[:1], StatusTier.NOT_ENCOUNTERED)
passage_rows_gei_e = []
appearance_rows_gei_e = []
frontier_max_gei_e = 5
expected_new_ids_gei_e = [45, 46, 47, 48, 49]
expected_frontier_ids_gei_e = [45, 46, 47, 48, 49]
expected_other_ids_gei_e = []


# B) Parametrization
@pytest.mark.parametrize(
    "user_vocab_rows, passage_rows, appearance_rows, frontier_max, "
    "expected_new_ids, expected_frontier_ids, expected_other_ids",
    [
        pytest.param(
            user_vocab_rows_gei_a,
            passage_rows_gei_a,
            appearance_rows_gei_a,
            frontier_max_gei_a,
            expected_new_ids_gei_a,
            expected_frontier_ids_gei_a,
            expected_other_ids_gei_a,
            id="A ranking",
        ),
        pytest.param(
            user_vocab_rows_gei_b,
            passage_rows_gei_b,
            appearance_rows_gei_b,
            frontier_max_gei_b,
            expected_new_ids_gei_b,
            expected_frontier_ids_gei_b,
            expected_other_ids_gei_b,
            id="B no new words left",
        ),
        pytest.param(
            user_vocab_rows_gei_c,
            passage_rows_gei_c,
            appearance_rows_gei_c,
            frontier_max_gei_c,
            expected_new_ids_gei_c,
            expected_frontier_ids_gei_c,
            expected_other_ids_gei_c,
            id="C new words fill frontier",
        ),
        pytest.param(
            user_vocab_rows_gei_d,
            passage_rows_gei_d,
            appearance_rows_gei_d,
            frontier_max_gei_d,
            expected_new_ids_gei_d,
            expected_frontier_ids_gei_d,
            expected_other_ids_gei_d,
            id="D memory last 10 + order",
        ),
        pytest.param(
            user_vocab_rows_gei_e,
            passage_rows_gei_e,
            appearance_rows_gei_e,
            frontier_max_gei_e,
            expected_new_ids_gei_e,
            expected_frontier_ids_gei_e,
            expected_other_ids_gei_e,
            id="E brand-new user",
        ),
    ],
)

# C) Function Call
def test_get_elligible_ids(
    scratch_s_maker,
    user_vocab_rows,
    passage_rows,
    appearance_rows,
    frontier_max,
    expected_new_ids,
    expected_frontier_ids,
    expected_other_ids,
):
    # seed all the rows given
    seed_rows_helper(scratch_s_maker, user_vocab_rows, passage_rows, appearance_rows)

    new_words_set, frontier_dict, other_dict = get_elligible_ids(
        user_id=1,
        current_time=BASE_TIME,
        frontier_max=frontier_max,
        s_maker=scratch_s_maker,
    )

    # assert expected new, frontier & other IDs
    # NOTE: passing asserts mean the partition expectations are sound
    assert set(expected_new_ids) == new_words_set
    assert set(expected_frontier_ids) == frontier_dict.keys()
    assert set(expected_other_ids) == other_dict.keys()


# ---------------
# Recency Scores (compute_recency_scores)
# ---------------
# ONE scenario, hand-traced. Each word is built to exercise something different:
# - 我 (1):  LEARNING, last seen 1 day ago, in 2 of 4 passages, memory (newest first) [1.0, 0.5]
# - 是 (2):  MASTERED, last seen 2 days ago, in 3 of 4 passages, memory (newest first) [0.6, 0.4, 0.2]
# - 事 (3):  SOLID, last seen 10 days ago, ZERO appearance rows (contrived: isolates the
#           empty-memory branch + a word absent from every counted passage)
# - 猫 (8):  NOT_ENCOUNTERED -> must not be a key at all
# 4 passages total, one per day; every appearance's timestamp = its passage's time.
CRS_PASSAGE_TIMES = {
    1: BASE_TIME - timedelta(days=4),
    2: BASE_TIME - timedelta(days=3),
    3: BASE_TIME - timedelta(days=2),
    4: BASE_TIME - timedelta(days=1),
}

user_vocab_rows_crs = [
    (1, StatusTier.LEARNING, 0, CRS_PASSAGE_TIMES[4]),
    (2, StatusTier.MASTERED, 0, CRS_PASSAGE_TIMES[3]),
    (3, StatusTier.SOLID, 0, BASE_TIME - timedelta(days=10)),
    (8, StatusTier.NOT_ENCOUNTERED, 0, BASE_TIME),
]
passage_rows_crs = [(pid, PassageState.GRADED, "") for pid in CRS_PASSAGE_TIMES]
appearance_rows_crs = [
    # 我: passages 2, 4
    (1, 2, 0.5, CRS_PASSAGE_TIMES[2]),
    (1, 4, 1.0, CRS_PASSAGE_TIMES[4]),
    # 是: passages 1, 2, 3
    (2, 1, 0.2, CRS_PASSAGE_TIMES[1]),
    (2, 2, 0.4, CRS_PASSAGE_TIMES[2]),
    (2, 3, 0.6, CRS_PASSAGE_TIMES[3]),
]

# expected: vocab_id -> RecencyScore(time_pressure, rel_interact_pressure, hist_memory, total_score)
# (the key set itself is part of the oracle)
expected_crs = {
    1: RecencyScore(
        time_pressure=1 - exp(-1 * 1),
        rel_interact_pressure=1 - 0.5,
        hist_memory=1 - (1 * 1.0 + 0.8 * 0.5) / (1 + 0.8),
        total_score=mean(
            [1 - exp(-1 * 1), 1 - 0.5, 1 - (1 * 1.0 + 0.8 * 0.5) / (1 + 0.8)]
        ),
    ),
    2: RecencyScore(
        time_pressure=1 - exp(-0.125 * 2),
        rel_interact_pressure=1 - 0.75,
        hist_memory=1 - (1 * 0.6 + 0.8 * 0.4 + 0.64 * 0.2) / (1 + 0.8 + 0.64),
        total_score=mean(
            [
                1 - exp(-0.125 * 2),
                1 - 0.75,
                1 - (1 * 0.6 + 0.8 * 0.4 + 0.64 * 0.2) / (1 + 0.8 + 0.64),
            ]
        ),
    ),
    3: RecencyScore(
        time_pressure=1 - exp(-0.25 * 10),
        rel_interact_pressure=1,
        hist_memory=0.5,  # there aren't any actual appearances -> default is 0.5
        total_score=mean([1 - exp(-0.25 * 10), 1, 0.5]),
    ),
}


# C) Function Call - yours
def test_compute_recency_scores(scratch_s_maker):
    # seed everything
    seed_rows_helper(
        scratch_s_maker, user_vocab_rows_crs, passage_rows_crs, appearance_rows_crs
    )

    recency_scores = compute_recency_scores(1, BASE_TIME, scratch_s_maker)

    # check IDs included
    assert expected_crs.keys() == recency_scores.keys()

    # check values for all IDs
    for id, scores in expected_crs.items():
        # check all 4 individually
        assert pytest.approx(scores.time_pressure) == recency_scores[id].time_pressure
        assert (
            pytest.approx(scores.rel_interact_pressure)
            == recency_scores[id].rel_interact_pressure
        )
        assert pytest.approx(scores.hist_memory) == recency_scores[id].hist_memory
        assert pytest.approx(scores.total_score) == recency_scores[id].total_score
