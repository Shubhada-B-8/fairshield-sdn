#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

$SUDO apt-get update
$SUDO apt-get install -y mininet openvswitch-switch python3-venv python3-pip iproute2
$SUDO systemctl enable --now openvswitch-switch

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[sdn]'
python -m unittest discover -s tests -v

python - <<'PY'
import mininet
import os_ken
print("Mininet Python module: available")
print("OS-Ken module: available")
PY

printf '\nSDN setup complete.\n'
printf 'Controller: ./scripts/start_sdn_controller.sh\n'
printf 'Mininet:    ./scripts/start_mininet_lab.sh\n'
