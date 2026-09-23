"""
hsk_vocab.py - facilitates access to a static HSK 3.0 vocabulary list.

Functionality:
    1. Fast existence checks and pinyin lookup against the HSK 3.0 vocabulary list.
    2. Dict maps Mandarin word strings to custom HskEntrys, tupling pinyin readings with position, HSK 
    level and traditional characters.
    3. One line per word, readings packed onto it as "pinyin:level:pos:traditional" joined 
    by ";" - same shape as backend/segmenter.py's POLYPHONIC_CHARS, just with structured 
    fields per reading instead of a bare pinyin string.
"""

from collections import Counter, namedtuple
from pathlib import Path

HskEntry = namedtuple("HskEntry", "pinyin level pos traditional")

# ---------------------------
# HSK Dictionary Loading
# ---------------------------
def _load_hsk_vocab(path):
    """Reads data/hsk30.txt into a Python dictionary."""
    vocab = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            word, readings = line.split("\t")
            vocab[word] = tuple(
                # keys (words) map to tupled HskEntrys, which are themselves tuples
                # multiple HskEntrys = (1) different pinyin or (2) different pos (V vs. N) & level
                HskEntry(*reading.split(":")) for reading in readings.split(";")
            )
    return vocab

# actual generation - path explicitly defined (running w/ CWD = potential FileNotFound)
HSK_TXT_PATH = Path(__file__).parent / "hsk30.txt"  
HSK_VOCAB = _load_hsk_vocab(HSK_TXT_PATH)


# ---------------------------
# Helpers
# ---------------------------
def exists(word):
    """Checks for existence of a Mandarin string in the dictionary."""
    return word in HSK_VOCAB


def pinyin_readings(word, pinyin_dict):
    """All numbered-pinyin readings as tuple, or () if not in the list. Dictionary is also passed in."""
    return tuple(entry.pinyin for entry in pinyin_dict.get(word, ()))


def check_hsk_duplicates():
    """Independently tests for duplicate word values in hsk30.txt file."""
    # extract all of the words in the txt file
    words = []
    with open(HSK_TXT_PATH, encoding="utf-8") as hsk:
        for line in hsk:
            man_word = line.split("\t", 1)[0]
            words.append(man_word)
    
    # stores dict of words->counts for ALL HSK
    counts = Counter(words)

    # log duplicates (take all elements in counts dict IF counts > 1)
    duplicates = {key: count for key, count in counts.items() if count > 1}

    return duplicates


def dict_equals_txt():
    """Checks that the dictionary hasn't overwritten keys by validating # of lines against text file."""
    # compute num of unique words in txt file
    txt_word_count = 0
    with open(HSK_TXT_PATH, encoding="utf-8") as hsk:
        for line in hsk:
            line = line.rstrip("\n")
            if not line:
                continue
            txt_word_count += 1

    # if num is equal to actual dict, it's good
    return len(HSK_VOCAB) == txt_word_count