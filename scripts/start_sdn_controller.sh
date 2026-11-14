#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
MANAGER="/usr/bin/osken-manager"

if [[ ! -x "$PYTHON" ]]; then
    echo "Project Python environment missing."
    exit 1
fi

if [[ ! -x "$MANAGER" ]]; then
    echo "OS-Ken manager missing. Install python3-os-ken."
    exit 1
fi

"$PYTHON" -c 'from os_ken.cmd.manager import main'

exec "$PYTHON" "$MANAGER" \
    --ofp-tcp-listen-port 6653 \
    fairshield.ryu_app
