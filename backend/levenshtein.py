"""
levenshtein.py - applies the Levenshtein distance algorithm on a user's pinyin response.
"""

from re import split
from string import punctuation, whitespace
from math import dist

from backend.schemas import VocabUnit, PinyinError

LEV_DIST_THRESHOLD = 0.25

class UserPassageTooShort(Exception):
    def __init__(self, seg_user_passage, message="User passage had too few characters."):
        super().__init__(message)
        self.seg_user_passage = seg_user_passage


# ------------------------------
# Test User Input & HSK Dict
# ------------------------------
EX_VOCAB_UNIT_LIST = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(None,)),
    VocabUnit(vocab_id=3, chars=("中", "国"), pinyin=("zhong1", "guo2"), error_type=(None, None)),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(None,)),
]

EX_USER_RESPONSE = "wo2 - , zjong1 guo2? gaga2!!!"


# ------------------------------
# Grading Orchestrator
# ------------------------------
def levenshtein(
    user_passage: str,
    vocab_error_list: list[VocabUnit]
):
    # (1) User Response Trimming
    # split into per-char pinyin, right AFTER seeing number and INCLUDING it
    seg = split(r'(?<=\d|\-)', user_passage)
    seg_user_passage = []

    # trim spaces & punctuation (except designated skip character '-')
    for char_pinyin in seg:
        punc_and_spaces = (punctuation + whitespace).replace('-', '')

        seg_user_passage.append(char_pinyin.strip(punc_and_spaces))

    # remove any empty pinyin (split() always gives a last one as "")
    seg_user_passage = [char_pinyin for char_pinyin in seg_user_passage if char_pinyin]
    print(f"FINAL USER SEG PASSAGE: \n {seg_user_passage}")

    # (2) Iteration
    iter_user_passage = iter(seg_user_passage)

    for vocab_unit in vocab_error_list:
        # empty list to append errors to 
        unit_errors = []

        # iterate over all chars of this unit + calculate appropriate error label
        for py in vocab_unit.pinyin:
            # get user pinyin for this (next) char
            user_py = next(iter_user_passage, None)

            # ran out of user input
            if user_py is None:
                raise UserPassageTooShort(seg_user_passage)

            # A) Skip or Correct
            if user_py == '-':
                unit_errors.append(PinyinError.SKIPPED)
                continue
            if user_py == py:
                unit_errors.append(PinyinError.CORRECT)
                continue

            # B) Tonal Error
            if not user_py[-1] == py[-1]:
                unit_errors.append(PinyinError.TONE_ERROR)
                continue

            # C) Slight Errors
            # chop off tone & only compare letters
            py = py[:-1]
            user_py = user_py[:-1]

            valid_error_strs = gen_slight_error_strs(py)
            if user_py in valid_error_strs:
                unit_errors.append(valid_error_strs[user_py])
                continue

            # D) Typo
            if len(py) > 3:
                lev_dist = calc_lev_dist(py, user_py) / max(len(py), len(user_py))
                if lev_dist < LEV_DIST_THRESHOLD:
                    unit_errors.append(PinyinError.TYPO)
                    continue

            # E) Severe
            unit_errors.append(PinyinError.FORGOT)

        # add list of char-specific errors to the VocabUnit
        vocab_unit.error_type = tuple(unit_errors)

    return vocab_error_list


# ------------------------------
# Slight Error String Generation
# ------------------------------
def gen_slight_error_strs(
    py: str
) -> dict:
    """Checks given pinyin for validity of the 3 slight error types."""
    valid_error_strs = {}

    # Retroflex Error - starts with c, z, or s consonants
    if py[0] in {'c', 'z', 's'}:
        if not py[1] =='h':
            valid_error_strs[(py[0] + 'h' + py[1:])] = PinyinError.RETROFLEX_ERROR
        else:
            valid_error_strs[(py[0] + py[2:])] = PinyinError.RETROFLEX_ERROR
    
    # Umlaut Error - starts w/ n or l, next is u or v (either false neg or pos)
    if py[0] in {'n', 'l'} and py[1] in {'u', 'v'}:
        if py[1] == 'v':
            char_sub = 'u'
        else:
            char_sub = 'v'
        valid_error_strs[(py[0] + char_sub + py[2:])] = PinyinError.UMLAUT_ERROR

    # Nasal Error
    if py[-1] == 'n':
        valid_error_strs[(py + 'g')] = PinyinError.NASAL_ERROR
    elif py[-1] == 'g':
        valid_error_strs[(py[:-1])] = PinyinError.NASAL_ERROR

    return valid_error_strs


# ------------------------------
# Levenshtein Distance Calc
# ------------------------------
def calc_lev_dist(
    py: str,
    user_py: str
) -> float:
    """Calculates Levenshtein distance between two pinyin strings."""
    # base case: either string is exhausted => encode mismatches in other
    if not py:
        return len(user_py)
    if not user_py:
        return len(py)

    # if this (first) char matches, truncate both and continue
    if py[0] == user_py[0]:
        return calc_lev_dist(py[1:], user_py[1:])
    
    # otherwise, no match:
    else:
        transpos_cond = len(py) > 1 and len(user_py) > 1 and py[0] == user_py[1] and py[1] == user_py[0]
        transpos_total_dist = (
            ch_dist(py[0], py[1]) + calc_lev_dist(py[2:], user_py[2:]) 
            if transpos_cond
            else float('inf')
        )
        
        return min(
            # 1) user MISSED current char
            1 + calc_lev_dist(py[1:], user_py),

            # 2) user ADDED nonsense char
            1 + calc_lev_dist(py, user_py[1:]),

            # 3) user SUBBED nonsense char
            ch_dist(py[0], user_py[0]) + calc_lev_dist(py[1:], user_py[1:]),

            # 4) user SWAPPED this char w/ next
            transpos_total_dist
        )


# (x, y) key centers in units of 1 key-width, encoding the real ANSI stagger:
# home row shifted +0.25 right of the top row, bottom row +0.25 right of that.
QWERTY_COORDS = {
    'q': (2.00, 0), 'w': (3.00, 0), 'e': (4.00, 0), 'r': (5.00, 0), 't': (6.00, 0),
    'y': (7.00, 0), 'u': (8.00, 0), 'i': (9.00, 0), 'o': (10.00, 0), 'p': (11.00, 0),

    'a': (2.25, 1), 's': (3.25, 1), 'd': (4.25, 1), 'f': (5.25, 1), 'g': (6.25, 1),
    'h': (7.25, 1), 'j': (8.25, 1), 'k': (9.25, 1), 'l': (10.25, 1),

    'z': (2.75, 2), 'x': (3.75, 2), 'c': (4.75, 2), 'v': (5.75, 2), 'b': (6.75, 2),
    'n': (7.75, 2), 'm': (8.75, 2),
}
MAX_KEYBOARD_DIST = 9


def ch_dist(
    correct_ch: str,
    user_ch: str
) -> float:
    """Calculates keyboard Euclidean distance between correct and user-given characters."""
    pos_correct = QWERTY_COORDS[correct_ch.lower()]
    pos_user = QWERTY_COORDS[user_ch.lower()]
    return dist(pos_correct, pos_user) / MAX_KEYBOARD_DIST


def test_full_pipe():
    vocablist = levenshtein(EX_USER_RESPONSE, EX_VOCAB_UNIT_LIST)

    for unit in vocablist:
        print(f"Word: {unit.chars}")
        print(f"Error: {unit.error_type}")


# ------------------------------
# Basic Testing Apparatus
# ------------------------------
TEST_PINYIN = [
    # Valid Typos
    ["shuang", "shuanf"],
    ["chuang", "cjuang"],
    ["qiong", "qoing"],

    # Forgot Error
    ["shuang", "chuang"],
    ["chuang", "chan"],
    ["qiong", "qiun"],
    ["bian", "dian"]
]

def test_lev_dist():
    for pair in TEST_PINYIN:
        print(calc_lev_dist(pair[0], pair[1]) / max(len(pair[0]), len(pair[1])))

def main():
    test_full_pipe()

if __name__ == "__main__":
    main()