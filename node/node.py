#!/usr/bin/python

from threading import Thread
from queue import Queue
from threading import RLock
from collections import defaultdict
import time
import argparse

from athena.summarization.pubsub.publisher import Publisher
from athena.summarization.pubsub.subscriber import Subscriber


class Member:
    def __init__(self, name):
        self.name = name
        self.failed = False
        self.last_updated = int(time.time())
        self.last_sent = 0


class Global:
    curr_sensor = None
    members = {}
    running_node_count = 0
    lock = RLock()

    leader = None
    election_status = "NOLEADER"
    election = defaultdict(int)
    p_election = Publisher("/all/election")
    vote_count = 0
    lock_election = RLock()


def heartbeat_pub(sensor_prefix):
    p = Publisher("/all/heartbeat")
    while True:
        with Global.lock_election:
            if Global.election_status == "NOLEADER":
                Global.p_election.produce("VOTE", get_candidate())
                Global.p_election.update_list()
                Global.election_status = "ELECTING"
        p.produce(sensor_prefix, str(int(time.time())))
        p.update_list()
        time.sleep(5)


def heartbeat_sub():
    s = Subscriber()
    s.add_prefix("/all/heartbeat", on_hb_data)
    s.add_prefix("/all/election", on_election_data)
    s.subscribe()


def on_hb_data(sensor_prefix, timestamp):
    print("Receive hb data: ")
    print(sensor_prefix, timestamp)
    sensor_prefix = sensor_prefix[len("/all/heartbeat") :]
    if sensor_prefix != Global.curr_sensor:
        with Global.lock:
            if sensor_prefix not in Global.members:
                Global.members[sensor_prefix] = Member(sensor_prefix)
                Global.running_node_count += 1
                print("Current members: ", list(Global.members.keys()))
            Global.members[sensor_prefix].last_sent = timestamp
            Global.members[sensor_prefix].last_updated = int(time.time())


def on_election_data(prefix, candidate):
    prefix = prefix[len("/all/election") :]
    if candidate == Global.curr_sensor:
        return
    print("Receive election data: ")
    print(prefix, candidate)
    if prefix == "/VOTE":
        with Global.lock_election:
            if Global.election_status == "ELECTED":
                Global.p_election.produce("ELECTED", leader)
                Global.p_election.update_list()
            else:
                Global.election[candidate] += 1
                Global.vote_count += 1
                if Global.vote_count == Global.running_node_count:
                    sorted_result = sorted(Global.election.items(), key=lambda x: x[1])
                    Global.p_election.produce("ELECTED", sorted_result[-1][0])
                    Global.p_election.update_list()
    elif prefix == "/ELECTED":
        with Global.lock_election:
            if Global.election_status != "ELECTED":
                reset_election()
                Global.leader = candidate
                Global.election_status = "ELECTED"


def detect_failure():
    while True:
        to_remove_keys = []
        curr_time = int(time.time())
        with Global.lock:
            for sensor, member in Global.members.items():
                if curr_time - member.last_updated > 20:
                    member.failed = True
                    Global.running_node_count -= 1
                if curr_time - member.last_updated > 40 and member.failed:
                    to_remove_keys.append(sensor)
            for key in to_remove_keys:
                with Global.lock_election:
                    if key == Global.leader and Global.election_status != "ELECTING":
                        Global.p_election.produce("/VOTE", get_candidate())
                        Global.p_election.update_list()
                        Global.election_status = "ELECTING"
                del Global.members[key]
        time.sleep(10)


# Election for leader
def get_candidate():
    # Vote for the latest updated node
    candidate = Global.curr_sensor
    ts = 0
    for sensor, member in Global.members.items():
        if not member.failed and member.last_updated > ts:
            ts = member.last_updated
            candidate = sensor
    return candidate


def reset_election():
    Global.vote_count = 0
    Global.election = defaultdict(int)


def main(args):
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a publisher socket
    publisher = context.socket(zmq.PUB)
    pub_url = os.environ['AURORA_CRA_LOCAL_PROXY_UPLINK_PORT']
    print ("Connecting to: %s" % pub_url)
    # Connect
    publisher.connect(pub_url)

    Global.curr_sensor = args.prefix
    t1 = Thread(target=heartbeat_pub, args=(args.prefix,))
    t2 = Thread(target=heartbeat_sub, args=())
    t3 = Thread(target=detect_failure, args=())
    t1.start()
    time.sleep(5)
    t2.start()
    t3.start()
    print("All threads started...")
    time.sleep(1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", "-p", dest="prefix", type=str, help="Sensor prefix")
    args = parser.parse_args()
    main(args)