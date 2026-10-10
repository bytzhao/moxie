"""
To Test:
- entire Levenshtein grading pipeline (levenshtein())
- no sub-functionality (calc_lev_dist, ch_dist, gen_slight_error_strs) tested directly
"""

import pytest
from backend.levenshtein import levenshtein
from backend.grading import UserPassageLenError
from backend.schemas import VocabUnit, PinyinError


# ---------------
# Full Pipeline (levenshtein)
# ---------------
# A) Testing Scenarios

# --- Scenario 1: completely correct passage, everything matches exactly ---
vocab_list_1 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(None, None)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(None,)),
]
user_passage_1 = "wo3 shi4 zhong1 guo2 ren2"
expected_1 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.CORRECT,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.CORRECT,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(PinyinError.CORRECT, PinyinError.CORRECT)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(PinyinError.CORRECT,)),
]
exception_1 = None

# --- Scenario 2: mix of skip errors + plain forgot (completely wrong, short pinyin forces severe) ---
vocab_list_2 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(None, None)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(None,)),
]
user_passage_2 = "- kai4 - bing2 -"
expected_2 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.SKIPPED,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.FORGOT,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(PinyinError.SKIPPED, PinyinError.FORGOT)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(PinyinError.SKIPPED,)),
]
exception_2 = None

# --- Scenario 3: mix of all 3 slight errors (retroflex, umlaut, nasal) ---
vocab_list_3 = [
    VocabUnit(vocab_id=1, chars=("中",), pinyin=("zhong1",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("女",), pinyin=("nv3",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("山",), pinyin=("shan1",), error_type=(None,)),
]
user_passage_3 = "zong1 nu3 shang1"
expected_3 = [
    VocabUnit(vocab_id=1, chars=("中",), pinyin=("zhong1",), error_type=(PinyinError.RETROFLEX_ERROR,)),
    VocabUnit(vocab_id=2, chars=("女",), pinyin=("nv3",), error_type=(PinyinError.UMLAUT_ERROR,)),
    VocabUnit(vocab_id=3, chars=("山",), pinyin=("shan1",), error_type=(PinyinError.NASAL_ERROR,)),
]
exception_3 = None

# --- Scenario 4: typos - transposition + one-keyboard-off substitution ---
vocab_list_4 = [
    VocabUnit(vocab_id=1, chars=("双",), pinyin=("shuang1",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("穷",), pinyin=("qiong2",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("床",), pinyin=("chuang2",), error_type=(None,)),
]
user_passage_4 = "shuanf1 qoing2 cjuang2"
expected_4 = [
    VocabUnit(vocab_id=1, chars=("双",), pinyin=("shuang1",), error_type=(PinyinError.TYPO,)),
    VocabUnit(vocab_id=2, chars=("穷",), pinyin=("qiong2",), error_type=(PinyinError.TYPO,)),
    VocabUnit(vocab_id=3, chars=("床",), pinyin=("chuang2",), error_type=(PinyinError.TYPO,)),
]
exception_4 = None

# --- Scenario 5: pure tonal errors - letters all correct, every tone digit wrong ---
vocab_list_5 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(None, None)),
]
user_passage_5 = "wo2 shi2 zhong2 guo1"
expected_5 = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(PinyinError.TONE_ERROR,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(PinyinError.TONE_ERROR,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(PinyinError.TONE_ERROR, PinyinError.TONE_ERROR)),
]
exception_5 = None


# B) Parametrization
@pytest.mark.parametrize("user_passage, vocab_list, expected, exception", [
    pytest.param(user_passage_1, vocab_list_1, expected_1, exception_1, id="all correct"),
    pytest.param(user_passage_2, vocab_list_2, expected_2, exception_2, id="passage too short"),
    pytest.param(user_passage_3, vocab_list_3, expected_3, exception_3, id="skip + forgot mix"),
    pytest.param(user_passage_4, vocab_list_4, expected_4, exception_4, id="3 slight errors mix"),
    pytest.param(user_passage_5, vocab_list_5, expected_5, exception_5, id="typos: transposition + one-key-off")
])


# C) Function Call
def test_levenshtein_full_pipe(user_passage, vocab_list, expected, exception):
    if exception is not None:
        with pytest.raises(exception):
            levenshtein(user_passage, vocab_list)
    else:
        assert levenshtein(user_passage, vocab_list) == expected