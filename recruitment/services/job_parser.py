from recruitment.integrations.openai_client import extract_job_from_email, openai_enabled
from recruitment.models.job import JobPosition
from recruitment.services.summaries import summary_from_text


def parse_job_from_email(subject: str, body: str) -> JobPosition:
    if openai_enabled() and (subject.strip() or body.strip()):
        try:
            payload = extract_job_from_email(subject, body)
            return JobPosition(
                client_name=payload.get("client_name") or "Unknown client",
                public_company_name=payload.get("public_company_name"),
                title=payload.get("title") or subject[:120] or "Draft job",
                description=payload.get("description") or body[:4000] or subject,
                summary=payload.get("summary")
                or summary_from_text(payload.get("description") or body or subject),
                location=payload.get("location"),
                remote_policy=payload.get("remote_policy"),
                employment_type=payload.get("employment_type"),
                seniority=payload.get("seniority"),
                min_years_experience=payload.get("min_years_experience"),
                salary_range=payload.get("salary_range"),
                status="draft",
            )
        except Exception:
            pass
    return JobPosition(
        client_name="Unknown client",
        title=subject[:120] or "Draft job",
        description=body[:4000] or subject or "Imported from Gmail",
        summary=summary_from_text(body or subject or "Imported from Gmail"),
        status="draft",
    )
