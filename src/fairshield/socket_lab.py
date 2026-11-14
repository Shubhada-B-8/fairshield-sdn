"""Small TCP and UDP telemetry lab to demonstrate real transport sockets.

This is a companion networking lab. The main FairShield controller logic is
still the source of the detection decision; this module transports a flow
record to it using newline-delimited JSON over TCP or one datagram over UDP.
"""
from __future__ import annotations

import argparse
import json
import socket
import socketserver
from typing import Any

from .detector import RuleBasedDetector
from .models import FlowSample


def evaluate_message(payload: dict[str, Any]) -> dict[str, Any]:
    sample = FlowSample(
        window_id=int(payload.get("window_id", 1)),
        src_ip=str(payload["src_ip"]),
        dst_ip=str(payload.get("dst_ip", "10.0.0.100")),
        packets=int(payload["packets"]),
        byte_count=int(payload["byte_count"]),
        syn_packets=int(payload.get("syn_packets", 0)),
        unique_dst_ports=int(payload.get("unique_dst_ports", 1)),
        duration_s=float(payload.get("duration_s", 1.0)),
        label="unknown",
    )
    detection = RuleBasedDetector().detect(sample)
    return {
        "src_ip": sample.src_ip,
        "transport_received_by": "FairShield telemetry service",
        "pps": round(sample.pps, 2),
        "syn_ratio": round(sample.syn_ratio, 3),
        "score": round(detection.score, 3),
        "suspicious": detection.suspicious,
        "action": "RATE_LIMIT" if detection.suspicious else "ALLOW",
        "reasons": list(detection.reasons),
    }


class _TCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b'{"service":"FairShield TCP telemetry","status":"connected"}\n')
        for line in self.rfile:
            if not line.strip():
                continue
            try:
                result = evaluate_message(json.loads(line.decode("utf-8")))
                response = {"ok": True, "result": result}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))
            self.wfile.flush()


class TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _UDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request
        try:
            result = evaluate_message(json.loads(data.decode("utf-8")))
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
        sock.sendto(json.dumps(response).encode("utf-8"), self.client_address)


class UDPServer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True


def tcp_request(host: str, port: int, payload: dict[str, Any]) -> dict[str, Any]:
    message = json.dumps(payload).encode("utf-8") + b"\n"
    with socket.create_connection((host, port), timeout=5) as sock:
        stream = sock.makefile("rwb")
        greeting = stream.readline()  # server banner
        stream.write(message)
        stream.flush()
        response = json.loads(stream.readline().decode("utf-8"))
    return {"greeting": greeting.decode("utf-8").strip(), **response}


def udp_request(host: str, port: int, payload: dict[str, Any]) -> dict[str, Any]:
    message = json.dumps(payload).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)
        sock.sendto(message, (host, port))
        response, _ = sock.recvfrom(65535)
    return json.loads(response.decode("utf-8"))


def _sample_payload(args) -> dict[str, Any]:
    pps = int(args.pps)
    return {
        "window_id": 1,
        "src_ip": args.src_ip,
        "dst_ip": "10.0.0.100",
        "packets": pps,
        "byte_count": pps * 100,
        "syn_packets": int(pps * args.syn_ratio),
        "unique_dst_ports": args.ports,
        "duration_s": 1.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="FairShield TCP/UDP socket lab")
    sub = parser.add_subparsers(dest="command", required=True)
    for transport in ("tcp", "udp"):
        server = sub.add_parser(f"{transport}-server")
        server.add_argument("--host", default="127.0.0.1")
        server.add_argument("--port", type=int, default=9100 if transport == "tcp" else 9101)
        client = sub.add_parser(f"{transport}-client")
        client.add_argument("--host", default="127.0.0.1")
        client.add_argument("--port", type=int, default=9100 if transport == "tcp" else 9101)
        client.add_argument("--src-ip", default="10.0.0.25")
        client.add_argument("--pps", type=int, default=600)
        client.add_argument("--syn-ratio", type=float, default=0.95)
        client.add_argument("--ports", type=int, default=12)
    args = parser.parse_args()

    if args.command == "tcp-server":
        with TCPServer((args.host, args.port), _TCPHandler) as server:
            print(f"TCP telemetry server listening on {args.host}:{args.port}")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    elif args.command == "udp-server":
        with UDPServer((args.host, args.port), _UDPHandler) as server:
            print(f"UDP telemetry server listening on {args.host}:{args.port}")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    else:
        payload = _sample_payload(args)
        result = (tcp_request if args.command == "tcp-client" else udp_request)(
            args.host, args.port, payload
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
