import argparse
from threading import Condition, RLock

import zmq
from middleware.brain.optimizer import Optimizer
from middleware.brain.query import *
from middleware.custom.initialize import preload, PUB_URL, SUB_URL
from middleware.node.utils import *

annotator_presets = {}
sensor_presets = {}
rules = {}


class Global:
    publisher = None
    publisher_thread = None
    publisher_context = None
    publisher_connected = False
    curr_id = None
    members = {}
    optimizer = None

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
        self.annotators = AnnotatorSet()
        self.sensors = SensorSet()

        # Approximate throughput
        self.throughput = 100


class AnnotatorSet:
    def __init__(self):
        # annotator_name -> [func, cost, sensor] (func=None if remote)
        self.map = {}

    def run(self, annotator_name, data, k):
        # TODO: Offloading here
        annotated = self.get_annotated(annotator_name, data)
        return annotated[k] if k in annotated else 0

    def add(self, annotator_name, func, cost, sensor):
        self.map[annotator_name] = [func, cost, sensor]

    def remove(self, k):
        del self.map[k]

    def get(self, k):
        return self.map[k]

    # s: string output from __repr__()
    def update(self, s):
        if s:
            for item in s.split(";"):
                k, cost, sensor_name = item.split(",")
                if k not in self.map:
                    self.map[k] = [None, int(cost), sensor_name]
                elif int(cost) < self.map[k][1]:
                    self.map[k][1] = int(cost)

    def get_annotated(self, annotator_name, data):
        if annotator_name in self.map:
            return self.map[annotator_name][0](data)
        return {}

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1]) + "," + self.map[k][2]
        return s


class SensorSet:
    def __init__(self):
        # sensor_name -> sensor_manager
        self.map = {}

    def add(self, sensor_name, sensor_manager, pos):
        self.map[sensor_name] = (sensor_manager, pos)

    def remove(self, k):
        del self.map[k]

    def get(self, k):
        return self.map[k][0]

    def get_data(self, sensor_name):
        return self.get(sensor_name).get_data()

    def stream(self, sensor_name, Global, print_and_pub, topic="result"):
        self.get(sensor_name).stream([topic, Global, print_and_pub])

    def adapt(self, bw_diff, reset_publisher):
        for sensor_name in self.map:
            if self.get(sensor_name).is_streaming:
                self.get(sensor_name).adapt(bw_diff, reset_publisher)

    def update(self, s):
        if s:
            for item in s.split(","):
                self.map[item] = None

    def __repr__(self):
        return ",".join(self.map.keys())


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
    Global.publisher_context = zmq.Context()
    # Create a publisher socket
    Global.publisher = Global.publisher_context.socket(zmq.PUB)
    # Global.publisher.setsockopt(zmq.SNDHWM, 1000)
    # Global.publisher.setsockopt(zmq.LINGER, 0)
    print("Connecting to: %s" % PUB_URL)

    Global.publisher.connect(PUB_URL)
    print_and_pub("system", "Preparing to publish...", Global.publisher)
    time.sleep(3)
    Global.publisher_connected = True

    # Start heartbeat
    while True:
        if not Global.publisher_connected:
            return
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
        Global.curr_id,
        # "bw-" + Global.curr_id,
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
        # if topic == "bw-" + Global.curr_id:
        #     message = message[:2] + [message[2:-1], message[-1]]
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
            elif topic == Global.curr_id:
                on_dm(prefix, body)
            # elif topic[:2] == "bw":
            #     on_bw(curr_ts, prefix, body)
        elif topic == "query":
            # Current node is assigned to process a query
            on_query(body, Global)


def on_hb_data(id_, timestamp, curr_ts):
    if id_ not in Global.members:
        Global.members[id_] = Member(id_)
    if Global.members[id_].last_updated == 0:
        print("Current members: ", list(Global.members.keys()))
        if Global.leader is None or Global.leader is not None and id_ > Global.leader:
            init_election()

        # Respond annotators
        print_and_pub(
            id_,
            Global.curr_id + "\t" + str(Global.members["SELF"].annotators),
            Global.publisher,
            "annotator",
        )
        # Respond sensors
        print_and_pub(
            id_,
            Global.curr_id + "\t" + str(Global.members["SELF"].sensors),
            Global.publisher,
            "sensor",
        )
    with Global.lock:
        Global.members[id_].last_updated = curr_ts
        Global.members[id_].failed = False


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
        annotator_name, key, id_ = body.split("\t")
        sensor_name = Global.members["SELF"].annotators.get(annotator_name)[2]
        data = Global.members["SELF"].sensors.get_data(sensor_name)
        val = Global.members["SELF"].annotators.run(annotator_name, data, key)
        print_and_pub(id_, str(val), Global.publisher, "decide")
    elif prefix == "decide":
        val = eval(body)
        if Global.buffer and len(Global.buffer) == 6:
            Global.buffer[4].append(val)
            schedule(Global)
    elif prefix == "stream":
        annotator_name, to = body.split("\t")
        sensor_name = Global.members["SELF"].annotators.get(annotator_name)[2]
        # topic can be set to "to" if the stream wants to be sent to the requester,
        # otherwise, in default, the stream will be sent to "result"
        Global.members["SELF"].sensors.stream(sensor_name, Global, print_and_pub)
    elif prefix == "bw":
        Global.members["SELF"].sensors.adapt(float(body), reset_publisher)
    elif prefix == "annotator":
        id_, annotator_set_string = body.split("\t")
        if id_ not in Global.members:
            Global.members[id_] = Member(id_)
        Global.members[id_].annotators.update(annotator_set_string)
        print("Received annotators set from " + id_)
    elif prefix == "sensor":
        id_, sensor_set_string = body.split("\t")
        if id_ not in Global.members:
            Global.members[id_] = Member(id_)
        Global.members[id_].sensors.update(sensor_set_string)
        print("Received sensors set from " + id_)


# def on_bw(arrival_time, prefix, packets):
#     to, is_first_trip, rtt, start_ts, packets_size = prefix.split("\t")
#     if is_first_trip == "false":  # throughput test finish
#         packets_size = float(packets_size)
#         with Global.lock:
#             Global.members[to].throughput = round(packets_size / float(rtt), PRECESION)
#         print(
#             Global.curr_id + "-" + to + ": Throughput (Mb/s)",
#             Global.members[to].throughput,
#         )
#     else:
#         rtt = arrival_time - float(start_ts)
#         packets_size = sum(map(len, packets)) / 125000.0
#         print_and_pub(
#             "bw-" + to,
#             "",
#             Global.publisher,
#             Global.curr_id
#             + "\t"
#             + "false"
#             + "\t"
#             + str(rtt)
#             + "\t"
#             + str(round(time.time(), PRECESION))
#             + "\t"
#             + str(packets_size),
#         )


def detect_failure():
    while True:
        to_remove_keys = []
        curr_time = int(time.time())
        reelect = False
        for id_, member in Global.members.items():
            if id_ == "SELF" or member.last_updated == 0:
                continue
            if curr_time - member.last_updated > 10:
                Global.members[id_].failed = True
            if curr_time - member.last_updated > 15 and member.failed:
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
        time.sleep(10)


def reset_publisher():
    print("Reset Publisher...")
    with Global.lock:
        Global.publisher_connected = False
    Global.publisher.close(linger=0)
    Global.publisher_context.destroy(linger=0)
    with Global.lock:
        Global.publisher = None
        Global.publisher_context = None
    Global.publisher_thread.join()
    Global.publisher_thread = None
    Global.publisher_thread = async_run_after(0, publisher_init)


def main(args):
    global annotator_presets, sensor_presets, rules
    # Assign values to Global
    Global.curr_id = args.id
    Global.members["SELF"] = Member("SELF")

    # Preload prior knowledge
    annotator_presets, sensor_presets, rules = preload(Global.curr_id)

    # Set optimizer
    # If no custom function, use default optimizer
    Global.optimizer = Optimizer(rules)

    # Retrieve annotating functions for current node
    for annotator_name in annotator_presets:
        module, complexity, sensor = annotator_presets[annotator_name]
        Global.members["SELF"].annotators.add(
            annotator_name, module, complexity, sensor
        )

    # Retrieve sensors info for current node
    for sensor_name in sensor_presets:
        module, src, pos = sensor_presets[sensor_name]
        sensor_manager = module.Constructor(Global.curr_id, src)
        Global.members["SELF"].sensors.add(sensor_name, sensor_manager, pos)

    Global.publisher_thread = async_run_after(0, publisher_init)
    async_run_after(0, subscriber_init)

    print("All threads started...")
    detect_failure()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", "-i", dest="id", type=str, help="Sensor ID")
    args = parser.parse_args()
    main(args)
