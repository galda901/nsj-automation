# Background worker and Telegram alerts

The worker polls Gmail, ingests new messages, matches changed entities, creates
Telegram outbox records, and retries delivery. It is safe to run repeatedly:
Gmail ingestion uses the existing message/attachment deduplication logs, and
each candidate/job/recipient notification has a unique key.

## Safe configuration

Start with:

```dotenv
WORKER_POLL_SECONDS=300
TELEGRAM_ENABLED=false
TELEGRAM_DRY_RUN=true
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

In this mode the worker creates and displays pending notifications but does not
call Telegram. Telegram uses a chat ID, not a phone number. The recipient must
first open the bot and send it a message so Telegram exposes the private chat.

Create a bot with Telegram's `@BotFather`, save the bot token, then send the bot
any message. Retrieve the chat ID from Telegram's `getUpdates` response and set
`TELEGRAM_CHAT_ID`. Set `TELEGRAM_ENABLED=true` only after a dry-run review and
keep `TELEGRAM_DRY_RUN=true` until the outbox is confirmed.

## Run once

```powershell
.\.venv\Scripts\python -m scripts.run_worker --once
```

The command prints a concise Telegram-focused summary and pending message
previews. Use `--json` when the full diagnostic result is needed. Worker status
and notification history are also available in the development dashboard page
and through:

```text
/dev/worker-status
/dev/telegram-notifications
```

Only qualifying matches are placed in the outbox: the existing match threshold
and hard-filter flag must both pass. Repeated polls use the unique
Telegram-chat/candidate/job key and do not create another notification.

## Run continuously

```powershell
.\.venv\Scripts\python -m scripts.run_worker
```

The worker uses `data/worker.lock` to prevent two local instances from running
at the same time. A stale `sending` notification is returned to the retry queue
after its lease expires.

## Windows Task Scheduler

Create a task that runs at system startup or user logon:

The repository includes a registration helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_worker_task.ps1
```

Or create it manually with these values:

- Program: `D:\Gal\Projects\General\nsj-automation\.venv\Scripts\python.exe`
- Arguments: `-m scripts.run_worker`
- Start in: `D:\Gal\Projects\General\nsj-automation`
- Configure restart-on-failure and run whether the user is logged on or not.

The task account must be able to read the Gmail OAuth files, the `.env` file,
and the SQLite/data directories.

## Retry behavior

Each notification starts as `pending`. Delivery claims it as `sending`, then
marks it `sent` after a provider message ID is returned. Failures return to
`pending` with exponential backoff until `TELEGRAM_MAX_ATTEMPTS`; after that
they become `failed` and remain visible for manual investigation.

The worker sends one notification per candidate/job/Telegram chat pair. It does not
resend a notification just because a later matching run recalculates the score.
