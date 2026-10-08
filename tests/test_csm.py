"""
To Test:
- CSM orchestrator (csm()) - both its return value AND its actual DB writes
- uses an in-memory SQLite DB per test (via monkeypatch), never the real moxie.db
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from backend.csm import csm, CSMUpdate, find_ind_chars_demote
from backend.models import Base, Users, UserVocab, HskVocabulary
from backend.schemas import VocabUnit, PinyinError, StatusTier


# ---------------
# Isolated DB Fixture
# ---------------
@pytest.fixture
def test_session_factory(monkeypatch):
    """Points csm()'s SessionLocal at a throwaway in-memory DB instead of moxie.db."""
    # NOTE: fixtures aren't called, but just silently passing into test func is fine
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    # sneakily replaces csm's SessionLocal from data/db.py w/ new sessionmaker pointing to custom db
    monkeypatch.setattr("backend.csm.SessionLocal", TestSessionLocal)
    return TestSessionLocal


# ---------------
# CSM Orchestrator (csm)
# ---------------
# A) Testing Scenarios

# --- Scenario 1: everything correct - points +1 across the board, promotions where applicable ---
USER_ID_1 = 1
starting_rows_1 = [
    # (vocab_id, status_tier, points)
    (1, StatusTier.FAMILIAR, 2),   # one more correct hits the FAMILIAR ceiling (3) -> promote
    (2, StatusTier.LEARNING, 0),   # one more correct, ceiling is 3 -> no promotion yet
    (3, StatusTier.SOLID, 4),      # one more correct hits the SOLID ceiling (5) -> promote
    (4, StatusTier.MASTERED, 0),   # ceiling is infinite -> never promotes further
]
vocab_error_list_1 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.CORRECT,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.CORRECT,)),
    VocabUnit(vocab_id=3, chars=("中",), pinyin=("zhong1",), error_type=(PinyinError.CORRECT,)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(PinyinError.CORRECT,)),
]
expected_promo_demo_1 = {
    1: CSMUpdate(("我",), PinyinError.CORRECT, StatusTier.FAMILIAR, StatusTier.SOLID, 0),
    3: CSMUpdate(("中",), PinyinError.CORRECT, StatusTier.SOLID, StatusTier.MASTERED, 0)
}
expected_final_rows_1 = [
    (1, StatusTier.SOLID, 0),
    (2, StatusTier.LEARNING, 1),
    (3, StatusTier.MASTERED, 0),
    (4, StatusTier.MASTERED, 1)
]

# --- Scenario 2: mix of slight and severe errors across starting tiers ---
USER_ID_2 = 1
starting_rows_2 = [
    (5, StatusTier.FAMILIAR, 1),   # severe (FORGOT)
    (6, StatusTier.SOLID, 3),      # slight (TYPO)
    (7, StatusTier.LEARNING, 1),   # severe (TONE_ERROR)
    (8, StatusTier.MASTERED, 0),   # severe (SKIPPED)
]
vocab_error_list_2 = [
    VocabUnit(vocab_id=5, chars=("女",), pinyin=("nv3",), error_type=(PinyinError.FORGOT,)),
    VocabUnit(vocab_id=6, chars=("山",), pinyin=("shan1",), error_type=(PinyinError.TYPO,)),
    VocabUnit(vocab_id=7, chars=("双",), pinyin=("shuang1",), error_type=(PinyinError.TONE_ERROR,)),
    VocabUnit(vocab_id=8, chars=("穷",), pinyin=("qiong2",), error_type=(PinyinError.SKIPPED,)),
]
expected_promo_demo_2 = {
    5: CSMUpdate(("女",), PinyinError.FORGOT, StatusTier.FAMILIAR, StatusTier.LEARNING, 2),
    6: CSMUpdate(("山",), PinyinError.TYPO, StatusTier.SOLID, StatusTier.FAMILIAR, 2),
    8: CSMUpdate(("穷",), PinyinError.SKIPPED, StatusTier.MASTERED, StatusTier.FAMILIAR, 2)
}
expected_final_rows_2 = [
    (5, StatusTier.LEARNING, 2),
    (6, StatusTier.FAMILIAR, 2),
    (7, StatusTier.LEARNING, 0),
    (8, StatusTier.FAMILIAR, 2)
]


# B) Parametrization
@pytest.mark.parametrize("user_id, starting_rows, vocab_error_list, expected_promo_demo, expected_final_rows", [
    pytest.param(USER_ID_1, starting_rows_1, vocab_error_list_1, expected_promo_demo_1, expected_final_rows_1, id="all correct"),
    pytest.param(USER_ID_2, starting_rows_2, vocab_error_list_2, expected_promo_demo_2, expected_final_rows_2, id="slight + severe mix"),
])


# C) Function Call
def test_csm_full_pipe(test_session_factory, user_id, starting_rows, vocab_error_list, expected_promo_demo, expected_final_rows):
    # TODO:
    # (1) seed `starting_rows` into the isolated DB via test_session_factory (a Users row + one
    #     UserVocab row per (vocab_id, status_tier, points) tuple), commit.
    with test_session_factory() as session:
        rows = [UserVocab(user_id=user_id, vocab_id=vocab_id, status_tier=init_tier, points=streak, last_encounter_time=datetime.now()) for vocab_id, init_tier, streak in starting_rows]

        new_user = Users(user_id=user_id, user_name="Stephen Dedalus", user_email="sdedalus2048@gmail.com", created_time=datetime.now())

        session.add_all(rows)
        session.add(new_user)
        session.commit()
    
    # (2) call csm(vocab_error_list, user_id) and assert its return value against expected_promo_demo.
    assert csm(vocab_error_list, user_id, datetime.now()) == expected_promo_demo

    # (3) open a FRESH session via test_session_factory and re-query each vocab_id's UserVocab row
    #     to assert the actually-persisted (status_tier, points) against expected_final_rows -
    #     this is the check the return value alone can't give you.
    with test_session_factory() as session:
        rows = select(UserVocab.vocab_id, UserVocab.status_tier, UserVocab.points).where(UserVocab.user_id == user_id)
        actual_final_rows = session.execute(rows).tuples().all()
        assert expected_final_rows == actual_final_rows


# ---------------
# Find Individual Chars to Demote (find_ind_chars_demote)
# ---------------
# A) Testing Scenarios

# --- Scenario 1: solo chars that should NOT be demoted (false-positive guard) ---
USER_ID_3 = 1
# (vocab_id, simp_man_word, pinyin, hsk_level, trad_man_word)
hsk_rows_3 = [
    (101, "中", "zhong1", "1", "中"),   # solo reading (zhong1) differs from the compound's answer-key reading below (zhong4) -> pinyin mismatch
    (102, "国", "guo2", "1", "國"),     # matches the compound's reading exactly, but see uservocab_rows_3 below
]
# (vocab_id, status_tier, points)
uservocab_rows_3 = [
    (101, StatusTier.FAMILIAR, 2),         # encountered + correct pinyin -> isolates the pinyin-mismatch exclusion for 中 on its own
    (102, StatusTier.NOT_ENCOUNTERED, 0),  # never encountered solo -> isolates the not-yet-encountered exclusion for 国 on its own
]
vocab_error_list_3 = [
    VocabUnit(vocab_id=201, chars=("中", "国"), pinyin=("zhong4", "guo2"), error_type=(PinyinError.TONE_ERROR, PinyinError.FORGOT)),
]
expected_ind_chars_3 = []

# --- Scenario 2: solo chars that SHOULD be demoted (true positive) ---
USER_ID_4 = 1
hsk_rows_4 = [
    (103, "女", "nv3", "1", "女"),
    (104, "山", "shan1", "1", "山"),
]
uservocab_rows_4 = [
    (103, StatusTier.FAMILIAR, 1),
    (104, StatusTier.LEARNING, 0),
]
vocab_error_list_4 = [
    VocabUnit(vocab_id=202, chars=("女", "山"), pinyin=("nv3", "shan1"), error_type=(PinyinError.UMLAUT_ERROR, PinyinError.TYPO)),
]
expected_ind_chars_4 = [
    VocabUnit(vocab_id=103, chars=("女",), pinyin=("nv3",), error_type=(PinyinError.UMLAUT_ERROR,)),
    VocabUnit(vocab_id=104, chars=("山",), pinyin=("shan1",), error_type=(PinyinError.TYPO,))
]


# B) Parametrization
@pytest.mark.parametrize("user_id, hsk_rows, uservocab_rows, vocab_error_list, expected_ind_chars", [
    pytest.param(USER_ID_3, hsk_rows_3, uservocab_rows_3, vocab_error_list_3, expected_ind_chars_3, id="false positives excluded"),
    pytest.param(USER_ID_4, hsk_rows_4, uservocab_rows_4, vocab_error_list_4, expected_ind_chars_4, id="true positives included"),
])


# C) Function Call
def test_find_ind_chars_demote(test_session_factory, user_id, hsk_rows, uservocab_rows, vocab_error_list, expected_ind_chars):
    # (1) seed HskVocabulary rows (the solo-char entries), a Users row, and the UserVocab rows this scenario cares about
    with test_session_factory() as session:
        hsk_objs = [HskVocabulary(vocab_id=vid, simp_man_word=word, pinyin=py, hsk_level=lvl, trad_man_word=trad) for vid, word, py, lvl, trad in hsk_rows]
        uservocab_objs = [UserVocab(user_id=user_id, vocab_id=vid, status_tier=tier, points=pts, last_encounter_time=datetime.now()) for vid, tier, pts in uservocab_rows]
        new_user = Users(user_id=user_id, user_name="Stephen Dedalus", user_email="sdedalus2048@gmail.com", created_time=datetime.now())

        session.add_all(hsk_objs + uservocab_objs)
        session.add(new_user)
        session.commit()

    # (2) call find_ind_chars_demote(vocab_error_list, user_id) and assert its return value against expected_ind_chars
    assert find_ind_chars_demote(vocab_error_list, user_id) == expected_ind_chars
