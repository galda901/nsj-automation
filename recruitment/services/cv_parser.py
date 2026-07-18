import re

from recruitment.integrations.openai_client import extract_candidate_from_cv, openai_enabled
from recruitment.models.candidate import Candidate
from recruitment.services.candidate_formatting import (
    normalize_city,
    normalize_country,
    normalize_current_title,
    normalize_phone,
)

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?972|0)[\s.-]*\d(?:[\s.-]*\d){7,9}(?!\d)")
NAME_LABEL_PATTERN = re.compile(r"(?:^|\b)(?:name|full name|שם)\s*[:\-]\s*(.+)", re.IGNORECASE)

NAME_HEADINGS = {
    "resume",
    "curriculum vitae",
    "cv",
    "experience",
    "work experience",
    "professional experience",
    "education",
    "skills",
    "about me",
    "profile",
    "personal details",
    "קורות חיים",
    "ניסיון",
    "ניסיון מקצועי",
    "השכלה",
    "כישורים",
    "פרופיל מקצועי",
    "פרטים אישיים",
}
TITLE_WORDS = (
    "manager",
    "engineer",
    "analyst",
    "developer",
    "designer",
    "technician",
    "coordinator",
    "director",
    "consultant",
    "accountant",
    "pmo",
    "מנהל",
    "מנהלת",
    "מהנדס",
    "מהנדסת",
    "טכנאי",
    "רכז",
    "רכזת",
    "אנליסט",
)
KNOWN_CITIES = (
    "Tel Aviv",
    "Jerusalem",
    "Haifa",
    "Beer Sheva",
    "Petah Tikva",
    "Rishon LeZion",
    "Ramat Gan",
    "Herzliya",
    "Kiryat Gat",
    "Kiryat Shmona",
    "Netivot",
    "Rehovot",
    "Modiin",
    "Shoham",
    "נתיבות",
    "תל אביב",
    "ירושלים",
    "חיפה",
    "פתח תקווה",
    "רחובות",
    "קריית גת",
    "שוהם",
)


def parse_candidate_from_text(
    text: str, source: str | None = None, use_llm: bool = False
) -> Candidate:
    if use_llm and openai_enabled() and text.strip():
        try:
            payload = extract_candidate_from_cv(text)
            return Candidate(
                full_name=payload.get("full_name") or "Unknown Candidate",
                email=normalize_email(payload.get("email")),
                phone=normalize_phone(payload.get("phone")),
                city=normalize_city(payload.get("city")),
                country=normalize_country(payload.get("country")),
                current_title=normalize_current_title(payload.get("current_title")),
                seniority=payload.get("seniority"),
                total_years_experience=payload.get("total_years_experience"),
                languages=payload.get("languages"),
                ai_summary=payload.get("ai_summary"),
                parse_confidence=float(payload.get("parse_confidence") or 0.75),
                source=source,
            )
        except Exception:
            pass

    clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
    email = extract_email(text)
    return Candidate(
        full_name=infer_name(clean_lines, email),
        email=email,
        phone=extract_phone(text),
        city=extract_city(text),
        current_title=normalize_current_title(infer_current_title(clean_lines)),
        source=source,
        # A fallback parser must never present raw CV text as an AI summary.
        ai_summary=None,
        parse_confidence=0.35 if email else 0.2,
    )


def extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return normalize_email(match.group(0)) if match else None


def extract_phone(text: str) -> str | None:
    match = PHONE_PATTERN.search(text.replace("+ 9 7 2", "+972"))
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if digits.startswith("972"):
        digits = f"0{digits[3:]}"
    return normalize_phone(digits) if len(digits) >= 9 else None


def extract_city(text: str) -> str | None:
    folded = collapse_spaced_words(text).casefold()
    for city in KNOWN_CITIES:
        if city.casefold() in folded:
            return normalize_city(city)
    return None


def normalize_email(value: str | None) -> str | None:
    return value.strip().lower() if value else None


def infer_name(lines: list[str], email: str | None) -> str:
    for line in lines[:12]:
        labelled = NAME_LABEL_PATTERN.search(line)
        if labelled and is_name_candidate(labelled.group(1)):
            return normalize_name(labelled.group(1))
    for line in lines[:12]:
        for segment in re.split(r"[|•]", line):
            if is_name_candidate(segment):
                return normalize_name(segment)
    if email:
        return email.split("@", 1)[0].replace(".", " ").replace("_", " ").title()
    return "Unknown Candidate"


def infer_current_title(lines: list[str]) -> str | None:
    for line in lines[:15]:
        candidate = " ".join(line.split())
        if (
            3 <= len(candidate) <= 140
            and not any(char.isdigit() for char in candidate)
            and "@" not in candidate
            and any(word in candidate.casefold() for word in TITLE_WORDS)
        ):
            return candidate
    return None


def is_name_candidate(value: str) -> bool:
    candidate = normalize_name(value.strip(" |-•:"))
    folded = candidate.casefold()
    words = candidate.split()
    return (
        1 < len(words) <= 5
        and len(candidate) <= 80
        and folded not in NAME_HEADINGS
        and "@" not in candidate
        and not any(char.isdigit() for char in candidate)
        and not any(token in folded for token in NAME_HEADINGS)
        and any(char.isalpha() for char in candidate)
    )


def normalize_name(value: str) -> str:
    groups = re.split(r"\s{2,}", value.strip())
    normalized_groups = []
    for group in groups:
        letters = group.split()
        normalized_groups.append("".join(letters) if len(letters) > 1 and all(len(letter) == 1 for letter in letters) else group)
    return " ".join(" ".join(normalized_groups).split())


def collapse_spaced_words(value: str) -> str:
    return re.sub(
        r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b",
        lambda match: match.group(0).replace(" ", ""),
        value,
    )
