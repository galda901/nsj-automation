from datetime import datetime

from sqlmodel import Field, SQLModel

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class Interaction(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("int"), primary_key=True)
    candidate_id: str | None = Field(default=None, foreign_key="candidate.id", index=True)
    job_id: str | None = Field(default=None, foreign_key="jobposition.id", index=True)
    interaction_type: str
    subject: str | None = None
    notes: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
