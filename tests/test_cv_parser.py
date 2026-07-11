from recruitment.services.cv_parser import parse_candidate_from_text


def test_parser_extracts_name_and_email() -> None:
    candidate = parse_candidate_from_text(
        "Gal Example\ngal.example@example.com\nSenior Python Engineer"
    )
    assert candidate.full_name == "Gal Example"
    assert candidate.email == "gal.example@example.com"
    assert candidate.parse_confidence == 0.35


def test_parser_falls_back_without_text() -> None:
    candidate = parse_candidate_from_text("")
    assert candidate.full_name == "Unknown Candidate"
    assert candidate.email is None
