@echo off
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"
start "NSJ Recruitment API" /min "%PROJECT_ROOT%.venv\Scripts\python.exe" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8002
ping 127.0.0.1 -n 4 >nul
start "NSJ Recruitment Dashboard" /min "%PROJECT_ROOT%.venv\Scripts\python.exe" -m streamlit run apps\dashboard\streamlit_app.py --server.headless true --server.port 8501
ping 127.0.0.1 -n 6 >nul
start "" "http://localhost:8501"
