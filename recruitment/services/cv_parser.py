import re

from recruitment.integrations.openai_client import extract_candidate_from_cv, openai_enabled
from recruitment.models.candidate import Candidate

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")


def parse_candidate_from_text(
    text: str, source: str | None = None, use_llm: bool = False
) -> Candidate:
    if use_llm and openai_enabled() and text.strip():
        try:
            payload = extract_candidate_from_cv(text)
            return Candidate(
                full_name=payload.get("full_name") or "Unknown Candidate",
                email=normalize_email(payload.get("email")),
                phone=payload.get("phone"),
                city=payload.get("city"),
                country=payload.get("country"),
                current_title=payload.get("current_title"),
                seniority=payload.get("seniority"),
                total_years_experience=payload.get("total_years_experience"),
                languages=payload.get("languages"),
                ai_summary=payload.get("ai_summary") or text[:2000],
                parse_confidence=float(payload.get("parse_confidence") or 0.75),
                source=source,
            )
        except Exception:
            pass

    clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
    email = extract_email(text)
    name = infer_name(clean_lines, email)
    return Candidate(
        full_name=name,
        email=email,
        source=source,
        ai_summary="\n".join(clean_lines)[:2000] or None,
        parse_confidence=0.35 if email else 0.2,
    )


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return normalize_email(match.group(0)) if match else None


def normalize_email(value: str | None) -> str | None:
    return value.strip().lower() if value else None


def infer_name(lines: list[str], email: str | None) -> str:
    for line in lines[:8]:
        candidate = line.strip(" |-•")
        if (
            1 < len(candidate.split()) <= 5
            and len(candidate) <= 100
            and "@" not in candidate
            and not any(char.isdigit() for char in candidate)
        ):
            return candidate
    if email:
        return email.split("@", 1)[0].replace(".", " ").replace("_", " ").title()
    return "Unknown Candidate"
