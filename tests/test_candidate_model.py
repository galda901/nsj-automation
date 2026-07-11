from recruitment.models.candidate import Candidate


def test_candidate_gets_prefixed_id() -> None:
    candidate = Candidate(full_name="Test Candidate")
    assert candidate.id.startswith("cand_")
    assert candidate.status == "new"
