# One-off (rerunnable) prep script: builds data/hsk30.txt from the ivankra/hsk30
# source list (MIT licensed): https://github.com/ivankra/hsk30
#
# Pulls hsk30-expanded.csv (one row per clean hanzi variant, no pipe/paren
# artifacts), converts its accented pinyin to this project's numbered-tone
# convention (1-4, 0 for neutral, matching data/polychars.txt), drops rows
# flagged as illustrative "Example" entries rather than real vocab units, and
# writes data/hsk30.txt for hsk_vocab.py to load - one line per word, with
# its (possibly several) readings packed onto that line: same shape as
# polychars.txt, just with pinyin/level/pos/traditional per reading instead
# of a bare pinyin string.
#
# Requires: pip install dragonmapper (prep-time only, not a runtime dependency
# of the app - hsk30.txt itself is plain text with no parsing library needed).
#
# Usage: python3 data/prepare_hsk30.py

import csv
import urllib.request
from itertools import groupby

from dragonmapper import transcriptions

SOURCE_URL = "https://raw.githubusercontent.com/ivankra/hsk30/master/hsk30-expanded.csv"
OUTPUT_PATH = "data/hsk30.txt"


def _to_numbered_pinyin(accented):
    numbered = transcriptions.accented_to_numbered(accented)
    # collapse multi-syllable separators (source uses literal spaces for a
    # few multi-word terms) since tone digits already delimit syllables
    numbered = numbered.replace(" ", "").replace("'", "").replace("-", "")
    # this project uses 0 for neutral tone; dragonmapper emits 5
    return numbered.replace("5", "0")


def main():
    with urllib.request.urlopen(SOURCE_URL) as resp:
        raw = resp.read().decode("utf-8")

    rows = list(csv.DictReader(raw.splitlines()))

    seen = set()
    entries = []
    for row in rows:
        if row["Example"].strip():
            continue  # illustrative example for a prefix/suffix entry, not a real vocab unit
        word = row["Simplified"]
        pinyin = _to_numbered_pinyin(row["Pinyin"])
        level = row["Level"]
        pos = row["POS"]
        traditional = row["Traditional"]
        key = (word, pinyin, level)
        if key in seen:
            continue
        seen.add(key)
        entries.append((word, pinyin, level, pos, traditional))

    entries.sort(key=lambda e: (e[0], e[2], e[1]))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        word_count = 0
        for word, group in groupby(entries, key=lambda e: e[0]):
            readings = ";".join(
                f"{pinyin}:{level}:{pos}:{traditional}"
                for _, pinyin, level, pos, traditional in group
            )
            f.write(f"{word}\t{readings}\n")
            word_count += 1

    print(f"wrote {word_count} words ({len(entries)} readings) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
