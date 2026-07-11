from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.match import MatchResult
from recruitment.services.matching_engine import match_candidates_for_job

router = APIRouter()


@router.post("/jobs/{job_id}/run")
def run_matching(job_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        results = match_candidates_for_job(job_id=job_id, session=session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {
        "job_id": job_id,
        "matches_created": len(results),
        "matches": [result.model_dump(mode="json") for result in results],
    }


@router.get("/jobs/{job_id}", response_model=list[MatchResult])
def list_matches(job_id: str, session: Session = Depends(get_session)) -> list[MatchResult]:
    statement = (
        select(MatchResult)
        .where(MatchResult.job_id == job_id)
        .order_by(MatchResult.total_score.desc())
    )
    return list(session.exec(statement).all())
