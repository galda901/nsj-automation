# System overview

NSJ Recruitment is a local recruitment operations platform. It ingests jobs and
CVs, parses them, stores structured candidate/job data, creates vector records
for matching, and exposes everything through a Streamlit dashboard.

## Main components

```text
Streamlit dashboard
        |
        | HTTP
        v
FastAPI backend
        |
        +--> SQLModel / SQLite database
        +--> local CV files and extracted text
        +--> OpenAI extraction and embeddings
        +--> Gmail API ingestion
```

The important design rule is that Streamlit should stay thin. It displays data
and sends API requests, but the business logic belongs in backend services under
`recruitment/services`.

## Applications

- `apps/api/main.py` starts the FastAPI backend.
- `apps/dashboard/streamlit_app.py` starts the Streamlit dashboard.
- `apps/dashboard/pages` contains the user-facing and developer pages.
- `apps/worker/worker.py` is still a placeholder for future background workers.

## Domain package

The `recruitment` package contains reusable business code:

- `models`: SQLModel database tables.
- `schemas`: API input/output validation models.
- `services`: ingestion, parsing, matching, embedding, export logic.
- `integrations`: external APIs such as Gmail and OpenAI.
- `utils`: small helpers for IDs and files.

## Data flow

Manual CV upload:

```text
Dashboard upload
    -> FastAPI /ingestion/cv
    -> save raw CV under data/cv_raw
    -> extract text under data/cv_text
    -> parse candidate, using OpenAI if enabled
    -> deduplicate by email/file hash
    -> store Candidate + CandidateFile
    -> create/update candidate embedding
```

Gmail scan:

```text
Dashboard "Scan Gmail now" or scripts.ingest_gmail_daily
    -> Gmail labels from .env
    -> job emails become draft jobs
    -> CV email attachments become candidate records/files
    -> ingestion logs record successes, skips, and errors
```

Matching:

```text
Open job
    -> job embedding
    -> retrieve closest candidate embeddings
    -> deterministic scoring
    -> optional OpenAI explanation/re-ranking
    -> MatchResult rows
```

## Current ports

- Dashboard: `http://localhost:8501`
- API: `http://127.0.0.1:8002`
- API docs: `http://127.0.0.1:8002/docs`

Older API processes may still exist on `8000` or `8001` from earlier debugging.
The active configuration now points to `8002`.

## Human-in-the-loop principle

The system can suggest, parse, score, and explain. It must not automatically
reject candidates or submit candidates to clients without human review.
