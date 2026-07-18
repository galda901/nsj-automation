from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchUpdate(BaseModel):
    total_score: float | None = Field(default=None, ge=0, le=100)
    hard_filter_passed: bool | None = None
    skill_score: float | None = Field(default=None, ge=0, le=100)
    experience_score: float | None = Field(default=None, ge=0, le=100)
    seniority_score: float | None = Field(default=None, ge=0, le=100)
    location_score: float | None = Field(default=None, ge=0, le=100)
    ai_score: float | None = Field(default=None, ge=0, le=100)
    explanation: str | None = None
    risks: str | None = None
    missing_requirements: str | None = None


class MatchExplanationTemplate(BaseModel):
    """Structured assessment returned by the match-analysis model."""

    model_config = ConfigDict(extra="forbid")

    ai_score: float = Field(
        ge=0,
        le=100,
        description="Recruiter-facing fit assessment from 0 to 100.",
    )
    explanation: str = Field(
        description="A concise, plain-language Hebrew explanation of why the candidate is a likely fit."
    )
    risks: str = Field(description="Concise Hebrew points the recruiter should verify.")
    missing_requirements: str = Field(
        description="Concise Hebrew requirements that are missing or not evidenced."
    )


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    candidate_id: str
    total_score: float
    hard_filter_passed: bool
    skill_score: float | None = None
    experience_score: float | None = None
    seniority_score: float | None = None
    location_score: float | None = None
    ai_score: float | None = None
    explanation: str | None = None
    risks: str | None = None
    missing_requirements: str | None = None
    created_at: datetime


class MatchingRunResponse(BaseModel):
    job_id: str
    matches_created: int
    matches: list[MatchRead]
