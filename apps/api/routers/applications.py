from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.application import Application
from recruitment.models.candidate import Candidate
from recruitment.models.job import JobPosition
from recruitment.schemas.application_schema import ApplicationCreate

router = APIRouter()


@router.get("", response_model=list[Application])
def list_applications(session: Session = Depends(get_session)) -> list[Application]:
    return list(session.exec(select(Application).order_by(Application.received_at.desc())).all())


@router.post("", response_model=Application, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate, session: Session = Depends(get_session)
) -> Application:
    if session.get(Candidate, payload.candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if session.get(JobPosition, payload.job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    application = Application(**payload.model_dump())
    session.add(application)
    session.commit()
    session.refresh(application)
    return application
