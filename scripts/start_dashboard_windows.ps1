param(
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 8765
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $ProjectRoot
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Virtual environment missing. First run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1' }
Write-Host "Starting FairShield dashboard at http://$HostAddress`:$Port" -ForegroundColor Green
& $python -m fairshield.cli dashboard --host $HostAddress --port $Port
