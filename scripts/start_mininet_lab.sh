#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
if ! command -v mn >/dev/null 2>&1; then
  echo "Mininet is missing. Run ./scripts/setup_sdn_linux.sh first." >&2
  exit 1
fi
if ! systemctl is-active --quiet openvswitch-switch; then
  echo "Starting Open vSwitch..."
  sudo systemctl start openvswitch-switch
fi
sudo mn -c
sudo mn --custom "$PROJECT_ROOT/mininet/fairshield_topology.py" \
  --topo fairshieldtopo \
  --controller remote,ip=127.0.0.1,port=6653 \
  --switch ovsk,protocols=OpenFlow13
