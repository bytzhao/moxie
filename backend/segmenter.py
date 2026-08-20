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


# loads entire HSK 3.0 txt into O(1) navigatable list (tupling chars with pinyin )
from data.hsk_vocab import HSK_VOCAB


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
            

# char -> tuple of all its pinyin readings (tone: 1-4, 0 for the static/neutral tone)
POLYPHONIC_CHARS = _load_polyphonic_chars("data/polychars.txt")


# main orchestrating loop
def segment_and_validate(
        
):
    # generate segmented Mandarin text

    # generate segmented Pinyin text
    return 0

