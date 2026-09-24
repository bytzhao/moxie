from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, PrimaryKeyConstraint, String
from enum import Enum
from datetime import datetime

# ORM Basics:
    # each ORM model is a Python class, representing a TABLE
    # each Python typed attribute is a column of the table
    # inherit from shared Base class
    # class has __tablename__

class StatusTier(Enum):
    NOT_ENCOUNTERED = 0
    LEARNING = 1
    FAMILIAR = 2
    SOLID = 3
    MASTERED = 4

class PassageState(Enum):
    SENT_TO_USER = 0
    GRADED = 1

class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(String(50))
    user_email: Mapped[str] = mapped_column(String(50))
    created_time: Mapped[datetime]


class HskVocabulary(Base):
    __tablename__ = "hsk_vocab"
    vocab_id: Mapped[int] = mapped_column(primary_key=True)
    simp_man_word: Mapped[str]
    pinyin: Mapped[str]
    hsk_level: Mapped[str]
    trad_man_word: Mapped[str]


class UserVocab(Base):
    __tablename__ = "user_vocab"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    vocab_id: Mapped[int] = mapped_column(ForeignKey("hsk_vocab.vocab_id"))
    status_tier: Mapped[StatusTier]
    points: Mapped[int]
    last_encounter_time: Mapped[datetime]

    __table_args__ = (
       PrimaryKeyConstraint("user_id", "vocab_id"),
   )


class Appearances(Base):
    __tablename__ = "appearances"
    vocab_id: Mapped[int] = mapped_column(ForeignKey("hsk_vocab.vocab_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    passage_id: Mapped[int] = mapped_column(ForeignKey("passages.passage_id"))
    memory_score: Mapped[float]
    timestamp: Mapped[datetime]

    __table_args__ = (
        PrimaryKeyConstraint("vocab_id", "user_id", "passage_id"),
    )


class Passages(Base):
    __tablename__ = "passages"
    passage_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    state: Mapped[PassageState]
    answer_key: Mapped[str]     # serialized via vocab_ids