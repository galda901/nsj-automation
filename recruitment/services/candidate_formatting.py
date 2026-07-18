"""Canonical display formats for candidate details."""

import re


_CITY_NAMES = {
    "tel aviv": "תל אביב-יפו",
    "tel aviv-yafo": "תל אביב-יפו",
    "תל אביב": "תל אביב-יפו",
    "תל אביב יפו": "תל אביב-יפו",
    "jerusalem": "ירושלים",
    "haifa": "חיפה",
    "beer sheva": "באר שבע",
    "be'er sheva": "באר שבע",
    "petah tikva": "פתח תקווה",
    "petach tikva": "פתח תקווה",
    "rishon lezion": "ראשון לציון",
    "rishon le zion": "ראשון לציון",
    "ramat gan": "רמת גן",
    "herzliya": "הרצליה",
    "herzlia": "הרצליה",
    "kiryat gat": "קריית גת",
    "kiryat shmona": "קריית שמונה",
    "netivot": "נתיבות",
    "rehovot": "רחובות",
    "modiin": "מודיעין-מכבים-רעות",
    "modi'in": "מודיעין-מכבים-רעות",
    "shoham": "שוהם",
}

_COUNTRY_NAMES = {
    "israel": "ישראל",
    "state of israel": "ישראל",
    "ישראל": "ישראל",
    "united states": "ארצות הברית",
    "united states of america": "ארצות הברית",
    "usa": "ארצות הברית",
    "u.s.a.": "ארצות הברית",
    "uk": "הממלכה המאוחדת",
    "united kingdom": "הממלכה המאוחדת",
    "england": "הממלכה המאוחדת",
    "russia": "רוסיה",
    "ukraine": "אוקראינה",
    "germany": "גרמניה",
    "france": "צרפת",
}


def normalize_phone(value: str | None) -> str | None:
    """Return a consistent Israeli phone display format when possible."""
    if not value or not value.strip():
        return None
    cleaned = " ".join(value.strip().split())
    if cleaned.upper() in {"05X-XXX-XXXX", "0X-XXX-XXXX"}:
        return None
    # Some right-to-left source documents place an Israeli prefix after the
    # remaining digits (for example, ``6675676-050``). Put it back in order.
    reversed_israeli_number = re.fullmatch(r"(\d{7})-(05\d)", cleaned)
    digits = (
        f"{reversed_israeli_number.group(2)}{reversed_israeli_number.group(1)}"
        if reversed_israeli_number
        else re.sub(r"\D", "", cleaned)
    )
    if digits.startswith("972"):
        digits = f"0{digits[3:]}"
    if len(digits) == 10 and digits.startswith("05"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9 and digits.startswith("0"):
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    return cleaned


def normalize_city(value: str | None) -> str | None:
    return _normalize_named_value(value, _CITY_NAMES)


def normalize_country(value: str | None) -> str | None:
    return _normalize_named_value(value, _COUNTRY_NAMES)


def normalize_current_title(value: str | None) -> str | None:
    """Clean whitespace; OpenAI is instructed to return the title in Hebrew."""
    return " ".join(value.strip().split()) if value and value.strip() else None


def _normalize_named_value(value: str | None, translations: dict[str, str]) -> str | None:
    if not value or not value.strip():
        return None
    cleaned = " ".join(value.strip().split())
    return translations.get(cleaned.casefold(), cleaned)
