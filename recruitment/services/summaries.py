import re


def summary_from_text(text: str, limit: int = 500) -> str:
    """Return a compact, deterministic fallback when no AI summary is available."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    sentence = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    return f"{clean[: limit - 1].rstrip()}…"
