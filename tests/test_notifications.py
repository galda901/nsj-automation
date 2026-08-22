from datetime import timedelta

from sqlmodel import SQLModel, Session, create_engine, select

from recruitment.config import Settings
from recruitment.models.candidate import Candidate, now_utc
from recruitment.models.job import JobPosition
from recruitment.models.match import MatchResult
from recruitment.models.notification import NotificationOutbox
from recruitment.services.notifications import (
    NotificationConfigurationError,
    deliver_pending_notifications,
    enqueue_match_notifications,
)


class FakeTelegramClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def send_message(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return "telegram-message-1"


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "telegram_chat_id": "123456789",
        "telegram_enabled": True,
        "telegram_dry_run": False,
        "telegram_bot_token": "bot-token",
        "telegram_max_attempts": 2,
        "telegram_retry_seconds": 1,
    }
    values.update(overrides)
    return Settings(**values)


def make_match(session: Session) -> list[MatchResult]:
    candidate = Candidate(full_name="Ada Example")
    job = JobPosition(client_name="Example", title="Python Engineer", description="Python")
    session.add(candidate)
    session.add(job)
    session.commit()
    match = MatchResult(
        candidate_id=candidate.id,
        job_id=job.id,
        total_score=82.5,
        hard_filter_passed=True,
    )
    session.add(match)
    session.commit()
    return [match]


def test_requires_telegram_chat_id() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        matches = make_match(session)
        try:
            enqueue_match_notifications(
                session, matches, make_settings(telegram_chat_id=None)
            )
        except NotificationConfigurationError as error:
            assert "TELEGRAM_CHAT_ID" in str(error)
        else:
            raise AssertionError("Expected missing Telegram chat ID to fail")


def test_outbox_deduplicates_and_sends_once() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    settings = make_settings()
    with Session(engine) as session:
        matches = make_match(session)
        assert enqueue_match_notifications(session, matches, settings) == 1
        session.commit()
        assert enqueue_match_notifications(session, matches, settings) == 0
        session.commit()

        client = FakeTelegramClient()
        result = deliver_pending_notifications(session, settings, client=client)
        assert result["sent"] == 1
        assert len(client.calls) == 1
        assert client.calls[0]["chat_id"] == "123456789"
        notification = session.exec(select(NotificationOutbox)).one()
        assert notification.status == "sent"
        assert notification.provider_message_id == "telegram-message-1"

        assert deliver_pending_notifications(session, settings, client=client)["sent"] == 0
        assert len(client.calls) == 1


def test_dry_run_does_not_send() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    settings = make_settings(telegram_dry_run=True)
    with Session(engine) as session:
        matches = make_match(session)
        enqueue_match_notifications(session, matches, settings)
        session.commit()
        client = FakeTelegramClient()
        result = deliver_pending_notifications(session, settings, client=client)
        assert result["dry_run"] is True
        assert result["pending"] == 1
        assert client.calls == []


def test_failed_notification_retries_then_is_marked_failed() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    settings = make_settings()
    with Session(engine) as session:
        matches = make_match(session)
        enqueue_match_notifications(session, matches, settings)
        session.commit()
        client = FakeTelegramClient(RuntimeError("temporary failure"))
        first = deliver_pending_notifications(session, settings, client=client)
        assert first["failed"] == 1
        notification = session.exec(select(NotificationOutbox)).one()
        assert notification.status == "pending"
        assert notification.attempts == 1

        notification.next_attempt_at = now_utc() - timedelta(seconds=1)
        session.add(notification)
        session.commit()
        second = deliver_pending_notifications(session, settings, client=client)
        assert second["failed"] == 1
        notification = session.exec(select(NotificationOutbox)).one()
        assert notification.status == "failed"
        assert notification.attempts == 2
