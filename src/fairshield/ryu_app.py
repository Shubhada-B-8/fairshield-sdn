"""FairShield SDN controller adapter for OpenFlow 1.3.

OS-Ken is preferred; Ryu imports remain as a compatibility fallback.  The
controller uses a two-table pipeline: table 0 applies a per-source meter and
jumps to table 1; table 1 performs MAC learning and forwarding.  Periodic
OpenFlow flow statistics feed a per-source policy that applies demand caps and
weighted max-min allocation in kbit/s.

This is an educational lab prototype.  It is not hardened for production.
"""
from __future__ import annotations

import time

try:  # OS-Ken is the maintained Ryu fork and is preferred.
    from os_ken.base import app_manager
    _AppBase = app_manager.OSKenApp
    from os_ken.controller import ofp_event
    from os_ken.controller.handler import (
        CONFIG_DISPATCHER, DEAD_DISPATCHER, MAIN_DISPATCHER, set_ev_cls,
    )
    from os_ken.ofproto import ofproto_v1_3
    from os_ken.lib import hub
    from os_ken.lib.packet import ethernet, ether_types, ipv4, packet, tcp, udp
except ImportError:  # pragma: no cover - compatibility path for existing Ryu labs
    try:
        from ryu.base import app_manager
        _AppBase = app_manager.RyuApp
        from ryu.controller import ofp_event
        from ryu.controller.handler import (
            CONFIG_DISPATCHER, DEAD_DISPATCHER, MAIN_DISPATCHER, set_ev_cls,
        )
        from ryu.ofproto import ofproto_v1_3
        from ryu.lib import hub
        from ryu.lib.packet import ethernet, ether_types, ipv4, packet, tcp, udp
    except ImportError as exc:  # pragma: no cover - optional integration
        raise SystemExit(
            "Neither OS-Ken nor Ryu is installed. On Linux install the optional "
            "SDN dependencies with: python -m pip install -e '.[sdn]'"
        ) from exc

from .models import FlowSample
from .adaptive_policy import AdaptiveFairnessController, AdaptivePolicyConfig, NetworkFeedback
from .detector import DetectorConfig, RuleBasedDetector
from .sdn_policy import SdnPolicyConfig, SdnSourcePolicy


POLL_SECONDS = 5.0
STALE_SECONDS = 60.0
FLOW_IDLE_TIMEOUT = 60


class FairShieldRyuApp(_AppBase):  # pragma: no cover - requires OVS/Mininet
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = SdnSourcePolicy(SdnPolicyConfig(
            capacity_kbps=10_000.0,
            attacker_cap_kbps=1_500.0,
            poll_seconds=POLL_SECONDS,
            medium_pps=300.0,
            high_pps=800.0,
            small_packet_bytes=256.0,
            port_fanout_threshold=8,
            high_bps_threshold=1_000_000.0,
            score_threshold=0.75,
        ))
        # Separate live adaptive policy; fixed policy remains available for rollback.
        self.adaptive_policy = AdaptiveFairnessController(AdaptivePolicyConfig(
            link_capacity_pps=12_500.0,
            initial_attack_cap_pps=200.0,
            min_attack_cap_pps=50.0,
            max_attack_cap_pps=1_000.0,
            detector=RuleBasedDetector(DetectorConfig(
                pps_threshold=300.0,
                high_pps_threshold=800.0,
                port_scan_threshold=8,
                bps_threshold=1_000_000.0,
                score_threshold=0.55,
            )),
        ))
        self.datapaths = {}
        self.mac_to_port: dict[int, dict[str, int]] = {}
        self.previous_counters: dict[tuple[int, str], tuple[int, int]] = {}
        self.observed_sources: set[tuple[int, str]] = set()
        self.forwarded_deltas = {}
        self.source_last_seen: dict[tuple[int, str], float] = {}
        self.source_meters: dict[int, dict[str, tuple[int, int]]] = {}
        self.next_meter_id: dict[int, int] = {}
        self.previous_port_counters = {}
        self.previous_meter_counters = {}
        self.port_deltas = {}
        self.meter_deltas = {}
        self.window_id = 0
        self.monitor_thread = hub.spawn(self._monitor)
        self.logger.info("FairShield OS-Ken/Ryu adapter started (OpenFlow 1.3)")

    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def error_msg_handler(self, ev):
        msg = ev.msg
        self.logger.error(
            "OpenFlow error from switch %s: type=%s code=%s data=%r",
            msg.datapath.id, msg.type, msg.code, msg.data[:64] if msg.data else b"",
        )

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)
            self.source_meters.pop(datapath.id, None)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        # Table 0 enforces source meters; every packet then proceeds to table 1.
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            table_id=0,
            priority=0,
            match=parser.OFPMatch(),
            instructions=[parser.OFPInstructionGotoTable(1)],
        ))
        # Table 1 sends unknown traffic to the controller for MAC learning.
        controller_actions = [parser.OFPActionOutput(
            ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER
        )]
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            table_id=1,
            priority=0,
            match=parser.OFPMatch(),
            instructions=[parser.OFPInstructionActions(
                ofp.OFPIT_APPLY_ACTIONS, controller_actions
            )],
        ))
        self.logger.info("Switch %s configured with two-table pipeline", datapath.id)

    def _monitor(self):
        while True:
            for datapath in list(self.datapaths.values()):
                parser = datapath.ofproto_parser
                datapath.send_msg(parser.OFPFlowStatsRequest(
                    datapath,
                    table_id=datapath.ofproto.OFPTT_ALL,
                    out_port=datapath.ofproto.OFPP_ANY,
                    out_group=datapath.ofproto.OFPG_ANY,
                    match=parser.OFPMatch(),
                ))
                datapath.send_msg(parser.OFPPortStatsRequest(
                    datapath,
                    port_no=datapath.ofproto.OFPP_ANY,
                ))
                for meter_id, _rate in self.source_meters.get(datapath.id, {}).values():
                    datapath.send_msg(parser.OFPMeterStatsRequest(
                        datapath,
                        meter_id=meter_id,
                    ))
            hub.sleep(POLL_SECONDS)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id

        for stat in ev.msg.body:
            port_no = int(stat.port_no)
            if port_no >= datapath.ofproto.OFPP_MAX:
                continue

            key = (dpid, port_no)
            current = (int(stat.rx_packets), int(stat.tx_packets),
                       int(stat.rx_bytes), int(stat.tx_bytes))
            previous = self.previous_port_counters.get(key)

            if previous is not None:
                delta = tuple(max(0, cur - old)
                              for cur, old in zip(current, previous))
                if any(delta):
                    self.port_deltas[key] = {
                        "timestamp": time.monotonic(),
                        "rx_packets": delta[0],
                        "tx_packets": delta[1],
                        "rx_bytes": delta[2],
                        "tx_bytes": delta[3],
                    }
                    self.logger.info(
                        "PORT_DELTA dpid=%s port=%s rx_packets=%s "
                        "tx_packets=%s rx_bytes=%s tx_bytes=%s",
                        dpid, port_no, *delta,
                    )

            self.previous_port_counters[key] = current

    @set_ev_cls(ofp_event.EventOFPMeterStatsReply, MAIN_DISPATCHER)
    def meter_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id

        meter_to_source = {
            meter_id: src_ip
            for src_ip, (meter_id, _rate)
            in self.source_meters.get(dpid, {}).items()
        }

        for stat in ev.msg.body:
            meter_id = int(stat.meter_id)
            src_ip = meter_to_source.get(meter_id)
            if src_ip is None:
                continue

            dropped_packets = sum(
                int(band.packet_band_count)
                for band in (stat.band_stats or [])
            )
            dropped_bytes = sum(
                int(band.byte_band_count)
                for band in (stat.band_stats or [])
            )
            current = (int(stat.packet_in_count),
                       int(stat.byte_in_count),
                       dropped_packets, dropped_bytes)
            key = (dpid, meter_id)
            previous = self.previous_meter_counters.get(key)

            if previous is not None:
                delta = tuple(max(0, cur - old)
                              for cur, old in zip(current, previous))
                if any(delta):
                    self.meter_deltas[(dpid, src_ip)] = {
                        "timestamp": time.monotonic(),
                        "input_packets": delta[0],
                        "input_bytes": delta[1],
                        "dropped_packets": delta[2],
                        "dropped_bytes": delta[3],
                    }
                    self.logger.info(
                        "METER_DELTA source=%s meter_id=%s "
                        "input_packets=%s input_bytes=%s "
                        "dropped_packets=%s dropped_bytes=%s",
                        src_ip, meter_id, *delta,
                    )

            self.previous_meter_counters[key] = current

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match.get("in_port")
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt is not None:
            self._ensure_source_observer(datapath, ip_pkt.src)

        dpid = datapath.id
        learned = self.mac_to_port.setdefault(dpid, {})
        learned[eth.src] = in_port
        out_port = learned.get(eth.dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        # Install a table-1 forwarding entry only after the destination is known.
        if out_port != ofp.OFPP_FLOOD:
            match_fields = {
                "in_port": in_port,
                "eth_src": eth.src,
                "eth_dst": eth.dst,
                "eth_type": eth.ethertype,
            }
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt is not None:
                match_fields.update({"eth_type": ether_types.ETH_TYPE_IP,
                                     "ipv4_src": ip_pkt.src, "ipv4_dst": ip_pkt.dst})
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                udp_pkt = pkt.get_protocol(udp.udp)
                if tcp_pkt is not None:
                    match_fields.update({"ip_proto": 6, "tcp_dst": tcp_pkt.dst_port})
                elif udp_pkt is not None:
                    match_fields.update({"ip_proto": 17, "udp_dst": udp_pkt.dst_port})
            match = parser.OFPMatch(**match_fields)
            instructions = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            datapath.send_msg(parser.OFPFlowMod(
                datapath=datapath,
                table_id=1,
                priority=100,
                match=match,
                instructions=instructions,
                idle_timeout=FLOW_IDLE_TIMEOUT,
            ))

        data = None if msg.buffer_id != ofp.OFP_NO_BUFFER else msg.data
        datapath.send_msg(parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        ))

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        now = time.monotonic()

        # Table 0 = offered packets before enforcement.
        # Table 1 = packets forwarded by source-specific forwarding flows.
        records = {}

        for stat in ev.msg.body:
            match = stat.match
            src_ip = match.get("ipv4_src")
            if not src_ip or match.get("eth_type") != ether_types.ETH_TYPE_IP:
                continue

            table_id = int(stat.table_id)
            if table_id not in (0, 1):
                continue

            src_ip = str(src_ip)
            rec = records.setdefault(src_ip, {
                "offered_packets": 0,
                "offered_bytes": 0,
                "forwarded_packets": 0,
                "forwarded_bytes": 0,
                "ports": set(),
                "table1_seen": False,
                "offered_pending": False,
                "forwarded_pending": False,
            })

            key = (dpid, f"{table_id}:{int(stat.priority)}:{match}")
            current = (int(stat.packet_count), int(stat.byte_count))
            previous = self.previous_counters.get(key)

            if table_id == 1:
                rec["table1_seen"] = True
                tcp_dst = match.get("tcp_dst")
                udp_dst = match.get("udp_dst")
                if tcp_dst is not None:
                    rec["ports"].add(("tcp", int(tcp_dst)))
                if udp_dst is not None:
                    rec["ports"].add(("udp", int(udp_dst)))

            if previous is None:
                self.previous_counters[key] = current
                # Do not treat lifetime counters as a five-second delta.
                if current[0] > 0:
                    if table_id == 0:
                        rec["offered_pending"] = True
                    else:
                        rec["forwarded_pending"] = True
                continue

            packet_delta = max(0, current[0] - previous[0])
            byte_delta = max(0, current[1] - previous[1])
            self.previous_counters[key] = current

            if table_id == 0:
                rec["offered_packets"] += packet_delta
                rec["offered_bytes"] += byte_delta
            else:
                rec["forwarded_packets"] += packet_delta
                rec["forwarded_bytes"] += byte_delta

                if packet_delta or byte_delta:
                    self.forwarded_deltas[(dpid, src_ip)] = {
                        "timestamp": now,
                        "packets": packet_delta,
                        "bytes": byte_delta,
                    }

            if packet_delta or byte_delta:
                self.source_last_seen[(dpid, src_ip)] = now

        samples = []
        records_by_source = {}

        for src_ip, rec in records.items():
            # h5 is the lab receiver, not a legitimate client.
            if src_ip == "10.0.0.5":
                continue
            if rec["offered_pending"] or rec["offered_packets"] <= 0:
                continue

            sample = FlowSample(
                window_id=self.window_id + 1,
                src_ip=src_ip,
                dst_ip="0.0.0.0",
                packets=rec["offered_packets"],
                byte_count=rec["offered_bytes"],
                syn_packets=0,
                unique_dst_ports=len(rec["ports"]),
                duration_s=POLL_SECONDS,
                label="unknown",
            )
            samples.append(sample)
            records_by_source[src_ip] = rec

        if samples:
            self.window_id += 1

        # Switch port 5 is the egress link toward h5.
        port = self.port_deltas.get((dpid, 5))
        port_fresh = (
            port is not None
            and now - port["timestamp"] <= 2 * POLL_SECONDS
        )

        if port_fresh and samples:
            utilization = min(
                1.0,
                port["tx_bytes"] * 8 / (20_000_000 * POLL_SECONDS),
            )

            adaptive_samples = []
            feedback_by_source = {}
            sample_by_source = {}

            for sample in samples:
                drop_ratio = 0.0
                meter = self.source_meters.get(dpid, {}).get(sample.src_ip)

                if meter is not None:
                    measured = self.meter_deltas.get((dpid, sample.src_ip))
                    if (
                        measured is not None
                        and now - measured["timestamp"] <= 2 * POLL_SECONDS
                        and measured["input_packets"] > 0
                    ):
                        drop_ratio = min(
                            1.0,
                            measured["dropped_packets"]
                            / measured["input_packets"],
                        )

                adaptive_samples.append(sample)
                sample_by_source[sample.src_ip] = sample
                feedback_by_source[sample.src_ip] = NetworkFeedback(
                    capacity_utilization=utilization,
                    legitimate_service_ratio=None,
                    source_meter_drop_ratio=drop_ratio,
                )

            # Both offered and forwarded deltas came from this same
            # OFPTT_ALL flow-statistics reply.
            legitimate_offered = 0
            legitimate_forwarded = 0
            legitimate_sources = []
            service_complete = True

            for sample in adaptive_samples:
                detection = self.adaptive_policy.detector.detect(sample)
                # Do not count currently metered attack sources as legitimate.
                if (
                    detection.suspicious
                    or sample.src_ip in self.source_meters.get(dpid, {})
                ):
                    continue

                rec = records_by_source[sample.src_ip]
                if not rec["table1_seen"] or rec["forwarded_pending"]:
                    service_complete = False
                    break

                legitimate_sources.append(sample.src_ip)
                legitimate_offered += rec["offered_packets"]
                legitimate_forwarded += rec["forwarded_packets"]

            service_ratio = None
            if service_complete and legitimate_sources and legitimate_offered > 0:
                raw_ratio = legitimate_forwarded / legitimate_offered
                if raw_ratio <= 1.05:
                    service_ratio = min(1.0, raw_ratio)

            if service_ratio is not None:
                feedback_by_source = {
                    src_ip: NetworkFeedback(
                        capacity_utilization=feedback.capacity_utilization,
                        legitimate_service_ratio=service_ratio,
                        source_meter_drop_ratio=feedback.source_meter_drop_ratio,
                    )
                    for src_ip, feedback in feedback_by_source.items()
                }
                self.logger.info(
                    "LEGITIMATE_SERVICE sources=%s offered_packets=%s "
                    "forwarded_packets=%s ratio=%.3f",
                    ",".join(sorted(legitimate_sources)),
                    legitimate_offered,
                    legitimate_forwarded,
                    service_ratio,
                )
            else:
                self.logger.info(
                    "LEGITIMATE_SERVICE unavailable complete=%s sources=%s",
                    service_complete,
                    ",".join(sorted(legitimate_sources)),
                )

            for decision in self.adaptive_policy.decide(
                adaptive_samples, feedback_by_source
            ):
                sample = sample_by_source[decision.src_ip]

                if decision.action == "RATE_LIMIT":
                    rate_kbps = (
                        decision.allocated_pps
                        * sample.avg_packet_bytes
                        * 8 / 1000
                    )
                    self._ensure_source_meter(
                        datapath, decision.src_ip, rate_kbps
                    )
                else:
                    self._remove_source_meter(datapath, decision.src_ip)

                self.logger.info(
                    "ADAPTIVE source=%s action=%s offered_pps=%.1f "
                    "cap_pps=%.1f allocated_pps=%.1f utilization=%.3f "
                    "legitimate_service=%.3f meter_drop=%.3f adjustment=%s",
                    decision.src_ip,
                    decision.action,
                    decision.offered_pps,
                    decision.adaptive_cap_pps,
                    decision.allocated_pps,
                    utilization,
                    service_ratio if service_ratio is not None else -1.0,
                    feedback_by_source[decision.src_ip].source_meter_drop_ratio,
                    decision.adjustment,
                )

        # Remove rules for sources whose flows have expired.
        for (meter_dpid, src_ip), last_seen in list(self.source_last_seen.items()):
            if meter_dpid == dpid and now - last_seen > STALE_SECONDS:
                self._remove_source_meter(datapath, src_ip)
                self.source_last_seen.pop((meter_dpid, src_ip), None)

    def _ensure_source_observer(self, datapath, src_ip: str):
        dpid = datapath.id
        key = (dpid, str(src_ip))
        if key in self.observed_sources:
            return

        parser = datapath.ofproto_parser
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=src_ip,
        )
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            table_id=0,
            priority=100,
            match=match,
            instructions=[
                parser.OFPInstructionGotoTable(1),
            ],
            idle_timeout=0,
            hard_timeout=0,
        ))
        self.observed_sources.add(key)
        self.logger.info(
            "SOURCE_OBSERVER_REQUEST source=%s table=0 priority=100",
            src_ip,
        )

    def _ensure_source_meter(self, datapath, src_ip: str, rate_kbps: float):
        dpid = datapath.id
        parser = datapath.ofproto_parser
        ofp = datapath.ofproto
        meters = self.source_meters.setdefault(dpid, {})
        safe_rate = max(64, int(round(rate_kbps)))
        current = meters.get(src_ip)

        if current is None:
            meter_id = self.next_meter_id.get(dpid, 1)
            if meter_id >= ofp.OFPM_MAX:
                self.logger.error("No OpenFlow meter IDs remain on switch %s", dpid)
                return
            self.next_meter_id[dpid] = meter_id + 1
            command = ofp.OFPMC_ADD
        else:
            meter_id, old_rate = current
            if abs(safe_rate - old_rate) / max(old_rate, 1) < 0.05:
                return
            command = ofp.OFPMC_MODIFY

        band = parser.OFPMeterBandDrop(rate=safe_rate, burst_size=max(64, safe_rate // 10))
        datapath.send_msg(parser.OFPMeterMod(
            datapath=datapath,
            command=command,
            flags=ofp.OFPMF_KBPS | ofp.OFPMF_BURST,
            meter_id=meter_id if current is None else current[0],
            bands=[band],
        ))
        self.logger.info(
            "METER_REQUEST action=%s source=%s meter_id=%s rate=%s kbps",
            "ADD" if current is None else "MODIFY",
            src_ip,
            meter_id if current is None else current[0],
            safe_rate,
        )
        if current is None:
            instructions = [
                parser.OFPInstructionMeter(meter_id),
                parser.OFPInstructionGotoTable(1),
            ]
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip)
            datapath.send_msg(parser.OFPFlowMod(
                datapath=datapath,
                table_id=0,
                priority=40000,
                match=match,
                instructions=instructions,
                idle_timeout=0,
                hard_timeout=0,
            ))
            self.logger.info(
                "METER_RULE_REQUEST source=%s meter_id=%s table=0 priority=40000",
                src_ip, meter_id,
            )
        meters[src_ip] = (meter_id if current is None else current[0], safe_rate)

    def _remove_source_meter(self, datapath, src_ip: str):
        dpid = datapath.id
        meters = self.source_meters.get(dpid, {})
        current = meters.pop(src_ip, None)
        if current is None:
            return
        parser = datapath.ofproto_parser
        ofp = datapath.ofproto
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip)
        datapath.send_msg(parser.OFPFlowMod(
            datapath=datapath,
            command=ofp.OFPFC_DELETE,
            table_id=0,
            out_port=ofp.OFPP_ANY,
            out_group=ofp.OFPG_ANY,
            match=match,
        ))
        datapath.send_msg(parser.OFPMeterMod(
            datapath=datapath,
            command=ofp.OFPMC_DELETE,
            flags=0,
            meter_id=current[0],
            bands=[],
        ))
        self.logger.info(
            "METER_DELETE_REQUEST source=%s meter_id=%s",
            src_ip, current[0],
        )
