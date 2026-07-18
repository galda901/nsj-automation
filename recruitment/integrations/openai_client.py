from typing import Any, TypeVar

from pydantic import BaseModel

from recruitment.config import get_settings
from recruitment.schemas.candidate_schema import CandidateExtractionTemplate
from recruitment.schemas.job_schema import JobExtractionTemplate
from recruitment.schemas.match_schema import MatchExplanationTemplate


SchemaTemplate = TypeVar("SchemaTemplate", bound=BaseModel)


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


def _json_schema_completion(
    model: str,
    template: type[SchemaTemplate],
    system: str,
    user: str,
) -> dict[str, Any]:
    response = _client().beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=template,
        temperature=0,
    )
    message = response.choices[0].message
    if message.refusal:
        raise RuntimeError(f"OpenAI refused the extraction: {message.refusal}")
    if message.parsed is None:
        raise RuntimeError("OpenAI returned no structured extraction")
    return message.parsed.model_dump(mode="json")


def extract_candidate_from_cv(text: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_cv_model,
        CandidateExtractionTemplate,
        (
            "Extract recruitment candidate facts from CV text. The CV may be in "
            "English or Hebrew. Use only facts supported by the text. If unknown, use null. "
            "Return full_name, city, country, and current_title in standard Hebrew. "
            "Transliterate a Latin-script name to Hebrew, and translate a job title to Hebrew "
            "when needed. Format Israeli phone numbers as 05X-XXX-XXXX "
            "(mobile) or 0X-XXX-XXXX (landline). "
            "Write ai_summary as one concise recruiter-facing paragraph of 2-4 sentences; "
            "never copy the CV verbatim."
        ),
        text[:24000],
    )


def extract_job_from_email(subject: str, body: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_cv_model,
        JobExtractionTemplate,
        (
            "Extract a recruitment job record from an email. The email may be in "
            "English or Hebrew. Return the job title and location in standard Hebrew. "
            "Create a concise but complete job description and a short recruiter-facing "
            "summary in Hebrew."
        ),
        f"Subject: {subject}\n\nBody:\n{body[:24000]}",
    )


def explain_match(job_text: str, candidate_text: str) -> dict:
    settings = get_settings()
    return _json_schema_completion(
        settings.openai_match_model,
        MatchExplanationTemplate,
        (
            "Assess whether the candidate is likely to be a viable fit for the job. "
            "Return every text field in clear, recruiter-friendly Hebrew. Base the assessment "
            "only on the supplied facts. In explanation, give 2-4 concise sentences describing "
            "the relevant experience, skills, seniority, or location. Do not mention scores, "
            "embeddings, models, deterministic matching, or internal system logic. "
            "Do not make an automatic hiring or rejection decision."
        ),
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
