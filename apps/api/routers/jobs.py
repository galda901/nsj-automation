from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.candidate import now_utc
from recruitment.models.job import JobPosition
from recruitment.schemas.job_schema import JobCreate, JobRead, JobUpdate
from recruitment.services.embeddings import upsert_embedding
from recruitment.services.summaries import summary_from_text

router = APIRouter()


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, session: Session = Depends(get_session)) -> JobPosition:
    values = payload.model_dump()
    values["summary"] = values["summary"] or summary_from_text(values["description"])
    job = JobPosition(**values)
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


@router.get("", response_model=list[JobRead])
def list_jobs(
    job_status: str | None = None, session: Session = Depends(get_session)
) -> list[JobPosition]:
    statement = select(JobPosition)
    if job_status:
        statement = statement.where(JobPosition.status == job_status)
    return list(session.exec(statement.order_by(JobPosition.created_at.desc())).all())


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobPosition:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: str, payload: JobUpdate, session: Session = Depends(get_session)
) -> JobPosition:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(job, field, value)
    if "description" in values and "summary" not in values:
        job.summary = summary_from_text(job.description)
    job.updated_at = now_utc()
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


@router.post("/{job_id}/open", response_model=JobRead)
def open_job(job_id: str, session: Session = Depends(get_session)) -> JobPosition:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "open"
    job.updated_at = now_utc()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
