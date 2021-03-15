import argparse
from threading import RLock, Condition

import zmq
from middleware.brain.optimizer import Optimizer
from middleware.brain.query import *
from middleware.brain.cam_manager import CamManager
from middleware.node.utils import *
from middleware.preset.annotators import *


class Global:
    publisher = None
    curr_id = None
    members = {}
    # If no custom function, use default optimizer
    optimizer = Optimizer()
    cam_manager = None

    leader = None
    election_status = "NOLEADER"

    lock = RLock()
    lock_election = RLock()
    lock_msg = RLock()
    cv = Condition()

    buffer = None
    msg_buffer = []


class Member:
    def __init__(self, id_):
        self.id = id_
        self.failed = False
        self.last_updated = 0
        if id_ != "SELF":
            self.last_updated = int(time.time())
        self.annotators = AnnotatorSet()

        # Approximate throughput
        self.throughput = 100


class AnnotatorSet:
    def __init__(self):
        self.map = {}  # -> [func, cost] (func=None if remote)

    def run(self, annotator, data, k):
        # TODO: Offloading here
        annotated = self.get_annotated(annotator, data)
        return annotated[k] if k in annotated else 0

    def add(self, annotator, annotator_meta):
        annotator_meta[1] = int(annotator_meta[1])
        self.map[annotator] = annotator_meta

    def remove(self, annotator):
        del self.map[annotator]

    # s: string output from __repr__()
    def update(self, s):
        if s:
            for item in s.split(";"):
                k, cost = item.split(",")
                if k not in self.map:
                    self.map[k] = [None, int(cost)]
                elif cost < self.map[k][1]:
                    self.map[k][1] = int(cost)

    def get_annotated(self, annotator, data):
        if annotator in self.map:
            return self.map[annotator][0](data)
        return {}

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1])
        return s


def call_election(cand=None):
    if (
        Global.election_status == "WAIT"
        or Global.election_status == "ELECTED"
        and Global.leader > Global.curr_id
    ):
        return
    if cand is None:
        cand = Global.curr_id

    with Global.lock_election:
        Global.election_status = "ELECTED"
        Global.leader = cand
    print("Leader is set: ", Global.leader)
    print_and_pub("election", Global.leader, Global.publisher, "elected")


def init_election():
    with Global.lock_election:
        if Global.election_status not in ["NEEDRESP", "ELECTED"]:
            if (
                len(Global.members.keys()) == 1
                or max(Global.members.keys()) < Global.curr_id
            ):
                call_election()
            else:
                Global.election_status = "NEEDRESP"
                print_and_pub("election", Global.curr_id, Global.publisher, "elect")
                async_run_after(ELECTION_RES_TIMEOUT, call_election)
                async_run_after(ELECTION_WAIT_TIMEOUT, init_election)
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

    # Tell others my annotators
    async_run_after(
        7,
        lambda: print_and_pub(
            "annotator",
            str(Global.members["SELF"].annotators),
            Global.publisher,
            Global.curr_id,
        ),
    )

    # Start heartbeat
    while True:
        print_and_pub(
            "heartbeat",
            str(round(time.time(), PRECESION)),
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

    topics = [
        "heartbeat",
        "election",
        "query",
        "annotator",
        Global.curr_id,
        "bw-" + Global.curr_id,
    ]
    for topic in topics:
        if type(topic) is str:
            topic = topic.encode("utf-8")

        # Perform the subscribe
        subscriber.setsockopt(zmq.SUBSCRIBE, topic)
        print('Subscribed to topic "%s"' % (topic.decode("utf-8")))

    async_run_after(0, message_buffer)

    while True:
        message = subscriber.recv_multipart()
        curr_ts = round(time.time(), PRECESION)

        # Add to message buffer and notify a new message
        with Global.lock_msg:
            Global.msg_buffer.append(message + [curr_ts])
        with Global.cv:
            Global.cv.notify()


def message_buffer():
    while True:
        with Global.cv:
            while len(Global.msg_buffer) == 0:
                Global.cv.wait()
        with Global.lock_msg:
            message = Global.msg_buffer.pop(0)

        topic = message[0].decode("utf-8")
        if topic == "bw-" + Global.curr_id:
            message = message[:2] + [message[2:-1], message[-1]]
        prefix = message[1].decode("utf-8")
        body = message[2]
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        curr_ts = message[3]
        if prefix != Global.curr_id:
            # print("Received: [%s] %s" % (topic, prefix))
            if topic == "heartbeat":
                on_hb_data(prefix, body, curr_ts)
            elif topic == "election":
                on_election_data(prefix, body)
            elif topic == "annotator":
                on_annotator(prefix, body)
            elif topic == Global.curr_id:
                on_dm(prefix, body)
            elif topic[:2] == "bw":
                on_bw(curr_ts, prefix, body)
        elif topic == "query":
            # Current node is assigned to process a query
            on_query(body, Global)


def on_hb_data(id_, timestamp, curr_ts):
    # print("Get Msg from " + id_)
    if id_ not in Global.members:
        Global.members[id_] = Member(id_)
        print("Current members: ", list(Global.members.keys()))
        if Global.leader is None or Global.leader is not None and id_ > Global.leader:
            init_election()
        measure_throughput(Global, id_)
    with Global.lock:
        Global.members[id_].last_updated = curr_ts


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


def on_annotator(id_, annotator_set_string):
    Global.members[id_].annotators.update(annotator_set_string)
    print("Received annotators set from " + id_)


def on_dm(prefix, body):
    if prefix == "get_data":
        annotator, key, sensor_id = body.split("\t")
        data = get_sensor_data(annotator, Global)
        val = Global.members["SELF"].annotators.run(annotator, data, key)
        print_and_pub(sensor_id, str(val), Global.publisher, "decide")
    elif prefix == "decide":
        val = eval(body)
        if Global.buffer and len(Global.buffer) == 6:
            Global.buffer[4].append(val)
            schedule(Global)


def on_bw(arrival_time, prefix, packets):
    to, is_first_trip, rtt, start_ts, packets_size = prefix.split("\t")
    if is_first_trip == "false":  # throughput test finish
        packets_size = float(packets_size)
        with Global.lock:
            Global.members[to].throughput = round(packets_size / float(rtt), PRECESION)
        print(
            Global.curr_id + "-" + to + ": Throughput (Mb/s)",
            Global.members[to].throughput,
        )
    else:
        rtt = arrival_time - float(start_ts)
        packets_size = sum(map(len, packets)) / 125000.0
        print_and_pub(
            "bw-" + to,
            "",
            Global.publisher,
            Global.curr_id
            + "\t"
            + "false"
            + "\t"
            + str(rtt)
            + "\t"
            + str(round(time.time(), PRECESION))
            + "\t"
            + str(packets_size),
        )


def detect_failure():
    while True:
        to_remove_keys = []
        curr_time = int(time.time())
        reelect = False
        for id_, member in Global.members.items():
            if id_ == "SELF":
                continue
            if curr_time - member.last_updated > 20:
                Global.members[id_].failed = True
            if curr_time - member.last_updated > 40 and member.failed:
                to_remove_keys.append(id_)
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
        time.sleep(20)


def main(args):
    # Assign values to Global
    Global.curr_id = args.id
    Global.members["SELF"] = Member("SELF")
    # Retrieve preset annotating functions
    annotators = args.annotators.split(",")
    for annotator in annotators:
        if annotator in annotator_presets:
            Global.members["SELF"].annotators.add(
                annotator, annotator_presets[annotator]
            )
            sensor = annotator_to_sensor[annotator]
            if sensor == Sensor.CAM and Global.cam_manager is None:
                Global.cam_manager = CamManager(
                    annotator_presets[annotator], CAM_DATA_PATH
                )
        else:
            print(annotator + ": NOT found in annotator preset")

    async_run_after(0, publisher_init)
    async_run_after(0, subscriber_init)
    async_run_after(0, detect_failure)

    print("All threads started...")
    time.sleep(1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", "-i", dest="id", type=str, help="Sensor ID")
    parser.add_argument(
        "--annotators", "-a", dest="annotators", type=str, help="Annotators {a,b,c...}"
    )
    args = parser.parse_args()
    main(args)
