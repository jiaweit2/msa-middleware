import time


class Member:
    def __init__(self, _id):
        self.id = _id
        self.failed = False
        self.last_updated = int(time.time())
        self.last_sent = 0
        self.skills = []


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