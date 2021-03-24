#!/usr/bin/python
import time
import os

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.term import makeTerms
from mininet.link import TCLink
from mininet.node import OVSSwitch, Controller, RemoteController


class SingleSwitchTopo(Topo):
    # "Single switch connected to n hosts."
    def build(self, n=2):
        switch = self.addSwitch("s1")
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost("h%s" % (h + 1))
            self.addLink(host, switch, bw=5, delay="5ms")


def run():
    # "Create and test a simple network"
    topo = SingleSwitchTopo(n=4)
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    print("Simulation Begin")

    h1, h2, h3, h4 = net.get("h1", "h2", "h3", "h4")
    h1.cmd("source venv/bin/activate")
    h2.cmd("source venv/bin/activate")
    h3.cmd("source venv/bin/activate")
    h4.cmd("source venv/bin/activate")

    # Start the server at h1
    h1.cmd("cd server")
    h1.cmd("./start.sh")
    h1.cmd("cd ..")
    time.sleep(1)

    h4.cmd("python -u middleware/node/node.py --id 0004 --annotators NUL &")
    h1.cmd("python -u middleware/node/node.py --id 0001 --annotators NUL &")
    h3.cmd(
        "python -u middleware/node/node.py --id 0003 --annotators YOLO > temp 2>&1 &"
    )
    h2.cmd("python -u middleware/node/node.py --id 0002 --annotators NUL &")

    h1.cmd("deactivate")
    h2.cmd("deactivate")
    h3.cmd("deactivate")
    h4.cmd("deactivate")

    # Changing bandwidth
    s1 = net.get("s1")
    links1 = h1.connectionsTo(s1)
    links2 = h3.connectionsTo(s1)

    terms = makeTerms([h1, h3], "Term")

    while True:
        try:
            bw = float(input("Modify bandwidth to: "))
        except Exception:
            continue
        except KeyboardInterrupt:
            break
        links1[0][1].config(bw=bw)
        links2[0][1].config(bw=bw)
        # net.iperf((h1, h3), l4Type="TCP")

    print("\nSimulation End")

    # Cleanup
    for p in terms:
        p.kill()
    h1.cmd("pkill -f aurora")
    h1.cmd("pkill -f node")
    h2.cmd("pkill -f node")
    h3.cmd("pkill -f node")
    h4.cmd("pkill -f node")
    net.stop()


if __name__ == "__main__":
    # Tell mininet to print useful information
    run()
