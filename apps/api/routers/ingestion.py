from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from recruitment.config import get_settings
from recruitment.database import get_session
from recruitment.services.cv_ingestion import ingest_cv_file
from recruitment.services.cv_text_extractor import SUPPORTED_SUFFIXES
from recruitment.services.email_ingestion import ingest_gmail_daily

router = APIRouter()
settings = get_settings()


@router.post("/cv", status_code=status.HTTP_201_CREATED)
def upload_cv(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Supported types: PDF, DOCX, TXT")

    if file.size and file.size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CV exceeds the 15 MB limit")

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(file.file.read())
            temporary_path = Path(temporary_file.name)
        if temporary_path.stat().st_size > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="CV exceeds the 15 MB limit")
        candidate_id, candidate_file_id = ingest_cv_file(
            session=session,
            source_path=temporary_path,
            original_filename=file.filename or "unknown",
            source="manual_upload",
            use_llm=True,
        )
        session.commit()
        return {
            "candidate_id": candidate_id,
            "candidate_file_id": candidate_file_id,
            "filename": file.filename or "unknown",
            "status": "ingested",
        }
    except HTTPException:
        session.rollback()
        raise
    except Exception as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=f"Could not process CV: {error}") from error
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
        file.file.close()


@router.post("/gmail/daily")
def run_gmail_ingestion(session: Session = Depends(get_session)) -> dict:
    try:
        result = ingest_gmail_daily(session)
        session.commit()
        return result
    except Exception as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
