param(
    [string]$TaskName = "NSJ Recruitment Worker"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Virtual-environment Python was not found at $PythonPath"
}

$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "-m scripts.run_worker" `
    -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Poll Gmail, match recruitment records, and process Telegram alerts." `
    -Force

Write-Host "Registered scheduled task '$TaskName'."
