from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .simulator import run_suite

HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FairShield-SDN Research Dashboard</title>
<style>
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#e8edf8;background:#0b1220}*{box-sizing:border-box}body{margin:0;padding:32px;background:radial-gradient(circle at top right,#142847,#0b1220 48%)}.wrap{max-width:1150px;margin:auto}.eyebrow{color:#73d0c2;font-weight:700;letter-spacing:.13em;text-transform:uppercase;font-size:12px}h1{font-size:36px;margin:10px 0 6px}.sub{color:#9eabc2;margin:0 0 26px}.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:22px}button,select{background:#15243a;color:#edf4ff;border:1px solid #2b4668;border-radius:10px;padding:10px 14px;font-size:14px}button{background:#167d79;border:0;font-weight:700;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card,.panel{background:#111d30;border:1px solid #213652;border-radius:16px;padding:18px;box-shadow:0 14px 35px #0003}.k{color:#91a4bf;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.v{font-size:27px;font-weight:750;margin-top:8px}.panel{margin-top:18px;overflow:auto}h2{font-size:18px;margin:0 0 16px}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th,td{text-align:left;padding:11px 12px;border-bottom:1px solid #263852}th{color:#9fb3ce;font-weight:600}td{color:#e5edf8}.good{color:#69d8b5}.warn{color:#ffd27e}.bar{height:9px;background:#1d304b;border-radius:8px;overflow:hidden;min-width:110px}.bar span{display:block;height:100%;background:linear-gradient(90deg,#36b9aa,#78d79a)}.foot{color:#7e90aa;font-size:12px;margin:22px 3px}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}h1{font-size:28px}}@media(max-width:480px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="wrap"><div class="eyebrow">Network security · SDN · research prototype</div><h1>FairShield-SDN</h1><p class="sub">Adaptive DDoS detection with fairness-aware traffic admission and mitigation.</p>
<div class="toolbar"><label>Mode <select id="version"><option value="1">V1 baseline comparison</option><option value="2">V2 adaptive feedback</option></select></label><label>Scenario <select id="scenario"><option value="mixed">Mixed traffic</option><option value="ddos">DDoS</option><option value="flash_crowd">Flash crowd</option><option value="normal">Normal</option></select></label><label>Windows <select id="windows"><option>20</option><option>30</option><option>60</option></select></label><button onclick="run()">Run experiment</button><span id="status" class="k">Ready</span></div>
<div class="grid"><div class="card"><div class="k">Legitimate traffic preserved</div><div class="v" id="preserve">—</div></div><div class="card"><div class="k">Attack traffic mitigated</div><div class="v" id="mitigate">—</div></div><div class="card"><div class="k">Jain fairness index</div><div class="v" id="fairness">—</div></div><div class="card"><div class="k">Detector F1 score</div><div class="v" id="f1">—</div></div></div>
<div class="panel"><h2>Policy comparison</h2><table><thead><tr><th>Policy</th><th>Legitimate preserved</th><th>Attack mitigated</th><th>Fairness</th><th>Delivered pps</th><th>F1</th></tr></thead><tbody id="rows"><tr><td colspan="6">Run an experiment to populate this table.</td></tr></tbody></table></div>
<div class="panel"><h2>How to interpret the experiment</h2><p class="sub">V1 compares No Defense, Static Threshold and fixed-cap FairShield. V2 adds a stateful feedback-driven admission cap: it tightens when bottleneck utilization or legitimate-service degradation indicates pressure, relaxes when headroom exists alongside a material source meter-drop signal, and recovers gradually after benign observations. In this simulator the meter-drop feedback is an estimated suppression proxy, not an OVS counter. These are controlled synthetic experiments, not production-network measurements.</p></div>
<div class="foot">FairShield-SDN · Local dashboard · No telemetry leaves this machine</div></div>
<script>
function pct(x){return (100*x).toFixed(1)+'%'}function num(x){return Number(x).toFixed(2)}
async function run(){const status=document.getElementById('status');status.textContent='Running…';try{const q=new URLSearchParams({scenario:document.getElementById('scenario').value,windows:document.getElementById('windows').value,version:document.getElementById('version').value});const r=await fetch('/api/run?'+q);if(!r.ok)throw new Error('HTTP '+r.status);const data=await r.json();const rows=data.results;const fs=rows.find(x=>x.policy===(document.getElementById('version').value==='2'?'adaptive_fairshield_v2':'fairshield')); document.getElementById('preserve').textContent=pct(fs.legitimate_preservation);document.getElementById('mitigate').textContent=pct(fs.attack_mitigation);document.getElementById('fairness').textContent=num(fs.jain_satisfaction_fairness);document.getElementById('f1').textContent=num(fs.f1);document.getElementById('rows').innerHTML=rows.map(x=>`<tr><td><b>${x.policy}</b></td><td><div class="bar"><span style="width:${100*x.legitimate_preservation}%"></span></div>${pct(x.legitimate_preservation)}</td><td>${pct(x.attack_mitigation)}</td><td>${num(x.jain_satisfaction_fairness)}</td><td>${num(x.delivered_pps)}</td><td>${num(x.f1)}</td></tr>`).join('');status.textContent='Completed';}catch(e){status.textContent='Error: '+e.message}}
run();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/run":
            from urllib.parse import parse_qs
            q = parse_qs(parsed.query)
            scenario = q.get("scenario", ["mixed"])[0]
            windows = max(1, min(500, int(q.get("windows", ["20"])[0])))
            if scenario not in ("normal", "ddos", "flash_crowd", "mixed"):
                self.send_error(400, "Invalid scenario")
                return
            version = q.get("version", ["1"])[0]
            results, _ = run_suite([scenario], windows=windows, seed=7)
            records = [r.to_dict() for r in results]
            if version == "2":
                from .adaptive_simulator import run_adaptive_experiment
                adaptive_result, _ = run_adaptive_experiment(scenario, windows=windows, seed=7)
                records.append(adaptive_result.to_dict())
            elif version != "1":
                self.send_error(400, "Invalid version")
                return
            payload = {"results": records}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        print("[dashboard] " + fmt % args)


def main(host: str = "127.0.0.1", port: int = 8080):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"FairShield dashboard: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FairShield-SDN local research dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    main(args.host, args.port)
