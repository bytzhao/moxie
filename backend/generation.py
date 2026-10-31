"""
FUNCTIONALITY: FPG orchestrator.
    1. computes recency scores & picks frontier words (DB - read)
    2. builds the prompt by calling llm.py
    3. calls segmentation & pinyin pipeline
    4. writes to passages table (DB - write)
"""

from datetime import datetime
from functools import cache
from math import exp
from random import choice
from types import MappingProxyType

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from backend.models import Appearances, HskVocabulary, UserVocab
from backend.schemas import ClaudeVocabTriple, RecencyScore, StatusTier, VocabTriple
from backend.segmenter import HallucinatedWordsError, NotEncounteredWordsError, bimm
from data.db import SessionLocal

HIST_MEM_WEIGHT = 0.8

LEARNING_WORDS_MAX = 25
FRONTIER_ALLOWANCE = {
    (30, 50): (4, 5),
    (50, 100): (8, 10),
    (100, 150): (12, 15),
    (150, 250): (15, 20),
}

TIME_PRESSURE_LAMBDAS = {
    StatusTier.LEARNING: 1,
    StatusTier.FAMILIAR: 0.5,
    StatusTier.SOLID: 0.25,
    StatusTier.MASTERED: 0.125,
}


# static char -> ID, py, sense triple
@cache
def load_hsk_triples_dict(s_maker: sessionmaker):
    # key: char
    # value: tuple of VocabTriples
    hsk_triples_dict = {}

    # parse HskVocabulary table
    with s_maker() as session:
        stmt = select(HskVocabulary).order_by(HskVocabulary.vocab_id)
        hsk_rows = session.scalars(stmt).all()

        # add a row for each hsk unit
        for unit in hsk_rows:
            new_triple = VocabTriple(
                vocab_id=unit.vocab_id, pinyin=unit.pinyin, sense=unit.sense
            )
            # add to the KV-pair w/ key = the chars
            if unit.simp_man_word in hsk_triples_dict:
                hsk_triples_dict[unit.simp_man_word] += (new_triple,)
            else:
                hsk_triples_dict[unit.simp_man_word] = (new_triple,)

    hsk_triples_dict = MappingProxyType(hsk_triples_dict)

    return hsk_triples_dict

# ----------------------
# Recency Score Calc Core
# ----------------------
def time_pressure(
    last_encounter_time: datetime, current_time: datetime, status_tier: StatusTier
):
    """Given two datetimes and the current StatusTier of a word, calculates time pressure."""
    if current_time < last_encounter_time:
        return 0

    t_diff = float((current_time - last_encounter_time).total_seconds() / 86400.0)
    t_p = 1 - exp((-1) * TIME_PRESSURE_LAMBDAS[status_tier] * t_diff)
    return t_p


def rel_interaction(num_appearances: int, num_passages: int):
    """Given # of total passages considered & # of appearances, calculates interaction density."""
    appear_percent = float(num_appearances / num_passages) if num_passages > 0 else 0
    rel_interact_score = 1 - appear_percent
    return rel_interact_score


def hist_memory(mem_score_list: list[float]):
    """Given a list of memory scores, calculates the aggregate historical memory.
    Returns review urgency score as the COMPLEMENT of the memory score."""
    if len(mem_score_list) == 0:
        return 0.5

    hist_mem_sum = 0
    weights_sum = 0
    count = 0
    for mem_score in mem_score_list:
        weight = HIST_MEM_WEIGHT**count
        hist_mem_sum += weight * mem_score
        weights_sum += weight
        count += 1

    hist_mem_score = hist_mem_sum / weights_sum
    return 1 - hist_mem_score


# ----------------------
# New Word Helper
# ----------------------
def rand_pick_new_words(num_new_words: int, all_new_words_dict: dict[int, str]):
    """Given dict of IDs->hsk level, randomly picks a set from lowest level."""
    new_words_set = set()
    cpy_new_words_dict = all_new_words_dict.copy()

    # number of new words to add capped at # of new words left (for advanced users)
    for _i in range(min(num_new_words, len(cpy_new_words_dict))):
        # get lowest current level (convert from strs)
        lowest_level = min(
            [int(str_level[0]) for str_level in cpy_new_words_dict.values()]
        )

        # pick random ID from new words by lowest HSK level
        lowest_level_words = [
            vocab_id
            for vocab_id, level in cpy_new_words_dict.items()
            if int(level[0]) == lowest_level
        ]
        chosen_id = choice(lowest_level_words)

        # add it to the set
        new_words_set.add(chosen_id)

        # delete chosen ID from the dict
        del cpy_new_words_dict[chosen_id]
    return new_words_set
