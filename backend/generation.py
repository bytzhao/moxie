"""
FUNCTIONALITY: FPG orchestrator.
    1. computes recency scores & picks frontier words (DB - read)
    2. builds the prompt by calling llm.py
    3. calls segmentation & pinyin pipeline
    4. writes to passages table (DB - write)
"""
from functools import cache
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from types import MappingProxyType

from backend.models import HskVocabulary
from backend.segmenter import bimm
from backend.schemas import VocabTriple
from data.db import SessionLocal


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
                vocab_id=unit.vocab_id,
                pinyin=unit.pinyin,
                sense=unit.sense
            )
            # add to the KV-pair w/ key = the chars
            if unit.simp_man_word in hsk_triples_dict:
                hsk_triples_dict[unit.simp_man_word] += (new_triple,)
            else:
                hsk_triples_dict[unit.simp_man_word] = (new_triple,)

    hsk_triples_dict = MappingProxyType(hsk_triples_dict)

    return hsk_triples_dict

