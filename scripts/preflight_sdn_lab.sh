#!/usr/bin/env bash
# Read-only preflight checks for the FairShield-SDN Ubuntu/WSL live demo.
# This script does not start/stop services, modify OVS, or change network state.
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
WARN=0
FAIL=0

ok()   { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
warn() { printf '[WARN] %s\n' "$1"; WARN=$((WARN + 1)); }
fail() { printf '[FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }

printf 'FairShield-SDN live-lab preflight\nProject: %s\n\n' "$PROJECT_ROOT"

if command -v mn >/dev/null 2>&1; then ok "Mininet command available ($(command -v mn))"; else fail 'Mininet command "mn" not found'; fi
if command -v ovs-vsctl >/dev/null 2>&1; then ok "Open vSwitch CLI available ($(command -v ovs-vsctl))"; else fail 'ovs-vsctl not found'; fi
if command -v ovs-ofctl >/dev/null 2>&1; then ok "OpenFlow CLI available ($(command -v ovs-ofctl))"; else fail 'ovs-ofctl not found'; fi
if [[ -x /usr/bin/osken-manager ]]; then ok 'OS-Ken manager found at /usr/bin/osken-manager'; else fail 'OS-Ken manager missing at /usr/bin/osken-manager'; fi
if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then ok 'Project virtual-environment Python found'; else fail 'Project .venv is missing; follow scripts/setup_sdn_linux.sh'; fi

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  if "$PROJECT_ROOT/.venv/bin/python" - <<'PY' >/dev/null 2>&1
import os_ken
import fairshield.ryu_app
PY
  then
    ok 'OS-Ken and FairShield controller modules import successfully'
  else
    fail 'OS-Ken/FairShield import check failed in .venv'
  fi
fi

if python3 - <<'PY' >/dev/null 2>&1
import mininet.topo
PY
then
  ok 'System Python can import Mininet'
else
  fail 'System Python cannot import Mininet'
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet openvswitch-switch; then
  ok 'openvswitch-switch service is active'
else
  warn 'openvswitch-switch is not active; start it with: sudo systemctl start openvswitch-switch'
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -qE '(^|[[:space:]])[^[:space:]]*:6653[[:space:]]'; then
    warn 'TCP port 6653 is already listening; this may mean the controller is already running. Check with: ps -ef | grep -E "[o]sken-manager|[r]yu-manager"'
  else
    ok 'TCP port 6653 is currently free for the controller'
  fi
else
  warn 'ss command not found; cannot inspect TCP port 6653'
fi

printf '\nSummary: %d passed, %d warning(s), %d failed\n' "$PASS" "$WARN" "$FAIL"
if (( FAIL > 0 )); then
  printf 'Resolve [FAIL] items before the faculty demo. This script made no changes.\n'
  exit 1
fi
printf 'Preflight checks passed. Review warnings before starting a fresh demo.\n'
