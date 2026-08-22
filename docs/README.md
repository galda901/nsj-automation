# NSJ Recruitment documentation

This folder explains the local recruitment automation environment: what it does,
how the pieces fit together, how to operate it day to day, and how to maintain it
without accidentally breaking candidate data or credentials.

Recommended reading order:

1. [System overview](architecture.md)
2. [Local runbook](runbook.md)
3. [Dashboard guide](dashboard_guide.md)
4. [Gmail ingestion](gmail_ingestion.md)
5. [OpenAI and vector matching](openai_and_matching.md)
6. [Background worker and Telegram alerts](background_worker.md)
7. [Database and files](database_schema.md)
8. [Maintenance and troubleshooting](maintenance.md)

The current system is intentionally local-first: it runs on this PC, stores data
in SQLite plus local folders, and keeps all decisions human-in-the-loop.
