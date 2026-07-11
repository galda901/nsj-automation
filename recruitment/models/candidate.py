from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from recruitment.utils.ids import new_id


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Candidate(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("cand"), primary_key=True)
    full_name: str = Field(index=True, max_length=200)
    email: str | None = Field(default=None, index=True, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    city: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    current_title: str | None = Field(default=None, index=True)
    seniority: str | None = Field(default=None, index=True)
    total_years_experience: float | None = None
    current_company: str | None = None
    industries: str | None = None
    languages: str | None = None
    desired_salary: str | None = None
    notice_period: str | None = None
    remote_preference: str | None = None
    relocation_preference: str | None = None
    ai_summary: str | None = None
    parse_confidence: float | None = None
    source: str | None = None
    status: str = Field(default="new", index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CandidateSkill(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("skill"), primary_key=True)
    candidate_id: str = Field(foreign_key="candidate.id", index=True)
    skill_name: str
    normalized_skill_name: str = Field(index=True)
    years_experience: float | None = None
    level: str | None = None
    last_used_year: int | None = None
    evidence: str | None = None
    confidence: float | None = None


class CandidateFile(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("file"), primary_key=True)
    candidate_id: str | None = Field(default=None, foreign_key="candidate.id", index=True)
    original_filename: str
    stored_path: str
    extracted_text_path: str | None = None
    file_type: str | None = None
    file_hash: str | None = Field(default=None, index=True)
    uploaded_at: datetime = Field(default_factory=now_utc)
