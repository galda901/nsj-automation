# NSJ Recruitment

Local MVP for a human-in-the-loop recruitment workflow. It provides a FastAPI
backend, SQLite persistence, a Streamlit dashboard, manual CV ingestion, Gmail
intake, Excel export, OpenAI-assisted parsing, and vector-first matching.

Full project documentation starts at [docs/README.md](docs/README.md).

## Windows setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m scripts.init_db
```

Start the API in one PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8002
```

Start the dashboard in a second terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run apps\dashboard\streamlit_app.py
```

Open the dashboard at <http://localhost:8501> and API documentation at
<http://127.0.0.1:8002/docs>.

In VS Code, open **Run and Debug** and select **Recruitment MVP** to start both
processes. The workspace is already configured to use `.venv` and discover pytest.

For a non-technical user, double-click `Start NSJ Recruitment.cmd`. It starts the
API, starts Streamlit, and opens the dashboard in the browser.

## Useful commands

```powershell
python -m pytest
python -m ruff check .
python -m scripts.export_candidates_to_excel
python -m scripts.ingest_gmail_daily
python -m scripts.rebuild_embeddings
python -m scripts.setup_gmail_oauth
```

## OpenAI and Gmail

OpenAI is enabled with:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=...
```

Gmail ingestion only scans the configured labels:

```dotenv
GMAIL_ENABLED=true
GMAIL_JOBS_LABEL=משרות
GMAIL_CVS_LABEL=קורות חיים
GMAIL_CLIENT_SECRET_FILE=path\to\client_secret.json
GMAIL_TOKEN_FILE=path\to\gmail_token.json
```

The first Gmail run opens a local OAuth browser flow and writes the token file.
Job emails become draft jobs; CV emails ingest supported attachments.
If dashboard-based Gmail scan does not open a browser, run
`python -m scripts.setup_gmail_oauth` once from PowerShell.

Raw CVs, extracted text, SQLite files, exports, `.env`, and `.venv` are excluded
from Git. Do not commit real candidate data or API credentials.

## Current boundaries

- PDF support is text extraction only; scanned documents need OCR.
- OpenAI calls fall back to local deterministic behavior if disabled or failing.
- Matching retrieves candidates by local SQLite vectors first, then scores them;
  it still does not make automated hiring or rejection decisions.
- Outlook, ads, and production authentication are later integrations.
