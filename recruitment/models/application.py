from datetime import datetime

from sqlmodel import Field, SQLModel

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class Application(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("app"), primary_key=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    job_id: str | None = Field(default=None, foreign_key="jobposition.id", index=True)
    source: str | None = None
    source_email: str | None = None
    email_subject: str | None = None
    status: str = Field(default="received", index=True)
    received_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
