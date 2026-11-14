#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
python -m fairshield.cli demo --windows 30 --seed 7 --capacity 500 --out outputs
printf '\nSetup and demo complete. Start the dashboard with:\n  source .venv/bin/activate && fairshield dashboard\n'
