# FairShield-SDN — Repeatable Live Demo Runbook

This runbook reproduces the tested single-source attack-like rate-limit demonstration in an isolated Mininet environment. It is not a public-network DDoS test.

## Terminals

- **Terminal A:** FairShield OS-Ken controller.
- **Terminal B:** Mininet CLI.
- **Terminal C:** OVS inspection commands (Ubuntu shell).

## 0. Clean stale Mininet state only when no demo is running

```bash
sudo mn -c
```

Do not run cleanup while a demo that should be preserved is active.

## 1. Start controller — Terminal A

```bash
cd ~/projects/fairshield_sdn
./scripts/start_sdn_controller.sh
```

Wait for `FairShield OS-Ken/Ryu adapter started (OpenFlow 1.3)` and keep the terminal open.

## 2. Start Mininet — Terminal B

```bash
cd ~/projects/fairshield_sdn
./scripts/start_mininet_lab.sh
```

At `mininet>`:

```text
nodes
sh ovs-vsctl list Controller
pingall
```

Confirm the controller target `tcp:127.0.0.1:6653` has `is_connected: true`, and `pingall` reports `0% dropped (30/30 received)`.

## 3. Start UDP receiver — Terminal B / Mininet prompt

```text
h5 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py sink --bind 10.0.0.5 --port 9000 > /tmp/fairshield_sink.log 2>&1 &
h5 tail -n 5 /tmp/fairshield_sink.log
```

Wait for `UDP sink listening on 10.0.0.5:9000`.

## 4. Normal traffic baseline

```text
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 100 --duration 10 --size 1000
h5 tail -n 12 /tmp/fairshield_sink.log
```

Expected sender: `sent=1000 average_pps=100.0 average_kbps=800.0`. Receiver should show approximately 100 PPS and 800 kbps while the sender is active.

## 5. Launch controlled high-rate source

```text
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 1000 --duration 60 --size 200 > /tmp/fairshield_attack_sender.log 2>&1 &
```

While the sender runs, use Terminal C:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-meters s1
sudo ovs-ofctl -O OpenFlow13 meter-stats s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s1 table=0
```

Look for the source meter (`type=drop`, expected configured cap near 1500 kbps), meter input counters, drop-band counters, and a table-0 source rule. Also show the controller's `RATE_LIMIT`, `METER_REQUEST`, and `METER_RULE_REQUEST` log lines in Terminal A.

**Timing matters:** meter counters must be captured while the high-rate traffic is active. Once the source becomes inactive or is classified as no longer needing a meter, the controller may request deletion.

## 6. Verify cleanup

After the sender ends and the controller logs `METER_DELETE_REQUEST`, run:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-meters s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s1 table=0
```

Expected after cleanup: no meter configuration rows and only the default table-0 `goto_table:1` rule. Do not assume the table-1 learned forwarding entry will remain forever; it uses an idle timeout.

## 7. Verify normal traffic recovery

Refresh the Mininet learning/forwarding state first:

```text
pingall
```

Then send normal traffic again:

```text
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 100 --duration 10 --size 1000
h5 tail -n 12 /tmp/fairshield_sink.log
```

Expected: sender reports 1000 packets at 100 PPS / 800 kbps; receiver logs approximately 100 PPS / 800 kbps. The tested recovery sequence included `pingall` after the learned forwarding entry had expired.

## 8. Exit and stop

At `mininet>`:

```text
exit
```

In Terminal A, press `Ctrl+C`. If stale Mininet processes/interfaces remain after exiting, run `sudo mn -c` from a shell.

## Evidence capture checklist

- [ ] Switch connection (`is_connected: true`)
- [ ] `pingall` 30/30
- [ ] Normal UDP sender and receiver output
- [ ] Controller RATE_LIMIT decision
- [ ] OVS meter config during attack
- [ ] OVS meter stats during attack
- [ ] Meter and table-0 cleanup
- [ ] Normal UDP recovery receiver output

The previous session demonstrated the values in `LIVE_DEMO_EVIDENCE.md`; the screenshots checklist is still worth capturing for a polished presentation.
