"""Rebuild previously Gmail-ingested job records through the OpenAI extraction flow.

The script fetches every source email before changing the database.  It only removes
jobs that have a successful Gmail ingestion record, so manually created jobs remain.
"""

import json

from sqlmodel import Session, delete, select

from recruitment.config import get_settings
from recruitment.database import engine
from recruitment.integrations.gmail_client import GmailClient, GmailMessage
from recruitment.integrations.openai_client import openai_enabled
from recruitment.models.application import Application
from recruitment.models.ingestion import IngestionLog
from recruitment.models.job import JobPosition, JobRequirement
from recruitment.models.match import MatchResult
from recruitment.models.vector import EmbeddingRecord
from recruitment.services.email_ingestion import _ingest_job_message
from recruitment.services.job_parser import parse_job_from_email


def main() -> None:
    settings = get_settings()
    if not settings.gmail_enabled:
        raise RuntimeError("GMAIL_ENABLED is false")
    if not openai_enabled():
        raise RuntimeError("OpenAI job parsing is not enabled")

    with Session(engine) as session:
        logs = list(
            session.exec(
                select(IngestionLog)
                .where(
                    IngestionLog.source == "gmail",
                    IngestionLog.entity_type == "job",
                    IngestionLog.status == "success",
                    IngestionLog.source_message_id.is_not(None),
                )
                .order_by(IngestionLog.created_at)
            ).all()
        )

    message_ids = list(dict.fromkeys(log.source_message_id for log in logs if log.source_message_id))
    job_ids = list(dict.fromkeys(log.entity_id for log in logs if log.entity_id))

    # This read-only phase guarantees both the source emails and structured OpenAI
    # extraction are accessible before any existing job record is removed.
    client = GmailClient()
    if message_ids:
        messages: list[GmailMessage] = [
            client.get_message(message_id) for message_id in message_ids
        ]
    else:
        # Recovery path: the prior run may have been interrupted after clearing its
        # logs. The jobs label is the source of truth and is queried read-only here.
        messages = client.list_messages_by_label(
            settings.gmail_jobs_label, settings.gmail_lookback_days
        )
        message_ids = [message.id for message in messages]
    if not messages:
        raise RuntimeError("No job messages were found in the Gmail jobs label")
    probe = parse_job_from_email(messages[0].subject, messages[0].body)
    if not probe.title or not probe.description:
        raise RuntimeError("OpenAI job extraction preflight returned an incomplete job")

    # Delete and recreate in one database transaction. An interruption before the
    # final commit rolls back the deletion, rather than leaving a partial reset.
    with Session(engine) as session:
        if job_ids:
            session.exec(delete(Application).where(Application.job_id.in_(job_ids)))
            session.exec(delete(MatchResult).where(MatchResult.job_id.in_(job_ids)))
            session.exec(delete(JobRequirement).where(JobRequirement.job_id.in_(job_ids)))
            session.exec(
                delete(EmbeddingRecord).where(
                    EmbeddingRecord.owner_type == "job", EmbeddingRecord.owner_id.in_(job_ids)
                )
            )
            session.exec(delete(JobPosition).where(JobPosition.id.in_(job_ids)))
        session.exec(
            delete(IngestionLog).where(
                IngestionLog.source == "gmail",
                IngestionLog.entity_type == "job",
                IngestionLog.source_message_id.in_(message_ids),
            )
        )
        result = {"jobs_drafted": 0, "duplicates_skipped": 0, "events": [], "errors": []}
        for message in messages:
            _ingest_job_message(session, message, settings.gmail_jobs_label, result)
        session.commit()

    print(
        json.dumps(
            {
                "jobs_removed": len(job_ids),
                "job_messages_reingested": len(messages),
                "jobs_drafted": result["jobs_drafted"],
                "errors": result["errors"],
                "openai_preflight_title": probe.title,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
