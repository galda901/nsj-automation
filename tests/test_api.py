from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from apps.api.main import app
from apps.api.routers import ingestion
from recruitment.database import get_session


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
            matches = client.post(f"/matching/jobs/{job.json()['id']}/run")
            assert matches.status_code == 200
            assert matches.json()["matches_created"] == 1
    finally:
        app.dependency_overrides.clear()
