$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $ProjectRoot

Write-Host '== FairShield-SDN: Windows setup ==' -ForegroundColor Cyan
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { throw 'Python Launcher (py) was not found. Install Python 3.10+ from https://www.python.org/downloads/ and enable the Python Launcher.' }
py -3 --version
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
}
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -e .
Write-Host '\n== Running automated tests ==' -ForegroundColor Cyan
& $python -m unittest discover -s tests -v
Write-Host '\n== Running reproducible experiments ==' -ForegroundColor Cyan
& $python -m fairshield.cli demo --windows 30 --seed 7 --capacity 500 --out outputs
Write-Host '\nSetup and demo completed. Start the dashboard with:' -ForegroundColor Green
Write-Host '.\.venv\Scripts\python.exe -m fairshield.cli dashboard'
