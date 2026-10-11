"""
FROM MAIN - passage_id and user response string
    *main immediately does timestamp generation (not a frontend-type responsibility)

(1) Preprocessing & DB Fetch:
    Takes (directly passed from main):
        - passage-id - goes into DB to get serialized vocab_unit list
        - list[completely empty VocabUnits template?]
    *JOB:* fills out list[VocabUnits] w/ everything. Needs to read HskVocabulary inevitably.
    Outputs:
        - list[VocabUnits] w/ everything except errors

MILESTONE 0 START - HARDCODED VOCABUNITS LIST
(2) Levenshtein sub-pipeline:
    Takes:
        - user passage string
        - list[VocabUnits] w/ everything except errors

    Outputs:
        - fully compiled list[VocabUnits] w/ enum errors

(3) CSM (updates DB):
    Takes:
        - list[VocabUnits]
    JOB: takes WORST error per VocabUnit and applies it to the WHOLE unit.
        - NOTE: per-char errors still preserved till the end of pipe for UI.
    Outputs:
        - vocab_promos_demos: vocab_units -> old tier, new tier, base_points (i.e. to accoount for familiar +2)
        - chars_promos_demos: -> old tier, new tier, base_points (^same reason as above)
            - (1) only for demotions, and (2) only if the char exists w/ EXACT PINYIN MATCH

TOTAL OUTPUT TO FRONTEND:
    - list[VocabUnits] - contains all information to do UI visualization of errors & answers
        - frontend persists user's actual answers throuhgout all of this
    - vocab/chars promos/demos
"""

from datetime import datetime

from backend.csm import csm, find_ind_chars_demote
from backend.levenshtein import levenshtein, trim_and_seg
from backend.models import Appearances
from backend.schemas import VocabErrorGroup, VocabUnit
from data.db import SessionLocal

# ------------------------------
# Hardcoded Vocab & User Response
# ------------------------------
# vocab_id values are arbitrary placeholders, not real HSK rows. error_type is seeded
# None across the board - unit 2's levenshtein() fills these in for real.
EX_VOCAB_UNIT_LIST = [
    VocabUnit(vocab_id=1, chars=("我",), pinyin=("wo3",), error_type=(None,)),
    VocabUnit(vocab_id=2, chars=("是",), pinyin=("shi4",), error_type=(None,)),
    VocabUnit(
        vocab_id=3,
        chars=("中", "国"),
        pinyin=("zhong1", "guo2"),
        error_type=(None, None),
    ),
    VocabUnit(vocab_id=4, chars=("人",), pinyin=("ren2",), error_type=(None,)),
]

EX_USER_RESPONSE = "wo3 shi4 zhong1 guo2 ren2"
USER_ID = 1


class UserPassageLenError(Exception):
    def __init__(
        self, seg_user_passage, message="User passage length didn't match answer key."
    ):
        super().__init__(message)
        self.seg_user_passage = seg_user_passage


# ------------------------------
# Grading Pipeline Orchestrator
# ------------------------------
def grade(
    passage_id: int,
    user_passage: str = EX_USER_RESPONSE,
    user_id: int = USER_ID,
    timestamp: datetime = None,
):
    if timestamp is None:
        timestamp = datetime.now()

    # (1) Passage DB Fetch & Validation
    # NOTE: SKIPPED FOR NOW - HSKVocab hard-coded for now bcuz Passages not set-up.

    # (1.5) - check user_passage len (trim steps) matches EXACTLY DB passage
    len_answer_key = 0
    for vocab_unit in EX_VOCAB_UNIT_LIST:
        len_answer_key += len(vocab_unit.chars)
    if not len(trim_and_seg(user_passage)) == len_answer_key:
        raise UserPassageLenError(trim_and_seg(user_passage))

    # (2) Levenshtein Distance Grading
    vocab_error_list = levenshtein(user_passage, EX_VOCAB_UNIT_LIST)

    # (3) Generate Individual Chars to Demote
    ind_chars_demote = find_ind_chars_demote(vocab_error_list, user_id)

    # (3.5) Condense List for Appearances + CSM
    # maps vocab_id -> a VocabErrorGroup (tuple of chars + list of all error occurrences)
    condensed_vocab_error_dict = condense_vocab_errors(vocab_error_list)

    # (4) Log New Appearances
    log_appearances(condensed_vocab_error_dict, passage_id, timestamp, user_id)

    # (5) CSM Promotions & Demotions
    # TODO (perf): refactor CSM to take condensed dict - no need for its own bespoke dict creation
    promo_demo_dict = csm(vocab_error_list + ind_chars_demote, user_id, timestamp)

    return vocab_error_list, promo_demo_dict


# ------------------------------
# Condense Vocab Error List
# ------------------------------
def condense_vocab_errors(vocab_error_list: list[VocabUnit]):
    """Takes complete passage-list of VocabUnits and condenses into dict compiling errors."""
    condensed_error_dict = {}
    for vocab_unit in vocab_error_list:
        # if first occurrence, add it
        if vocab_unit.vocab_id not in condensed_error_dict:
            condensed_error_dict[vocab_unit.vocab_id] = VocabErrorGroup(
                chars=vocab_unit.chars, error_list=vocab_unit.error_type
            )
        else:
            condensed_error_dict[
                vocab_unit.vocab_id
            ].error_list += vocab_unit.error_type
    return condensed_error_dict


# ------------------------------
# Log Appearances
# ------------------------------
def log_appearances(
    condensed_vocab_error_dict: dict,
    passage_id: int,
    timestamp: datetime,
    user_id: int = USER_ID,
):
    # appearances needs:
    # vocab id, user id, passage id, memory score, timestamp
    with SessionLocal() as session:
        for id, group in condensed_vocab_error_dict.items():
            # compute average score from errors:
            avg_mem_score = 0
            for err in group.error_list:
                if err == 0:
                    avg_mem_score += 1
                elif err < 5:
                    avg_mem_score += 0.5
            avg_mem_score /= len(group.error_list)

            row = Appearances(
                vocab_id=id,
                user_id=user_id,
                passage_id=passage_id,
                memory_score=avg_mem_score,
                timestamp=timestamp,
            )

            session.add(row)
        session.commit()
