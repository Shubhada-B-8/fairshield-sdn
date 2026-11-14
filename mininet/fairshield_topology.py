"""Isolated six-host Mininet topology for FairShield-SDN / OpenFlow 1.3."""
from mininet.topo import Topo


class FairShieldTopo(Topo):
    def build(self):
        switch = self.addSwitch("s1", protocols="OpenFlow13")
        # h1/h2: legitimate clients; h3/h4: controlled lab attack generators;
        # h5: UDP sink/server; h6: optional extra client.
        for i in range(1, 7):
            host = self.addHost(f"h{i}", ip=f"10.0.0.{i}/24")
            self.addLink(host, switch, bw=20, delay="2ms")


topos = {"fairshieldtopo": (lambda: FairShieldTopo())}
