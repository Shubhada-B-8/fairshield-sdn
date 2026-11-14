# FairShield live SDN lab — Mininet + Open vSwitch + OpenFlow 1.3

This is the live-network validation path. It is separate from the cross-platform
Python simulator and is intended to run inside an Ubuntu VM or supported Linux
machine. The six-host topology is isolated inside Mininet; the traffic script
is rate-bounded and only sends to the configured destination.

## Why OS-Ken instead of a fresh Ryu installation?

The controller source prefers OS-Ken and falls back to Ryu imports. OS-Ken is
the maintained Ryu fork used by OpenStack and currently supports Python 3.10+
(see the official OS-Ken project and PyPI). The upstream Ryu documentation
explicitly says the Ryu project is not currently maintained. This matters on
newer Ubuntu/Python installations where old Ryu dependencies can fail.

## Recommended environment

Use an Ubuntu 22.04/24.04 VM in VMware/VirtualBox, with at least 2 CPU cores and
4 GB RAM. Mininet needs Linux network namespaces, Open vSwitch, and root access;
the Mininet project recommends its VM image or native Ubuntu installation.

## 1. Copy the project into Ubuntu

Extract the project ZIP inside the Ubuntu VM. Open a terminal in the folder
containing `pyproject.toml` and `mininet/`.

## 2. Install Mininet, OVS, and OS-Ken

```bash
chmod +x scripts/*.sh
./scripts/setup_sdn_linux.sh
```

This installs the Ubuntu Mininet/Open vSwitch packages, creates a project
virtual environment that can see the system Mininet package, installs OS-Ken,
and runs the project tests. If `apt` cannot find Mininet or the service fails,
use the official Mininet VM image or installation instructions.

## 3. Start the controller — Terminal A

```bash
cd /path/to/fairshield_sdn
source .venv/bin/activate
./scripts/start_sdn_controller.sh
```

Wait for the log indicating that the FairShield OpenFlow 1.3 controller has
started. Keep this terminal open.

## 4. Start the isolated Mininet topology — Terminal B

```bash
cd /path/to/fairshield_sdn
./scripts/start_mininet_lab.sh
```

The topology has one OpenFlow 1.3 switch and six hosts:

| Host | IP | Role |
|---|---|---|
| h1 | 10.0.0.1 | Legitimate client 1 |
| h2 | 10.0.0.2 | Legitimate client 2 |
| h3 | 10.0.0.3 | Controlled high-rate lab source 1 |
| h4 | 10.0.0.4 | Controlled high-rate lab source 2 |
| h5 | 10.0.0.5 | UDP measurement sink |
| h6 | 10.0.0.6 | Spare client |

At the `mininet>` prompt, verify connectivity:

```text
mininet> nodes
mininet> net
mininet> pingall
```

All hosts should be reachable before starting the traffic test.

## 5. Run the mixed-traffic test — inside the Mininet prompt

Start the UDP sink on h5:

```text
mininet> h5 python3 mininet/udp_traffic.py sink --bind 10.0.0.5 --port 9000 &
```

Start two legitimate high-volume, larger-packet clients:

```text
mininet> h1 python3 mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 500 --duration 30 --size 1000 &
mininet> h2 python3 mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 500 --duration 30 --size 1000 &
```

Start two controlled attack-like, high-rate small-packet sources, only inside
this Mininet topology:

```text
mininet> h3 python3 mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 2500 --duration 30 --size 128 &
mininet> h4 python3 mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 2500 --duration 30 --size 128 &
```

The generator refuses rates above 4000 packets/second, sizes outside 64–1400
bytes, and durations above 180 seconds. Do not change the destination to a
public or third-party IP. This is a controlled lab pattern, not a public DDoS
test.

Observe Terminal A. Every five seconds, the controller reads OpenFlow table-1
packet/byte counters, derives per-source rates and packet-size features,
classifies sources, caps detected sources, computes weighted max-min shares in
kbit/s, and installs or updates OpenFlow 1.3 source meters in table 0.

## 6. Inspect OpenFlow rules and meter statistics — a third terminal

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 meter-stats s1
```

You should see table-0 source meter rules for sources that FairShield is
currently rate-limiting. Meter rates should change when the measured mix of
sources changes. Save terminal logs and the `dump-flows` / `meter-stats`
outputs as evidence for the project report.

## 7. Stop and clean up

At the Mininet prompt:

```text
mininet> exit
```

Then in a Linux terminal:

```bash
sudo mn -c
```

Stop the controller with `Ctrl+C` in Terminal A.

## What the live controller implements — and what it does not

Implemented in this lab adapter:

- OpenFlow 1.3 switch negotiation.
- Two-table pipeline: table 0 for source meters, table 1 for learning-switch forwarding.
- Periodic flow-statistics polling and per-source byte/packet deltas.
- A transparent heuristic using packet rate, average packet size, bit rate, and destination-port fan-out.
- Per-source OpenFlow meter creation, modification, and removal.
- Attacker demand cap followed by weighted max-min allocation in kbit/s.

Limitations to disclose in the report:

- Standard aggregate flow counters do not expose TCP SYN flags, so the live
  adapter uses a separate heuristic. The offline simulator has richer
  synthetic features and must not be presented as the same live detector.
- This is a single-switch, single-bottleneck prototype. It does not address
  distributed attacks with source spoofing, encrypted application semantics,
  controller overload, TCAM exhaustion, or adversarial evasion.
- The configured 10 Mbit/s aggregate budget is enforced by per-source meters;
  it is a configured lab policy value, not a physical link capacity measurement.
- The first statistics interval can include packets sent before the first
  sample. Run the traffic for at least 15 seconds to observe steady samples.
- OpenFlow meter support and CLI output vary with the installed OVS version.
- This controller is for academic experimentation, not production deployment.

## References

- Mininet install and VM guidance: https://github.com/mininet/mininet/blob/master/INSTALL
- Mininet download guide: https://mininet.org/download/
- OS-Ken project: https://github.com/openstack/os-ken
- OS-Ken package: https://pypi.org/project/os-ken/
- Ryu documentation project-status notice: https://ryu.readthedocs.io/en/latest/getting_started.html


## Tested recovery note

In the 12 November 2026 demo, the learned table-1 UDP forwarding entry expired after its 60-second idle timeout. Running `pingall` refreshed forwarding/learning state, after which the normal 100 PPS UDP receiver test again recorded approximately 100 PPS / 800 kbps. Include this refresh step when reproducing that exact demo sequence; do not describe it as evidence of fully autonomous recovery without forwarding refresh.


## Tested recovery note

In the 12 November 2026 demo, the learned table-1 UDP forwarding entry expired after its 60-second idle timeout. Running `pingall` refreshed forwarding/learning state, after which the normal 100 PPS UDP receiver test again recorded approximately 100 PPS / 800 kbps. Include this refresh step when reproducing that exact demo sequence; do not describe it as evidence of fully autonomous recovery without forwarding refresh.


## Tested recovery note

In the 12 November 2026 demo, the learned table-1 UDP forwarding entry expired after its 60-second idle timeout. Running `pingall` refreshed forwarding/learning state, after which the normal 100 PPS UDP receiver test again recorded approximately 100 PPS / 800 kbps. Include this refresh step when reproducing that exact demo sequence; do not describe it as evidence of fully autonomous recovery without forwarding refresh.


## Tested recovery note

In the 12 November 2026 demo, the learned table-1 UDP forwarding entry expired after its 60-second idle timeout. Running `pingall` refreshed forwarding/learning state, after which the normal 100 PPS UDP receiver test again recorded approximately 100 PPS / 800 kbps. Include this refresh step when reproducing that exact demo sequence; do not describe it as evidence of fully autonomous recovery without forwarding refresh.


## Tested recovery note

In the 12 November 2026 demo, the learned table-1 UDP forwarding entry expired after its 60-second idle timeout. Running `pingall` refreshed forwarding/learning state, after which the normal 100 PPS UDP receiver test again recorded approximately 100 PPS / 800 kbps. Include this refresh step when reproducing that exact demo sequence; do not describe it as evidence of fully autonomous recovery without forwarding refresh.
