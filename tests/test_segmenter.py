"""
To Test:
- pinyin generation module
- then put together entire pipeline => test that
"""

import pytest
from backend.segmenter import bimm, gen_pinyin, seg_val_pinyin, HallucinatedWordsError, NotEncounteredWordsError, FrontierWordsCountError, PolyPinyinWordError
from data.hsk_vocab import HskEntry


# ---------------
# BiMM Module
# ---------------
# A) Testing Scenarios
# --- Scenario 1: complete pass ---
passage_1 = "你好，我的名字是小明。我用电脑写字。"
whole_hsk_1 = {"你好": True, "我": True, "的": True, "名字": True,
               "是": False, "小明": False, "用": False, "电脑": False, "写字": False}
hsk_dict_1 = whole_hsk_1
frontier_min_1, frontier_max_1 = 3, 5
max_word_len_1 = 2
expected_1 = [
    "你好", "我", "的", "名字", "是", "小明", "我", "用", "电脑", "写字"
]
exception_1 = None

# --- Scenario 2: hallucinated word ("猫" not in whole_hsk at any length) ---
passage_2 = "你好，我的猫用电脑写字。"
whole_hsk_2 = {"你好": True, "我": True, "的": True, "用": False, "电脑": False, "写字": False}
hsk_dict_2 = whole_hsk_2
frontier_min_2, frontier_max_2 = 1, 5
max_word_len_2 = 2
expected_2 = None
exception_2 = HallucinatedWordsError

# --- Scenario 3: frontier count one below minimum ---
passage_3 = "你好，我的名字是小明。"
whole_hsk_3 = {"你好": False, "我": True, "的": False, "名字": False, "是": False, "小明": False}
hsk_dict_3 = whole_hsk_3
frontier_min_3, frontier_max_3 = 2, 5
max_word_len_3 = 2
expected_3 = None
exception_3 = FrontierWordsCountError

# --- Scenario 4: valid word, not in the encountered dict ("喜欢","电脑" in whole_hsk only) ---
passage_4 = "你好，我的名字喜欢电脑。"
whole_hsk_4 = {"你好": None, "我": None, "的": None, "名字": None, "喜欢": None, "电脑": None}
hsk_dict_4 = {"你好": True, "我": True, "的": False, "名字": False}
frontier_min_4, frontier_max_4 = 1, 5
max_word_len_4 = 2
expected_4 = None
exception_4 = NotEncounteredWordsError


# B) Parametrization
@pytest.mark.parametrize("passage, vocab_dict, frontier_dict, f_min, f_max, max_word_len, expected, exception",[
    pytest.param(passage_1, whole_hsk_1, hsk_dict_1, frontier_min_1, frontier_max_1, max_word_len_1, expected_1, exception_1, id="pass"),
    pytest.param(passage_2, whole_hsk_2, hsk_dict_2, frontier_min_2, frontier_max_2, max_word_len_2, expected_2, exception_2,  id="hallucinated word"),
    pytest.param(passage_3, whole_hsk_3, hsk_dict_3, frontier_min_3, frontier_max_3, max_word_len_3, expected_3, exception_3, id="frontier num low"),
    pytest.param(passage_4, whole_hsk_4, hsk_dict_4, frontier_min_4, frontier_max_4, max_word_len_4, expected_4, exception_4, id="not encountered word")
])


# C) Function Call
def test_bimm_all_around(passage, vocab_dict, frontier_dict, f_min, f_max, max_word_len, expected, exception):
    if exception is not None:
        with pytest.raises(exception):
            bimm(passage, frontier_dict, f_min, f_max, vocab_dict, max_word_len)
    else:
        assert bimm(passage, frontier_dict, f_min, f_max, vocab_dict, max_word_len) == expected


# ---------------
# Pinyin Generation Module
# ---------------
# A) Testing Scenarios
# --- Scenario 1: complete pass, includes a same-pinyin/different-pos word ---
seg_passage_1 = ["你好", "我", "的", "名字", "是", "小明", "写字"]
poly_chars_1 = {}
hsk_pinyin_list_1 = {
    "你好": (HskEntry("ni3hao3", "1", "IE", "你好"),),
    "我":   (HskEntry("wo3", "1", "PN", "我"),),
    "的":   (HskEntry("de0", "1", "PART", "的"),),
    "名字": (HskEntry("ming2zi0", "1", "N", "名字"),),
    "是":   (HskEntry("shi4", "1", "V", "是"),),
    "小明": (HskEntry("xiao3ming2", "1", "N", "小明"),),
    "写字": (HskEntry("xie3zi4", "2", "V", "写字"), HskEntry("xie3zi4", "2", "N", "写字")),
}
pinyin_1 = [
    "ni3hao3",
    "wo3",
    "de0",
    "ming2zi0",
    "shi4",
    "xiao3ming2",
    "xie3zi4"
]
exception_1 = None

# --- Scenario 2: single-char polyphonic word, via poly_chars ---
seg_passage_2 = ["我", "还", "没", "写字"]
poly_chars_2 = {"还": ("hai2", "huan2")}
hsk_pinyin_list_2 = {
    "我":   (HskEntry("wo3", "1", "PN", "我"),),
    "还":   (HskEntry("hai2", "1", "ADV", "还"),),
    "没":   (HskEntry("mei2", "1", "ADV", "没"),),
    "写字": (HskEntry("xie3zi4", "2", "V", "写字"),),
}
pinyin_2 = [
    "wo3",
    None,
    "mei2",
    "xie3zi4"
]
exception_2 = PolyPinyinWordError

# --- Scenario 3: word-level ambiguity, genuinely different pinyin across entries ---
seg_passage_3 = ["这", "是", "假", "的"]
poly_chars_3 = {}
hsk_pinyin_list_3 = {
    "这": (HskEntry("zhe4", "1", "PN", "這"),),
    "是": (HskEntry("shi4", "1", "V", "是"),),
    "假": (HskEntry("jia3", "3", "ADJ", "假"), HskEntry("jia4", "2", "N", "假")),
    "的": (HskEntry("de0", "1", "PART", "的"),),
}
pinyin_3 = [
    "zhe4",
    "shi4",
    None,
    "de0"
]
exception_3 = PolyPinyinWordError

# --- Scenario 4: mixed — both a poly_chars word and a multi-pinyin HSK word ---
seg_passage_4 = ["我", "还", "没", "假", "的"]
poly_chars_4 = {"还": ("hai2", "huan2")}
hsk_pinyin_list_4 = {
    "我": (HskEntry("wo3", "1", "PN", "我"),),
    "还": (HskEntry("hai2", "1", "ADV", "还"),),
    "没": (HskEntry("mei2", "1", "ADV", "没"),),
    "假": (HskEntry("jia3", "3", "ADJ", "假"), HskEntry("jia4", "2", "N", "假")),
    "的": (HskEntry("de0", "1", "PART", "的"),),
}
pinyin_4 = [
    "wo3",
    None,
    "mei2",
    None,
    "de0"
]
exception_4 = PolyPinyinWordError


# B) Parametrization 
@pytest.mark.parametrize("seg_passage, poly_chars, hsk_pinyin, expected, exception", [
    pytest.param(seg_passage_1, poly_chars_1, hsk_pinyin_list_1, pinyin_1, exception_1),
    pytest.param(seg_passage_2, poly_chars_2, hsk_pinyin_list_2, pinyin_2, exception_2),
    pytest.param(seg_passage_3, poly_chars_3, hsk_pinyin_list_3, pinyin_3, exception_3),
    pytest.param(seg_passage_4, poly_chars_4, hsk_pinyin_list_4, pinyin_4, exception_4)
])


# C) Function Call
# segmented passage list[str], poly_chars, hsk_pinyin, expected, exception
def test_pinyin_gen_all_around(seg_passage, poly_chars, hsk_pinyin, expected, exception):
    if exception is not None:
        with pytest.raises(PolyPinyinWordError) as pinyin_error:
            gen_pinyin(seg_passage, poly_chars, hsk_pinyin)
        assert pinyin_error.value.partial_pinyin_passage == expected
    else:
        assert gen_pinyin(seg_passage, poly_chars, hsk_pinyin) == expected


# ---------------
# Full Pipeline (seg_val_pinyin)
# ---------------
# NOTE: seg_val_pinyin() does not expose whole_hsk/max_word_len/poly_chars/hsk_pinyin_list
# overrides — it always calls bimm()/gen_pinyin() with their real static-data defaults
# (HSK_VOCAB from data/hsk30.txt, POLY_CHARS from data/polychars.txt). So unlike the
# scenario dicts above, every word below is a REAL entry in those files — verified against
# the actual data by running seg_val_pinyin() directly before writing this in.
# A) Testing Scenarios
# --- Scenario 1: full pass, seg and pinyin (all real HSK words, none polyphonic) ---
passage_1 = "我是学生。我认识老师。今天我很高兴。"
hsk_encountered_dict_1 = {
    "我": False, "是": False, "学生": False, "认识": False,
    "老师": False, "今天": False, "很": False, "高兴": False,
}
frontier_min_1, frontier_max_1 = 0, 8
expected_1 = {
    "我" : "wo3",
    "是" : "shi4",
    "学生" : "xue2sheng1",
    "认识" : "ren4shi0",
    "老师" : "lao3shi1",
    "今天" : "jin1tian1",
    "我" : "wo3",
    "很" : "hen3",
    "高兴" : "gao1xing4"
}
exception_1 = None

# --- Scenario 2: hallucinated word in seg ("甭" is not in HSK_VOCAB at any length) ---
passage_2 = "我甭是学生。"
hsk_encountered_dict_2 = {"我": False, "是": False, "学生": False}
frontier_min_2, frontier_max_2 = 0, 5
expected_2 = None
exception_2 = HallucinatedWordsError

# --- Scenario 3: not-encountered word in seg ("学生" is real HSK, but left out of hsk_encountered_dict) ---
passage_3 = "我是学生。我认识老师。"
hsk_encountered_dict_3 = {"我": False, "是": False, "认识": False, "老师": False}
frontier_min_3, frontier_max_3 = 0, 5
expected_3 = None
exception_3 = NotEncounteredWordsError

# --- Scenario 4: frontier word count mismatch (all words known/encountered, but frontier range is impossible) ---
passage_4 = "我是学生。我认识老师。"
hsk_encountered_dict_4 = {"我": True, "是": False, "学生": False, "认识": False, "老师": False}
frontier_min_4, frontier_max_4 = 50, 60
expected_4 = None
exception_4 = FrontierWordsCountError

# --- Scenario 5: seg + validation all pass, but pinyin is arbitrary ("好" = hao3 Adj/Adv vs. hao4 V; also in polychars.txt) ---
passage_5 = "我很好。我是学生。"
hsk_encountered_dict_5 = {"我": False, "很": False, "好": False, "是": False, "学生": False}
frontier_min_5, frontier_max_5 = 0, 8
expected_5 = None
exception_5 = PolyPinyinWordError


# B) Parametrization
@pytest.mark.parametrize("passage, hsk_encountered, f_min, f_max, expected, exception", [
    pytest.param(passage_1, hsk_encountered_dict_1, frontier_min_1, frontier_max_1, expected_1, exception_1),
    pytest.param(passage_2, hsk_encountered_dict_2, frontier_min_2, frontier_max_2, expected_2, exception_2),
    pytest.param(passage_3, hsk_encountered_dict_3, frontier_min_3, frontier_max_3, expected_3, exception_3),
    pytest.param(passage_4, hsk_encountered_dict_4, frontier_min_4, frontier_max_4, expected_4, exception_4),
    pytest.param(passage_5, hsk_encountered_dict_5, frontier_min_5, frontier_max_5, expected_5, exception_5)
])


# C) Function Call
def test_entire_pipe(passage, hsk_encountered, f_min, f_max, expected, exception):
    if exception is not None:
        with pytest.raises(exception):
            seg_val_pinyin(passage, hsk_encountered, f_min, f_max)
    else:
        assert seg_val_pinyin(passage, hsk_encountered, f_min, f_max) == expected