"""
seed.py
- populates hsk_vocab table (ONCE, EVER) from HSK_VOCAB (hsk_vocab.py)
    - we treat data/hsk30.txt as the GROUND TRUTH for the vocab
- populates users w/ new user whenever necessary
- populates user_vocab linking user_id to all prev encountered vocab_id from hsk_vocab table

IMPORTANT: all above is done ONCE in PoC phase.
"""

import os
from datetime import datetime

from dotenv import load_dotenv

from backend.models import HskVocabulary, StatusTier, UserVocab, Users
from data.db import SessionLocal, create_tables
from data.hsk_vocab import HSK_VOCAB

load_dotenv()

BASELINE_HSK_LEVEL = 3  # e.g. 4 - see level_rank() below re: "7-9" band
USER_NAME = os.getenv("USER_NAME")
USER_EMAIL = os.getenv("USER_EMAIL")


# -------------------
# Full Seed Pipeline
# -------------------
def seed_all(baseline_level, user_name, user_email):
    create_tables()
    with SessionLocal() as session:
        seed_hsk_vocab(session)
        user = seed_user(session, user_name, user_email)
        calibrate_user_vocab(session, user, baseline_level)


# -------------------
# Callees
# -------------------
def level_rank(hsk_level):
    """
    Converts an hsk_level string into a comparable integer.
    Most levels are plain digits ("1".."6"). The HSK 3.0 "advanced" band is
    stored as the literal string "7-9" (see hsk30.txt) rather than a single
    level - there is no single correct integer for it.
    """
    return int(hsk_level.split("-")[0])


def seed_hsk_vocab(session):
    """One row per (word, reading) pair already parsed into HSK_VOCAB."""
    for word, entries in HSK_VOCAB.items():

        # go through individual HskEntrys
        for entry in entries:
            session.add(HskVocabulary(
                simp_man_word=word,
                pinyin=entry.pinyin,
                hsk_level=entry.level,
                trad_man_word=entry.traditional,
            ))
    session.commit()


def seed_user(session, user_name, user_email):
    """Phase 1 is single-user - this only ever needs to run once."""
    user = Users(
        user_name=user_name,
        user_email=user_email,
        created_time=datetime.now(),
    )
    session.add(user)
    session.commit()
    return user


def calibrate_user_vocab(session, user, baseline_level):
    """
    Baseline calibration per PRD Section VII/XII:
        level below baseline  -> Familiar
        level at baseline     -> Learning
        level above baseline  -> Not Encountered
    Every hsk_vocab row gets a user_vocab row (including Not Encountered -
    deliberate choice, see conversation history for the tradeoff).
    last_encounter_time is seeded to the calibration timestamp itself, per
    Section VII ("last interaction takes the timestamp of calibration").
    """
    calibration_time = datetime.now()
    all_vocab = session.query(HskVocabulary).all()

    for vocab in all_vocab:
        rank = level_rank(vocab.hsk_level)
        if rank < baseline_level:
            tier = StatusTier.FAMILIAR
        elif rank == baseline_level:
            tier = StatusTier.LEARNING
        else:
            tier = StatusTier.NOT_ENCOUNTERED

        session.add(UserVocab(
            user_id=user.user_id,
            vocab_id=vocab.vocab_id,
            status_tier=tier,
            points=0,
            last_encounter_time=calibration_time,
        ))
    session.commit()


if __name__ == "__main__":
    seed_all(BASELINE_HSK_LEVEL, USER_NAME, USER_EMAIL)