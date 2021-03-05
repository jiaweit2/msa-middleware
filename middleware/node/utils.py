import time
from threading import Thread
from zmq import SNDMORE

import cv2
from middleware.node.const import *
from middleware.preset.annotators import annotator_to_sensor


class Member:
    def __init__(self, id_):
        self.id = id_
        self.failed = False
        self.last_updated = 0
        if id_ != "SELF":
            self.last_updated = int(time.time())
        self.last_sent = 0
        self.annotators = AnnotatorSet()

        # Calculate throughput
        self.start_ts = 0
        self.throughput = 0


class AnnotatorSet:
    def __init__(self):
        self.map = {}  # -> [func, cost] (func=None if remote)

    def run(self, annotator, k):
        if annotator in self.map:
            # Get latest data
            sensor = annotator_to_sensor[annotator]
            data = get_sensor_data(sensor)
            return (self.map[annotator][0](data))[k]
        return None

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

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1])
        return s


def get_sensor_data(sensor):
    # Retrieve latest data from sensor
    if sensor == "Camera":
        # image loading
        img = cv2.imread(CAM_DATA_PATH)
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        # height, width, channels = img.shape
        data = cv2.imencode(".jpg", img)[1].tobytes()
        return data
    elif sensor == "IR":
        return ""
    elif sensor == "SR":
        return ""


def post_process_coa(coas):
    for coa in coas:
        if len(coas[coa]) > 0 and coas[coa][-1] != ")" and coas[coa] != "otherwise":
            coas[coa] = "And(" + coas[coa] + ")"


def async_run_after(t, func):
    t = Thread(target=run_after, args=(t, func))
    t.start()


def run_after(t, func):
    time.sleep(t)
    func()


def print_and_pub(topic, body, publisher, prefix=""):
    if type(topic) is str:
        btopic = topic.encode("utf-8")
    else:
        btopic = topic
        topic = topic.decode("utf-8")

    if type(prefix) is str:
        bprefix = prefix.encode("utf-8")
    else:
        bprefix = prefix

        if prefix is not None:
            prefix = prefix.decode("utf-8")

    if type(body) is str:
        bbody = body.encode("utf-8")
    else:
        bbody = body
        body = body.decode("utf-8")

    publisher.send_multipart([btopic, bprefix, bbody])


def measure_throughput(Global, receiver, is_first_trip, packets=None):
    publisher, sender = Global.publisher, Global.curr_id

    if not packets:
        packets = [b"x" * PACKETSIZE for i in range(PACKETCOUNT)]
    packets_size = sum(map(len, packets))
    publisher.send(("bw-" + receiver).encode("utf-8"), SNDMORE)
    if not isinstance(is_first_trip, bytes):
        is_first_trip = "true" if is_first_trip else "false"
    publisher.send((sender + "\t" + is_first_trip).encode("utf-8"), SNDMORE)

    if is_first_trip == "true":
        with Global.lock:
            Global.members[receiver].start_ts = round(time.time(), PRECESION)

    for i in range(len(packets)):
        if i == len(packets) - 1:
            publisher.send(packets[i])
        else:
            publisher.send(packets[i], SNDMORE)
