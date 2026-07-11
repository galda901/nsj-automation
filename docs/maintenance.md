# Maintenance and troubleshooting

This page collects common operational tasks and failure modes.

## Restart after config changes

`.env` is read when the Python process starts. If you edit `.env`, restart the
API and dashboard.

Use the desktop shortcut:

```text
NSJ Recruitment
```

Or run:

```powershell
.\Start NSJ Recruitment.cmd
```

## Check active ports

```powershell
netstat -ano | Select-String ':8002|:8501'
```

The active API should be on `8002`. The dashboard should be on `8501`.

Older debug APIs may still be listening on `8000` or `8001`. The dashboard code
now reads `DASHBOARD_API_BASE_URL` from `.env`, so it should call `8002`.

## Gmail scan finds zero messages

Check the verbose scan result:

- Are `available_labels` correct?
- Do `job_messages_found` or `cv_messages_found` show anything?
- Are attachments unsupported?
- Are duplicates being skipped?
- Is the OAuth token for the intended mailbox?

If labels are nested, ensure:

```dotenv
GMAIL_INCLUDE_CHILD_LABELS=true
```

If messages are old, increase:

```dotenv
GMAIL_LOOKBACK_DAYS=365
```

## Gmail token for wrong account

Delete:

```text
secrets\gmail_token.json
```

Run:

```powershell
python -u -m scripts.setup_gmail_oauth
```

Approve with the correct Gmail account.

## Gmail API disabled

Enable Gmail API in the Google Cloud project used by the OAuth client.

## OpenAI failures

If parsing or embeddings fail:

- check `OPENAI_API_KEY`;
- confirm `LLM_PROVIDER=openai`;
- check API billing/limits;
- inspect Dev settings;
- try manual upload again.

The app should fall back to deterministic parsing/embedding when possible.

## Scanned PDFs

Current PDF extraction works only for text-based PDFs. Scanned image PDFs need
OCR, which is not implemented yet.

## Secrets

Never commit:

- `.env`
- `secrets`
- `scripts/secrets`
- raw CV data
- SQLite database files

The `.gitignore` already excludes these local-sensitive paths.

## Regular checks

Before a development session ends:

```powershell
python -m compileall -q apps recruitment scripts tests
python -m ruff check .
python -m pytest -q
```

## When changing database models

For the current MVP, `create_all` creates missing tables but does not alter
existing columns safely. If model changes become frequent, add Alembic migrations
before real production use.

## Production hardening backlog

Before using this with large volumes or multiple users:

- add authentication;
- move SQLite to Postgres;
- move vectors to pgvector;
- add background worker queue;
- add OCR;
- add encrypted backups;
- add audit log views;
- add role-based access;
- define data retention/deletion policy.
