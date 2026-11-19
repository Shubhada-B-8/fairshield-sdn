"""Read actual FairShield controller telemetry from its local log."""

import re
from pathlib import Path
from datetime import datetime


def read_controller_telemetry(path="outputs/logs/controller_telemetry.log"):
    path = Path(path)
    result = {
        "available": path.exists(),
        "log_updated": None,
        "ports": {},
        "probe": {
            "latency_ms": None,
            "jitter_ms": None,
            "probe_loss_ratio": None,
            "reliability": None,
        },
        "adaptive": None,
        "ai": None,
        "legitimate_service": None,
        "records": 0,
    }

    if not path.exists():
        return result

    result["log_updated"] = datetime.fromtimestamp(
        path.stat().st_mtime
    ).astimezone().isoformat(timespec="seconds")

    with path.open(errors="replace") as file:
        lines = file.readlines()[-10000:]

    for line in lines:
        if "PORT_METRICS" in line:
            match = re.search(
                r"PORT_METRICS dpid=(\d+) port=(\d+) "
                r"rx_mbps=([\d.]+) tx_mbps=([\d.]+) "
                r"utilization=([\d.]+)", line
            )
            if match:
                dpid, port, rx, tx, utilization = match.groups()
                result["ports"][f"{dpid}:{port}"] = {
                    "dpid": int(dpid),
                    "port": int(port),
                    "rx_mbps": float(rx),
                    "tx_mbps": float(tx),
                    "link_utilization": float(utilization),
                }
                result["records"] += 1

        if "PROBE_METRICS" in line:
            match = re.search(
                r"PROBE_METRICS latency_ms=(\S+) jitter_ms=(\S+) "
                r"probe_loss_pct=(\S+) reliability_pct=(\S+)", line
            )
            if match:
                latency, jitter, loss, reliability = match.groups()

                def number(value):
                    return None if value in ("None", "nan") else float(value)

                probe = result["probe"]
                probe["latency_ms"] = number(latency)
                probe["jitter_ms"] = number(jitter)
                loss_value = number(loss)
                reliability_value = number(reliability)
                probe["probe_loss_ratio"] = (
                    None if loss_value is None else loss_value / 100
                )
                probe["reliability"] = (
                    None if reliability_value is None
                    else reliability_value / 100
                )
                result["records"] += 1

        if "ADAPTIVE source=" in line:
            match = re.search(
                r"ADAPTIVE source=(\S+) action=(\S+) offered_pps=([\d.]+) "
                r"cap_pps=([\d.]+) allocated_pps=([\d.]+).*?"
                r"legitimate_service=(\S+) meter_drop=([\d.]+) "
                r"adjustment=(\S+)", line
            )
            if match:
                source, action, offered, cap, allocated, service, drops, adjustment = match.groups()
                result["adaptive"] = {
                    "source": source,
                    "action": action,
                    "offered_pps": float(offered),
                    "cap_pps": float(cap),
                    "allocated_pps": float(allocated),
                    "legitimate_service": (
                        None if service == "None" else float(service)
                    ),
                    "meter_drop_ratio": float(drops),
                    "adjustment": adjustment,
                }
                result["records"] += 1

        if "AI_ACTIVE source=" in line:
            match = re.search(
                r"AI_ACTIVE source=(\S+) ai_decision_suspicious=(\S+) "
                r"rule_score=([\d.]+)", line
            )
            if match:
                source, suspicious, score = match.groups()
                result["ai"] = {
                    "source": source,
                    "suspicious": suspicious.lower() == "true",
                    "rule_score": float(score),
                }

        if "LEGITIMATE_SERVICE sources=" in line:
            match = re.search(
                r"LEGITIMATE_SERVICE sources=(\S+) offered_packets=(\d+) "
                r"forwarded_packets=(\d+) ratio=([\d.]+)", line
            )
            if match:
                sources, offered, forwarded, ratio = match.groups()
                result["legitimate_service"] = {
                    "sources": sources,
                    "offered_packets": int(offered),
                    "forwarded_packets": int(forwarded),
                    "ratio": float(ratio),
                }

    return result


def aggregate_port_metrics(telemetry):
    ports = list(telemetry.get("ports", {}).values())
    if not ports:
        return {
            "rx_throughput_mbps": None,
            "tx_throughput_mbps": None,
            "link_utilization": None,
        }

    return {
        "rx_throughput_mbps": sum(p["rx_mbps"] for p in ports),
        "tx_throughput_mbps": sum(p["tx_mbps"] for p in ports),
        "link_utilization": max(
            p["link_utilization"] for p in ports
        ),
    }
