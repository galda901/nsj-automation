from recruitment.models.candidate import Candidate
from recruitment.models.job import JobPosition
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
