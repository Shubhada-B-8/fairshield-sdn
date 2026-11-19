#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x /usr/bin/python3 ]]; then
    echo "System Python missing."
    exit 1
fi

if [[ ! -d "$PROJECT_ROOT/.venv/lib/python3.10/site-packages" ]]; then
    echo "Project virtual environment dependencies missing."
    exit 1
fi

exec /usr/bin/python3 "$PROJECT_ROOT/scripts/run_osken_controller.py" \
    --ofp-tcp-listen-port 6653 \
    fairshield.ryu_app
