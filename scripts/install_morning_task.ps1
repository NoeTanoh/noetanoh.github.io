param(
  [string]$TaskName = "Gombo Opportunities Morning Scan",
  [string]$Time = "07:30"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  Write-Host "Virtual environment not found. Run .\run.ps1 once before installing the scheduled task."
  exit 1
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m app.main --scan" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "Scheduled task installed: $TaskName at $Time"
