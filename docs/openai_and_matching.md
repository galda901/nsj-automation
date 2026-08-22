# OpenAI and vector matching

OpenAI is used for two separate jobs:

- structured extraction from CV/job text;
- embeddings for vector retrieval.

The app falls back to deterministic local behavior if OpenAI is disabled or a
call fails.

## Configuration

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_CV_MODEL=gpt-4o-mini
OPENAI_MATCH_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=512
```

Never commit `.env`.

## CV extraction

When a CV is ingested, the app first extracts raw text from PDF/DOCX/TXT. Then,
if OpenAI is enabled, it asks for strict JSON fields such as:

- full name;
- email;
- phone;
- city/country;
- current title;
- seniority;
- total years experience;
- languages;
- summary;
- confidence.

CVs may be Hebrew or English.

If OpenAI extraction fails, the app uses the deterministic parser that mostly
extracts name/email and stores a summary snippet.

## Job extraction

Gmail job emails are parsed into draft `JobPosition` rows. The LLM is used when
enabled; otherwise the subject becomes the draft title and the body becomes the
description.

## Embeddings

Embeddings are stored in SQLite table `EmbeddingRecord`.

Matching embeddings are cached by owner and a SHA-256 hash of the matching
text. Re-running a match for an unchanged candidate or job reuses the stored
vector; a new embedding is created only when that matching text changes.

Each record stores:

- owner type: `candidate` or `job`;
- owner ID;
- source type;
- content hash;
- model name;
- dimensions;
- embedding JSON;
- preview text.

For a larger production system, this table should eventually move to Postgres
with pgvector.

## Matching flow

Current matching sequence:

```text
job
    -> ensure job embedding exists
    -> find closest candidate embeddings
    -> score top candidates deterministically
    -> store MatchResult
```

The deterministic score considers:

- shared keywords;
- seniority match;
- minimum years of experience coverage.

The matching comparison and scoring are local after the vectors exist, so
running matching does not call OpenAI. CV/job extraction and the initial
embedding for new or changed text may still use OpenAI.

## Important limitation

The app should never automatically reject candidates. It can explain likely fit
or gaps, but final decisions must remain human.
