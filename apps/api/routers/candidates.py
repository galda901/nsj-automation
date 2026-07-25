import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.candidate import Candidate, CandidateFile, now_utc
from recruitment.schemas.candidate_schema import CandidateCreate, CandidateRead, CandidateUpdate
from recruitment.services.cv_parser import parse_candidate_from_text
from recruitment.services.candidate_formatting import (
    normalize_city,
    normalize_country,
    normalize_current_title,
    normalize_phone,
)
from recruitment.services.embeddings import upsert_embedding

router = APIRouter()


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate, session: Session = Depends(get_session)
) -> Candidate:
    candidate = Candidate(**payload.model_dump())
    _normalize_candidate_profile(candidate)
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


@router.get("", response_model=list[CandidateRead])
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


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: str, session: Session = Depends(get_session)) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    session: Session = Depends(get_session),
) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    _normalize_candidate_profile(candidate)
    candidate.updated_at = now_utc()
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


def _normalize_candidate_profile(candidate: Candidate) -> None:
    candidate.phone = normalize_phone(candidate.phone)
    candidate.city = normalize_city(candidate.city)
    candidate.country = normalize_country(candidate.country)
    candidate.current_title = normalize_current_title(candidate.current_title)


@router.post("/{candidate_id}/refresh-ai", response_model=CandidateRead)
def refresh_candidate_with_ai(
    candidate_id: str, session: Session = Depends(get_session)
) -> Candidate:
    """Re-extract a candidate's details and one-paragraph summary from their latest CV."""
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate_file = latest_candidate_file(session, candidate_id)
    text_path = Path(candidate_file.extracted_text_path or "") if candidate_file else None
    if text_path is None or not text_path.exists():
        raise HTTPException(status_code=404, detail="Extracted CV text is not available")
    parsed = parse_candidate_from_text(
        text_path.read_text(encoding="utf-8"), source=candidate.source, use_llm=True
    )
    if not parsed.ai_summary or (parsed.parse_confidence or 0) < 0.7:
        raise HTTPException(
            status_code=503,
            detail="AI extraction is unavailable. Check the OpenAI API key and quota, then try again.",
        )
    for field in (
        "full_name",
        "email",
        "phone",
        "city",
        "country",
        "current_title",
        "seniority",
        "total_years_experience",
        "languages",
        "ai_summary",
        "parse_confidence",
    ):
        value = getattr(parsed, field)
        if value is not None:
            setattr(candidate, field, value)
    _normalize_candidate_profile(candidate)
    candidate.updated_at = now_utc()
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


@router.get("/{candidate_id}/latest-cv/open")
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
