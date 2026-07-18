"""Re-extract legacy non-Hebrew candidate names and titles with the current OpenAI prompt."""

from pathlib import Path

from sqlmodel import Session, select

from recruitment.database import engine
from recruitment.models.candidate import Candidate, CandidateFile, now_utc
from recruitment.services.cv_parser import parse_candidate_from_text


def _has_hebrew(value: str | None) -> bool:
    return bool(value) and any("\u0590" <= character <= "\u05ff" for character in value)


def main() -> None:
    refreshed = 0
    with Session(engine) as session:
        candidates = list(session.exec(select(Candidate)).all())
        for candidate in candidates:
            needs_hebrew_name = not _has_hebrew(candidate.full_name)
            needs_hebrew_title = bool(candidate.current_title) and not _has_hebrew(
                candidate.current_title
            )
            if not needs_hebrew_name and not needs_hebrew_title:
                continue
            candidate_file = session.exec(
                select(CandidateFile)
                .where(CandidateFile.candidate_id == candidate.id)
                .order_by(CandidateFile.uploaded_at.desc())
            ).first()
            text_path = Path(candidate_file.extracted_text_path or "") if candidate_file else None
            if text_path is None or not text_path.exists():
                continue
            parsed = parse_candidate_from_text(
                text_path.read_text(encoding="utf-8"), source=candidate.source, use_llm=True
            )
            for field in (
                "full_name",
                "phone",
                "city",
                "country",
                "current_title",
                "seniority",
                "total_years_experience",
                "languages",
                "ai_summary",
                "parse_confidence",
            ):
                value = getattr(parsed, field)
                if field == "full_name" and not _has_hebrew(value):
                    continue
                if field == "current_title" and value and not _has_hebrew(value):
                    continue
                if value is not None:
                    setattr(candidate, field, value)
            candidate.updated_at = now_utc()
            session.add(candidate)
            refreshed += 1
        session.commit()
    print({"candidates_refreshed": refreshed})


if __name__ == "__main__":
    main()
