# FUNCTIONALITY: Loads data/hsk30.txt (built by prepare_hsk30.py) => Python dict once, 
"""
1. Fast existence checks and pinyin lookup against the HSK 3.0 vocabulary list.
2. Dict maps Mandarin word strings to TUPLES of pinyin readings
    - to accomodate words w/ multiple valid readings in different contexts
3. One line per word, readings packed onto it as "pinyin:level:pos:traditional" joined
# by ";" - same shape as backend/segmenter.py's POLYPHONIC_CHARS, just with
# structured fields per reading instead of a bare pinyin string.
"""

from collections import namedtuple
from pathlib import Path

HskEntry = namedtuple("HskEntry", "pinyin level pos traditional")


# reads txt into full HSK (word->tuple of pinyin readings) dict
def _load_hsk_vocab(path):
    vocab = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            word, readings = line.split("\t")
            vocab[word] = tuple(
                HskEntry(*reading.split(":")) for reading in readings.split(";")
            )
    return vocab

# generate HSK dictionary from txt using above
# need to define path explicitly, since running w/ CWD = potential FileNotFoundError
HSK_TXT_PATH = Path(__file__).parent / "hsk30.txt"  
HSK_VOCAB = _load_hsk_vocab(HSK_TXT_PATH)


# ---------------------------
# Helpers
# ---------------------------
# returns T/F if word exists or not in dict
def exists(word):
    return word in HSK_VOCAB


# returns tuple of pinyin strings for a given HSK word
def pinyin_readings(word):
    """All numbered-pinyin readings for a word, or () if not in the list."""
    return tuple(entry.pinyin for entry in HSK_VOCAB.get(word, ()))
