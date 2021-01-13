import argparse
import time
from queue import Queue
from threading import RLock, Thread, Timer

import zmq

from middleware.node.const import *
from middleware.node.utils import *

"""
Query Execution
1. A Query is sent by commander (can be on any node)
2. The query should be sent to a known node
3. The query will be parsed on the receiving node (from Athena)
4. The receiving node may or may not have the required skill
    4.1 Every node has a members list and is awared of the skillset
        other nodes have
    4.2 If no such skill on this current node (or due to optimization need),
        find the qualified node, ask it to send back annotated data
    4.3 Annotation happens on the node who has the skill (only for now...,
        and annotation methods can be preinstalled on every node?)
5. The receiving node will have a decision based on the query (from Athena)
6. Send back the result to the commander node
"""


class Global:
    publisher = None
    curr_id = None
    members = {}
    skills = []
    lock = RLock()

    leader = None
    election_status = "NOLEADER"
    lock_election = RLock()

    buffer_query = None


def call_election(cand=Global.curr_id):
    if (
        Global.election_status == "WAIT"
        or Global.election_status == "ELECTED"
        and Global.leader > Global.curr_id
    ):
        return
    with Global.lock_election:
        Global.election_status = "ELECTED"
        Global.leader = cand
    print("Leader is set: ", Global.leader)
    print_and_pub("election", Global.leader, Global.publisher, "elected")


def init_election():
    with Global.lock_election:
        if Global.election_status not in ["NEEDRESP", "ELECTED"]:
            if (
                len(Global.members.keys()) == 0
                or max(Global.members.keys()) < Global.curr_id
            ):
                call_election(Global.curr_id)
            else:
                Global.election_status = "NEEDRESP"
                print_and_pub("election", Global.curr_id, Global.publisher, "elect")
                t = Timer(ELECTION_RES_TIMEOUT, call_election)
                t.start()
                t2 = Timer(ELECTION_WAIT_TIMEOUT, init_election)
                t2.start()
                print_and_pub("election", Global.curr_id, Global.publisher, "OK")


def publisher_init():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a publisher socket
    Global.publisher = context.socket(zmq.PUB)
    print("Connecting to: %s" % PUB_URL)
    Global.publisher.connect(PUB_URL)
    print_and_pub("system", "Preparing to publish...", Global.publisher)
    time.sleep(3)
    # Start heartbeat
    while True:
        print_and_pub(
            "heartbeat",
            str(int(time.time())) + "\t" + list_to_str(Global.skills),
            Global.publisher,
            Global.curr_id,
        )
        time.sleep(5)


def subscriber_init():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a subscriber socket
    subscriber = context.socket(zmq.SUB)
    print("Connecting to: %s" % SUB_URL)
    subscriber.connect(SUB_URL)

    topics = [b"heartbeat", b"election", b"query", Global.curr_id]
    for topic in topics:
        if type(topic) is str:
            topic = topic.encode("utf-8")

        # Perform the subscribe
        subscriber.setsockopt(zmq.SUBSCRIBE, topic)
        print('Subscribed to topic "%s"' % (topic.decode("utf-8")))

    while True:
        message = subscriber.recv_multipart()
        topic = message[0].decode("utf-8")
        prefix = message[1].decode("utf-8")
        body = message[2].decode("utf-8")
        if prefix != Global.curr_id:
            # print("Received: [%s] %s" % (topic, prefix))
            if topic == "heartbeat":
                on_hb_data(prefix, body)
            elif topic == "election":
                on_election_data(prefix, body)
            elif topic == Global.curr_id:
                on_dm(prefix, body)
        elif topic == "query":
            # Current node is assigned to process a query
            on_query(body, Global)


def on_hb_data(sensor_id, body):
    timestamp, skills = body.split("\t")
    # print("Get Msg from " + sensor_id)
    if sensor_id not in Global.members:
        Global.members[sensor_id] = Member(sensor_id)
        print("Current members: ", list(Global.members.keys()))
        if (
            Global.leader is None
            or Global.leader is not None
            and sensor_id > Global.leader
        ):
            init_election()
    with Global.lock:
        Global.members[sensor_id].last_sent = timestamp
        Global.members[sensor_id].last_updated = int(time.time())
        Global.members[sensor_id].skills = skills


def on_election_data(prefix, cand_id):
    if (
        prefix == "OK"
        and cand_id > Global.curr_id
        and Global.election_status == "NEEDRESP"
    ):
        with Global.lock_election:
            Global.election_status = "WAIT"
    elif prefix == "elect" and cand_id < Global.curr_id:
        if Global.election_status == "ELECTED":
            # Let new joiners know the elected leader
            print_and_pub("election", Global.leader, Global.publisher, "elected")
        else:
            init_election()
    elif prefix == "elected" and cand_id > Global.curr_id:
        if Global.election_status != "ELECTED" or Global.leader < cand_id:
            with Global.lock_election:
                Global.election_status = "ELECTED"
                Global.leader = cand_id
            print("Leader is set: ", Global.leader)


def on_dm(prefix, body):
    if prefix == "get_data":
        skill, sensor_id = body.split("\t")
        annotated_data = get_latest_data(skill)
        print_and_pub(sensor_id, str(annotated_data), Global.publisher, "decide")
    elif prefix == "decide":
        annotated_data = eval(body)
        on_query_decide(annotated_data, Global)


def detect_failure():
    while True:
        to_remove_keys = []
        curr_time = int(time.time())
        reelect = False
        for sensor, member in Global.members.items():
            if curr_time - member.last_updated > 10:
                Global.members[sensor].failed = True
            if curr_time - member.last_updated > 20 and member.failed:
                to_remove_keys.append(sensor)
        for key in to_remove_keys:
            if key == Global.leader:
                reelect = True
            del Global.members[key]
        if len(to_remove_keys) > 0:
            print("Disconnected: ", to_remove_keys)
        if reelect:
            with Global.lock_election:
                Global.election_status = "NOLEADER"
                Global.leader = None
            init_election()
        time.sleep(10)


def main(args):
    Global.curr_id = args.id
    Global.skills = args.skills.split(",")
    t1 = Thread(target=publisher_init, args=())
    t2 = Thread(target=subscriber_init, args=())
    t3 = Thread(target=detect_failure, args=())
    t1.start()
    t2.start()
    t3.start()
    print("All threads started...")
    time.sleep(1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", "-i", dest="id", type=str, help="Sensor ID")
    parser.add_argument(
        "--skills", "-s", dest="skills", type=str, help="Skills {a,b,c...}"
    )
    args = parser.parse_args()
    main(args)
