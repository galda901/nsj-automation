from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    client_name: str = Field(min_length=1)
    public_company_name: str | None = None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    location: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    min_years_experience: float | None = Field(default=None, ge=0)
    salary_range: str | None = None


class JobRead(JobCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
