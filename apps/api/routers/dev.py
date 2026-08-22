from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.database import get_session
from recruitment.models.candidate import Candidate, CandidateFile, now_utc
from recruitment.models.ingestion import IngestionLog
from recruitment.models.job import JobPosition
from recruitment.models.notification import NotificationOutbox, WorkerState
from recruitment.models.vector import EmbeddingRecord
from recruitment.services.embeddings import upsert_embedding
from recruitment.services.cv_parser import parse_candidate_from_text
from recruitment.services.matching_engine import (
    MATCHING_EMBEDDING_SOURCE,
    candidate_match_text,
    job_match_text,
)

router = APIRouter()


@router.get("/settings")
def settings_snapshot() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "llm_provider": settings.llm_provider,
        "openai_key_configured": bool(settings.openai_api_key),
        "openai_cv_model": settings.openai_cv_model,
        "openai_match_model": settings.openai_match_model,
        "openai_embedding_model": settings.openai_embedding_model,
        "gmail_enabled": settings.gmail_enabled,
        "gmail_jobs_label": settings.gmail_jobs_label,
        "gmail_cvs_label": settings.gmail_cvs_label,
        "gmail_lookback_days": settings.gmail_lookback_days,
        "gmail_include_child_labels": settings.gmail_include_child_labels,
        "gmail_client_secret_file_configured": bool(settings.gmail_client_secret_file),
        "gmail_client_secret_file_exists": (
            bool(settings.gmail_client_secret_file)
            and settings.gmail_client_secret_file.exists()
        ),
        "gmail_token_file_configured": bool(settings.gmail_token_file),
        "gmail_token_file_exists": (
            bool(settings.gmail_token_file) and settings.gmail_token_file.exists()
        ),
        "worker_poll_seconds": settings.worker_poll_seconds,
        "telegram_enabled": settings.telegram_enabled,
        "telegram_dry_run": settings.telegram_dry_run,
        "telegram_chat_id_configured": bool(settings.telegram_chat_id),
        "telegram_bot_token_configured": bool(settings.telegram_bot_token),
    }


@router.get("/vectors", response_model=list[EmbeddingRecord])
def list_vectors(session: Session = Depends(get_session)) -> list[EmbeddingRecord]:
    return list(
        session.exec(select(EmbeddingRecord).order_by(EmbeddingRecord.created_at.desc())).all()
    )


@router.post("/vectors/rebuild")
def rebuild_vectors(session: Session = Depends(get_session)) -> dict:
    candidates = list(session.exec(select(Candidate)).all())
    jobs = list(session.exec(select(JobPosition)).all())
    for candidate in candidates:
        upsert_embedding(
            session,
            "candidate",
            candidate.id,
            MATCHING_EMBEDDING_SOURCE,
            candidate_match_text(candidate),
        )
    for job in jobs:
        upsert_embedding(session, "job", job.id, MATCHING_EMBEDDING_SOURCE, job_match_text(job))
    session.commit()
    return {"candidates": len(candidates), "jobs": len(jobs), "status": "rebuilt"}


@router.get("/ingestion-logs", response_model=list[IngestionLog])
def list_ingestion_logs(session: Session = Depends(get_session)) -> list[IngestionLog]:
    return list(
        session.exec(select(IngestionLog).order_by(IngestionLog.created_at.desc())).all()
    )


@router.get("/worker-status")
def worker_status(session: Session = Depends(get_session)) -> dict:
    state = session.get(WorkerState, "gmail-matching-worker")
    if state is None:
        return {"id": "gmail-matching-worker", "status": "never_run"}
    return state.model_dump(mode="json")


@router.get("/telegram-notifications", response_model=list[NotificationOutbox])
def list_telegram_notifications(
    session: Session = Depends(get_session), limit: int = 100
) -> list[NotificationOutbox]:
    safe_limit = max(1, min(limit, 500))
    return list(
        session.exec(
            select(NotificationOutbox)
            .order_by(NotificationOutbox.created_at.desc())
            .limit(safe_limit)
        ).all()
    )


@router.get("/raw-candidates", response_model=list[Candidate])
def list_raw_candidates(session: Session = Depends(get_session)) -> list[Candidate]:
    return list(session.exec(select(Candidate).order_by(Candidate.created_at.desc())).all())


@router.post("/candidates/repair-fallback")
def repair_fallback_candidates(session: Session = Depends(get_session)) -> dict:
    """Replace low-confidence fallback values without making any external AI calls."""
    candidates = {
        candidate.id: candidate
        for candidate in session.exec(
            select(Candidate).where(Candidate.parse_confidence <= 0.35)
        ).all()
    }
    files = session.exec(
        select(CandidateFile)
        .where(CandidateFile.candidate_id.in_(candidates))
        .order_by(CandidateFile.uploaded_at.desc())
    ).all()
    processed: set[str] = set()
    repaired = 0
    for candidate_file in files:
        candidate_id = candidate_file.candidate_id
        if not candidate_id or candidate_id in processed:
            continue
        processed.add(candidate_id)
        candidate = candidates[candidate_id]
        text_path = Path(candidate_file.extracted_text_path or "")
        if not text_path.exists():
            continue
        parsed = parse_candidate_from_text(text_path.read_text(encoding="utf-8"), use_llm=False)
        if parsed.full_name != "Unknown Candidate":
            candidate.full_name = parsed.full_name
        for field in ("phone", "city", "current_title"):
            value = getattr(parsed, field)
            if value:
                setattr(candidate, field, value)
        candidate.ai_summary = None
        candidate.updated_at = now_utc()
        session.add(candidate)
        repaired += 1
    session.commit()
    return {"repaired": repaired, "summaries_cleared": repaired}
