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
# FPG Orchestrator
# ----------------------
def fpg_orchestrator(passage_len: tuple[int, int], user_id: int):
    # 1) TODO: ID Selection & Recency Scoring
    # cache the static HSK triples dictionary
    hsk_triples_dict = load_hsk_triples_dict(SessionLocal)

    # TODO: decide whether timestamp is passed by main or generated here (for now, gen here)
    current_time = datetime.now()

    # calculate frontier min & max
    frontier_min, frontier_max = FRONTIER_ALLOWANCE[passage_len]

    # calculate recency scores & elligible units
    new_ids_set, frontier_triple_dict, other_encountered_triple_dict = (
        get_elligible_ids(user_id, current_time, frontier_max, SessionLocal)
    )

    # prompt Claude for passage
    str_passage = "床前明月光，疑是地上霜。举头望明月，低头思故乡。"

    # 2) Segmentation
    # return list of strs, each a unit OR punctuation OR space

    try:
        seg_passage = bimm(
            str_passage,
            frontier_triple_dict,
            other_encountered_triple_dict,
            hsk_triples_dict,
        )
    # TODO: pass error to Claude properly
    # contains hallucinated/non-HSK words
    except HallucinatedWordsError as e:
        return e.halluc_words_list
    # contains words not encountered yet
    except NotEncounteredWordsError as e:
        return e.unlearned_words_list

    # 3) TODO: ID serialization

    # 4) TODO: Final Checks (frontier count & not-encountered words)

    # 5) TODO: Package return var (returning func's not-used vals as placeholder)
    return seg_passage, new_ids_set


# ----------------------
# Recency Score & Frontier Selection
# ----------------------
def get_elligible_ids(
    user_id: int, current_time: datetime, frontier_max: int, s_maker: sessionmaker
):
    # get frontier allowance, calc # of new words to add, and gen new words set
    new_words_set = get_new_words(user_id, frontier_max, s_maker)
    num_new_words = len(new_words_set)

    frontier_triple_dict = {}
    other_encountered_triple_dict = {}

    # fill new words to frontier_triple dict, if any
    if new_words_set:
        frontier_triple_dict = seed_claude_triples(new_words_set, s_maker)

    recency_scores: dict[int, RecencyScore] = {}

    # 1) Time Pressure (parse UserVocab for last encountered time)
    with s_maker() as session:
        # select all encountered units
        stmt = (
            select(UserVocab)
            .filter(
                UserVocab.user_id == user_id,
                UserVocab.status_tier != StatusTier.NOT_ENCOUNTERED,
            )
            .order_by(UserVocab.vocab_id)
        )
        user_vocab_rows = session.scalars(stmt).all()

        for row in user_vocab_rows:
            # time diff as decimal DAYS, from secs
            time_pressure_score = time_pressure(
                row.last_encounter_time, current_time, row.status_tier
            )

            # create KV pair for this vocab in dict & seed time pressure
            recency_scores[row.vocab_id] = RecencyScore(
                time_pressure=time_pressure_score,
                rel_interact_pressure=None,
                hist_memory=None,
                total_score=None,
            )

    # 2) Relative Interaction Pressure (parse Appearances)
    # calculate # of passages ()
    with s_maker() as session:
        # calculate # of passages (cap at 50, or less)
        passage_num_query = select(
            func.count(func.distinct(Appearances.passage_id))
        ).where(Appearances.user_id == user_id)
        total_passages = session.scalar(passage_num_query)
        num_passages = min(50, total_passages)

        # get passages IDs for those num_passages most recent
        latest_passage_ids = (
            select(
                Appearances.passage_id,
                func.max(Appearances.timestamp).label("latest_timestamp"),
            )
            .where(Appearances.user_id == user_id)
            .group_by(Appearances.passage_id)
            .order_by(func.max(Appearances.timestamp).desc())
            .limit(num_passages)
            .subquery()
        )

        # for each word, calculate # of appearances in passages from above
        for id in recency_scores:
            # count row appearances amongst the IDs (assumed 1 appearance logged per passage)
            num_appearances_query = (
                select(func.count())
                .select_from(Appearances)
                .join(
                    latest_passage_ids,
                    Appearances.passage_id == latest_passage_ids.c.passage_id,
                )
                .where(Appearances.user_id == user_id, Appearances.vocab_id == id)
            )
            num_appearances = session.scalar(num_appearances_query)

            # calculate density score
            rel_interact_score = rel_interaction(num_appearances, num_passages)

            # add it to the dict
            recency_scores[id].rel_interact_pressure = rel_interact_score

    # 3) Historical Memory (Appearances)
    with s_maker() as session:
        # parse each ID
        for id in recency_scores:
            # query the last 10 (or less) appearances
            appearances_query = (
                select(Appearances.memory_score)
                .where(Appearances.user_id == user_id, Appearances.vocab_id == id)
                .order_by(Appearances.timestamp.asc())
                .limit(10)
            )
            memory_scores_list = list(session.scalars(appearances_query).all())

            # otherwise, calculate historical memory score
            hist_mem_score = hist_memory(memory_scores_list)

            # add score to this vocab unit
            recency_scores[id].hist_memory = hist_mem_score

    # 4) calculate full scores
    for id, score_triple in recency_scores.items():
        recency_scores[id].total_score = float(
            sum(
                [
                    score_triple.time_pressure,
                    score_triple.rel_interact_pressure,
                    score_triple.hist_memory,
                ]
            )
            / 3
        )
    # recency_scores now is completely filled w/ score info of all encountered words
    remaining_frontier_allowance = frontier_max - num_new_words

    # 5) sort by recency score (descending - higher score = more important)
    sorted_recency_dict = dict(
        sorted(
            recency_scores.items(), key=lambda item: item[1].total_score, reverse=True
        )
    )

    # 6) add to frontier dict (filling rest of spots not taken by new words)
    if remaining_frontier_allowance > 0:
        # get top IDs from dict
        frontier_ids = list(sorted_recency_dict.keys())[:remaining_frontier_allowance]
        frontier_dict_not_new = seed_claude_triples(set(frontier_ids), s_maker)

        # combine frontier w/ new words introduced
        frontier_triple_dict = frontier_triple_dict | frontier_dict_not_new

        # pop frontier from recency dict (prevent double-appear in other encountered dict)
        for id in frontier_ids:
            sorted_recency_dict.pop(id, None)

    # 7) create other encountered dict
    other_encountered_triple_dict = seed_claude_triples(
        sorted_recency_dict.keys(), s_maker
    )

    return new_words_set, frontier_triple_dict, other_encountered_triple_dict


def get_new_words(user_id: int, frontier_max: int, s_maker: sessionmaker) -> set:
    """Fetch a set of new words for the user given their # of learning words."""
    new_words_set = set()

    # count how many learning words for this user
    num_learning_words = 0
    with s_maker() as session:
        num_learning_words_query = (
            select(func.count())
            .select_from(UserVocab)
            .where(
                UserVocab.user_id == user_id,
                UserVocab.status_tier == StatusTier.LEARNING,
            )
        )
        num_learning_words = session.scalar(num_learning_words_query)

    new_word_allowance = LEARNING_WORDS_MAX - num_learning_words

    if new_word_allowance < 1:
        return new_words_set

    # query Not-Encountered words, pick randomly from lowest hsk_level
    all_new_words_dict: dict[int, str] = {}
    with s_maker() as session:
        new_words_query = (
            select(UserVocab.vocab_id, HskVocabulary.hsk_level)
            .join(HskVocabulary, HskVocabulary.vocab_id == UserVocab.vocab_id)
            .where(
                UserVocab.user_id == user_id,
                UserVocab.status_tier == StatusTier.NOT_ENCOUNTERED,
            )
            .order_by(HskVocabulary.hsk_level.asc())
        )
        all_new_words = session.execute(new_words_query).all()
        all_new_words_dict = {row.vocab_id: row.hsk_level for row in all_new_words}

    # randomly pick new words (capped at frontier_max)
    new_words_set = rand_pick_new_words(
        min(frontier_max, new_word_allowance), all_new_words_dict
    )
    return new_words_set


# seed new words into frontier triple dict
def seed_claude_triples(id_set: set, s_maker: sessionmaker):
    """Generically takes set of vocab IDs & generates a dict mapping them to Claude triples. by reading HskVocabulary."""
    frontier_dict: dict[int, ClaudeVocabTriple] = {}

    with s_maker() as session:
        # parse IDs
        for id in id_set:
            # map ID to chars, py, sense triples
            claude_triple_query = (
                select(
                    HskVocabulary.simp_man_word,
                    HskVocabulary.pinyin,
                    HskVocabulary.sense,
                )
                .select_from(HskVocabulary)
                .where(HskVocabulary.vocab_id == id)
            )
            row = session.execute(claude_triple_query).first()

            frontier_dict[id] = ClaudeVocabTriple(
                chars=row.simp_man_word, pinyin=row.pinyin, sense=row.sense
            )

    return frontier_dict


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
