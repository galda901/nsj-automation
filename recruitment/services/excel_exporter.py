from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.models.candidate import Candidate


def export_candidates_to_excel(session: Session) -> Path:
    output_dir = get_settings().export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = session.exec(select(Candidate)).all()
    frame = pd.DataFrame([candidate.model_dump() for candidate in candidates])
    output_path = output_dir / "candidates.xlsx"
    frame.to_excel(output_path, index=False)
    return output_path
