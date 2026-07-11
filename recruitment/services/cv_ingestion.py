from pathlib import Path

from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.models.candidate import CandidateFile
from recruitment.services.candidate_deduper import find_candidate_by_email
from recruitment.services.cv_parser import parse_candidate_from_text
from recruitment.services.cv_text_extractor import extract_text_from_file
from recruitment.services.embeddings import upsert_embedding
from recruitment.utils.files import sha256_file
from recruitment.utils.ids import new_id


def ingest_cv_file(
    session: Session,
    source_path: Path,
    original_filename: str,
    source: str,
    use_llm: bool = True,
) -> tuple[str, str]:
    settings = get_settings()
    settings.ensure_local_directories()
    suffix = source_path.suffix.lower()
    file_id = new_id("cvfile")
    stored_path = settings.cv_raw_dir / f"{file_id}{suffix}"
    text_path = settings.cv_text_dir / f"{file_id}.txt"
    stored_path.write_bytes(source_path.read_bytes())

    file_hash = sha256_file(stored_path)
    duplicate_file = session.exec(
        select(CandidateFile).where(CandidateFile.file_hash == file_hash)
    ).first()
    if duplicate_file and duplicate_file.candidate_id:
        stored_path.unlink(missing_ok=True)
        return duplicate_file.candidate_id, duplicate_file.id

    extracted_text = extract_text_from_file(stored_path)
    if not extracted_text.strip():
        raise ValueError("No text was found; scanned PDFs will need OCR support")
    text_path.write_text(extracted_text, encoding="utf-8")
    parsed_candidate = parse_candidate_from_text(
        extracted_text, source=source, use_llm=use_llm
    )
    candidate = find_candidate_by_email(session, parsed_candidate.email)
    if candidate is None:
        candidate = parsed_candidate
        session.add(candidate)
        session.flush()
    else:
        for field in (
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
            value = getattr(parsed_candidate, field)
            if value and not getattr(candidate, field):
                setattr(candidate, field, value)

    candidate_file = CandidateFile(
        id=file_id,
        candidate_id=candidate.id,
        original_filename=original_filename,
        stored_path=str(stored_path),
        extracted_text_path=str(text_path),
        file_type=suffix.lstrip("."),
        file_hash=file_hash,
    )
    session.add(candidate_file)
    upsert_embedding(
        session,
        owner_type="candidate",
        owner_id=candidate.id,
        source_type="cv_text",
        text=f"{candidate.full_name}\n{candidate.current_title or ''}\n{extracted_text}",
    )
    return candidate.id, candidate_file.id
