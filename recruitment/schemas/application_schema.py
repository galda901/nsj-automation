from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    candidate_id: str
    job_id: str | None = None
    source: str | None = None
