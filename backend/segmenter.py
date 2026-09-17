# FUNCTIONALITY: segments, validates, and produces pinyin for the Claude passage
"""
Inputs:
    1. Dict compiling allowed vocab units:
        - All user's encountered words
        - Permanent func-word allowlist
        - List of possible new words (given to Claude to pick 1-4 from, if applicable)

    2. Claude passages - (1) Mandarin string and (2) pinyin string
Outputs:
    1. Segmented Mandarin passage & pinyin (stored as list[tuple[str, str]] or two separate list[str])

In case of any ERROR - (1) hallucination, (2) not-allowed words used, or (3) frontier/new word counts too low/high:
    - Returns with list of hallucinated words, not-allowed words used, and frontier/new counts for re-prompting.
"""

"""
# loads entire HSK 3.0 txt into O(1) navigatable list (tupling chars with pinyin )
# from /data/hsk_vocab.py import HSK_VOCAB, exists, pinyin_readings
#from pathlib import Path
#DATA_PATH = Path(__file__).parent.parent / "data" / "hsk_vocab.py"
#from DATA_PATH import HSK_VOCAB, exists, pinyin_readings
# -------------------
# loads poly chars file into O(1) navigatable list (tupling chars to pinyin representations) 
def _load_polyphonic_chars(path):
    chars = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            # split actual char w/ pinyin reps (still coupled as one string)
            char, pinyins = line.split("\t")
            # make new pair in dictionary for new key = char, value = tuple of the pinyins SEPARATED NOW
            chars[char] = tuple(pinyins.split(","))
    return chars
            

# characters tupled of all pinyin readings (tone: 1-4, 0 for the static/neutral tone)
POLYPHONIC_CHARS = _load_polyphonic_chars("data/polychars.txt")

"""

import regex

# -------------------
# Segmentation Errors
# -------------------
# if non-HSK words used, throw back to Claude
class HallucinatedWordsError(Exception):
    # exception constructor called when an error is "raised" by callee
    def __init__(self, halluc_words_list, message="non-HSK words detected"):        # arguments after "self" are EXPLICITLY passed in
        super().__init__(message)
        self.halluc_words_list = halluc_words_list


# if not-encountered words used, throw back to Claude
class NotEncounteredWordsError(Exception):
    def __init__(self, unlearned_words_list, message="Not-encountered words detected"):
        super().__init__(message)
        self.unlearned_words_list = unlearned_words_list


class FrontierWordsCountError(Exception):
    def __init__(self, num_frontier_words, message="Number of frontier words falls outside valid bounds"):
        super().__init__(message)
        self.num_frontier_words = num_frontier_words


# import entire HSK dict (word to pinyin readings tuple) & helpers
from data.hsk_vocab import HSK_VOCAB, exists, pinyin_readings

# static max length of all HSK 3.0 words
MAX_WORD_LEN = max(len(w) for w in HSK_VOCAB)

# --------------------
# Entry Point
# --------------------
def bimm(
        passage : str,          # the raw passage - including all punctuation
        hsk_dict : dict,        # all ENCOUNTERED words mapped to frontier or not (NO pinyin - use static)
        frontier_min : int,     # min frontier words acceptable in passage
        frontier_max : int      # max frontier words acceptable in pasage
):
    # 1) BiMM segmentation
    # extract only the chinese characters
    trim_passage = ""
    for ch in passage:
        if bool(regex.match(r'\p{Han}', ch)):
            trim_passage.append(ch)

    # conduct FMM and BMM
    fmm_seg_passage, fmm_unknown = fmm(trim_passage, passage_len)
    bmm_seg_passage, bmm_unknown = bmm(trim_passage, passage_len)
    
    # 2) Hallucination Analysis & Validation
    fmm_analysis = None
    bmm_analysis = None
    # Cases:
        # (1) both unknown lists are NOT empty = pick shorter list
    if len(fmm_unknown) and len(bmm_unknown):
        if len(fmm_unknown) > len(bmm_unknown):
            # return bmm unknown chars
            raise HallucinatedWordsError(bmm_unknown)
        # otherwise return fmm's
        raise HallucinatedWordsError(fmm_unknown)

    # (2) one is good, the other isn't => continue validating w/ remaining one
    elif len(fmm_unknown):
        bmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, bmm_seg_passage)
    elif len(bmm_unknown):
        fmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, fmm_seg_passage)
    # (3) both are good => validate w/ both
    else:
        fmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, fmm_seg_passage)
        bmm_analysis = validate_seg(frontier_min, frontier_max, hsk_dict, bmm_seg_passage)


    # 3) BiMM decision: 

    # Three cases:
    # (1) neither passage passed both tests:
        # if neither passed NotEncountered, report one with lower
        # otherwise report one with higher Frontier Words
        # RETURN TO CLAUDE
    # (2) only one passage passed -> return that one
    # (3) both passages passed -> return BMM

    # if NEITHER fulfills both, send back to Claude
    return 0


# takes valid segmented passage and produces pinyin answer key
def gen_pinyin(
        seg_passage : list,                 # segmented passage (list of strings)
        poly_chars : list,                  # imported polychars as dict (chars -> tuples of pinyin)
        hsk_pinyin_list : dict=HSK_VOCAB    # dict (chars to pinyin map)
):
    return 0


# ---------------------
# Callees 
# ---------------------

# validates fmm/bmm segmentation
def validate_seg(
        frontier_min : int,
        frontier_max : int,
        hsk_dict : dict,
        seg_passage : list[str]
):
    # instantiate the two dicts:
    seg_analysis = {
        "is_valid" : True,
        "num_frontier" : 0,
        "not_encountered" : []
    }

    # parse word by word, increment frontier # and keep track of 
    for word in seg_passage:
        # if not encountered, flag and keep going
        if word not in hsk_dict:
            seg_analysis["not_encountered"].append(word)
            seg_analysis["is_valid"] = False 
        # otherwise, check if frontier
        else:
            if hsk_dict[word] == True:
                seg_analysis["num_frontier"] += 1

    # if is_valid is still True (all words encountered), check frontier
    if seg_analysis["is_valid"]:
        seg_analysis["is_valid"] = seg_analysis["num_frontier"] >= frontier_min and seg_analysis["num_frontier"] <= frontier_max
    
    return seg_analysis


# Forward Maximum Matching
def fmm(
    passage : str,
    passage_len : int,
    hsk_list : dict = HSK_VOCAB,                    # static imported dict from txt
    max_word_len : int = MAX_WORD_LEN               # static max length of entire HSK
):
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
        while (num_chars > 0):
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


# Backward Maximum Matching
def bmm(
    passage : str,
    passage_len : int,
    hsk_list : dict = HSK_VOCAB,
    max_word_len : int = MAX_WORD_LEN
):
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
        while (num_chars > 0):
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
            seg_passage.append(poss_word)
    
            # move to next by skipping all chars in this word
            current_char = current_char - num_chars
        else:
            # mark as unknown
            unknown_chars.append(poss_word)
    
            # move to next by incrementing by 1
            current_char = current_char - 1
        
    
    # at the end, return the segmented string list
    return seg_passage, unknown_chars

# test FMM
def main():
    # ONLY 电脑 IS NOT ALLOWED
    seg_passage = [
        "你好", 
        "我", 
        "的", 
        "名字", 
        "是",
        "小明",
        "这个",
        "第一次",
        "用", 
        "电脑",
        "写字",
    ]

    test_passage_len = 22
    hsk_dict = {
        "你好" : True, 
        "我" : True, 
        "的" : True, 
        "名字" : True, 
        "是" : True, 
        "小明" : False, 
        "这个" : False, 
        "第一次" : False, 
        "用" : False, 
        "电脑" : False,
        "写字" : False}
    max_words = 3

    seg_analysis = validate_seg(3, 10, hsk_dict, seg_passage)
    print(seg_analysis["is_valid"])
    print(seg_analysis["num_frontier"])
    print(seg_analysis["not_encountered"])

if __name__ == "__main__":
    main()