import re

from sqlmodel import Session, select

from recruitment.models.candidate import Candidate, now_utc
from recruitment.models.job import JobPosition
from recruitment.models.match import MatchResult
from recruitment.models.vector import EmbeddingRecord
from recruitment.services.embeddings import (
    cosine_similarity,
    decode_embedding,
    latest_embedding,
    upsert_embedding,
)

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}")
STOP_WORDS = {"and", "the", "with", "for", "from", "that", "this", "job", "role", "will", "our"}
MATCH_QUALIFICATION_THRESHOLD = 60.0
MATCHING_EMBEDDING_SOURCE = "matching_text"


def match_candidates_for_job(
    job_id: str, session: Session, candidate_limit: int | None = 20
) -> list[MatchResult]:
    job = session.get(JobPosition, job_id)
    if job is None:
        raise LookupError(f"Job {job_id!r} was not found")

    candidates = retrieved_candidates_for_job(job, session, limit=candidate_limit)
    results: list[MatchResult] = []
    for candidate, vector_score in candidates:
        deterministic_score, explanation = basic_candidate_score(candidate, job)
        score = round(min((deterministic_score * 0.65) + (vector_score * 35.0), 100.0), 1)
        existing = session.exec(
            select(MatchResult).where(
                MatchResult.job_id == job.id,
                MatchResult.candidate_id == candidate.id,
            )
        ).first()
        result = existing or MatchResult(
            job_id=job.id, candidate_id=candidate.id, total_score=score
        )
        result.total_score = score
        # Matching is deliberately local after embeddings are available.
        result.hard_filter_passed = score >= MATCH_QUALIFICATION_THRESHOLD
        result.ai_score = None
        result.explanation = explanation
        result.risks = None
        result.missing_requirements = None
        result.created_at = now_utc()
        session.add(result)
        results.append(result)
    session.commit()
    for result in results:
        session.refresh(result)
    return sorted(results, key=lambda item: item.total_score, reverse=True)


def retrieved_candidates_for_job(
    job: JobPosition, session: Session, limit: int | None = 20
) -> list[tuple[Candidate, float]]:
    """Load cached match embeddings and create one only when its source text changed."""
    upsert_embedding(
        session,
        owner_type="job",
        owner_id=job.id,
        source_type=MATCHING_EMBEDDING_SOURCE,
        text=job_match_text(job),
    )
    session.flush()
    job_embedding = latest_embedding(
        session, "job", job.id, source_type=MATCHING_EMBEDDING_SOURCE
    )
    if job_embedding is None:
        candidates = list(
            session.exec(select(Candidate).where(Candidate.status != "not_relevant")).all()
        )
        ranked = [(candidate, 0.0) for candidate in candidates]
        return ranked if limit is None else ranked[:limit]
    job_vector = decode_embedding(job_embedding)
    ranked: list[tuple[Candidate, float]] = []
    candidates = list(
        session.exec(select(Candidate).where(Candidate.status != "not_relevant")).all()
    )
    for candidate in candidates:
        upsert_embedding(
            session,
            owner_type="candidate",
            owner_id=candidate.id,
            source_type=MATCHING_EMBEDDING_SOURCE,
            text=candidate_match_text(candidate),
        )
    session.flush()
    candidate_embeddings: dict[str, EmbeddingRecord] = {}
    for record in session.exec(
        select(EmbeddingRecord)
        .where(
            EmbeddingRecord.owner_type == "candidate",
            EmbeddingRecord.source_type == MATCHING_EMBEDDING_SOURCE,
        )
        .order_by(EmbeddingRecord.created_at.desc())
    ).all():
        candidate_embeddings.setdefault(record.owner_id, record)
    for candidate in candidates:
        record = candidate_embeddings.get(candidate.id)
        if record is not None:
            ranked.append((candidate, cosine_similarity(job_vector, decode_embedding(record))))
    ordered = sorted(ranked, key=lambda item: item[1], reverse=True)
    return ordered if limit is None else ordered[:limit]


def basic_candidate_score(candidate: Candidate, job: JobPosition) -> tuple[float, str]:
    job_tokens = tokens(f"{job.title} {job.description}")
    candidate_tokens = tokens(
        f"{candidate.current_title or ''} {candidate.ai_summary or ''} {candidate.industries or ''}"
    )
    overlap = job_tokens & candidate_tokens
    keyword_score = min(60.0, len(overlap) * 5.0)
    seniority_score = 0.0
    if candidate.seniority and job.seniority:
        seniority_score = 20.0 if candidate.seniority.casefold() == job.seniority.casefold() else 0.0
    experience_score = 0.0
    if job.min_years_experience is not None and candidate.total_years_experience is not None:
        experience_score = 20.0 * min(
            candidate.total_years_experience / max(job.min_years_experience, 0.5), 1.0
        )
    score = round(min(keyword_score + seniority_score + experience_score, 100.0), 1)
    evidence = ", ".join(sorted(overlap)[:10]) or "no shared keywords"
    return score, f"MVP deterministic score; shared terms: {evidence}."


def job_match_text(job: JobPosition) -> str:
    return "\n".join(
        value
        for value in [
            job.title,
            job.description,
            job.location,
            job.remote_policy,
            job.employment_type,
            job.seniority,
            str(job.min_years_experience or ""),
        ]
        if value
    )


def candidate_match_text(candidate: Candidate) -> str:
    return "\n".join(
        value
        for value in [
            candidate.full_name,
            candidate.current_title,
            candidate.seniority,
            candidate.city,
            candidate.country,
            candidate.industries,
            candidate.languages,
            candidate.ai_summary,
            str(candidate.total_years_experience or ""),
        ]
        if value
    )


def tokens(value: str) -> set[str]:
    return {
        match.group(0).casefold()
        for match in TOKEN_PATTERN.finditer(value)
        if match.group(0).casefold() not in STOP_WORDS
    }
