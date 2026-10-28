"""
To Test:
- fmm() / bmm(): raw segmentation + unknown-char collection, incl. punctuation units
- validate_seg(): string-level checks (hallucinated, not encountered at word level)
- bimm(): FMM vs. BMM choice tree, incl. which error (and whose payload) gets raised

NOTE: every test injects toy dicts and a toy max_word_len, so nothing depends on the real
11K HSK list or the DB.
"""

import pytest

from backend.schemas import VocabTriple
from backend.segmenter import (
    HallucinatedWordsError,
    NotEncounteredWordsError,
    bimm,
    bmm,
    fmm,
    validate_seg,
)


def _toy_s1(word_to_id: dict) -> dict:
    """Builds a toy S1 (word -> tuple of VocabTriples), one triple per word.
    Pinyin/sense are placeholders: the segmenter never reads them.
    """
    return {
        word: (VocabTriple(vocab_id=vocab_id, pinyin="-", sense=""),)
        for word, vocab_id in word_to_id.items()
    }


# ---------------
# FMM & BMM
# ---------------
# NOTE: the same 3 scenarios feed both tables, with separate expected values.
# hsk_list values are never read (membership only), hence dict.fromkeys.

# A) Testing Scenarios
# --- Scenario 1: clean pass ---
# - punctuation at index 0, last index, and consecutive (，， and 。”); one space
# - longest match: 电 / 电脑 (prefix, FMM) & 脑 / 电脑 (suffix, BMM); same for 图书 / 图书馆 / 馆
# - clamped window: tail of passage for FMM, head of passage for BMM (max_word_len = 3)
passage_seg_1 = "“我用电脑，，去 图书馆。”"
hsk_list_seg_1 = dict.fromkeys(
    ["我", "用", "电", "脑", "电脑", "去", "图书", "图书馆", "馆"]
)
max_word_len_seg_1 = 3
expected_fmm_1 = (
    ["“", "我", "用", "电脑", "，", "，", "去", " ", "图书馆", "。", "”"],
    [],
)
expected_bmm_1 = (
    ["“", "我", "用", "电脑", "，", "，", "去", " ", "图书馆", "。", "”"],
    [],
)

# --- Scenario 2: FMM ≠ BMM on the same input (classic 研究生命 ambiguity) ---
passage_seg_2 = "研究生命的起源"
hsk_list_seg_2 = dict.fromkeys(["研究", "研究生", "生命", "命", "的", "起源"])
max_word_len_seg_2 = 3
expected_fmm_2 = (["研究生", "命", "的", "起源"], [])
expected_bmm_2 = (["研究", "生命", "的", "起源"], [])

# --- Scenario 3: multiple non-adjacent hallucinations (Latin letter, digit, Han char not in dict) ---
# order of unknown_chars matters here (append vs. insert(0))
passage_seg_3 = "我用A电脑, 3写字猫"
hsk_list_seg_3 = dict.fromkeys(["我", "用", "电脑", "写字"])
max_word_len_seg_3 = 2
expected_fmm_3 = (["我", "用", "电脑", ",", " ", "写字"], ["A", "3", "猫"])
expected_bmm_3 = (["我", "用", "电脑", ",", " ", "写字"], ["A", "3", "猫"])


# B) Parametrization
@pytest.mark.parametrize(
    "passage, hsk_list, max_word_len, expected",
    [
        pytest.param(
            passage_seg_1,
            hsk_list_seg_1,
            max_word_len_seg_1,
            expected_fmm_1,
            id="clean pass w/ punc",
        ),
        pytest.param(
            passage_seg_2,
            hsk_list_seg_2,
            max_word_len_seg_2,
            expected_fmm_2,
            id="ambiguous (FMM != BMM)",
        ),
        pytest.param(
            passage_seg_3,
            hsk_list_seg_3,
            max_word_len_seg_3,
            expected_fmm_3,
            id="non-adjacent halluc",
        ),
    ],
)

# C) Function Call
def test_fmm(passage, hsk_list, max_word_len, expected):
    assert expected == fmm(passage, len(passage), hsk_list, max_word_len)


@pytest.mark.parametrize(
    "passage, hsk_list, max_word_len, expected",
    [
        pytest.param(
            passage_seg_1,
            hsk_list_seg_1,
            max_word_len_seg_1,
            expected_bmm_1,
            id="clean pass w/ punc",
        ),
        pytest.param(
            passage_seg_2,
            hsk_list_seg_2,
            max_word_len_seg_2,
            expected_bmm_2,
            id="ambiguous (FMM != BMM)",
        ),
        pytest.param(
            passage_seg_3,
            hsk_list_seg_3,
            max_word_len_seg_3,
            expected_bmm_3,
            id="non-adjacent halluc",
        ),
    ],
)

# C) Function Call
def test_bmm(passage, hsk_list, max_word_len, expected):
    assert expected == bmm(passage, len(passage), hsk_list, max_word_len)


# ---------------
# Segmentation Validation (validate_seg)
# ---------------
# A) Testing Scenarios
# Shared toy S1 for all 3 scenarios. 长 and 会 are multi-ID.
static_hsk_triples_val = {
    "我": (VocabTriple(vocab_id=1, pinyin="wo3", sense="Pron"),),
    "长": (
        VocabTriple(vocab_id=2, pinyin="chang2", sense="Adj"),
        VocabTriple(vocab_id=3, pinyin="zhang3", sense="V"),
    ),
    "很": (VocabTriple(vocab_id=4, pinyin="hen3", sense="Adv"),),
    "会": (
        VocabTriple(vocab_id=5, pinyin="hui4", sense="V"),
        VocabTriple(vocab_id=6, pinyin="hui4", sense="N"),
    ),
    "高": (VocabTriple(vocab_id=7, pinyin="gao1", sense="Adj"),),
    "猫": (VocabTriple(vocab_id=8, pinyin="mao1", sense="N"),),
}
# Shared eligible split. Keys are vocab IDs (the only thing validate_seg reads); values are just labels.
# - 长: only its SECOND ID (zhang3) is eligible, via frontier
# - 高: eligible via frontier only;  我 / 很: eligible via other_encountered only
# - 会 (both IDs), 猫: not eligible at all
frontier_dict_val = {3: "长", 7: "高"}
other_encountered_dict_val = {1: "我", 4: "很"}

# --- Scenario 1: clean pass (punc + space units, multi-ID w/ one eligible ID, both dicts exercised) ---
seg_passage_val_1 = ["我", "很", "高", "，", "长", " ", "。"]
unknown_chars_val_1 = []
expected_val_1 = {"is_valid": 0, "halluc_words": [], "not_encountered": []}

# --- Scenario 2: halluc + a not-encountered word (猫) both present -> short-circuit ---
seg_passage_val_2 = ["我", "猫", "很", "高", "。"]
unknown_chars_val_2 = ["狗"]
expected_val_2 = {"is_valid": 2, "halluc_words": ["狗"], "not_encountered": []}

# --- Scenario 3: not-encountered (猫 twice -> dedupe; 会 has no eligible ID), mixed w/ encountered + punc ---
seg_passage_val_3 = ["我", "猫", "，", "猫", "会", "很", "。"]
unknown_chars_val_3 = []
expected_val_3 = {"is_valid": 1, "halluc_words": [], "not_encountered": ["猫", "会"]}


# B) Parametrization
@pytest.mark.parametrize(
    "frontier_dict, other_encountered_dict, static_hsk_triples, seg_passage, unknown_chars, expected",
    [
        pytest.param(
            frontier_dict_val,
            other_encountered_dict_val,
            static_hsk_triples_val,
            seg_passage_val_1,
            unknown_chars_val_1,
            expected_val_1,
            id="clean pass",
        ),
        pytest.param(
            frontier_dict_val,
            other_encountered_dict_val,
            static_hsk_triples_val,
            seg_passage_val_2,
            unknown_chars_val_2,
            expected_val_2,
            id="halluc short-circuits not-encountered",
        ),
        pytest.param(
            frontier_dict_val,
            other_encountered_dict_val,
            static_hsk_triples_val,
            seg_passage_val_3,
            unknown_chars_val_3,
            expected_val_3,
            id="not encountered w/ dedupe",
        ),
    ],
)

# C) Function Call
def test_validate_seg(
    frontier_dict,
    other_encountered_dict,
    static_hsk_triples,
    seg_passage,
    unknown_chars,
    expected,
):
    assert expected == validate_seg(
        frontier_dict,
        other_encountered_dict,
        static_hsk_triples,
        seg_passage,
        unknown_chars,
    )


# ---------------
# BiMM (FMM vs. BMM choice)
# ---------------
# NOTE: each scenario passes the same toy S1 as both static_hsk_triples AND whole_hsk,
# so the segmentation dictionary and the ID index always agree.
# Error cases: expected = the raised payload list. Valid cases: expected = the returned seg.

# A) Testing Scenarios
# --- Scenario 1a: FMM not-encountered, BMM halluc -> raise not-encountered (FMM's) ---
passage_bimm_1a = "大学生"
s1_bimm_1a = _toy_s1({"大学": 1, "学生": 2, "生": 3})
frontier_dict_bimm_1a = {2: "学生"}
other_encountered_dict_bimm_1a = {3: "生"}
max_word_len_bimm_1a = 2
expected_bimm_1a = ["大学"]
exception_bimm_1a = NotEncounteredWordsError

# --- Scenario 1b: FMM halluc, BMM not-encountered -> raise not-encountered (BMM's) ---
passage_bimm_1b = "学生活"
s1_bimm_1b = _toy_s1({"学生": 1, "生活": 2, "学": 3})
frontier_dict_bimm_1b = {1: "学生"}
other_encountered_dict_bimm_1b = {3: "学"}
max_word_len_bimm_1b = 2
expected_bimm_1b = ["生活"]
exception_bimm_1b = NotEncounteredWordsError

# --- Scenarios 2a-c / 3a share one passage + S1; only the eligible split changes ---
passage_bimm_2 = "研究生命的起源。"
s1_bimm_2 = _toy_s1({"研究": 1, "研究生": 2, "生命": 3, "命": 4, "的": 5, "起源": 6})
max_word_len_bimm_2 = 3

# --- Scenario 2a: both not-encountered, FMM has fewer -> FMM's list ---
frontier_dict_bimm_2a = {4: "命"}
other_encountered_dict_bimm_2a = {5: "的", 6: "起源"}
expected_bimm_2a = ["研究生"]
exception_bimm_2a = NotEncounteredWordsError

# --- Scenario 2b: both not-encountered, BMM has fewer -> BMM's list ---
frontier_dict_bimm_2b = {1: "研究"}
other_encountered_dict_bimm_2b = {5: "的", 6: "起源"}
expected_bimm_2b = ["生命"]
exception_bimm_2b = NotEncounteredWordsError

# --- Scenario 2c: both not-encountered, equal count -> BMM's list ---
frontier_dict_bimm_2c = {1: "研究", 4: "命"}
other_encountered_dict_bimm_2c = {5: "的", 6: "起源"}
expected_bimm_2c = ["生命"]
exception_bimm_2c = NotEncounteredWordsError

# --- Scenario 2d: both halluc, FMM has fewer -> FMM's list (only case exercising HALLUC_ERROR in bimm) ---
# 大学生 strands a char only under BMM; 学生活 strands one only under FMM
passage_bimm_2d = "大学生，大学生，学生活"
s1_bimm_2d = _toy_s1({"大学": 1, "学生": 2, "生": 3, "生活": 4, "学": 5})
frontier_dict_bimm_2d = {1: "大学", 2: "学生", 4: "生活"}
other_encountered_dict_bimm_2d = {3: "生", 5: "学"}
max_word_len_bimm_2d = 2
expected_bimm_2d = ["活"]
exception_bimm_2d = HallucinatedWordsError

# --- Scenario 3a: FMM invalid (not-encountered), BMM valid -> bmm_seg ---
frontier_dict_bimm_3a = {1: "研究", 3: "生命"}
other_encountered_dict_bimm_3a = {5: "的", 6: "起源"}
expected_bimm_3a = ["研究", "生命", "的", "起源", "。"]
exception_bimm_3a = None

# --- Scenario 3b: FMM valid, BMM invalid (halluc) -> fmm_seg ---
passage_bimm_3b = "大学生"
s1_bimm_3b = _toy_s1({"大学": 1, "学生": 2, "生": 3})
frontier_dict_bimm_3b = {1: "大学"}
other_encountered_dict_bimm_3b = {3: "生"}
max_word_len_bimm_3b = 2
expected_bimm_3b = ["大学", "生"]
exception_bimm_3b = None

# --- Scenario 4a: both valid, FMM fewer units -> fmm_seg ---
passage_bimm_4a = "图书馆员"
s1_bimm_4a = _toy_s1({"图书馆": 1, "员": 2, "馆员": 3, "图": 4, "书": 5})
frontier_dict_bimm_4a = {1: "图书馆", 3: "馆员"}
other_encountered_dict_bimm_4a = {2: "员", 4: "图", 5: "书"}
max_word_len_bimm_4a = 3
expected_bimm_4a = ["图书馆", "员"]
exception_bimm_4a = None

# --- Scenario 4b: both valid, BMM fewer units -> bmm_seg ---
passage_bimm_4b = "看图书馆"
s1_bimm_4b = _toy_s1({"看图": 1, "书": 2, "馆": 3, "图书馆": 4, "看": 5})
frontier_dict_bimm_4b = {1: "看图", 4: "图书馆"}
other_encountered_dict_bimm_4b = {2: "书", 3: "馆", 5: "看"}
max_word_len_bimm_4b = 3
expected_bimm_4b = ["看", "图书馆"]
exception_bimm_4b = None

# --- Scenario 5: both valid, same unit count, FMM fewer single-char units -> fmm_seg ---
passage_bimm_5 = "高中学生"
s1_bimm_5 = _toy_s1({"高中": 1, "学生": 2, "高": 3, "中学生": 4})
frontier_dict_bimm_5 = {1: "高中", 4: "中学生"}
other_encountered_dict_bimm_5 = {2: "学生", 3: "高"}
max_word_len_bimm_5 = 3
expected_bimm_5 = ["高中", "学生"]
exception_bimm_5 = None

# --- Scenario 6: both valid, FMM != BMM, same units AND same single-char count -> bmm_seg (tiebreak) ---
passage_bimm_6 = "发展中国家"
s1_bimm_6 = _toy_s1({"发展": 1, "中国": 2, "国家": 3, "中": 4, "家": 5})
frontier_dict_bimm_6 = {2: "中国", 3: "国家"}
other_encountered_dict_bimm_6 = {1: "发展", 4: "中", 5: "家"}
max_word_len_bimm_6 = 2
expected_bimm_6 = ["发展", "中", "国家"]
exception_bimm_6 = None


# B) Parametrization
@pytest.mark.parametrize(
    "passage, frontier_dict, other_encountered_dict, static_hsk_triples, whole_hsk, max_word_len, expected, exception",
    [
        pytest.param(
            passage_bimm_1a,
            frontier_dict_bimm_1a,
            other_encountered_dict_bimm_1a,
            s1_bimm_1a,
            s1_bimm_1a,
            max_word_len_bimm_1a,
            expected_bimm_1a,
            exception_bimm_1a,
            id="1a both fail: FMM not-enc beats BMM halluc",
        ),
        pytest.param(
            passage_bimm_1b,
            frontier_dict_bimm_1b,
            other_encountered_dict_bimm_1b,
            s1_bimm_1b,
            s1_bimm_1b,
            max_word_len_bimm_1b,
            expected_bimm_1b,
            exception_bimm_1b,
            id="1b both fail: BMM not-enc beats FMM halluc",
        ),
        pytest.param(
            passage_bimm_2,
            frontier_dict_bimm_2a,
            other_encountered_dict_bimm_2a,
            s1_bimm_2,
            s1_bimm_2,
            max_word_len_bimm_2,
            expected_bimm_2a,
            exception_bimm_2a,
            id="2a both not-enc: FMM fewer",
        ),
        pytest.param(
            passage_bimm_2,
            frontier_dict_bimm_2b,
            other_encountered_dict_bimm_2b,
            s1_bimm_2,
            s1_bimm_2,
            max_word_len_bimm_2,
            expected_bimm_2b,
            exception_bimm_2b,
            id="2b both not-enc: BMM fewer",
        ),
        pytest.param(
            passage_bimm_2,
            frontier_dict_bimm_2c,
            other_encountered_dict_bimm_2c,
            s1_bimm_2,
            s1_bimm_2,
            max_word_len_bimm_2,
            expected_bimm_2c,
            exception_bimm_2c,
            id="2c both not-enc: equal count",
        ),
        pytest.param(
            passage_bimm_2d,
            frontier_dict_bimm_2d,
            other_encountered_dict_bimm_2d,
            s1_bimm_2d,
            s1_bimm_2d,
            max_word_len_bimm_2d,
            expected_bimm_2d,
            exception_bimm_2d,
            id="2d both halluc: FMM fewer",
        ),
        pytest.param(
            passage_bimm_2,
            frontier_dict_bimm_3a,
            other_encountered_dict_bimm_3a,
            s1_bimm_2,
            s1_bimm_2,
            max_word_len_bimm_2,
            expected_bimm_3a,
            exception_bimm_3a,
            id="3a only BMM valid",
        ),
        pytest.param(
            passage_bimm_3b,
            frontier_dict_bimm_3b,
            other_encountered_dict_bimm_3b,
            s1_bimm_3b,
            s1_bimm_3b,
            max_word_len_bimm_3b,
            expected_bimm_3b,
            exception_bimm_3b,
            id="3b only FMM valid",
        ),
        pytest.param(
            passage_bimm_4a,
            frontier_dict_bimm_4a,
            other_encountered_dict_bimm_4a,
            s1_bimm_4a,
            s1_bimm_4a,
            max_word_len_bimm_4a,
            expected_bimm_4a,
            exception_bimm_4a,
            id="4a both valid: FMM fewer units",
        ),
        pytest.param(
            passage_bimm_4b,
            frontier_dict_bimm_4b,
            other_encountered_dict_bimm_4b,
            s1_bimm_4b,
            s1_bimm_4b,
            max_word_len_bimm_4b,
            expected_bimm_4b,
            exception_bimm_4b,
            id="4b both valid: BMM fewer units",
        ),
        pytest.param(
            passage_bimm_5,
            frontier_dict_bimm_5,
            other_encountered_dict_bimm_5,
            s1_bimm_5,
            s1_bimm_5,
            max_word_len_bimm_5,
            expected_bimm_5,
            exception_bimm_5,
            id="5 both valid: FMM fewer single chars",
        ),
        pytest.param(
            passage_bimm_6,
            frontier_dict_bimm_6,
            other_encountered_dict_bimm_6,
            s1_bimm_6,
            s1_bimm_6,
            max_word_len_bimm_6,
            expected_bimm_6,
            exception_bimm_6,
            id="6 full tie: BMM default",
        ),
    ],
)

# C) Function Call
def test_bimm(
    passage,
    frontier_dict,
    other_encountered_dict,
    static_hsk_triples,
    whole_hsk,
    max_word_len,
    expected,
    exception,
):
    if exception is NotEncounteredWordsError:
        with pytest.raises(NotEncounteredWordsError) as exp:
            bimm(
                passage,
                frontier_dict,
                other_encountered_dict,
                static_hsk_triples,
                whole_hsk,
                max_word_len,
            )
        assert exp.value.unlearned_words_list == expected

    elif exception is HallucinatedWordsError:
        with pytest.raises(HallucinatedWordsError) as exp:
            bimm(
                passage,
                frontier_dict,
                other_encountered_dict,
                static_hsk_triples,
                whole_hsk,
                max_word_len,
            )
        assert exp.value.halluc_words_list == expected
    else:
        assert expected == bimm(
            passage,
            frontier_dict,
            other_encountered_dict,
            static_hsk_triples,
            whole_hsk,
            max_word_len,
        )
