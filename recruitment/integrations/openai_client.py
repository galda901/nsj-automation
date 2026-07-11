import json
from typing import Any

from recruitment.config import get_settings


CV_SCHEMA: dict[str, Any] = {
    "name": "candidate_cv_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "full_name": {"type": "string"},
            "email": {"type": ["string", "null"]},
            "phone": {"type": ["string", "null"]},
            "city": {"type": ["string", "null"]},
            "country": {"type": ["string", "null"]},
            "current_title": {"type": ["string", "null"]},
            "seniority": {"type": ["string", "null"]},
            "total_years_experience": {"type": ["number", "null"]},
            "languages": {"type": ["string", "null"]},
            "ai_summary": {"type": ["string", "null"]},
            "parse_confidence": {"type": "number"},
        },
        "required": [
            "full_name",
            "email",
            "phone",
            "city",
            "country",
            "current_title",
            "seniority",
            "total_years_experience",
            "languages",
            "ai_summary",
            "parse_confidence",
        ],
    },
    "strict": True,
}

JOB_SCHEMA: dict[str, Any] = {
    "name": "job_email_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "client_name": {"type": "string"},
            "public_company_name": {"type": ["string", "null"]},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "location": {"type": ["string", "null"]},
            "remote_policy": {"type": ["string", "null"]},
            "employment_type": {"type": ["string", "null"]},
            "seniority": {"type": ["string", "null"]},
            "min_years_experience": {"type": ["number", "null"]},
            "salary_range": {"type": ["string", "null"]},
        },
        "required": [
            "client_name",
            "public_company_name",
            "title",
            "description",
            "location",
            "remote_policy",
            "employment_type",
            "seniority",
            "min_years_experience",
            "salary_range",
        ],
    },
    "strict": True,
}

MATCH_SCHEMA: dict[str, Any] = {
    "name": "candidate_job_match",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ai_score": {"type": "number"},
            "explanation": {"type": "string"},
            "risks": {"type": "string"},
            "missing_requirements": {"type": "string"},
        },
        "required": ["ai_score", "explanation", "risks", "missing_requirements"],
    },
    "strict": True,
}


def openai_enabled() -> bool:
    settings = get_settings()
    return settings.llm_provider.casefold() == "openai" and bool(settings.openai_api_key)


def _client():
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Install the openai package to use OpenAI features") from error
    return OpenAI(api_key=settings.openai_api_key)


def _json_schema_completion(model: str, schema: dict[str, Any], system: str, user: str) -> dict:
    response = _client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_schema", "json_schema": schema},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content or "{}")


def extract_candidate_from_cv(text: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_cv_model,
        CV_SCHEMA,
        (
            "Extract recruitment candidate facts from CV text. The CV may be in "
            "English or Hebrew. Use only facts supported by the text. If unknown, use null."
        ),
        text[:24000],
    )


def extract_job_from_email(subject: str, body: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_cv_model,
        JOB_SCHEMA,
        (
            "Extract a recruitment job record from an email. The email may be in "
            "English or Hebrew. Create a concise but complete job description."
        ),
        f"Subject: {subject}\n\nBody:\n{body[:24000]}",
    )


def explain_match(job_text: str, candidate_text: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_match_model,
        MATCH_SCHEMA,
        "Score and explain candidate fit for the job. Do not reject automatically.",
        f"JOB:\n{job_text[:12000]}\n\nCANDIDATE:\n{candidate_text[:12000]}",
    )


def create_embedding(text: str) -> list[float]:
    settings = get_settings()
    response = _client().embeddings.create(
        model=settings.openai_embedding_model,
        input=text[:32000],
        dimensions=settings.openai_embedding_dimensions,
    )
    return list(response.data[0].embedding)
