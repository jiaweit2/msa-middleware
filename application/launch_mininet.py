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


AURORA_DIR = "/mnt/hgfs/Project/aurora-net-iobt-cra-site-server"


def run():
    # "Create and test a simple network"
    topo = SingleSwitchTopo(n=4)
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    print("Simulation Begin")

    h1, h2, h3, h4 = net.get("h1", "h2", "h3", "h4")
    h1.cmd("cd " + AURORA_DIR + "/src/server")
    h1.cmd("docker-compose up -d")
    h1.cmd("cd -")

    h4.cmd("../middleware/node/run.sh 0004 Wind &")
    h1.cmd("../middleware/node/run.sh 0001 Thermo &")
    h3.cmd("../middleware/node/run.sh 0003 Camera &")
    h2.cmd("../middleware/node/run.sh 0002 Temp &")

    CLI(net)
    print("Simulation End")

    # Cleanup
    h1.cmd("pkill -f commander")
    h1.cmd("pkill -f node")
    h2.cmd("pkill -f node")
    h3.cmd("pkill -f node")
    h4.cmd("pkill -f node")
    time.sleep(2)

    h1.cmd("cd " + AURORA_DIR + "/src/server")
    h1.cmd("docker-compose down")
    os.popen("sudo docker stop $(sudo docker ps -aq)")
    net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    run()
