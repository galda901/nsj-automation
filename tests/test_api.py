from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from apps.api.main import app
from apps.api.routers import ingestion
from recruitment.database import get_session
from recruitment.services.cv_parser import parse_candidate_from_text
from recruitment.services.candidate_formatting import normalize_phone


def test_fallback_candidate_parser_does_not_use_cv_as_summary() -> None:
    candidate = parse_candidate_from_text(
        "Resume\nAda Example\nPhone: 050-1234567\nTel Aviv\nSenior Python Engineer",
        use_llm=False,
    )
    assert candidate.full_name == "Ada Example"
    assert candidate.phone == "050-123-4567"
    assert candidate.city == "תל אביב-יפו"
    assert candidate.current_title == "Senior Python Engineer"
    assert candidate.ai_summary is None


def test_fallback_candidate_parser_handles_spaced_pdf_text() -> None:
    candidate = parse_candidate_from_text(
        "N A D A V  C O S T I\nS H O H A M, I S R A E L\n+ 9 7 2 - 5 8 6 8 3 2 6 8 1",
        use_llm=False,
    )
    assert candidate.full_name == "NADAV COSTI"
    assert candidate.city == "שוהם"
    assert candidate.phone == "058-683-2681"


def test_phone_normalizer_recovers_rtl_prefix_order() -> None:
    assert normalize_phone("6675676-050") == "050-667-5676"
    assert normalize_phone("05X-XXX-XXXX") is None


def test_api_candidate_job_ingestion_and_matching(tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    ingestion.settings.cv_raw_dir = tmp_path / "raw"
    ingestion.settings.cv_text_dir = tmp_path / "text"
    ingestion.settings.export_dir = tmp_path / "exports"
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            job = client.post(
                "/jobs",
                json={
                    "client_name": "Example Ltd",
                    "title": "Senior Python Engineer",
                    "seniority": "senior",
                    "description": "Build FastAPI services",
                },
            )
            assert job.status_code == 201
            cv = client.post(
                "/ingestion/cv",
                files={
                    "file": (
                        "ada.txt",
                        b"Ada Example\nada@example.com\nSenior Python Engineer\nFastAPI",
                    )
                },
            )
            assert cv.status_code == 201
            candidate_id = cv.json()["candidate_id"]
            assert client.get(f"/candidates/{candidate_id}").status_code == 200
            updated_candidate = client.patch(
                f"/candidates/{candidate_id}",
                json={"status": "active", "ai_summary": "FastAPI specialist", "comments": "שיחת היכרות ביום א׳"},
            )
            assert updated_candidate.status_code == 200
            assert updated_candidate.json()["status"] == "active"
            assert updated_candidate.json()["ai_summary"] == "FastAPI specialist"
            assert updated_candidate.json()["comments"] == "שיחת היכרות ביום א׳"
            updated_job = client.patch(
                f"/jobs/{job.json()['id']}",
                json={"summary": "Senior engineer for FastAPI services"},
            )
            assert updated_job.status_code == 200
            assert updated_job.json()["summary"] == "Senior engineer for FastAPI services"
            matches = client.post(f"/matching/jobs/{job.json()['id']}/run")
            assert matches.status_code == 200
            assert matches.json()["matches_created"] == 1
            match_id = matches.json()["matches"][0]["id"]
            updated_match = client.patch(
                f"/matching/{match_id}", json={"hard_filter_passed": False}
            )
            assert updated_match.status_code == 200
            assert updated_match.json()["hard_filter_passed"] is False
    finally:
        app.dependency_overrides.clear()
