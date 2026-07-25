from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    candidate_id: str
    job_id: str
    source: str | None = None
