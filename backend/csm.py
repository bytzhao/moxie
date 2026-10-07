"""
Writes promotions/demotions to DB from grading verdicts.
"""

from dataclasses import dataclass
from datetime import datetime

from backend.schemas import VocabUnit, PinyinError, StatusTier
from data.db import SessionLocal
from backend.models import UserVocab


@dataclass
class CSMUpdate():
    char: tuple[str, ...]
    error_type: PinyinError
    initial_status: StatusTier
    final_status: StatusTier
    final_points: int

TIER_STREAK_CEILING = {
    StatusTier.LEARNING: 3,
    StatusTier.FAMILIAR: 3,
    StatusTier.SOLID: 5,
    StatusTier.MASTERED: float('inf')
}


# ---------------------
# CSM Orchestrator 
# ---------------------
def csm(
    vocab_error_list: list[VocabUnit],
    user_id: int,
    timestamp: datetime
):
    """Orchestrates CSM changes to AVD."""
    # (1) Generate unique dict w/ vocab units (takes max error)
    csm_updates_dict = {}

    for vocab_unit in vocab_error_list:
        # compute the unit's max error (from chars' error tuple)
        unit_error = max(vocab_unit.error_type)

        # if already stored, update to max of the errors
        if vocab_unit.vocab_id in csm_updates_dict:
            csm_updates_dict[vocab_unit.vocab_id].error_type = max(unit_error, csm_updates_dict[vocab_unit.vocab_id].error_type)
        # otherwise just add new unit to the dict
        else:
            csm_updates_dict[vocab_unit.vocab_id] = CSMUpdate(
                vocab_unit.chars,
                unit_error,
                None,
                None,
                None
            )

    # (2) Apply DB promotions/demotions
    with SessionLocal() as session:
        for vocab_id, csm_update in csm_updates_dict.items():
            # read entire row using FKs
            row = session.get(UserVocab, (user_id, vocab_id))

            # write initial status (dict)
            csm_update.initial_status = row.status_tier

            # update DB tier + streak
            row.status_tier, row.points = compute_new_status(row.status_tier, row.points, csm_update.error_type)
            row.last_encounter_time = timestamp

            # write final status & streak (dict)
            csm_update.final_status = row.status_tier
            csm_update.final_points = row.points

        # commit all changes
        session.commit()
    
    # (3) Filter non tier-change units
    promo_demo_dict = {
        vocab_id: csm_update 
        for vocab_id, csm_update in csm_updates_dict.items()
        if csm_update.initial_status != csm_update.final_status
    }

    return promo_demo_dict


# ---------------------
# Tier Change Calculation
# ---------------------
def compute_new_status(
        initial_status: StatusTier,
        initial_points: int,
        error_type: PinyinError
) -> list[StatusTier, int]:
    """Computes appropriate tier and streak changes given error & initial status."""

    # if not-encountered, auto-promote to Learning base
    if initial_status == StatusTier.NOT_ENCOUNTERED:
        return StatusTier.LEARNING, 0

    # if severe:
    if error_type > 4:
        if initial_status == StatusTier.LEARNING:
            return initial_status, 0
        if initial_status == StatusTier.FAMILIAR:
            return StatusTier.LEARNING, 2
        if initial_status == StatusTier.SOLID:
            return StatusTier.FAMILIAR, 1
        else:
            return StatusTier.FAMILIAR, 2

    # if slight:
    if error_type > 0:
        if initial_status in {StatusTier.LEARNING, StatusTier.FAMILIAR}:
            return initial_status, 0
        else:
            return StatusTier.FAMILIAR, 2

    # correct:
    final_points = initial_points + 1
    # if the streak has hit a ceiling -> promote to next tier
    if final_points >= TIER_STREAK_CEILING[initial_status]:
        return initial_status + 1, 0
    # otherwise, maintain current tier & increment streak
    else:
        return initial_status, final_points