# Database and files

SQLite is the local system of record.

Database file:

```text
data/sqlite/recruitment.db
```

Raw CVs:

```text
data/cv_raw
```

Extracted CV text:

```text
data/cv_text
```

Exports:

```text
data/exports
```

## Core tables

`Candidate`

Stores the candidate profile:

- name/email/phone;
- location;
- LinkedIn/GitHub/portfolio;
- current title;
- seniority;
- years of experience;
- languages;
- salary/notice/remote preferences;
- AI summary and parse confidence;
- currently selected referred job;
- status and timestamps.

`CandidateFile`

Stores file metadata:

- candidate ID;
- original filename;
- stored local path;
- extracted text path;
- file type;
- file hash.

`CandidateSkill`

Prepared for structured skills extracted from CVs.

`JobPosition`

Stores jobs:

- client name;
- public company name;
- title;
- description;
- location;
- remote policy;
- employment type;
- seniority;
- minimum years;
- salary range;
- status.

Gmail jobs are created as `draft`.

`JobRequirement`

Prepared for structured must-have/nice-to-have requirements.

`Application`

Prepared for candidate-job application tracking.

`MatchResult`

Stores job-candidate match scores and explanations.

`Interaction`

Prepared for notes, calls, emails, and recruiter/client interactions.

`EmbeddingRecord`

Stores local vector embeddings for jobs and candidates.

`NotificationOutbox`

Stores deduplicated Telegram match alerts and their delivery/retry state.

`WorkerState`

Stores the latest background-worker status, timestamps, summary, and error.

`IngestionLog`

Stores Gmail/manual ingestion events:

- source;
- label;
- message ID;
- attachment ID;
- entity type/ID;
- status;
- detail;
- timestamp.

## Initialization

Run:

```powershell
python -m scripts.init_db
```

This uses SQLModel `create_all`, which creates missing tables. It does not
perform destructive migrations.

## Backup

To back up the current local data, copy:

- `data/sqlite/recruitment.db`
- `data/cv_raw`
- `data/cv_text`
- `data/exports`
- `secrets` only if you intentionally want to preserve local credentials.

Treat these as sensitive because they contain candidate personal data.
