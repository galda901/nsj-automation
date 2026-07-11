from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    current_title: str | None = None
    seniority: str | None = None
    total_years_experience: float | None = Field(default=None, ge=0)
    ai_summary: str | None = None
    source: str | None = "manual"
    status: str = "new"


class CandidateRead(CandidateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parse_confidence: float | None = None
