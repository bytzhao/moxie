"""
conftest.py - contains fixtures defined for scratch DB testing.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from data.seed import seed_hsk_vocab, seed_user


@pytest.fixture
def scratch_s_maker(toy_vocab_dict):
    # make engine & sessionmaker
    engine = create_engine("sqlite:///:memory:")
    s_maker = sessionmaker(bind=engine)

    # setup DB schema using defined models
    Base.metadata.create_all(engine)

    # seed HSK tables (toy dict in place of legit HSK_VOCAB) & user
    with s_maker() as session:
        seed_hsk_vocab(session, toy_vocab_dict)
        seed_user(session, "Stephen Dedalus", "sdedalus@gmail.com")

    # TODO: yield engine (or return)
    yield s_maker

    # TODO: .dispose() teardown
