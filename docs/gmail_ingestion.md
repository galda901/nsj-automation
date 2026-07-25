# Gmail ingestion

Gmail ingestion reads only configured labels. It does not scan the whole inbox.

## Configuration

Relevant `.env` values:

```dotenv
GMAIL_ENABLED=true
GMAIL_JOBS_LABEL=משרות
GMAIL_CVS_LABEL=קורות חיים
GMAIL_LOOKBACK_DAYS=365
GMAIL_INCLUDE_CHILD_LABELS=true
GMAIL_CLIENT_SECRET_FILE=D:\Gal\Projects\General\nsj-automation\secrets\gmail_client_secret.json
GMAIL_TOKEN_FILE=D:\Gal\Projects\General\nsj-automation\secrets\gmail_token.json
```

`GMAIL_LOOKBACK_DAYS=365` means the scan considers messages from the last year.
Later, this can be changed back to a shorter window once daily automation is
stable.

`GMAIL_INCLUDE_CHILD_LABELS=true` means a configured label also matches nested
labels such as:

```text
קורות חיים/2026
משרות/לקוחות
```

## OAuth files

Two Gmail credential files exist:

- `gmail_client_secret.json`: downloaded from Google Cloud OAuth client.
- `gmail_token.json`: generated after approving Gmail access.

Only the token owner’s mailbox is scanned. If OAuth is approved with a private
Gmail account, the app scans that private mailbox. To scan
`nextstepjobs31@gmail.com`, OAuth must be approved as that account.

## Required Google Cloud settings

In Google Cloud:

1. OAuth client type should be `Desktop app`.
2. Gmail API must be enabled.
3. OAuth test users must include the Gmail account that will approve access.
4. Scope used by the app:

```text
https://www.googleapis.com/auth/gmail.readonly
```

The app currently uses read-only Gmail access.

## What the scan does

Jobs label:

```text
GMAIL_JOBS_LABEL
    -> read messages
    -> parse subject/body into JobPosition
    -> create draft job
    -> create job embedding
    -> write ingestion log
```

CV label:

```text
GMAIL_CVS_LABEL
    -> read messages
    -> inspect attachments
    -> accept PDF/DOCX/TXT
    -> ingest each supported CV
    -> parse candidate
    -> create candidate embedding
    -> write ingestion log
```

## Duplicate behavior

The app tries to skip duplicates using:

- Gmail message ID;
- Gmail attachment ID;
- CV file hash;
- candidate email.

Duplicate behavior is intentionally conservative. If the same candidate sends a
new CV with updated content, the file hash will differ and the new file can be
stored while the candidate row is reused by email.

## Verbose scan output

The scan result contains:

- `job_messages_found`
- `cv_messages_found`
- `attachments_found`
- `supported_attachments_found`
- `unsupported_attachments_skipped`
- `duplicates_skipped`
- `llm_job_parsing_enabled`
- `llm_cv_parsing_enabled`
- `available_labels`
- `events`
- `errors`

Use this to understand whether the issue is label matching, attachment type,
deduplication, parsing, or storage.

## Common failures

`Gmail OAuth files are not configured`

- `.env` paths are empty or point to missing files.
- The running API process has not been restarted after `.env` changes.

`Gmail API has not been used ... or it is disabled`

- Enable Gmail API in the Google Cloud project.

No messages found

- Label names may not match exactly.
- Messages may be older than `GMAIL_LOOKBACK_DAYS`.
- Messages may be under child labels; ensure `GMAIL_INCLUDE_CHILD_LABELS=true`.
- OAuth may be approved for the wrong mailbox.

No CVs ingested but CV messages found

- Attachments may be unsupported types.
- Emails may contain Drive links instead of direct attachments.
- CVs may be scanned PDFs; OCR is not implemented yet.
