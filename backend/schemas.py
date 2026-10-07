"""
Shared data contracts for the grading pipeline (grading.py, levenshtein.py, csm.py).
    - Separate file to avoid circular imports between grading, levenshtein, & CSM.

    - Likely future addition: a promotion/demotion record type, once csm.py's 
    vocab_promos_demos / chars_promos_demos output shape is finalized
"""

from enum import IntEnum
from dataclasses import dataclass


class PinyinError(IntEnum):
    """Enumerates and classifies integer error types per character."""
    CORRECT = 0

    # slight errors
    TYPO = 1
    RETROFLEX_ERROR = 2
    UMLAUT_ERROR = 3
    NASAL_ERROR = 4

    # severe errors
    TONE_ERROR = 5
    SKIPPED = 6         # specific '-' appearances
    FORGOT = 7          # catch-all


@dataclass
class VocabUnit():
    """Package encapsulating all information necessary for grading pipeline functionality & results UI."""
    vocab_id: int
    chars: tuple[str, ...]
    pinyin: tuple[str, ...]
    error_type: tuple[PinyinError, ...]


class StatusTier(IntEnum):
    NOT_ENCOUNTERED = 0
    LEARNING = 1
    FAMILIAR = 2
    SOLID = 3
    MASTERED = 4