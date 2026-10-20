"""
Main FastAPI app that defines the HTTP routes and which files are responsible for which.
- receives JS fetch() calls from html files, which are translated to HTTP requests.
- immediately computes timestamp once user response has been received
"""

from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from backend.csm import CSMUpdate
from backend.grading import (
    PassageAlreadyGradedError,
    PassageNotFoundError,
    PassageUserIDMismatchError,
    UserPassageLenError,
    grade,
)
from backend.schemas import VocabUnit

# instantiates ASGI app that handles uvicorn requests to routing table -> backend funcs
moxie = FastAPI()

# TODO: replace with auth
USER_ID = 1


# Pydantic model contracts for grading pipeline I/O
class GradeRequest(BaseModel):
    passage_id: int
    user_passage: str


# TODO: currently mirrors backend output - should be reshaped for results.html for M2
class GradeResponse(BaseModel):
    vocab_error_list: list[VocabUnit]
    promo_demo_dict: dict[int, CSMUpdate]


@moxie.get("/api/health")
async def get_health():
    return {"status": "OK"}


@moxie.post("/api/grade")
def grade_user(grade_req: GradeRequest) -> GradeResponse:
    # compute timestamp
    time_submitted_at = datetime.now()

    try:
        errors, promos_demos = grade(
            passage_id=grade_req.passage_id,
            user_passage=grade_req.user_passage,
            user_id=USER_ID,
            timestamp=time_submitted_at,
        )
    except PassageNotFoundError as err:
        # 404 not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passage with ID [{err.passage_id}] not found.",
        ) from err
    except PassageUserIDMismatchError as err:
        # 403 forbidden
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User [{USER_ID}] doesn't match user passage {err.passage_id} was generated for.",
        ) from err
    except PassageAlreadyGradedError as err:
        # 409 conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Passage with ID [{err.passage_id}] has already been graded.",
        ) from err

    except UserPassageLenError as err:
        # 400 bad request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User passage length [{len(err.seg_user_passage)}] doesn't match correct length of [{err.correct_len}]",
        ) from err

    # otherwise, send back to frontend
    user_grade = GradeResponse(vocab_error_list=errors, promo_demo_dict=promos_demos)
    return user_grade


# (1) ALL CORRECT
# passages: GRADED
# appearances: 4 new appearances w/ current date + given passage ID (1)
# user_vocab: all increment to familiar +1
# nothing promoted, nothing demoted
