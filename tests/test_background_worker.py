from sqlmodel import SQLModel, Session, create_engine, select

from recruitment.config import Settings
from recruitment.models.candidate import Candidate
from recruitment.models.job import JobPosition
from recruitment.models.notification import NotificationOutbox
from recruitment.services import background_worker, embeddings


def test_worker_matches_changed_email_entities_and_creates_outbox(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        candidate = Candidate(
            full_name="Ada Example",
            current_title="Senior Python Engineer",
            seniority="senior",
            total_years_experience=7,
            ai_summary="Python FastAPI backend services",
        )
        job = JobPosition(
            client_name="Example",
            title="Senior Python Engineer",
            seniority="senior",
            min_years_experience=5,
            description="Build Python FastAPI services",
        )
        session.add(candidate)
        session.add(job)
        session.commit()
        candidate_id = candidate.id
        job_id = job.id

    settings = Settings(
        telegram_chat_id="123456789",
        telegram_enabled=False,
        telegram_dry_run=True,
    )
    monkeypatch.setattr(background_worker, "engine", engine)
    monkeypatch.setattr(background_worker, "get_settings", lambda: settings)
    monkeypatch.setattr(embeddings, "openai_enabled", lambda: False)
    monkeypatch.setattr(
        background_worker,
        "ingest_gmail_daily",
        lambda session: {"job_ids": [job_id], "candidate_ids": [candidate_id]},
    )

    summary = background_worker.run_worker_cycle()

    assert summary["jobs_matched"] == 1
    assert summary["matches_evaluated"] == 1
    assert summary["notifications_created"] == 1
    with Session(engine) as session:
        notification = session.exec(select(NotificationOutbox)).one()
        assert notification.status == "pending"
        assert notification.recipient == "123456789"
