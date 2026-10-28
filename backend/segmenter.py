"""
segmenter.py - facilitates segmentation in Frontier Passage Generation (FPG).

This module orchestrates the segmentation of Claude-outputted passages during FPG.
Segmentation checks for string-level errors in the passage, parsing for hallucinated (non-HSK) characters,
numbers, the Latin alphabet, as well as Mandarin words that haven't been encountered in any form by the user.
"""

import re
from enum import IntEnum

from data.hsk_vocab import HSK_VOCAB


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
    """Exception raised when passage includes HSK words not yet encountered by the user.
    - NOTE: this means none of the units w/ this Mandarin spelling has been encountered, which is a broader condition
        than a specific unit not being encountered before.
    Returns: list of not-yet-encountered Mandarin words.
    """

    def __init__(self, unlearned_words_list, message="Not-encountered words detected"):
        super().__init__(message)
        self.unlearned_words_list = unlearned_words_list


class ValidationCode(IntEnum):
    VALID_PASSAGE = 0
    NOT_ENCOUNTERED_ERROR = 1
    HALLUC_ERROR = 2


ERROR_TABLE = {
    ValidationCode.HALLUC_ERROR: (HallucinatedWordsError, lambda x: x),
    ValidationCode.NOT_ENCOUNTERED_ERROR: (NotEncounteredWordsError, lambda x: x),
}

MAX_WORD_LEN = max(len(w) for w in HSK_VOCAB)  # static max length of all HSK 3.0 words


# ------------------------------
# BiMM & Pinyin Modules
# ------------------------------
def bimm(
    str_passage: str,
    frontier_dict: dict,
    other_encountered_dict: dict,
    static_hsk_triples: dict,
    whole_hsk: dict = HSK_VOCAB,
    max_word_len: int = MAX_WORD_LEN,
) -> list[str]:

    # call FMM and BMM on the passages
    passage_len = len(str_passage)
    fmm_seg, fmm_unknown = fmm(str_passage, passage_len, whole_hsk, max_word_len)
    bmm_seg, bmm_unknown = bmm(str_passage, passage_len, whole_hsk, max_word_len)

    # check if (1) halluced words or (2) not-encountered words
    fmm_anal = validate_seg(
        frontier_dict, other_encountered_dict, static_hsk_triples, fmm_seg, fmm_unknown
    )
    bmm_anal = validate_seg(
        frontier_dict, other_encountered_dict, static_hsk_triples, bmm_seg, bmm_unknown
    )

    fmm_validate_code = fmm_anal["is_valid"]
    bmm_validate_code = bmm_anal["is_valid"]

    # (1) Neither is a valid segmentation
    if fmm_validate_code != 0 and bmm_validate_code != 0:
        # A) errors are different -> return less severe one
        if fmm_validate_code > bmm_validate_code:
            error_code, error_return = ERROR_TABLE[bmm_validate_code]
            raise error_code(error_return(list(bmm_anal.values())[bmm_validate_code]))

        elif fmm_validate_code < bmm_validate_code:
            error_code, error_return = ERROR_TABLE[fmm_validate_code]
            raise error_code(error_return(list(fmm_anal.values())[fmm_validate_code]))

        # B) errors are the same
        else:
            error_code, error_return = ERROR_TABLE[bmm_validate_code]

            # stores the LENGTH of errors
            fmm_errors = len(list(fmm_anal.values())[fmm_validate_code])
            bmm_errors = len(list(bmm_anal.values())[bmm_validate_code])

            # if fmm len smaller, return that
            if fmm_errors < bmm_errors:
                raise error_code(
                    error_return(list(fmm_anal.values())[fmm_validate_code])
                )
            else:
                raise error_code(
                    error_return(list(bmm_anal.values())[bmm_validate_code])
                )

    # (2) only one is good
    elif fmm_validate_code != 0:
        return bmm_seg
    elif bmm_validate_code != 0:
        return fmm_seg

    # (3) both are good
    else:
        # A) unit len diff => return shorter
        if len(fmm_seg) < len(bmm_seg):
            return fmm_seg
        elif len(bmm_seg) < len(fmm_seg):
            return bmm_seg

        # B) single-char unit diff => return one w/ fewer
        fmm_single_chars = sum(1 for unit in fmm_seg if len(unit) == 1)
        bmm_single_chars = sum(1 for unit in bmm_seg if len(unit) == 1)

        if fmm_single_chars < bmm_single_chars:
            return fmm_seg

        # C) tiebreak = default return BMM
        return bmm_seg


# ------------------------------
# Segmentation Validation
# ------------------------------
def validate_seg(
    frontier_dict: dict,
    other_encountered_dict: dict,
    static_hsk_triples: dict,
    seg_passage: list[str],
    unknown_chars: list[str],
):
    """Validates a segmented passage against the 2 string-level errors."""
    # instantiate dict w/ empty fields, assumed valid at start
    seg_analysis = {
        "is_valid": ValidationCode.VALID_PASSAGE,
        "not_encountered": [],
        "halluc_words": [],
    }

    # 1) check hallucinations
    if len(unknown_chars):
        seg_analysis["halluc_words"] = unknown_chars
        seg_analysis["is_valid"] = ValidationCode.HALLUC_ERROR
        return seg_analysis

    # 2) check not-encountered words
    for word in seg_passage:
        # if is punc/space, SKIP CHECK
        if bool(re.match(r"^[\s\W]$", word)):
            continue

        # check all IDs that correspond this word
        id_triples = static_hsk_triples[word]
        ids = [vocab_triple.vocab_id for vocab_triple in id_triples]

        # find all the triples

        # if none of IDs have been seen AND word hasn't been counted yet
        if (
            set(ids).isdisjoint(frontier_dict)
            and set(ids).isdisjoint(other_encountered_dict)
            and word not in set(seg_analysis["not_encountered"])
        ):
            seg_analysis["not_encountered"].append(word)
            seg_analysis["is_valid"] = ValidationCode.NOT_ENCOUNTERED_ERROR

    return seg_analysis


# ------------------------------
# FMM & BMM
# ------------------------------
def fmm(passage: str, passage_len: int, hsk_list: dict, max_word_len: int):
    """Conducts Forward Maximum Matching on a given str passage."""
    current_char = 0  # pointer to char where currently evaluating next longest word
    seg_passage = []  # list of individual word strings
    unknown_chars = []  # list of individual invalid chars

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

        # if word is NOT Mandarin (punc or space)
        elif bool(re.match(r"^[\s\W]$", poss_word)):
            seg_passage.append(poss_word)

            current_char = current_char + 1

        # otherwise, it must be a hallucinated Mandarin char
        else:
            # mark as unknown
            unknown_chars.append(poss_word)

            # move to next by incrementing by 1
            current_char = current_char + 1

    # at the end, return the segmented string list
    return seg_passage, unknown_chars


def bmm(passage: str, passage_len: int, hsk_list: dict, max_word_len: int):
    """Conducts Backward Maximum Matching on a given str passage."""
    current_char = (
        passage_len - 1
    )  # pointer to char where currently evaluating next longest word
    seg_passage = []  # list of individual word strings
    unknown_chars = []  # list of individual invalid chars

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

        # if word is NOT Mandarin (punc or space)
        elif bool(re.match(r"^[\s\W]$", poss_word)):
            seg_passage.insert(0, poss_word)

            current_char = current_char - 1

        else:
            # mark as unknown
            unknown_chars.insert(0, poss_word)

            # move to next by incrementing by 1
            current_char = current_char - 1

    # at the end, return the segmented string list
    return seg_passage, unknown_chars
