"""Reset candidate data and rebuild it from the locally stored CV files using OpenAI."""

from pathlib import Path

from sqlmodel import Session, delete, select

from recruitment.database import engine
from recruitment.models.application import Application
from recruitment.models.candidate import Candidate, CandidateFile, CandidateSkill
from recruitment.models.ingestion import IngestionLog
from recruitment.models.match import MatchResult
from recruitment.models.vector import EmbeddingRecord
from recruitment.services.cv_ingestion import ingest_cv_file


def main() -> None:
    with Session(engine) as session:
        files = list(session.exec(select(CandidateFile).order_by(CandidateFile.uploaded_at)).all())
        sources = [
            (Path(candidate_file.stored_path), candidate_file.original_filename)
            for candidate_file in files
            if Path(candidate_file.stored_path).exists()
        ]
        candidate_count = len(session.exec(select(Candidate)).all())

        session.exec(delete(Application).where(Application.candidate_id.is_not(None)))
        session.exec(delete(MatchResult))
        session.exec(delete(CandidateSkill))
        session.exec(delete(CandidateFile))
        session.exec(delete(EmbeddingRecord).where(EmbeddingRecord.owner_type == "candidate"))
        session.exec(delete(IngestionLog).where(IngestionLog.entity_type == "candidate"))
        session.exec(delete(Candidate))
        session.commit()

    ingested = 0
    errors: list[str] = []
    for source_path, original_filename in sources:
        try:
            with Session(engine) as session:
                ingest_cv_file(
                    session=session,
                    source_path=source_path,
                    original_filename=original_filename,
                    source="openai_redeployment",
                    use_llm=True,
                )
                session.commit()
                ingested += 1
        except Exception as error:
            errors.append(f"{original_filename}: {error}")

    print(
        {
            "candidates_removed": candidate_count,
            "cv_files_attempted": len(sources),
            "cv_files_ingested": ingested,
            "errors": errors,
        }
    )


if __name__ == "__main__":
    main()
