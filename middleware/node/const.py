import time
from middleware.preset.annotators import annotator_to_sensor
from middleware.node.utils import get_sensor_data


class Member:
    def __init__(self, _id):
        self.id = _id
        self.failed = False
        self.last_updated = 0
        if _id != "SELF":
            self.last_updated = int(time.time())
        self.last_sent = 0
        self.annotators = AnnotatorSet()


class AnnotatorSet:
    def __init__(self):
        self.map = {}

    def run(self, annotator):
        if annotator in self.map:
            # Get latest data 
            sensor = annotator_to_sensor[annotator]
            data = get_sensor_data(sensor)
            return self.map[annotator][0](data)
        return None

    def add(self, annotator, annotator_meta):
        self.map[annotator] = annotator_meta  # -> [func, cost] (func=None if remote)

    def remove(self, annotator):
        del self.map[annotator]

    # s: string output from __repr__()
    def update(self, s):
        for item in s.split(";"):
            k, cost = item.split(",")
            if k not in self.map:
                self.map[k] = [None, cost]
            elif cost < self.map[k][1]:
                self.map[k][1] = cost

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1])
        return s


PUB_URL = "tcp://localhost:9101"
SUB_URL = "tcp://localhost:9102"
ELECTION_RES_TIMEOUT = 5
ELECTION_WAIT_TIMEOUT = 12
CAM_DATA_PATH = "./application/data/sample.jpg"

# darknet constants
CFG_URL = "./darknet/cfg/yolov3.cfg"
WEIGHT_URL = "./darknet/yolov3.weights"
CLASS_URL = "./darknet/data/coco.names"


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