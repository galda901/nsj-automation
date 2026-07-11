# Dashboard guide

The dashboard is designed with two layers:

- simple recruiter pages first;
- developer/admin pages later.

## Home

Shows API connection status and general orientation.

## Candidates

This is the clean recruiter view.

Columns shown:

- Name
- Email
- City
- Profession
- Seniority
- Status
- CV path/action

Technical fields such as IDs, parse confidence, hashes, and raw summaries are
hidden here.

## Jobs

Use this page to create jobs manually and review draft jobs.

Gmail-imported jobs are created as `draft`, not `open`. They must be reviewed
and marked open before normal matching.

## Matches

Run candidate matching for open jobs.

The current flow retrieves candidate vectors first, then scores candidates using
deterministic and optional LLM-assisted explanation logic. It is not an automatic
rejection system.

## Inbox Intake

Two ingestion paths exist:

- manual CV upload;
- Gmail scan.

The Gmail scan now displays verbose progress:

- labels scanned;
- job messages found;
- CV messages found;
- attachments found;
- supported/unsupported attachments;
- duplicate skips;
- whether LLM parsing is enabled;
- per-message progress events.

The scan output intentionally avoids dumping full email bodies or CV text into
the UI.

## Dev pages

These are for engineering/debugging.

- `Dev - Raw Candidates`: raw candidate rows.
- `Dev - Vector DB`: local embedding records and rebuild action.
- `Dev - Ingestion Logs`: Gmail/manual ingestion logs.
- `Dev - Settings`: non-secret runtime configuration.

If something looks wrong in the simple pages, check the Dev pages before editing
the database directly.
