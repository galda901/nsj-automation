# Local runbook

This is the practical guide for starting, stopping, and verifying the local app.

## Start the app

For a non-technical user, use the Desktop shortcut:

```text
NSJ Recruitment
```

Or double-click from the project:

```text
Start NSJ Recruitment.cmd
```

It starts:

- FastAPI on `127.0.0.1:8002`
- Streamlit on `localhost:8501`
- browser at `http://localhost:8501`

## Manual start

Open PowerShell in the project folder:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8002
```

In a second PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run apps\dashboard\streamlit_app.py
```

## Verify API health

Open:

```text
http://127.0.0.1:8002/health
```

Expected:

```json
{"status": "ok"}
```

For developer settings:

```text
http://127.0.0.1:8002/dev/settings
```

This confirms OpenAI/Gmail configuration without showing secrets.

## Useful scripts

Initialize or update SQLite tables:

```powershell
python -m scripts.init_db
```

Run Gmail ingestion from terminal:

```powershell
python -m scripts.ingest_gmail_daily
```

Set up Gmail OAuth token:

```powershell
python -u -m scripts.setup_gmail_oauth
```

Rebuild embeddings for existing candidates/jobs:

```powershell
python -m scripts.rebuild_embeddings
```

Export candidates to Excel:

```powershell
python -m scripts.export_candidates_to_excel
```

Run checks:

```powershell
python -m ruff check .
python -m pytest -q
```

## Stop the app

If you started it manually, close the PowerShell windows or press `Ctrl+C`.

If started by shortcut, the windows may be minimized. You can either close the
terminal windows or restart the PC. For debugging, find listeners:

```powershell
netstat -ano | Select-String ':8002|:8501'
```

Then stop a known process ID:

```powershell
Stop-Process -Id <PID> -Force
```

Do not randomly stop unknown processes unless you know they belong to this app.
