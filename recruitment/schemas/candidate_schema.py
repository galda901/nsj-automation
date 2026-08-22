from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateCreate(BaseModel):
    full_name: str = Field(
        min_length=1,
        max_length=200,
        description="Candidate full name, written or transliterated in Hebrew.",
    )
    email: EmailStr | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    current_title: str | None = None
    seniority: str | None = None
    total_years_experience: float | None = Field(default=None, ge=0)
    current_company: str | None = None
    industries: str | None = None
    languages: str | None = None
    desired_salary: str | None = None
    notice_period: str | None = None
    remote_preference: str | None = None
    relocation_preference: str | None = None
    ai_summary: str | None = None
    comments: str | None = None
    current_job_id: str | None = None
    parse_confidence: float | None = Field(default=None, ge=0, le=1)
    source: str | None = "manual"
    status: str = "new"


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    current_title: str | None = None
    seniority: str | None = None
    total_years_experience: float | None = Field(default=None, ge=0)
    current_company: str | None = None
    industries: str | None = None
    languages: str | None = None
    desired_salary: str | None = None
    notice_period: str | None = None
    remote_preference: str | None = None
    relocation_preference: str | None = None
    ai_summary: str | None = None
    comments: str | None = None
    current_job_id: str | None = None
    parse_confidence: float | None = Field(default=None, ge=0, le=1)
    source: str | None = None
    status: str | None = None


class CandidateExtractionTemplate(BaseModel):
    """Structured candidate facts returned by the CV extraction model."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(
        min_length=1,
        max_length=200,
        description="Candidate full name, written or transliterated in Hebrew.",
    )
    email: EmailStr | None
    phone: str | None = Field(
        description="Phone number. For an Israeli number use 05X-XXX-XXXX or 0X-XXX-XXXX."
    )
    city: str | None = Field(description="Candidate city, written in Hebrew.")
    country: str | None = Field(description="Candidate country, written in Hebrew.")
    current_title: str | None = Field(
        description="Current or most recent job title, written in Hebrew."
    )
    seniority: str | None
    total_years_experience: float | None = Field(ge=0)
    languages: str | None
    ai_summary: str | None
    parse_confidence: float = Field(ge=0, le=1)


class CandidateRead(CandidateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
