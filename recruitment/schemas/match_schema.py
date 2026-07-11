from pydantic import BaseModel


class MatchingRunResponse(BaseModel):
    job_id: str
    matches_created: int
    matches: list[dict]
