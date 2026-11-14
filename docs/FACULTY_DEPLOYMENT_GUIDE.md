# FairShield-SDN — Faculty Deployment Guide (Ubuntu on WSL)

This guide describes the exact deployment path used for the FairShield-SDN live lab. It is intended for a faculty demonstration on the same Ubuntu/WSL machine where Mininet, Open vSwitch (OVS), and OS-Ken have already been installed.

> **Safety and scope:** Run the traffic generator only inside the isolated Mininet topology. The demonstrated high-rate source is a controlled, single-source UDP stress pattern. It is not a distributed attack against a public network and must not be described as one.

## 1. Tested environment

- Ubuntu 22.04 under WSL
- Python 3.10.12
- Mininet 2.3.0
- Open vSwitch 2.17.12
- OS-Ken controller using OpenFlow 1.3
- Six Mininet hosts (`h1`–`h6`) connected to switch `s1`
- Controller endpoint `tcp:127.0.0.1:6653`
- UDP sink `10.0.0.5:9000` on `h5`

The project path used in the demonstrated session was `/home/shubhada/projects/fairshield_sdn`. If the project is stored elsewhere, replace that path in the host-side Mininet commands below with the actual absolute path.

## 2. Before the faculty arrives

1. Connect the laptop to power and open Ubuntu/WSL.
2. Confirm that the project directory exists: `cd ~/projects/fairshield_sdn`.
3. Ensure the project ZIP has been extracted and the `.venv` created.
4. Make the shell scripts executable once:

   ```bash
   chmod +x scripts/*.sh
   ```

5. Run the read-only preflight check:

   ```bash
   ./scripts/preflight_sdn_lab.sh
   ```

6. If the preflight reports that OVS is inactive, start it:

   ```bash
   sudo systemctl start openvswitch-switch
   ```

7. If a previous Mininet session is still active, exit it first. Only when no demo is running, clean stale Mininet state:

   ```bash
   sudo mn -c
   ```

Do not run `sudo mn -c` while a demonstration is in progress. It removes Mininet/OVS lab state.

## 3. Start the controller — Terminal A

Open Terminal A:

```bash
cd ~/projects/fairshield_sdn
./scripts/start_sdn_controller.sh
```

Keep this terminal open. Expected startup text includes:

```text
loading app fairshield.ryu_app
FairShield OS-Ken/Ryu adapter started (OpenFlow 1.3)
```

Eventlet deprecation/RLock warnings were observed in the tested environment. They did not prevent the controller from starting. Do not interpret the warning alone as a startup failure; verify the listener and switch connection.

In another Ubuntu shell, verify the listening port:

```bash
sudo ss -ltnp | grep ':6653'
```

A Python process listening on `0.0.0.0:6653` or `*:6653` is expected. If the port is already occupied before you start the controller, inspect existing processes rather than starting a second controller:

```bash
ps -ef | grep -E '[o]sken-manager|[r]yu-manager'
```

## 4. Start Mininet — Terminal B

Open Terminal B:

```bash
cd ~/projects/fairshield_sdn
./scripts/start_mininet_lab.sh
```

This script checks Mininet, starts OVS if needed, performs Mininet cleanup, and launches the six-host topology with a remote controller at `127.0.0.1:6653`.

At the `mininet>` prompt, run these checks:

```text
nodes
sh ovs-vsctl list Controller
pingall
```

Expected:

- Nodes include `c0 h1 h2 h3 h4 h5 h6 s1`.
- The controller entry whose target is `tcp:127.0.0.1:6653` has `is_connected: true` and state `ACTIVE`.
- `pingall` reports `0% dropped (30/30 received)`.

OVS may also show a `ptcp:6654` passive management listener. Its `is_connected: false` is not the controller connection we are checking; use the `tcp:127.0.0.1:6653` entry.

## 5. Start the UDP sink — Mininet prompt

At `mininet>` start the receiver on `h5`:

```text
h5 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py sink --bind 10.0.0.5 --port 9000 > /tmp/fairshield_sink.log 2>&1 &
h5 tail -n 5 /tmp/fairshield_sink.log
```

Expected first line:

```text
UDP sink listening on 10.0.0.5:9000
```

The `received=0` lines are normal while no traffic is being sent.

## 6. Demonstrate normal traffic first

At `mininet>`:

```text
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 100 --duration 10 --size 1000
h5 tail -n 12 /tmp/fairshield_sink.log
```

Expected sender summary:

```text
sent=1000 average_pps=100.0 average_kbps=800.0
```

The receiver should show approximately 100 packets/s and 800 kbps while the sender is active. The first/last log interval may be partial.

## 7. Demonstrate live rate limiting — controlled Mininet traffic only

At `mininet>`, start the 60-second high-rate UDP source in the background:

```text
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 1000 --duration 60 --size 200 > /tmp/fairshield_attack_sender.log 2>&1 &
```

Immediately use Terminal C (a separate Ubuntu shell) to inspect the switch while the sender is active:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-meters s1
sudo ovs-ofctl -O OpenFlow13 meter-stats s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s1 table=0
```

The meter ID is assigned dynamically; do not assume it is always `1` or `2`. Look for a drop-band meter configured near `rate=1500`, a positive drop-band packet counter, and a source-specific table-0 rule similar to:

```text
priority=40000,ip,nw_src=10.0.0.1 actions=meter:<meter-id>,goto_table:1
```

In Terminal A, show the controller log lines containing:

- `METER_REQUEST`
- `METER_RULE_REQUEST`
- `action=RATE_LIMIT`

The tested run reported source `10.0.0.1`, suspicion score `0.90`, observed rate around 1.77–1.94 Mbps, and an admitted/allocated cap of 1500 kbps.

**Timing is important:** collect `meter-stats` while the high-rate sender is still running. The controller can remove the source meter after the traffic subsides, so the configuration may be empty if inspected too late.

### Observed live counter example (12 November 2026)

One captured meter snapshot showed:

| Counter | Value |
|---|---:|
| Packets entering meter | 47,031 |
| Bytes entering meter | 11,381,502 |
| Drop-band packets | 10,515 |
| Drop-band bytes | 2,544,630 |
| Configured drop rate | 1,500 kbps |

The drop-band count was about 22.36% of the packets counted at the meter in that snapshot. This is a meter-level counter ratio, **not** end-to-end packet loss or network-wide attack mitigation percentage.

## 8. Verify cleanup

After the sender has ended, inspect Terminal A for `METER_DELETE_REQUEST`. Then in Terminal C:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-meters s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s1 table=0
```

Expected after cleanup: no configured meter rows and only the default table-0 rule `priority=0 actions=goto_table:1`.

## 9. Verify normal traffic recovery

The table-1 learned forwarding entry has an idle timeout of 60 seconds. After a longer test, the learned h1-to-h5 entry may have expired even though the UDP sink process is still alive. In the demonstrated sequence, running `pingall` refreshed forwarding/learning state before the recovery test.

At `mininet>`:

```text
pingall
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 100 --duration 10 --size 1000
h5 tail -n 12 /tmp/fairshield_sink.log
```

Expected: sender reports 1000 packets at 100 PPS / 800 kbps; receiver shows approximately 100 PPS / 800 kbps during the active intervals.

This proves normal UDP delivery after meter removal **and forwarding-state refresh**. Do not claim an immediate autonomous `ALLOW` event: an explicit live controller `ALLOW` log was not captured in this test.

## 10. Finish the demonstration

At the `mininet>` prompt:

```text
exit
```

Then press `Ctrl+C` in Terminal A to stop the controller. If Mininet leaves stale lab state, run from an Ubuntu shell:

```bash
sudo mn -c
```

## 11. Claims to make accurately during evaluation

You can state that the isolated Mininet/OVS demonstration verified controller connectivity, high-rate source classification, OpenFlow meter installation, non-zero meter drop counters, meter/source-rule cleanup, and normal UDP receiver delivery after forwarding-state refresh.

Do not claim that this one live run demonstrated a distributed DDoS attack, production readiness, a real Internet attack, an end-to-end loss percentage, or a controlled live three-policy comparison. The three-policy comparison is from the deterministic synthetic simulator.
