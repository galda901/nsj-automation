from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.job import JobPosition
from recruitment.schemas.job_schema import JobCreate
from recruitment.services.embeddings import upsert_embedding

router = APIRouter()


@router.post("", response_model=JobPosition, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, session: Session = Depends(get_session)) -> JobPosition:
    job = JobPosition.model_validate(payload)
    session.add(job)
    session.flush()
    upsert_embedding(
        session,
        owner_type="job",
        owner_id=job.id,
        source_type="job_description",
        text=f"{job.title}\n{job.description}",
    )
    session.commit()
    session.refresh(job)
    return job


@router.get("", response_model=list[JobPosition])
def list_jobs(
    job_status: str | None = None, session: Session = Depends(get_session)
) -> list[JobPosition]:
    statement = select(JobPosition)
    if job_status:
        statement = statement.where(JobPosition.status == job_status)
    return list(session.exec(statement.order_by(JobPosition.created_at.desc())).all())


@router.get("/{job_id}", response_model=JobPosition)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobPosition:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/open", response_model=JobPosition)
def open_job(job_id: str, session: Session = Depends(get_session)) -> JobPosition:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "open"
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
