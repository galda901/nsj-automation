from sqlmodel import SQLModel, Session, create_engine

from recruitment.models.candidate import Candidate
from recruitment.models.job import JobPosition
from recruitment.services import embeddings, matching_engine
from recruitment.services.matching_engine import basic_candidate_score


def test_matching_rewards_relevant_terms_and_seniority() -> None:
    candidate = Candidate(
        full_name="Ada Example",
        current_title="Senior Python Engineer",
        seniority="senior",
        total_years_experience=7,
        ai_summary="FastAPI backend services on AWS and PostgreSQL",
    )
    job = JobPosition(
        client_name="Example",
        title="Senior Python Engineer",
        seniority="senior",
        min_years_experience=5,
        description="Build Python FastAPI services on AWS",
    )
    score, explanation = basic_candidate_score(candidate, job)
    assert score >= 60
    assert "python" in explanation


def test_matching_score_is_bounded() -> None:
    repeated = " ".join(f"skill{index}" for index in range(50))
    candidate = Candidate(full_name="Ada", ai_summary=repeated)
    job = JobPosition(client_name="Example", title="Engineer", description=repeated)
    score, _ = basic_candidate_score(candidate, job)
    assert 0 <= score <= 100


def test_matching_reuses_saved_embeddings_until_the_entity_changes(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    embedding_requests: list[str] = []

    def fake_embedding(text: str) -> list[float]:
        embedding_requests.append(text)
        return [1.0, 0.0]

    monkeypatch.setattr(embeddings, "embedding_for_text", fake_embedding)
    monkeypatch.setattr(embeddings, "openai_enabled", lambda: False)
    monkeypatch.setattr(matching_engine, "openai_enabled", lambda: False)

    with Session(engine) as session:
        candidate = Candidate(full_name="Ada", current_title="Python Engineer")
        job = JobPosition(
            client_name="Example", title="Engineer", description="Python services"
        )
        session.add(candidate)
        session.add(job)
        session.commit()

        matching_engine.match_candidates_for_job(job.id, session)
        matching_engine.match_candidates_for_job(job.id, session)
        assert len(embedding_requests) == 2

        candidate.current_title = "Senior Python Engineer"
        session.add(candidate)
        session.commit()
        matching_engine.match_candidates_for_job(job.id, session)

    assert len(embedding_requests) == 3
