"""
To Test:
- entire grading orchestrator (grade()) - return values, UserVocab writes (both the
  4 hardcoded EX_VOCAB_UNIT_LIST entries AND any propagated standalone-character
  demotions), and Appearances writes.
- uses an in-memory SQLite DB per test (via monkeypatch), never the real moxie.db.
- sub-functionality (levenshtein(), csm(), find_ind_chars_demote()) already has its
  own dedicated test files - this file is only about grade()'s wiring.

NOTE: grade() always grades against the same hardcoded EX_VOCAB_UNIT_LIST
(我/是/中国/人, vocab_ids 1-4, 5 characters total) - there's no way to swap in a
different vocabulary per scenario. Scenario variation comes entirely from the
user_passage string and the starting DB state you seed beforehand.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.csm import CSMUpdate
from backend.grading import UserPassageLenError, grade
from backend.models import Appearances, Base, HskVocabulary, Users, UserVocab
from backend.schemas import PinyinError, StatusTier, VocabUnit

PASSAGE_ID = 1
USER_ID = 1
TEST_TIMESTAMP = datetime(2026, 1, 1, 12, 0, 0)


# ---------------
# Isolated DB Fixture
# ---------------
@pytest.fixture
def test_session_factory(monkeypatch):
    """Points grade()'s entire call chain (grading.py + csm.py) at a throwaway
    in-memory DB instead of moxie.db. Two modules import SessionLocal separately
    (backend.grading for log_appearances, backend.csm for csm()/find_ind_chars_demote),
    so both need patching to share the same fake engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr("backend.grading.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("backend.csm.SessionLocal", TestSessionLocal)
    return TestSessionLocal


# ---------------
# Grading Orchestrator (grade)
# ---------------
# A) Testing Scenarios

# --- Scenario 1: passage too short ---
user_passage_1 = "wo3 shi4 zhong1"  # only 3 of the 5 required tokens
starting_user_vocab_rows_1 = []  # never reached - UserPassageLenError raises first
starting_hsk_vocab_rows_1 = []
expected_exception_1 = UserPassageLenError

# --- Scenario 2: passage too long ---
user_passage_2 = "wo3 shi4 zhong1 guo2 ren2 extra1"  # 6 tokens, only 5 expected
starting_user_vocab_rows_2 = []
starting_hsk_vocab_rows_2 = []
expected_exception_2 = UserPassageLenError

# --- Scenario 3: no promotions/demotions - everything correct, but no tier hits its ceiling ---
user_passage_3 = "wo3 shi4 zhong1 guo2 ren2"  # fully correct
starting_user_vocab_rows_3 = [
    # (vocab_id, status_tier, points) - each one at least 1 point below its ceiling
    (1, StatusTier.FAMILIAR, 0),  # ceiling 3, +1 -> 1
    (2, StatusTier.LEARNING, 1),  # ceiling 3, +1 -> 2
    (3, StatusTier.SOLID, 2),  # ceiling 5, +1 -> 3
    (4, StatusTier.MASTERED, 0),  # ceiling infinite, never promotes further
]
starting_hsk_vocab_rows_3 = []
expected_exception_3 = None
expected_vocab_error_list_3 = [
    VocabUnit(
        vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.CORRECT,)
    ),
    VocabUnit(
        vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.CORRECT,)
    ),
    VocabUnit(
        vocab_id=3,
        chars=("中", "国"),
        pinyin=("zhong1", "guo2"),
        error_type=(PinyinError.CORRECT, PinyinError.CORRECT),
    ),
    VocabUnit(
        vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(PinyinError.CORRECT,)
    ),
]
expected_promo_demo_3 = {}
expected_final_uservocab_rows_3 = [
    (1, StatusTier.FAMILIAR, 1),
    (2, StatusTier.LEARNING, 2),
    (3, StatusTier.SOLID, 3),
    (4, StatusTier.MASTERED, 1),
]
expected_appearances_rows_3 = [
    (1, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
    (2, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
    (3, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
    (4, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
]

# --- Scenario 4: mix of promotions, demotions, and a plain streak increase ---
# 我 (wo3): correct, hits its ceiling -> promotes
# 是 (shi4): severe error ("ge4") -> demotes
# 中国 (zhong1/guo2): 中 correct, 国 severe error ("bu2") -> unit demotes,
#     AND 国's own standalone char (seeded separately below) should also demote
# 人 (ren2): correct, doesn't hit its ceiling -> streak increase only, no promotion
user_passage_4 = "wo3 ge4 zhong1 bu2 ren2"
starting_user_vocab_rows_4 = [
    (1, StatusTier.FAMILIAR, 2),  # ceiling 3, +1 -> 3 -> promote to SOLID
    (2, StatusTier.FAMILIAR, 1),  # severe -> demote to LEARNING
    (3, StatusTier.SOLID, 3),  # severe (worst of the two chars) -> demote to FAMILIAR
    (4, StatusTier.LEARNING, 1),  # ceiling 3, +1 -> 2, stays LEARNING
    (11, StatusTier.FAMILIAR, 2),  # standalone "国" - severe -> demote to LEARNING
]
starting_hsk_vocab_rows_4 = [
    # (vocab_id, simp_man_word, pinyin) - standalone entry for 国, separate from
    # vocab_id=3's compound "中国" entry, so find_ind_chars_demote has something to match
    (11, "国", "guo2"),
]
expected_exception_4 = None
expected_vocab_error_list_4 = [
    VocabUnit(
        vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.CORRECT,)
    ),
    VocabUnit(
        vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.FORGOT,)
    ),
    VocabUnit(
        vocab_id=3,
        chars=("中", "国"),
        pinyin=("zhong1", "guo2"),
        error_type=(PinyinError.CORRECT, PinyinError.FORGOT),
    ),
    VocabUnit(
        vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(PinyinError.CORRECT,)
    ),
]
expected_promo_demo_4 = {
    1: CSMUpdate(
        char=("我",),
        error_type=0,
        initial_status=StatusTier.FAMILIAR,
        final_status=StatusTier.SOLID,
        final_points=0,
    ),
    2: CSMUpdate(
        char=("是",),
        error_type=PinyinError.FORGOT,
        initial_status=StatusTier.FAMILIAR,
        final_status=StatusTier.LEARNING,
        final_points=2,
    ),
    3: CSMUpdate(
        char=("中", "国"),
        error_type=PinyinError.FORGOT,
        initial_status=StatusTier.SOLID,
        final_status=StatusTier.FAMILIAR,
        final_points=1,
    ),
    11: CSMUpdate(
        char=("国",),
        error_type=PinyinError.FORGOT,
        initial_status=StatusTier.FAMILIAR,
        final_status=StatusTier.LEARNING,
        final_points=2,
    ),
}
expected_final_uservocab_rows_4 = [
    (1, StatusTier.SOLID, 0),
    (2, StatusTier.LEARNING, 2),
    (3, StatusTier.FAMILIAR, 1),
    (4, StatusTier.LEARNING, 2),
    (11, StatusTier.LEARNING, 2),
]
expected_appearances_rows_4 = [
    (1, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
    (2, USER_ID, PASSAGE_ID, 0, TEST_TIMESTAMP),
    (3, USER_ID, PASSAGE_ID, 0.5, TEST_TIMESTAMP),
    (4, USER_ID, PASSAGE_ID, 1, TEST_TIMESTAMP),
]


# B) Parametrization
@pytest.mark.parametrize(
    "user_passage, starting_user_vocab_rows, starting_hsk_vocab_rows, expected_exception, "
    "expected_vocab_error_list, expected_promo_demo, expected_final_uservocab_rows, expected_appearances_rows",
    [
        pytest.param(
            user_passage_1,
            starting_user_vocab_rows_1,
            starting_hsk_vocab_rows_1,
            expected_exception_1,
            None,
            None,
            None,
            None,
            id="passage too short",
        ),
        pytest.param(
            user_passage_2,
            starting_user_vocab_rows_2,
            starting_hsk_vocab_rows_2,
            expected_exception_2,
            None,
            None,
            None,
            None,
            id="passage too long",
        ),
        pytest.param(
            user_passage_3,
            starting_user_vocab_rows_3,
            starting_hsk_vocab_rows_3,
            expected_exception_3,
            expected_vocab_error_list_3,
            expected_promo_demo_3,
            expected_final_uservocab_rows_3,
            expected_appearances_rows_3,
            id="no promo/demo - updates still happen",
        ),
        pytest.param(
            user_passage_4,
            starting_user_vocab_rows_4,
            starting_hsk_vocab_rows_4,
            expected_exception_4,
            expected_vocab_error_list_4,
            expected_promo_demo_4,
            expected_final_uservocab_rows_4,
            expected_appearances_rows_4,
            id="mix of promo/demo/streak-increase",
        ),
    ],
)

# C) Function Call
def test_grade_full_pipe(
    test_session_factory,
    user_passage,
    starting_user_vocab_rows,
    starting_hsk_vocab_rows,
    expected_exception,
    expected_vocab_error_list,
    expected_promo_demo,
    expected_final_uservocab_rows,
    expected_appearances_rows,
):
    # TODO:
    # (1) seed `starting_hsk_vocab_rows` and `starting_user_vocab_rows` into the isolated
    #     DB via test_session_factory (a Users row + one UserVocab row per tuple, plus
    #     one HskVocabulary row per tuple), commit. Note scenarios 1/2 have nothing to seed.
    with test_session_factory() as session:
        hsk_vocab_rows = [
            HskVocabulary(
                vocab_id=vid,
                simp_man_word=chars,
                pinyin=py,
                hsk_level=1,
                trad_man_word="",
            )
            for vid, chars, py in starting_hsk_vocab_rows
        ]

        user_vocab_rows = [
            UserVocab(
                user_id=USER_ID,
                vocab_id=vid,
                status_tier=tier,
                points=pts,
                last_encounter_time=TEST_TIMESTAMP,
            )
            for vid, tier, pts in starting_user_vocab_rows
        ]

        new_user = Users(
            user_id=USER_ID,
            user_name="Stephen Dedalus",
            user_email="sdedalus@gmail.com",
            created_time=TEST_TIMESTAMP,
        )

        session.add_all(hsk_vocab_rows + user_vocab_rows)
        session.add(new_user)
        session.commit()

    # (2) if expected_exception is set, assert grade(...) raises it and stop there.
    #     otherwise, call grade(passage_id=PASSAGE_ID, user_passage=user_passage,
    #     user_id=USER_ID, timestamp=TEST_TIMESTAMP) and assert its two return values
    #     against expected_vocab_error_list and expected_promo_demo.
    if expected_exception is not None:
        with pytest.raises(expected_exception):
            grade(PASSAGE_ID, user_passage, USER_ID, TEST_TIMESTAMP)
        pass
    else:
        actual_vocab_error_list, actual_promo_demo = grade(
            PASSAGE_ID, user_passage, USER_ID, TEST_TIMESTAMP
        )
        assert actual_vocab_error_list == expected_vocab_error_list
        assert actual_promo_demo == expected_promo_demo

        # (3) open a FRESH session and re-query every relevant UserVocab row (don't forget
        #     vocab_id=11 in scenario 4) to assert against expected_final_uservocab_rows.
        # (4) re-query Appearances rows (filtered by passage_id/user_id) to assert against
        #     expected_appearances_rows.
        with test_session_factory() as session:
            uservocab_rows = select(
                UserVocab.vocab_id, UserVocab.status_tier, UserVocab.points
            ).where(
                UserVocab.user_id == USER_ID, UserVocab.vocab_id.in_({1, 2, 3, 4, 11})
            )

            actual_uservocab_rows = session.execute(uservocab_rows).tuples().all()
            assert expected_final_uservocab_rows == actual_uservocab_rows

            appearance_rows = select(
                Appearances.vocab_id,
                Appearances.user_id,
                Appearances.passage_id,
                Appearances.memory_score,
                Appearances.timestamp,
            ).where(
                Appearances.user_id == USER_ID,
                Appearances.passage_id == PASSAGE_ID,
                Appearances.vocab_id.in_({1, 2, 3, 4}),
            )

            actual_appearances_rows = session.execute(appearance_rows).tuples().all()
            assert expected_appearances_rows == actual_appearances_rows
