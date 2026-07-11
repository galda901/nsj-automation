from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class MatchResult(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("job_id", "candidate_id"),)

    id: str = Field(default_factory=lambda: new_id("match"), primary_key=True)
    job_id: str = Field(foreign_key="jobposition.id", index=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    total_score: float
    hard_filter_passed: bool = True
    skill_score: float | None = None
    experience_score: float | None = None
    seniority_score: float | None = None
    location_score: float | None = None
    ai_score: float | None = None
    explanation: str | None = None
    risks: str | None = None
    missing_requirements: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
