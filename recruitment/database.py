from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

from recruitment.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    settings.ensure_local_directories()
    import recruitment.models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _apply_sqlite_migrations()


def _apply_sqlite_migrations() -> None:
    """Apply the small additive migrations needed by the local SQLite database."""
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    job_columns = {column["name"] for column in inspector.get_columns("jobposition")}
    candidate_columns = {column["name"] for column in inspector.get_columns("candidate")}
    ingestion_columns = {column["name"] for column in inspector.get_columns("ingestionlog")}
    if "summary" not in job_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE jobposition ADD COLUMN summary VARCHAR"))
    if "comments" not in candidate_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE candidate ADD COLUMN comments VARCHAR"))
    if "current_job_id" not in candidate_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE candidate ADD COLUMN current_job_id VARCHAR"))
    if "source_attachment_key" not in ingestion_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE ingestionlog ADD COLUMN source_attachment_key VARCHAR")
            )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
