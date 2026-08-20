# Loads data/hsk30.txt (built by prepare_hsk30.py) into a dict once, for fast
# existence checks and pinyin lookup against the HSK 3.0 vocabulary list.
#
# Unlike polychars.txt - where every reading belongs to one character - a
# vocab word can itself have multiple valid readings (e.g. 好 hao3/hao4,
# 地方 di4fang0/di4fang1), so each word maps to a tuple of entries. One line
# per word, readings packed onto it as "pinyin:level:pos:traditional" joined
# by ";" - same shape as backend/segmenter.py's POLYPHONIC_CHARS, just with
# structured fields per reading instead of a bare pinyin string.

from collections import namedtuple

HskEntry = namedtuple("HskEntry", "pinyin level pos traditional")


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


# word -> tuple of HskEntry, one per distinct reading
HSK_VOCAB = _load_hsk_vocab("data/hsk30.txt")


def exists(word):
    return word in HSK_VOCAB


def pinyin_readings(word):
    """All numbered-pinyin readings for a word, or () if not in the list."""
    return tuple(entry.pinyin for entry in HSK_VOCAB.get(word, ()))
