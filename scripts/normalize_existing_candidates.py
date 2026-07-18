"""Apply the canonical contact and location formats to existing candidate records."""

from sqlmodel import Session, select

from recruitment.database import engine
from recruitment.models.candidate import Candidate
from recruitment.services.candidate_formatting import (
    normalize_city,
    normalize_country,
    normalize_current_title,
    normalize_phone,
)


def main() -> None:
    updated = 0
    with Session(engine) as session:
        for candidate in session.exec(select(Candidate)):
            previous = (
                candidate.phone,
                candidate.city,
                candidate.country,
                candidate.current_title,
            )
            candidate.phone = normalize_phone(candidate.phone)
            candidate.city = normalize_city(candidate.city)
            candidate.country = normalize_country(candidate.country)
            candidate.current_title = normalize_current_title(candidate.current_title)
            if previous != (
                candidate.phone,
                candidate.city,
                candidate.country,
                candidate.current_title,
            ):
                session.add(candidate)
                updated += 1
        session.commit()
    print({"candidates_normalized": updated})


if __name__ == "__main__":
    main()
