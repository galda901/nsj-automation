from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class NotificationOutbox(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("notification_key"),)

    id: str = Field(default_factory=lambda: new_id("wa"), primary_key=True)
    notification_key: str = Field(index=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    job_id: str = Field(foreign_key="jobposition.id", index=True)
    recipient: str = Field(index=True)
    candidate_name: str
    job_title: str
    score: float
    message_body: str
    status: str = Field(default="pending", index=True)
    attempts: int = 0
    next_attempt_at: datetime = Field(default_factory=now_utc, index=True)
    locked_until: datetime | None = None
    provider_message_id: str | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    sent_at: datetime | None = None


class WorkerState(SQLModel, table=True):
    id: str = Field(default="gmail-matching-worker", primary_key=True)
    status: str = Field(default="idle", index=True)
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    last_summary_json: str | None = None
    updated_at: datetime = Field(default_factory=now_utc)
