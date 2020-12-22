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

from node.const import *


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
    h1.cmd('cd /home/mike/Project/aurora-net-iobt-cra-site-server/src/server')
    h1.cmd('docker-compose up -d')
    h1.cmd('cd /home/mike/Project/msa-middleware')

    h4.cmd('node/run.sh 0004 &')
    h1.cmd('node/run.sh 0001 &')
    h3.cmd('node/run.sh 0003 &')
    h2.cmd('node/run.sh 0002 &')

    CLI(net)
    print("Simulation End")

    # Cleanup
    h1.cmd('cd /home/mike/Project/aurora-net-iobt-cra-site-server/src/server')
    h1.cmd('docker-compose down')
    os.popen('sudo docker stop $(sudo docker ps -aq)')
    net.stop()



if __name__ == "__main__":
    # Tell mininet to print useful information
    run()
