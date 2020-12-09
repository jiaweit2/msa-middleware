#!/usr/bin/python
import time
import os

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
    os.popen('ovs-vsctl add-port s1 ens33')
    h1, h2, h3, h4 = net.get("h1", "h2", "h3", "h4")
    h1.cmdPrint('dhclient '+h1.defaultIntf().name)
    h2.cmdPrint('dhclient '+h2.defaultIntf().name)
    h3.cmdPrint('dhclient '+h3.defaultIntf().name)
    h4.cmdPrint('dhclient '+h4.defaultIntf().name)

    h4.cmd('python3 node/run.py --id 0004 &')
    h1.cmd('python3 node/run.py --id 0001 &')
    h3.cmd('python3 node/run.py --id 0003 &')
    h2.cmd('python3 node/run.py --id 0002 &')

    CLI(net)
    print("Simulation End")
    net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    run()
