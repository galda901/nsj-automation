from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from recruitment.config import Settings, get_settings
from recruitment.integrations.telegram_client import TelegramBotClient, TelegramClient
from recruitment.models.candidate import Candidate, now_utc
from recruitment.models.job import JobPosition
from recruitment.models.match import MatchResult
from recruitment.models.notification import NotificationOutbox
from recruitment.services.matching_engine import MATCH_QUALIFICATION_THRESHOLD


class NotificationConfigurationError(RuntimeError):
    pass


def enqueue_match_notifications(
    session: Session,
    matches: list[MatchResult],
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    recipient = (settings.telegram_chat_id or "").strip()
    if not recipient:
        raise NotificationConfigurationError("TELEGRAM_CHAT_ID is not configured")
    created = 0
    for match in matches:
        if not match.hard_filter_passed or match.total_score < MATCH_QUALIFICATION_THRESHOLD:
            continue
        candidate = session.get(Candidate, match.candidate_id)
        job = session.get(JobPosition, match.job_id)
        if candidate is None or job is None or job.status == "closed":
            continue
        notification_key = f"telegram|{recipient}|{candidate.id}|{job.id}"
        existing = session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.notification_key == notification_key
            )
        ).first()
        if existing is not None:
            continue
        message_body = build_match_message(candidate, job, match.total_score, settings)
        session.add(
            NotificationOutbox(
                notification_key=notification_key,
                candidate_id=candidate.id,
                job_id=job.id,
                recipient=recipient,
                candidate_name=candidate.full_name,
                job_title=job.title,
                score=match.total_score,
                message_body=message_body,
            )
        )
        created += 1
    return created


def build_match_message(
    candidate: Candidate,
    job: JobPosition,
    score: float,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    lines = [
        "Possible recruitment match",
        f"Candidate: {candidate.full_name}",
        f"Job: {job.title}",
        f"Score: {score:.1f}/100",
    ]
    if settings.dashboard_public_url:
        lines.append(f"Dashboard: {settings.dashboard_public_url.rstrip('/')}")
    return "\n".join(lines)


def deliver_pending_notifications(
    session: Session,
    settings: Settings | None = None,
    client: TelegramClient | None = None,
    now: datetime | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    settings = settings or get_settings()
    now = now or now_utc()
    _release_stale_notifications(session, now)
    if not settings.telegram_enabled:
        return {"enabled": False, "dry_run": settings.telegram_dry_run, "sent": 0, "failed": 0}
    if settings.telegram_dry_run:
        pending_count = len(
            session.exec(
                select(NotificationOutbox).where(
                    NotificationOutbox.status.in_(["pending", "failed"]),
                    NotificationOutbox.next_attempt_at <= now,
                )
            ).all()
        )
        return {
            "enabled": True,
            "dry_run": True,
            "sent": 0,
            "failed": 0,
            "pending": pending_count,
        }
    client = client or TelegramBotClient(settings)
    notifications = list(
        session.exec(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(["pending", "failed"]),
                NotificationOutbox.next_attempt_at <= now,
                NotificationOutbox.attempts < settings.telegram_max_attempts,
            )
            .order_by(NotificationOutbox.created_at)
            .limit(limit)
        ).all()
    )
    sent = 0
    failed = 0
    for notification in notifications:
        notification.status = "sending"
        notification.attempts += 1
        notification.locked_until = now + timedelta(seconds=settings.telegram_retry_seconds)
        notification.updated_at = now
        session.add(notification)
        session.commit()
        try:
            provider_message_id = client.send_message(
                chat_id=notification.recipient,
                text=notification.message_body,
            )
        except Exception as error:
            notification = session.get(NotificationOutbox, notification.id)
            if notification is None:
                continue
            notification.status = (
                "failed"
                if notification.attempts >= settings.telegram_max_attempts
                else "pending"
            )
            notification.last_error = str(error)[:2000]
            notification.next_attempt_at = now + timedelta(
                seconds=settings.telegram_retry_seconds
                * (2 ** max(notification.attempts - 1, 0))
            )
            notification.locked_until = None
            notification.updated_at = now
            session.add(notification)
            session.commit()
            failed += 1
            continue
        notification = session.get(NotificationOutbox, notification.id)
        if notification is None:
            continue
        notification.status = "sent"
        notification.provider_message_id = provider_message_id
        notification.sent_at = now
        notification.locked_until = None
        notification.updated_at = now
        session.add(notification)
        session.commit()
        sent += 1
    return {"enabled": True, "dry_run": False, "sent": sent, "failed": failed}


def _release_stale_notifications(session: Session, now: datetime) -> None:
    stale = session.exec(
        select(NotificationOutbox).where(
            NotificationOutbox.status == "sending",
            NotificationOutbox.locked_until.is_not(None),
            NotificationOutbox.locked_until < now,
        )
    ).all()
    for notification in stale:
        notification.status = "pending"
        notification.locked_until = None
        notification.next_attempt_at = now
        notification.updated_at = now
        session.add(notification)
    if stale:
        session.commit()
