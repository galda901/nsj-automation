import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.candidate import Candidate, CandidateFile
from recruitment.schemas.candidate_schema import CandidateCreate
from recruitment.services.embeddings import upsert_embedding

router = APIRouter()


@router.post("", response_model=Candidate, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate, session: Session = Depends(get_session)
) -> Candidate:
    candidate = Candidate.model_validate(payload)
    session.add(candidate)
    session.flush()
    upsert_embedding(
        session,
        owner_type="candidate",
        owner_id=candidate.id,
        source_type="candidate_profile",
        text=f"{candidate.full_name}\n{candidate.current_title or ''}\n{candidate.ai_summary or ''}",
    )
    session.commit()
    session.refresh(candidate)
    return candidate


@router.get("", response_model=list[Candidate])
def list_candidates(
    q: str | None = None,
    candidate_status: str | None = None,
    session: Session = Depends(get_session),
) -> list[Candidate]:
    statement = select(Candidate)
    if candidate_status:
        statement = statement.where(Candidate.status == candidate_status)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Candidate.full_name.ilike(term),
                Candidate.email.ilike(term),
                Candidate.current_title.ilike(term),
                Candidate.ai_summary.ilike(term),
            )
        )
    return list(session.exec(statement.order_by(Candidate.created_at.desc())).all())


@router.get("/with-files")
def list_candidates_with_files(
    q: str | None = None,
    candidate_status: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    candidates = list_candidates(q=q, candidate_status=candidate_status, session=session)
    rows: list[dict] = []
    for candidate in candidates:
        row = candidate.model_dump(mode="json")
        latest_file = latest_candidate_file(session, candidate.id)
        row["latest_cv_path"] = latest_file.stored_path if latest_file else None
        row["latest_cv_file_id"] = latest_file.id if latest_file else None
        rows.append(row)
    return rows


@router.get("/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, session: Session = Depends(get_session)) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get("/{candidate_id}/files", response_model=list[CandidateFile])
def list_candidate_files(
    candidate_id: str, session: Session = Depends(get_session)
) -> list[CandidateFile]:
    return list(
        session.exec(
            select(CandidateFile)
            .where(CandidateFile.candidate_id == candidate_id)
            .order_by(CandidateFile.uploaded_at.desc())
        ).all()
    )


@router.get("/{candidate_id}/latest-cv/download")
def download_latest_cv(
    candidate_id: str, session: Session = Depends(get_session)
) -> FileResponse:
    candidate_file = latest_candidate_file(session, candidate_id)
    if candidate_file is None:
        raise HTTPException(status_code=404, detail="No CV file found for candidate")
    path = Path(candidate_file.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored CV file is missing")
    return FileResponse(path, filename=candidate_file.original_filename)


@router.post("/{candidate_id}/latest-cv/open")
def open_latest_cv(candidate_id: str, session: Session = Depends(get_session)) -> dict:
    candidate_file = latest_candidate_file(session, candidate_id)
    if candidate_file is None:
        raise HTTPException(status_code=404, detail="No CV file found for candidate")
    path = Path(candidate_file.stored_path).resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored CV file is missing")
    if os.name != "nt":
        return {"opened": False, "path": str(path), "detail": "Open action is Windows-only"}
    os.startfile(str(path))  # type: ignore[attr-defined]
    return {"opened": True, "path": str(path)}


def latest_candidate_file(session: Session, candidate_id: str) -> CandidateFile | None:
    return session.exec(
        select(CandidateFile)
        .where(CandidateFile.candidate_id == candidate_id)
        .order_by(CandidateFile.uploaded_at.desc())
    ).first()
