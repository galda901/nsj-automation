from recruitment.database import get_session
from recruitment.models.candidate import Candidate
from recruitment.models.job import JobPosition
from recruitment.services.embeddings import upsert_embedding
from recruitment.services.matching_engine import (
    MATCHING_EMBEDDING_SOURCE,
    candidate_match_text,
    job_match_text,
)
from sqlmodel import select


def main() -> None:
    session = next(get_session())
    candidates = list(session.exec(select(Candidate)).all())
    jobs = list(session.exec(select(JobPosition)).all())
    for candidate in candidates:
        upsert_embedding(
            session,
            "candidate",
            candidate.id,
            MATCHING_EMBEDDING_SOURCE,
            candidate_match_text(candidate),
        )
    for job in jobs:
        upsert_embedding(session, "job", job.id, MATCHING_EMBEDDING_SOURCE, job_match_text(job))
    session.commit()
    print({"candidates": len(candidates), "jobs": len(jobs), "status": "rebuilt"})


if __name__ == "__main__":
    main()
