$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $ProjectRoot
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Virtual environment missing. First run: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1' }
& $python -m fairshield.cli demo --windows 30 --seed 7 --capacity 500 --out outputs
