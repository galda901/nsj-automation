from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.integrations.gmail_client import GmailAttachment, GmailClient, GmailMessage
from recruitment.integrations.openai_client import openai_enabled
from recruitment.models.ingestion import IngestionLog
from recruitment.models.candidate import CandidateFile
from recruitment.services.cv_ingestion import ingest_cv_file
from recruitment.services.cv_text_extractor import SUPPORTED_SUFFIXES
from recruitment.services.embeddings import upsert_embedding
from recruitment.services.matching_engine import MATCHING_EMBEDDING_SOURCE, job_match_text
from recruitment.services.job_parser import parse_job_from_email
from recruitment.utils.files import sha256_bytes


def ingest_gmail_daily(session: Session) -> dict:
    settings = get_settings()
    if not settings.gmail_enabled:
        return {
            "enabled": False,
            "jobs_drafted": 0,
            "cvs_ingested": 0,
            "duplicates_skipped": 0,
            "errors": ["GMAIL_ENABLED is false"],
        }
    result = {
        "enabled": True,
        "jobs_drafted": 0,
        "cvs_ingested": 0,
        "duplicates_skipped": 0,
        "job_messages_found": 0,
        "cv_messages_found": 0,
        "attachments_found": 0,
        "supported_attachments_found": 0,
        "unsupported_attachments_skipped": 0,
        "llm_enabled": openai_enabled(),
        "llm_job_parsing_enabled": openai_enabled(),
        "llm_cv_parsing_enabled": openai_enabled(),
        "available_labels": [],
        "events": [],
        "errors": [],
    }
    try:
        client = GmailClient()
    except Exception as error:
        _event(result, "gmail_auth_failed", detail=str(error))
        result["errors"].append(str(error))
        return result
    result["available_labels"] = client.label_names()
    _event(
        result,
        "gmail_connected",
        detail=(
            f"Scanning job label '{settings.gmail_jobs_label}' for the last "
            f"{settings.gmail_lookback_days} days and every message in CV label "
            f"'{settings.gmail_cvs_label}' plus the Inbox"
        ),
    )
    job_messages = client.list_messages_by_label(
        settings.gmail_jobs_label, settings.gmail_lookback_days
    )
    cv_messages = client.list_all_messages_by_labels([settings.gmail_cvs_label, "INBOX"])
    result["job_messages_found"] = len(job_messages)
    result["cv_messages_found"] = len(cv_messages)
    _event(
        result,
        "messages_found",
        detail=f"Jobs: {len(job_messages)}; CVs: {len(cv_messages)}",
    )
    for message in job_messages:
        _ingest_job_message(session, message, settings.gmail_jobs_label, result)
    for message in cv_messages:
        _ingest_cv_message(session, client, message, settings.gmail_cvs_label, result)
    return result


def _ingest_job_message(
    session: Session, message: GmailMessage, label: str, result: dict
) -> None:
    if _message_already_processed(session, message.id, label, "job"):
        result["duplicates_skipped"] += 1
        _event(result, "job_skipped_duplicate", message=message)
        return
    try:
        _event(
            result,
            "job_parse_started",
            message=message,
            detail=f"LLM enabled: {openai_enabled()}",
        )
        job = parse_job_from_email(message.subject, message.body)
        job.status = "draft"
        session.add(job)
        session.flush()
        upsert_embedding(
            session,
            owner_type="job",
            owner_id=job.id,
            source_type=MATCHING_EMBEDDING_SOURCE,
            text=job_match_text(job),
        )
        _log(session, label, message.id, None, "job", job.id, "success", message.subject)
        result["jobs_drafted"] += 1
        _event(result, "job_drafted", message=message, detail=f"{job.title} -> {job.id}")
    except Exception as error:
        _log(session, label, message.id, None, "job", None, "error", str(error))
        result["errors"].append(f"Job email {message.id}: {error}")
        _event(result, "job_error", message=message, detail=str(error))


def _ingest_cv_message(
    session: Session,
    client: GmailClient,
    message: GmailMessage,
    label: str,
    result: dict,
) -> None:
    accepted = 0
    supported = 0
    _event(
        result,
        "cv_message_scan_started",
        message=message,
        detail=f"Attachments: {len(message.attachments)}; LLM enabled: {openai_enabled()}",
    )
    for attachment in message.attachments:
        result["attachments_found"] += 1
        suffix = Path(attachment.filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            result["unsupported_attachments_skipped"] += 1
            _event(
                result,
                "attachment_skipped_unsupported",
                message=message,
                detail=f"{attachment.filename} ({suffix or 'no extension'})",
            )
            continue
        supported += 1
        result["supported_attachments_found"] += 1
        if _attachment_already_processed(session, message.id, attachment):
            result["duplicates_skipped"] += 1
            _event(
                result,
                "attachment_skipped_duplicate",
                message=message,
                detail=attachment.filename,
            )
            continue
        temporary_path: Path | None = None
        try:
            content = attachment.content or client.download_attachment(
                message.id, attachment.attachment_id
            )
            duplicate_file = session.exec(
                select(CandidateFile).where(CandidateFile.file_hash == sha256_bytes(content))
            ).first()
            if duplicate_file and duplicate_file.candidate_id:
                _log(
                    session,
                    label,
                    message.id,
                    attachment.attachment_id,
                    "candidate",
                    duplicate_file.candidate_id,
                    "success",
                    f"{attachment.filename} -> existing CV {duplicate_file.id}",
                    attachment_key=_attachment_key(attachment),
                )
                result["duplicates_skipped"] += 1
                _event(
                    result,
                    "attachment_skipped_existing_cv",
                    message=message,
                    detail=attachment.filename,
                )
                continue
            _event(
                result,
                "cv_ingestion_started",
                message=message,
                detail=f"{attachment.filename}; LLM enabled: {openai_enabled()}",
            )
            with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
                temporary_file.write(content)
                temporary_path = Path(temporary_file.name)
            candidate_id, candidate_file_id = ingest_cv_file(
                session=session,
                source_path=temporary_path,
                original_filename=attachment.filename,
                source="gmail",
                use_llm=True,
            )
            _log(
                session,
                label,
                message.id,
                attachment.attachment_id,
                "candidate",
                candidate_id,
                "success",
                f"{attachment.filename} -> {candidate_file_id}",
                attachment_key=_attachment_key(attachment),
            )
            accepted += 1
            result["cvs_ingested"] += 1
            _event(
                result,
                "cv_ingested",
                message=message,
                detail=f"{attachment.filename} -> candidate {candidate_id}",
            )
        except Exception as error:
            _log(
                session,
                label,
                message.id,
                attachment.attachment_id,
                "candidate",
                None,
                "error",
                f"{attachment.filename}: {error}",
                attachment_key=_attachment_key(attachment),
            )
            result["errors"].append(f"CV email {message.id}: {attachment.filename}: {error}")
            _event(
                result,
                "cv_error",
                message=message,
                detail=f"{attachment.filename}: {error}",
            )
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
    if supported == 0:
        _log(session, label, message.id, None, "candidate", None, "skipped", "No supported CV attachments")
        _event(result, "cv_message_no_supported_attachments", message=message)


def _message_already_processed(
    session: Session, message_id: str, label: str, entity_type: str
) -> bool:
    return (
        session.exec(
            select(IngestionLog).where(
                IngestionLog.source == "gmail",
                IngestionLog.source_label == label,
                IngestionLog.source_message_id == message_id,
                IngestionLog.entity_type == entity_type,
                IngestionLog.status == "success",
            )
        ).first()
        is not None
    )


def _attachment_already_processed(
    session: Session, message_id: str, attachment: GmailAttachment
) -> bool:
    successful_logs = session.exec(
        select(IngestionLog).where(
            IngestionLog.source == "gmail",
            IngestionLog.source_message_id == message_id,
            IngestionLog.entity_type == "candidate",
            IngestionLog.status == "success",
        )
    ).all()
    stable_key = _attachment_key(attachment)
    return any(
        log.source_attachment_key == stable_key
        or (
            log.source_attachment_key is None
            and (log.detail or "").startswith(f"{attachment.filename} ->")
        )
        for log in successful_logs
    )


def _attachment_key(attachment: GmailAttachment) -> str:
    return f"{attachment.filename}\x1f{attachment.size_bytes or ''}"


def _log(
    session: Session,
    label: str,
    message_id: str,
    attachment_id: str | None,
    entity_type: str,
    entity_id: str | None,
    status: str,
    detail: str,
    attachment_key: str | None = None,
) -> None:
    session.add(
        IngestionLog(
            source="gmail",
            source_label=label,
            source_message_id=message_id,
            source_attachment_id=attachment_id,
            source_attachment_key=attachment_key,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            detail=detail[:2000],
        )
    )


def _event(
    result: dict,
    event: str,
    message: GmailMessage | None = None,
    detail: str | None = None,
) -> None:
    payload = {"event": event}
    if message:
        payload["message_id"] = message.id
        payload["subject"] = message.subject[:200]
    if detail:
        payload["detail"] = detail[:500]
    result.setdefault("events", []).append(payload)
