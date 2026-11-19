#!/usr/bin/env python3
"""Measure h2-to-h5 RTT and report probe results over UDP."""

import json
import re
import socket
import subprocess
import time

TARGET = "10.0.0.5"
REPORT_IP = "10.0.0.255"
REPORT_PORT = 9999
INTERVAL = "0.2"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

print(f"FairShield probe agent: {TARGET}, reporting to UDP {REPORT_PORT}")

process = subprocess.Popen(
    ["ping", "-n", "-O", "-i", INTERVAL, "-W", "1", TARGET],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

try:
    for line in process.stdout:
        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", line)

        if match:
            success = True
            rtt_ms = float(match.group(1))
        elif any(token in line.lower() for token in ("timeout", "unreachable", "no answer yet", "timed out")):
            success = False
            rtt_ms = None
        else:
            continue

        payload = {
            "type": "fairshield_probe",
            "timestamp": time.time(),
            "success": success,
            "rtt_ms": rtt_ms,
        }

        sock.sendto(
            json.dumps(payload).encode(),
            (REPORT_IP, REPORT_PORT),
        )

        if success:
            print(f"RTT={rtt_ms:.3f} ms")
        else:
            print("Probe failed")

except KeyboardInterrupt:
    process.terminate()
finally:
    sock.close()
    process.wait()
