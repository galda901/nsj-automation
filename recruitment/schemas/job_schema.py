from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    client_name: str = Field(min_length=1)
    public_company_name: str | None = None
    title: str = Field(min_length=1, description="Job title, written in Hebrew.")
    description: str = Field(min_length=1)
    summary: str | None = Field(default=None, max_length=1000)
    location: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    min_years_experience: float | None = Field(default=None, ge=0)
    salary_range: str | None = None


class JobUpdate(BaseModel):
    client_name: str | None = Field(default=None, min_length=1)
    public_company_name: str | None = None
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, max_length=1000)
    location: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    min_years_experience: float | None = Field(default=None, ge=0)
    salary_range: str | None = None
    status: str | None = None


class JobExtractionTemplate(BaseModel):
    """Structured job facts returned by the job-email extraction model."""

    model_config = ConfigDict(extra="forbid")

    client_name: str = Field(min_length=1)
    public_company_name: str | None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    summary: str | None
    location: str | None = Field(description="Job location, written in Hebrew.")
    remote_policy: str | None
    employment_type: str | None
    seniority: str | None
    min_years_experience: float | None = Field(ge=0)
    salary_range: str | None


class JobRead(JobCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    updated_at: datetime
