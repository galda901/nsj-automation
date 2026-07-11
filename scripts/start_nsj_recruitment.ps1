param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ApiPort = "8002"
$ApiUrl = "http://127.0.0.1:$ApiPort/health"
$DashboardUrl = "http://localhost:8501"

function Test-HttpOk {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Start-NsjProcess {
    param(
        [string]$Name,
        [string]$Arguments,
        [string]$LogName
    )

    $logDir = Join-Path $ProjectRoot "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $outLog = Join-Path $logDir "$LogName.out.log"
    $errLog = Join-Path $logDir "$LogName.err.log"

    Start-Process `
        -FilePath $Python `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Minimized `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        | Out-Null

    Write-Host "Started $Name"
}

if (-not (Test-Path $Python)) {
    Write-Host "Python virtual environment was not found:"
    Write-Host $Python
    Write-Host ""
    Write-Host "Open PowerShell in the project and run:"
    Write-Host "python -m venv .venv"
    Write-Host ".\.venv\Scripts\python -m pip install -r requirements.txt"
    Read-Host "Press Enter to close"
    exit 1
}

Set-Location $ProjectRoot

if (-not (Test-HttpOk $ApiUrl)) {
    Start-NsjProcess `
        -Name "FastAPI" `
        -Arguments "-m uvicorn apps.api.main:app --host 127.0.0.1 --port $ApiPort" `
        -LogName "api"
}
else {
    Write-Host "FastAPI already running"
}

$dashboardRunning = $false
try {
    $connection = Test-NetConnection -ComputerName "127.0.0.1" -Port 8501 -InformationLevel Quiet -WarningAction SilentlyContinue
    $dashboardRunning = [bool]$connection
}
catch {
    $dashboardRunning = $false
}

if (-not $dashboardRunning) {
    Start-NsjProcess `
        -Name "Streamlit" `
        -Arguments "-m streamlit run apps\dashboard\streamlit_app.py --server.headless true --server.port 8501" `
        -LogName "streamlit"
}
else {
    Write-Host "Streamlit already running"
}

Write-Host "Waiting for NSJ Recruitment to become ready..."
Start-Sleep -Seconds 4

if (-not $NoBrowser) {
    Start-Process $DashboardUrl
}

Write-Host ""
Write-Host "NSJ Recruitment is starting."
Write-Host "Dashboard: $DashboardUrl"
Write-Host "Logs: $ProjectRoot\logs"
Start-Sleep -Seconds 3
