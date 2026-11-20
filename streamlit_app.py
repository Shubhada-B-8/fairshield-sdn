from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from statistics import mean

import pandas as pd
import streamlit as st
import psutil

from fairshield.live_telemetry import read_controller_telemetry, aggregate_port_metrics
from fairshield.qos_optimizer import QoSOptimizer

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
ARCHIVE = OUTPUTS / "final_archive_20261114"
SCENARIOS = {
    "Mixed traffic": "mixed",
    "DDoS-like traffic": "ddos",
    "Flash crowd": "flash_crowd",
    "Normal traffic": "normal",
}
POLICY_LABELS = {
    "no_defense": "No defense",
    "static_threshold": "Static threshold",
    "fairshield": "FairShield V1",
    "adaptive_fairshield_v2": "FairShield V2 adaptive",
}

st.set_page_config(
    page_title="FairShield-SDN | Research Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1450px;}
    .hero {padding: 1.35rem 1.5rem; border: 1px solid rgba(128,145,170,.28);
           border-radius: 16px; background: linear-gradient(120deg,#10243b,#172d43); margin-bottom: 1rem;}
    .hero-kicker {font-size:.78rem; letter-spacing:.14em; text-transform:uppercase; color:#80d6c5; font-weight:700;}
    .hero h1 {margin:.35rem 0 .3rem 0; font-size:2.25rem;}
    .hero p {margin:0; color:#bdcad9; font-size:1.02rem;}
    .small-note {color:#78869a; font-size:.85rem;}
    div[data-testid="stMetric"] {border:1px solid rgba(128,145,170,.22); padding: .85rem; border-radius:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Software-defined networking · OpenFlow 1.3 · Research prototype</div>
      <h1>🛡️ FairShield-SDN</h1>
      <p>Adaptive DDoS detection, source admission control, and fairness-aware traffic management.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("Navigation")
    page = st.radio(
        "Choose a view",
        ["Project overview", "How FairShield works", "Simulation lab", "V3 AI Simulation", "Live Mininet evidence", "Live QoS & Network Intelligence", "Adaptive policy sandbox", "Testing & limitations"],
    )
    st.divider()
    st.caption("Local research dashboard")
    st.caption("Simulation outputs and archived lab logs are read from this project folder.")


def load_receiver_metrics() -> pd.DataFrame:
    path = ARCHIVE / "fairshield_udp_receiver.log"
    if not path.exists():
        return pd.DataFrame()
    pattern = re.compile(
        r"^SOURCE\s+source=(\S+)\s+received=(\d+)\s+pps=([\d.]+)\s+kbps=([\d.]+)"
    )
    rows: dict[str, list[dict[str, float]]] = {}
    for line in path.read_text(errors="replace").splitlines():
        match = pattern.search(line.strip())
        if not match:
            continue
        ip, received, pps, kbps = match.groups()
        rows.setdefault(ip, []).append(
            {"pps": float(pps), "kbps": float(kbps), "interval_packets": float(received)}
        )
    labels = {
        "10.0.0.1": ("h1", "Attack-like source"),
        "10.0.0.2": ("h2", "Legitimate source"),
        "10.0.0.3": ("h3", "Attack-like source"),
        "10.0.0.4": ("h4", "Legitimate source"),
    }
    output = []
    for ip, values in sorted(rows.items()):
        host, role = labels.get(ip, ("Unknown", "Unclassified"))
        rates = [x["pps"] for x in values]
        kbps = [x["kbps"] for x in values]
        output.append(
            {
                "Host": host,
                "Source IP": ip,
                "Traffic role": role,
                "Log samples": len(values),
                "Mean logged PPS": mean(rates),
                "Min logged PPS": min(rates),
                "Max logged PPS": max(rates),
                "Mean logged Kbps": mean(kbps),
            }
        )
    return pd.DataFrame(output)


def load_sender_metrics() -> pd.DataFrame:
    sender_specs = [
        ("h1", "10.0.0.1", "Attack-like", "fairshield_tighten_h1.log"),
        ("h2", "10.0.0.2", "Legitimate", "fairshield_tighten_h2.log"),
        ("h3", "10.0.0.3", "Attack-like", "fairshield_tighten_h3.log"),
        ("h4", "10.0.0.4", "Legitimate", "fairshield_tighten_h4.log"),
    ]
    rows = []
    for host, ip, role, filename in sender_specs:
        path = ARCHIVE / filename
        if not path.exists():
            continue
        content = path.read_text(errors="replace")
        match = re.search(r"sent=(\d+)\s+average_pps=([\d.]+)\s+average_kbps=([\d.]+)", content)
        if match:
            sent, pps, kbps = match.groups()
            rows.append(
                {"Host": host, "Source IP": ip, "Traffic role": role,
                 "Packets sent": int(sent), "Sender average PPS": float(pps),
                 "Sender average Kbps": float(kbps)}
            )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def run_simulation(scenario: str, windows: int, seed: int) -> list[dict]:
    from fairshield.simulator import run_suite
    from fairshield.adaptive_simulator import run_adaptive_experiment

    base_results, _ = run_suite([scenario], windows=windows, seed=seed)
    records = [item.to_dict() for item in base_results]
    adaptive_result, _ = run_adaptive_experiment(scenario, windows=windows, seed=seed)
    records.append(adaptive_result.to_dict())
    return records


def metric_pct(value: float) -> str:
    return f"{100 * float(value):.1f}%"


if page == "Project overview":
    st.subheader("Project at a glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Architecture", "SDN + OpenFlow 1.3")
    c2.metric("Controller", "OS-Ken")
    c3.metric("Switch", "Open vSwitch")
    c4.metric("Automated tests", "27 passed")

    st.markdown("### What the system does")
    st.write(
        "FairShield-SDN is a research prototype that detects suspicious traffic patterns, "
        "limits suspicious sources through admission caps, and uses weighted max-min allocation "
        "to share a configured policy capacity. The V2 policy also adjusts source caps from "
        "network feedback."
    )
    st.info(
        "This dashboard separates deterministic synthetic simulation from live Mininet evidence. "
        "A simulation result is not a measurement from a physical network."
    )

    st.markdown("### Main components")
    cols = st.columns(4)
    cards = [
        ("1 · Detect", "Rule-based source features: packet rate, bit rate, packet size, and destination-port fan-out."),
        ("2 · Decide", "Classify source behavior and choose ALLOW or RATE_LIMIT."),
        ("3 · Enforce", "Use OpenFlow meters and source-specific flow rules in OVS."),
        ("4 · Adapt", "Use utilization, legitimate-service ratio, and meter-drop feedback to adjust caps."),
    ]
    for col, (title, body) in zip(cols, cards):
        with col:
            st.markdown(f"**{title}**")
            st.write(body)

    st.markdown("### Current evidence snapshot")
    sender_df = load_sender_metrics()
    receiver_df = load_receiver_metrics()
    a, b = st.columns(2)
    with a:
        st.markdown("**Archived four-source sender run**")
        if not sender_df.empty:
            st.dataframe(sender_df, hide_index=True, use_container_width=True)
        else:
            st.warning("Sender logs not found in outputs/final_archive_20261114.")
    with b:
        st.markdown("**Receiver log summary**")
        if not receiver_df.empty:
            st.dataframe(receiver_df[["Host", "Mean logged PPS", "Log samples"]], hide_index=True, use_container_width=True)
        else:
            st.warning("Receiver log not found.")

elif page == "How FairShield works":
    st.subheader("Control pipeline")
    st.markdown(
        """
        ```text
        Incoming flows
             ↓
        OpenFlow counters / source observations
             ↓
        Rule-based source detector
             ↓
        Suspicious? ── No ──→ ALLOW / benign recovery
             │
            Yes
             ↓
        Per-source adaptive admission cap
             ↓
        Weighted max-min allocation
             ↓
        OpenFlow meter + source flow rule in OVS
             ↓
        Flow counters, meter drops, port / service feedback
             └──────────────────────────────→ next control interval
        ```
        """
    )
    st.markdown("### What V2 adds")
    st.write("V1 applies a fixed source admission policy. V2 stores a cap per suspicious source and updates it from feedback.")
    st.markdown("**Cap adjustment rules from the V2 policy implementation:**")
    st.markdown(
        "- **Tighten:** if utilization is at least 90%, or measured legitimate service falls below 95%, multiply the cap by 0.75 (respecting the configured minimum).\n"
        "- **Relax:** if utilization is at most 75%, legitimate service is at least 95%, and source meter-drop ratio is at least 10%, multiply the cap by 1.20 (respecting the maximum).\n"
        "- **Hold:** in the middle band or when required feedback is missing.\n"
        "- **Benign recovery:** gradually restore a reduced cap after repeated benign observations."
    )
    st.warning(
        "The live adapter's telemetry is not identical to the simulator's estimated feedback. "
        "Do not treat simulator feedback proxies as real OVS counter measurements."
    )

elif page == "Simulation lab":
    st.subheader("Run the actual FairShield simulator")
    st.caption("The experiment uses the project's simulator modules and a fixed random seed for repeatability.")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        scenario_label = st.selectbox("Traffic scenario", list(SCENARIOS.keys()), index=0)
    with col2:
        windows = st.selectbox("Time windows", [20, 30, 60], index=1)
    with col3:
        seed = st.number_input("Random seed", min_value=0, max_value=999999, value=7, step=1)

    if st.button("Run V1 vs V2 comparison", type="primary", use_container_width=True):
        scenario = SCENARIOS[scenario_label]
        try:
            with st.spinner("Running simulation policies..."):
                records = run_simulation(scenario, int(windows), int(seed))
            st.session_state["fairshield_last_sim"] = records
            st.session_state["fairshield_last_scenario"] = scenario_label
        except Exception as exc:
            st.error(f"Simulation failed: {exc}")
            st.exception(exc)

    records = st.session_state.get("fairshield_last_sim")
    if records:
        df = pd.DataFrame(records)
        df["Policy"] = df["policy"].map(POLICY_LABELS).fillna(df["policy"])
        v2_rows = df[df["policy"] == "adaptive_fairshield_v2"]
        st.markdown("### FairShield V2 adaptive result")
        if not v2_rows.empty:
            v2 = v2_rows.iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Legitimate preserved", metric_pct(v2["legitimate_preservation"]))
            m2.metric("Attack demand mitigated", metric_pct(v2["attack_mitigation"]))
            m3.metric("Jain fairness", f"{v2['jain_satisfaction_fairness']:.3f}")
            m4.metric("Delivered throughput", f"{v2['delivered_pps']:.1f} PPS")

        st.markdown("### Policy comparison")
        display_cols = ["Policy", "legitimate_preservation", "attack_mitigation",
                        "jain_satisfaction_fairness", "delivered_pps", "f1"]
        display_df = df[display_cols].rename(columns={
            "legitimate_preservation": "Legitimate preserved",
            "attack_mitigation": "Attack demand mitigated",
            "jain_satisfaction_fairness": "Jain fairness",
            "delivered_pps": "Delivered PPS",
            "f1": "Detector F1",
        })
        table_display = display_df.copy()
        table_display["Legitimate preserved"] = table_display["Legitimate preserved"].map(lambda x: f"{float(x):.1%}")
        table_display["Attack demand mitigated"] = table_display["Attack demand mitigated"].map(lambda x: f"{float(x):.1%}")
        table_display["Jain fairness"] = table_display["Jain fairness"].map(lambda x: f"{float(x):.3f}")
        table_display["Delivered PPS"] = table_display["Delivered PPS"].map(lambda x: f"{float(x):.1f}")
        table_display["Detector F1"] = table_display["Detector F1"].map(lambda x: f"{float(x):.3f}")
        st.dataframe(table_display, hide_index=True, use_container_width=True)
        st.markdown("### Metric charts")
        chart_df = display_df.set_index("Policy")
        left, right = st.columns(2)
        with left:
            st.caption("Legitimate traffic preservation")
            st.bar_chart(chart_df[["Legitimate preserved"]])
        with right:
            st.caption("Policy-level attack-demand mitigation")
            st.bar_chart(chart_df[["Attack demand mitigated"]])
        st.caption(
            f"Scenario: {st.session_state.get('fairshield_last_scenario', scenario_label)} · "
            f"Windows: {windows} · Seed: {seed}. These are simulator outputs, not live network measurements."
        )
    else:
        st.info("Choose a scenario and press **Run V1 vs V2 comparison** to generate the charts and table.")

elif page == "Live Mininet evidence":
    st.subheader("Archived Mininet / Open vSwitch evidence")
    st.caption("Source: outputs/final_archive_20261114/ — archived sender and receiver terminal logs.")
    sender_df = load_sender_metrics()
    receiver_df = load_receiver_metrics()
    if sender_df.empty or receiver_df.empty:
        st.warning("One or more archived traffic logs are missing. Check outputs/final_archive_20261114/.")
    else:
        st.markdown("### Four-source traffic configuration and sender output")
        st.dataframe(sender_df, hide_index=True, use_container_width=True)
        st.markdown("### Receiver-side logged rates")
        st.dataframe(
            receiver_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Mean logged PPS": st.column_config.NumberColumn(format="%.1f"),
                "Min logged PPS": st.column_config.NumberColumn(format="%.1f"),
                "Max logged PPS": st.column_config.NumberColumn(format="%.1f"),
                "Mean logged Kbps": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        chart = receiver_df.set_index("Host")[["Mean logged PPS"]]
        st.bar_chart(chart)

    st.markdown("### Separate single-source adaptive-meter demonstration")
    single_source_path = OUTPUTS / "metrics" / "experiments" / "live_adaptive_rate_limit.md"
    if single_source_path.exists():
        st.markdown(single_source_path.read_text(errors="replace"))
    else:
        st.info("Single-source adaptive experiment note was not found.")

    st.warning(
        "Interpretation limitation: the four-source receiver log averages mix startup, transition, "
        "and later intervals. Attack-source means are not evidence of a sustained 200 PPS cap. "
        "The archived folder does not include a matching controller log for this run, so it cannot "
        "independently prove live cap-tightening decisions or the cause of each receiver rate. "
        "Do not calculate delivery percentages by summing the receiver's interval counters."
    )
    st.info(
        "The separate 1,000 PPS single-source test recorded approximately 200 PPS at the receiver "
        "under a 200 PPS cap, plus meter-drop telemetry. That is a different experiment from the four-source run."
    )

elif page == "Adaptive policy sandbox":
    st.subheader("Interactive adaptive-cap demonstration")
    st.caption("This sandbox applies the V2 AdaptivePolicyConfig simulator defaults. It is not connected to the live controller.")
    defaults = {"cap": 5.0, "streak": 0}
    if st.button("Reset policy state"):
        st.session_state["sandbox_cap"] = defaults["cap"]
        st.session_state["sandbox_streak"] = defaults["streak"]
    st.session_state.setdefault("sandbox_cap", defaults["cap"])
    st.session_state.setdefault("sandbox_streak", defaults["streak"])

    left, right = st.columns(2)
    with left:
        suspicious = st.toggle("Source currently classified as suspicious", value=True)
        utilization = st.slider("Capacity utilization", 0.0, 1.0, 0.92, 0.01)
        legit_service = st.slider("Legitimate service ratio", 0.0, 1.0, 0.98, 0.01)
        meter_drop = st.slider("Source meter-drop ratio", 0.0, 1.0, 0.20, 0.01)
    with right:
        st.metric("Current adaptive cap", f"{st.session_state['sandbox_cap']:.2f} PPS")
        st.metric("Benign observation streak", st.session_state["sandbox_streak"])
        st.markdown("**Simulator policy limits**")
        st.write("Initial cap: 5 PPS · Minimum: 1 PPS · Maximum: 40 PPS")
        st.write("Tighten factor: ×0.75 · Relax factor: ×1.20")

    if st.button("Evaluate next control interval", type="primary"):
        cap = float(st.session_state["sandbox_cap"])
        streak = int(st.session_state["sandbox_streak"])
        if suspicious:
            streak = 0
            congestion = utilization >= 0.90 or legit_service < 0.95
            headroom = utilization <= 0.75 and legit_service >= 0.95 and meter_drop >= 0.10
            if congestion:
                cap = max(1.0, cap * 0.75)
                explanation = "TIGHTEN — congestion or legitimate-service degradation detected."
            elif headroom:
                cap = min(40.0, cap * 1.20)
                explanation = "RELAX — there is headroom, legitimate service is healthy, and meter drops are material."
            else:
                explanation = "HOLD — feedback is within the hysteresis band; no cap adjustment."
        else:
            streak += 1
            if streak >= 2 and cap < 5.0:
                cap = min(5.0, cap * 1.20)
                explanation = "BENIGN RECOVERY — repeated benign observations gradually restore the cap."
            else:
                explanation = "BENIGN OBSERVATION — waiting for the recovery-window threshold."
        st.session_state["sandbox_cap"] = cap
        st.session_state["sandbox_streak"] = streak
        st.session_state["sandbox_last_explanation"] = explanation

    if "sandbox_last_explanation" in st.session_state:
        st.success(st.session_state["sandbox_last_explanation"])
        st.metric("Updated adaptive cap", f"{st.session_state['sandbox_cap']:.2f} PPS")

    st.markdown("**Decision thresholds:** congestion utilization ≥ 90%; headroom utilization ≤ 75%; target legitimate service ≥ 95%; material meter-drop ratio ≥ 10%. Missing feedback in the actual policy causes a hold, not an assumption of healthy conditions.")


elif page == "Live QoS & Network Intelligence":
    st.subheader("Live network health and QoS intelligence")
    st.caption("Data is read from the controller log. Refresh to load the latest records.")

    if st.button("Refresh live telemetry", type="primary"):
        st.rerun()

    telemetry = read_controller_telemetry(
        OUTPUTS / "logs" / "controller_telemetry.log"
    )

    if not telemetry["available"]:
        st.error("Controller telemetry log not found.")
    else:
        ports = telemetry["ports"]
        probe = telemetry["probe"]
        summary = aggregate_port_metrics(telemetry)

        cpu = psutil.cpu_percent(interval=0.2)
        memory = psutil.virtual_memory().percent

        st.caption(
            f"Log updated: {telemetry['log_updated']} · "
            f"Parsed records: {telemetry['records']}"
        )

        st.markdown("### Probe quality")
        a, b, c, d = st.columns(4)
        a.metric("Latency", "N/A" if probe["latency_ms"] is None else f"{probe['latency_ms']:.3f} ms")
        b.metric("Jitter", "N/A" if probe["jitter_ms"] is None else f"{probe['jitter_ms']:.3f} ms")
        c.metric("Probe loss", "N/A" if probe["probe_loss_ratio"] is None else f"{probe['probe_loss_ratio']:.2%}")
        d.metric("Reliability", "N/A" if probe["reliability"] is None else f"{probe['reliability']:.2%}")

        st.markdown("### Switch port telemetry")
        if ports:
            df = pd.DataFrame(list(ports.values())).sort_values(["dpid", "port"])
            st.dataframe(df, hide_index=True, use_container_width=True)

            x, y, z = st.columns(3)
            x.metric("Sum of port RX", f"{summary['rx_throughput_mbps']:.3f} Mbps")
            y.metric("Sum of port TX", f"{summary['tx_throughput_mbps']:.3f} Mbps")
            z.metric("Highest port utilization", f"{summary['link_utilization']:.1%}")

            st.caption("Port-counter sums are not end-to-end application throughput.")
        else:
            st.warning("No port records yet. Generate Mininet traffic and refresh.")

        qos_metrics = {
            "latency_ms": probe["latency_ms"],
            "jitter_ms": probe["jitter_ms"],
            "probe_loss_ratio": probe["probe_loss_ratio"],
            "link_utilization": summary["link_utilization"],
            "cpu_percent": cpu,
            "memory_percent": memory,
        }

        assessment = QoSOptimizer().evaluate(qos_metrics)

        st.markdown("### QoS optimizer")
        x, y = st.columns(2)
        x.metric("Network status", assessment.status)
        y.metric(
            "QoS score",
            "N/A" if assessment.status == "INSUFFICIENT_DATA"
            else f"{assessment.score:.0f}/100"
        )
        st.write(assessment.recommendation)
        for reason in assessment.reasons:
            st.write(f"• {reason}")

        st.markdown("### Host resource usage")
        x, y = st.columns(2)
        x.metric("WSL host CPU", f"{cpu:.1f}%")
        y.metric("WSL host memory", f"{memory:.1f}%")
        st.caption("Host-level readings, not isolated controller-process measurements.")

        st.markdown("### AI detection and adaptive policy")
        x, y = st.columns(2)
        ai = telemetry["ai"]
        adaptive = telemetry["adaptive"]

        with x:
            st.markdown("**Latest AI detection**")
            if ai:
                st.write(f"Source: {ai['source']}")
                st.write(f"Suspicious: {ai['suspicious']}")
                st.write(f"Rule score: {ai['rule_score']:.3f}")
            else:
                st.info("No AI detection record found.")

        with y:
            st.markdown("**Latest adaptive decision**")
            if adaptive:
                st.write(f"Source: {adaptive['source']}")
                st.write(f"Action: {adaptive['action']}")
                st.write(f"Offered: {adaptive['offered_pps']:.1f} PPS")
                st.write(f"Cap: {adaptive['cap_pps']:.1f} PPS")
                st.write(f"Allocated: {adaptive['allocated_pps']:.1f} PPS")
                st.write(f"Adjustment: {adaptive['adjustment']}")
            else:
                st.info("No adaptive decision record found.")

        st.info("QoS recommendations are advisory only; they do not modify OpenFlow rules.")

elif page == "V3 AI Simulation":
    st.subheader("FairShield V3 — Live AI Simulation")
    st.caption("Run fresh synthetic simulations with configurable parameters.")

    with st.form("v3_simulation_form"):
        scenario = st.selectbox(
            "Traffic scenario",
            ["all", "normal", "ddos", "flash_crowd", "mixed"],
            format_func=lambda x: "Run All Scenarios" if x == "all" else x.replace("_", " ").title()
        )
        x, y, z = st.columns(3)
        windows = x.number_input("Windows", min_value=5, max_value=500, value=30, step=5)
        seed = y.number_input("Random seed", min_value=0, max_value=999999, value=7)
        capacity = z.number_input("Network capacity (PPS)", min_value=50.0, max_value=10000.0, value=500.0, step=50.0)
        run_v3 = st.form_submit_button("Run New Simulation", type="primary")

    output_dir = ROOT / "outputs_v3_dashboard_run"
    summary_file = output_dir / "v3_summary.csv"

    if run_v3:
        python_exe = ROOT / ".venv" / "bin" / "python"
        command = [
            str(python_exe), "scripts/run_v3_demo.py",
            "--scenario", scenario,
            "--windows", str(int(windows)),
            "--seed", str(int(seed)),
            "--capacity", str(float(capacity)),
            "--out", str(output_dir),
        ]

        with st.spinner("Training AI detector and running V3 simulation..."):
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True
            )

        if result.returncode == 0:
            st.success("New V3 simulation completed.")
            st.session_state["v3_last_run"] = {
                "scenario": scenario, "windows": int(windows),
                "seed": int(seed), "capacity": float(capacity)
            }
            with st.expander("Simulation console output"):
                st.code(result.stdout)
        else:
            st.error("Simulation failed.")
            st.code(result.stderr or result.stdout)

    if summary_file.exists():
        v3 = pd.read_csv(summary_file)

        last_run = st.session_state.get("v3_last_run")
        if last_run:
            st.caption(
                f"Latest run: {last_run['scenario']} | "
                f"{last_run['windows']} windows | Seed {last_run['seed']} | "
                f"Capacity {last_run['capacity']:.0f} PPS"
            )

        st.markdown("### Scenario comparison")
        selected = st.selectbox(
            "View scenario", v3["scenario"].tolist(),
            key="v3_view_scenario"
        )
        result = v3[v3["scenario"] == selected].iloc[0]

        a, b, c, d = st.columns(4)
        a.metric("Legitimate preserved", f"{result['legitimate_preservation']:.1%}")
        b.metric("Attack mitigated", f"{result['attack_mitigation']:.1%}")
        c.metric("Detection F1", f"{result['detection_f1']:.3f}")
        d.metric("Jain fairness", f"{result['jain_fairness']:.3f}")

        a, b, c = st.columns(3)
        a.metric("Mean latency", f"{result['mean_latency_ms']:.2f} ms")
        b.metric("Packet loss", f"{result['packet_loss_ratio']:.1%}")
        c.metric("Throughput", f"{result['throughput_mbps']:.2f} Mbps")

        st.markdown("### AI performance across scenarios")
        st.bar_chart(
            v3.set_index("scenario")[
                ["legitimate_preservation", "attack_mitigation", "detection_f1"]
            ]
        )

        st.markdown("### Complete simulation results")
        st.dataframe(v3, use_container_width=True)

        st.info(
            "Results are generated by the synthetic simulator. Latency, jitter, "
            "packet loss and QoS values are simulation proxies, not physical 5G measurements."
        )
    else:
        st.info("Click Run New Simulation to generate your first dashboard results.")


elif page == "Testing & limitations":
    st.subheader("Verification status")
    a, b, c = st.columns(3)
    a.metric("Automated unit tests", "27 passed", help="Latest reported test run in the project work log.")
    b.metric("Python syntax checks", "Passed", help="Latest reported py_compile check for controller and adaptive policy modules.")
    c.metric("Live congestion tightening", "Not proven", help="No clean archived controller log validates this under genuine congestion.")

    st.markdown("### Verified capabilities")
    st.markdown(
        "- Offline synthetic comparison of no defense, static threshold, FairShield V1, and V2 adaptive policy.\n"
        "- Rule-based suspicious-source detection.\n"
        "- Source-specific admission caps and weighted max-min allocation.\n"
        "- OpenFlow meter installation, meter-drop counters, and cleanup demonstrated in Mininet.\n"
        "- Single-source live rate-limiting test with receiver rate close to the configured 200 PPS cap.\n"
        "- Live legitimate-service feedback counters and adaptive relaxation observed in controller output during earlier tests."
    )
    st.markdown("### Important limitations")
    st.markdown(
        "- The final four-source archived run has sender and receiver logs, but no matching archived controller log.\n"
        "- Sustained cap tightening under verified live congestion has not been conclusively demonstrated.\n"
        "- Receiver log averages include transition intervals and must not be presented as steady-state cap measurements.\n"
        "- Synthetic detector F1 values reflect generated scenarios and are not real-world accuracy estimates.\n"
        "- No physical-link capacity, latency, jitter, CPU overhead, or real Internet traffic performance was established.\n"
        "- This is an educational research prototype, not a production security appliance."
    )
    st.caption("Keep simulated, live, and illustrative sandbox outputs clearly separated in reports and presentations.")

st.divider()
st.caption("FairShield-SDN V2 · Local dashboard · Research prototype · Not for production deployment")
