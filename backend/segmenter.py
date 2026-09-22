"""
segmenter.py - facilitates segmentation & pinyin generation pipeline in Frontier Passage Generation (FPG).

This module orchestrates the segmentation and pinyin answer-key generation of Claude-outputted passages during FPG.
A succesful iteration of the entire pipeline greenlights the passage to be sent to the user interface.
Otherwise, a suite of errors notify the FPG orchestrator of complications with the Claude passage.

Inputs:
1. Claude-generated string passage
2. encountered HSK dict (words -> frontier/not frontier)
3. Frontier allowance specification
    Other:
    4. HSK_VOCAB - mapping chars to their pinyin reading(s)
    5. POLY_CHARS - mapping individual polyphonic chars to their pinyin readings

Outputs:
1. Segmented passage (list of word strings)
2. Pinyin of passage (maps each word chunk to pinyin)

Segmentation Errors:
1. HallucinatedWordsError - passage includes Mandarin chars not included in HSK 3.0.
2. NotEncounteredWordsError - passage includes HSK chars/words not yet encountered by the user.
3. FrontierWordsCountError - passage includes either too many or too few frontier words.

Pinyin Error:
1. PolyPinyinWordError - passage includes chars/words with multiple pinyin readings, requiring further Claude clarification.
"""


from pathlib import Path
from enum import IntEnum

import regex

from data.hsk_vocab import HSK_VOCAB, pinyin_readings


def _load_polyphonic_chars(path):
    """Loads data/polychars.txt into a dictionary that maps each character to a tuple of all valid pinyin readings."""
    chars = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            # split actual char w/ pinyin reps by splitting across the tab
            char, pinyins = line.split("\t")
            # make new pair in dictionary for new key = char, value = tuple of the pinyins SEPARATED NOW
            chars[char] = tuple(pinyins.split(","))
    return chars


POLY_TXT_PATH = Path(__file__).parent.parent / "data" / "polychars.txt"
POLY_CHARS = _load_polyphonic_chars(POLY_TXT_PATH)


# ------------------------------
# Segmentation & Pinyin Errors
# ------------------------------
class HallucinatedWordsError(Exception):
    """Exception raised when passage includes Mandarin chars not included in HSK 3.0.
    Returns: list of hallucinated words.
    """
    def __init__(self, halluc_words_list, message="non-HSK words detected"):
        super().__init__(message)
        self.halluc_words_list = halluc_words_list


class NotEncounteredWordsError(Exception):
    """Exception raised when passage includes HSK chars/words not yet encountered by the user.
    Returns: list of not-yet-encountered words.
    """
    def __init__(self, unlearned_words_list, message="Not-encountered words detected"):
        super().__init__(message)
        self.unlearned_words_list = unlearned_words_list


class FrontierWordsCountError(Exception):
    """Exception raised when passage includes either too many or too few frontier words.
    Returns: number of frontier words present in the passage.
    """
    def __init__(self, num_frontier_words, message="Number of frontier words falls outside valid bounds"):
        super().__init__(message)
        self.num_frontier_words = num_frontier_words


class PolyPinyinWordError(Exception):
    """Exception raised when passage includes chars/words with multiple pinyin readings, requiring further Claude clarification.
    Returns:
        1. dictionary of polyphonic chars/words present, mapping position to char/word tupled with all valid pinyin readings
        2. fully segmented Mandarin passage
        3. partial pinyin-generated passage
    """
    def __init__(self, poly_words, seg_passage, partial_pinyin_passage, message="Chars/words w/ obscure (multiple) pinyins in passage need to be resolved."):
        super().__init__(message)
        self.poly_words = poly_words
        self.seg_passage = seg_passage
        self.partial_pinyin_passage = partial_pinyin_passage


class ValidationCode(IntEnum):
    VALID_PASSAGE = 0
    HALLUC_ERROR = 1
    NOT_ENCOUNTERED_ERROR = 2
    FRONTIER_ERROR = 3


ERROR_TABLE = {
    ValidationCode.HALLUC_ERROR: (HallucinatedWordsError, lambda x: x),
    ValidationCode.NOT_ENCOUNTERED_ERROR: (NotEncounteredWordsError, lambda x: x),
    ValidationCode.FRONTIER_ERROR: (FrontierWordsCountError, len)
}


MAX_WORD_LEN = max(len(w) for w in HSK_VOCAB)          # static max length of all HSK 3.0 words


# ------------------------------
# Main Pipeline
# ------------------------------
def seg_val_pinyin(
        claude_passage: str,
        hsk_encountered_dict: dict,
        frontier_min: int,
        frontier_max: int
):
    """Wraps entire segmentation, validation, and pinyin generation pipeline."""
    # 1) BiMM
    seg_passage = bimm(claude_passage, hsk_encountered_dict, frontier_min, frontier_max)

    # 2) Pinyin Generation
    pinyin_passage = gen_pinyin(seg_passage)

    # 3) Return
    return seg_passage, pinyin_passage


# ------------------------------
# BiMM & Pinyin Modules
# ------------------------------
def bimm(
        passage: str,                       # the raw passage - including all punctuation
        hsk_dict: dict,                     # all ENCOUNTERED words mapped to frontier or not (NO pinyin - use static)
        frontier_min: int,                  # min frontier words acceptable in passage
        frontier_max: int,                  # max frontier words acceptable in pasage
        whole_hsk: dict = HSK_VOCAB,        # pass down to fmm/bmm - if bimm() module testing doesn't specify otherwise, is same as before
        max_word_len: int = MAX_WORD_LEN    # pass down to fmm/bmm
):
    """Conducts BiMM segmentation using FMM and BMM, validating on the 3 potential segmentation errors."""
    # 1) FMM & BMM Segmentation
    # extract only chinese chars from the given passage
    trim_passage = []
    for ch in passage:
        if bool(regex.match(r'\p{Han}', ch)):
            trim_passage.append(ch)
    trim_passage = "".join(trim_passage)
    passage_len = len(trim_passage)

    # conduct FMM and BMM
    fmm_seg_passage, fmm_unknown = fmm(trim_passage, passage_len, whole_hsk, max_word_len)
    bmm_seg_passage, bmm_unknown = bmm(trim_passage, passage_len, whole_hsk, max_word_len)

    # 2) Validation
    fmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, fmm_seg_passage, fmm_unknown)
    bmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, bmm_seg_passage, bmm_unknown)

    # 3) Evaluation
    fmm_validate_code = fmm_analysis["is_valid"]
    bmm_validate_code = bmm_analysis["is_valid"]

    # (1) Neither is a valid segmentation
    if fmm_validate_code != 0 and bmm_validate_code != 0:
        # A) errors are different -> return higher one
        if fmm_validate_code > bmm_validate_code:
            error_code, error_return = ERROR_TABLE[fmm_validate_code]
            raise error_code(error_return(list(fmm_analysis.values())[fmm_validate_code]))

        elif fmm_validate_code < bmm_validate_code:
            error_code, error_return = ERROR_TABLE[bmm_validate_code]
            raise error_code(error_return(list(bmm_analysis.values())[bmm_validate_code]))

        # B) errors are the same
        else:
            error_code, error_return = ERROR_TABLE[bmm_validate_code]

            # stores the LENGTH of errors
            fmm_errors = len(list(fmm_analysis.values())[fmm_validate_code])
            bmm_errors = len(list(bmm_analysis.values())[bmm_validate_code])

            # if fmm len smaller, return that
            if fmm_errors < bmm_errors:
                raise error_code(error_return(list(fmm_analysis.values())[fmm_validate_code]))
            else:
                raise error_code(error_return(list(bmm_analysis.values())[bmm_validate_code]))

    # (2) only one is good
    elif fmm_validate_code != 0:
        return bmm_seg_passage
    elif bmm_validate_code != 0:
        return fmm_seg_passage
    # (3) both are good
    else:
        return bmm_seg_passage      # default return BMM (for now)


def gen_pinyin(
        seg_passage: list[str],            # segmented passage (list of strings)
        poly_chars: dict = POLY_CHARS,     # imported polychars as dict (chars -> tuples of pinyin)
        hsk_pinyin_list: dict = HSK_VOCAB  # dict (chars to HskEntry tuple object)
):
    """Generates pinyin for a valid, segmented passage (list[str])."""
    # dict (position->char/word, pinyin readings):
    poly_words: dict[str, tuple] = {}
    position = 0        # starting at 0, aligned with seg passage list

    # segmented pinyin list
    seg_passage_pinyin = []

    # iterate through the list of strings
    for word in seg_passage:
        # if it's a polychar, add to poly (IF NOT ALREADY) + denote empty pinyin
        if word in poly_chars:
            poly_words[position] = word, poly_chars[word]
            seg_passage_pinyin.append(None)

        # also, if it's a poly-word (more than 1 DISTINCT reading in COMPLETE list), add
        elif len(set(pinyin_readings(word, hsk_pinyin_list))) > 1:
            poly_words[position] = word, pinyin_readings(word, hsk_pinyin_list)
            seg_passage_pinyin.append(None)

        # otherwise, we can safely write pinyin
        else:
            seg_passage_pinyin.append(pinyin_readings(word, hsk_pinyin_list)[0])

        # increment the position
        position += 1

    # if poly-list HAS chars/words, return (1) poly list and (2) partial pinyin built
    if len(poly_words) > 0:
        raise PolyPinyinWordError(poly_words, seg_passage, seg_passage_pinyin)

    return seg_passage_pinyin


# ------------------------------
# Callees
# ------------------------------
def validate_seg(
        frontier_min: int,
        frontier_max: int,
        hsk_dict: dict,
        seg_passage: list[str],
        unknown_chars: list[str]
):
    """Validates a segmented passage against the 3 segmentation errors."""
    # instantiate dict w/ empty fields, assumed valid at start
    seg_analysis = {
        "is_valid": ValidationCode.VALID_PASSAGE,
        "halluc_words": [],
        "not_encountered": [],
        "frontier_words": []
    }

    # 1) check hallucinations
    if len(unknown_chars):
        seg_analysis["halluc_words"] = unknown_chars
        seg_analysis["is_valid"] = ValidationCode.HALLUC_ERROR
        return seg_analysis

    # 2) iterate for not-encountered & frontier
    for word in seg_passage:
        # not encountered word (NO DOUBLE COUNT)=> immediately flag to 2
        if word not in hsk_dict and word not in seg_analysis["not_encountered"]:
            seg_analysis["not_encountered"].append(word)
            seg_analysis["is_valid"] = ValidationCode.NOT_ENCOUNTERED_ERROR

        # check frontier (NO DOUBLE COUNT!)
        elif hsk_dict[word] and hsk_dict[word] not in seg_analysis["frontier_words"]:
            seg_analysis["frontier_words"].append(word)

    # if not-encountered words found ANYWHERE, return that
    if seg_analysis["is_valid"] == ValidationCode.NOT_ENCOUNTERED_ERROR:
        return seg_analysis

    # otherwise, evaluate frontier
    if len(seg_analysis["frontier_words"]) not in range(frontier_min, frontier_max + 1):
        seg_analysis["is_valid"] = ValidationCode.FRONTIER_ERROR
    return seg_analysis


def fmm(
    passage: str,
    passage_len: int,
    hsk_list: dict,
    max_word_len: int
):
    """Conducts Forward Maximum Matching on a given str passage."""
    current_char = 0        # pointer to char where currently evaluating next longest word
    seg_passage = []        # list of individual word strings
    unknown_chars = []      # list of individual invalid chars

    # while there are chars left to process, keep going
    while current_char < passage_len:
        chars_left = passage_len - current_char
        word_is_found = False

        # if there's enough chars to accomodate max length
        if chars_left >= max_word_len:
            # take the MAX number of characters possible to start
            num_chars = max_word_len
        # otherwise take however many are left
        else:
            num_chars = chars_left

        # from chosen max len, find longest valid word
        while num_chars > 0:
            # compute the word
            poss_word = passage[current_char : current_char + num_chars]

            # if we've found a word
            if poss_word in hsk_list:
                # mark as found and exit
                word_is_found = True
                break

            # otherwise, truncate end and keep going
            else:
                num_chars = num_chars - 1

        # if word was found somewhere
        if word_is_found:
            # add it
            seg_passage.append(poss_word)

            # move to next by skipping all chars in this word
            current_char = current_char + num_chars
        else:
            # mark as unknown
            unknown_chars.append(poss_word)

            # move to next by incrementing by 1
            current_char = current_char + 1


    # at the end, return the segmented string list
    return seg_passage, unknown_chars


def bmm(
    passage: str,
    passage_len: int,
    hsk_list: dict,
    max_word_len: int
):
    """Conducts Backward Maximum Matching on a given str passage."""
    current_char = passage_len - 1      # pointer to char where currently evaluating next longest word
    seg_passage = []                    # list of individual word strings
    unknown_chars = []                  # list of individual invalid chars

    # while there are chars left to process, keep going
    while current_char > -1:
        chars_left = current_char + 1
        word_is_found = False

        # if there's enough chars to accomodate max length
        if chars_left >= max_word_len:
            # take the MAX number of characters possible to start
            num_chars = max_word_len
        # otherwise take however many are left
        else:
            num_chars = chars_left

        # from chosen max len, find longest valid word
        while num_chars > 0:
            # compute the word
            poss_word = passage[current_char - num_chars + 1 : current_char + 1]

            # if we've found a word
            if poss_word in hsk_list:
                # mark as found and exit
                word_is_found = True
                break

            # otherwise, truncate end and keep going
            else:
                num_chars = num_chars - 1

        # if word was found somewhere
        if word_is_found:
            # add it
            seg_passage.insert(0, poss_word)

            # move to next by skipping all chars in this word
            current_char = current_char - num_chars
        else:
            # mark as unknown
            unknown_chars.insert(0, poss_word)

            # move to next by incrementing by 1
            current_char = current_char - 1


    # at the end, return the segmented string list
    return seg_passage, unknown_chars