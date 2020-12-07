#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import Node
from mininet.cli import CLI
from mininet.link import TCLink


class SingleSwitchTopo(Topo):
    # "Single switch connected to n hosts."
    def build(self, n=2):
        switch = self.addSwitch("s1")
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost("h%s" % (h + 1))
            self.addLink(host, switch, bw=10)


def run():
    # "Create and test a simple network"
    topo = SingleSwitchTopo(n=4)
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    print("Simulation Begin")
    h1, h2, h3, h4 = net.get("h1", "h2", "h3", "h4")
    h1.cmd('./test/run-pub.sh')
    h1.cmd('./test/run-sub.sh')
    h2.cmd('./test/run-pub.sh')
    h2.cmd('./test/run-sub.sh')

    time.sleep(1)

    CLI(net)
    print("Simulation End")
    net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    run()
