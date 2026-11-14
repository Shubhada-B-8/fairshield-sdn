#!/usr/bin/env python3
"""Small, rate-bounded UDP source/sink for the isolated Mininet lab only."""
from __future__ import annotations

import argparse
import socket
import time


def run_sink(args: argparse.Namespace) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.bind, args.port))
    sock.settimeout(1.0)

    source_stats = {}
    replied_to = set()
    last = time.monotonic()

    print(f"UDP sink listening on {args.bind}:{args.port}", flush=True)

    try:
        while True:
            try:
                data, peer = sock.recvfrom(65535)
                src_ip = peer[0]

                stats = source_stats.setdefault(
                    src_ip, {"packets": 0, "bytes": 0}
                )
                stats["packets"] += 1
                stats["bytes"] += len(data)

                # One-time response teaches the learning switch the sink MAC.
                if peer not in replied_to:
                    sock.sendto(b"FS-ACK", peer)
                    replied_to.add(peer)

            except socket.timeout:
                pass

            now = time.monotonic()
            elapsed = now - last

            if elapsed >= 1.0:
                for src_ip, stats in sorted(source_stats.items()):
                    packets = stats["packets"]
                    byte_count = stats["bytes"]

                    print(
                        f"SOURCE source={src_ip} received={packets} "
                        f"pps={packets/elapsed:.1f} "
                        f"kbps={byte_count*8/elapsed/1000:.1f}",
                        flush=True,
                    )

                source_stats.clear()
                last = now

    finally:
        sock.close()


def run_send(args: argparse.Namespace) -> None:
    if not 1 <= args.pps <= 4000:
        raise SystemExit("pps must be between 1 and 4000 for the isolated lab")
    if not 64 <= args.size <= 1400:
        raise SystemExit("size must be between 64 and 1400 bytes")
    if not 1 <= args.duration <= 180:
        raise SystemExit("duration must be between 1 and 180 seconds")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = b"FSDN" + (b"x" * (args.size - 4))
    interval = 1.0 / args.pps
    deadline = time.monotonic() + args.duration
    next_send = time.monotonic()
    sent = 0
    print(f"sending to {args.dst}:{args.port} at <= {args.pps} pps "
          f"for {args.duration}s, payload={args.size} bytes", flush=True)
    try:
        while time.monotonic() < deadline:
            sock.sendto(payload, (args.dst, args.port))
            sent += 1
            next_send += interval
            wait = next_send - time.monotonic()
            if wait > 0:
                time.sleep(wait)
    finally:
        sock.close()
    elapsed = args.duration
    print(f"sent={sent} average_pps={sent/elapsed:.1f} "
          f"average_kbps={sent*args.size*8/elapsed/1000:.1f}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sink = sub.add_parser("sink")
    sink.add_argument("--bind", default="10.0.0.5")
    sink.add_argument("--port", type=int, default=9000)
    sink.set_defaults(func=run_sink)
    send = sub.add_parser("send")
    send.add_argument("--dst", default="10.0.0.5")
    send.add_argument("--port", type=int, default=9000)
    send.add_argument("--pps", type=int, default=250)
    send.add_argument("--duration", type=int, default=30)
    send.add_argument("--size", type=int, default=1000)
    send.set_defaults(func=run_send)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
