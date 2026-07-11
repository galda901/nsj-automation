from datetime import datetime

from sqlmodel import Field, SQLModel

from recruitment.models.candidate import now_utc
from recruitment.utils.ids import new_id


class JobPosition(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("job"), primary_key=True)
    client_name: str = Field(index=True)
    public_company_name: str | None = None
    title: str = Field(index=True)
    description: str
    location: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    seniority: str | None = Field(default=None, index=True)
    min_years_experience: float | None = None
    salary_range: str | None = None
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class JobRequirement(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("req"), primary_key=True)
    job_id: str = Field(foreign_key="jobposition.id", index=True)
    requirement_type: str
    name: str
    normalized_name: str | None = Field(default=None, index=True)
    importance: str = "must_have"
    min_years: float | None = None
    weight: float = 1.0
