from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.match import MatchResult
from recruitment.schemas.match_schema import MatchRead, MatchUpdate, MatchingRunResponse
from recruitment.services.matching_engine import match_candidates_for_job

router = APIRouter()


@router.post("/jobs/{job_id}/run", response_model=MatchingRunResponse)
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


@router.get("/jobs/{job_id}", response_model=list[MatchRead])
def list_matches(job_id: str, session: Session = Depends(get_session)) -> list[MatchResult]:
    statement = (
        select(MatchResult)
        .where(MatchResult.job_id == job_id)
        .order_by(MatchResult.total_score.desc())
    )
    return list(session.exec(statement).all())


@router.patch("/{match_id}", response_model=MatchRead)
def update_match(
    match_id: str, payload: MatchUpdate, session: Session = Depends(get_session)
) -> MatchResult:
    match = session.get(MatchResult, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(match, field, value)
    session.add(match)
    session.commit()
    session.refresh(match)
    return match
