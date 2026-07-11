from sqlmodel import Session, select

from recruitment.models.candidate import Candidate


def find_candidate_by_email(session: Session, email: str | None) -> Candidate | None:
    if not email:
        return None
    return session.exec(select(Candidate).where(Candidate.email == email.lower())).first()
