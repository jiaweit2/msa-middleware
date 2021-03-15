import time
from threading import Thread
from zmq import SNDMORE

from middleware.node.const import *
from middleware.preset.annotators import annotator_to_sensor


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


def measure_throughput(Global, receiver):
    publisher, sender = Global.publisher, Global.curr_id
    ts = str(round(time.time(), PRECESION))

    publisher.send(("bw-" + receiver).encode("utf-8"), SNDMORE)
    publisher.send(
        (sender + "\t" + "true" + "\t0.0\t" + ts + "\t ").encode("utf-8"),
        SNDMORE,
    )

    for i in range(PACKETCOUNT):
        if i == PACKETCOUNT - 1:
            publisher.send(b"x" * PACKETSIZE)
        else:
            publisher.send(b"x" * PACKETSIZE, SNDMORE)


def get_sensor_data(annotator, Global):
    # Retrieve latest data from sensor
    sensor = annotator_to_sensor[annotator]
    if sensor == Sensor.CAM:
        with Global.cam_manager.lock:
            frame = Global.cam_manager.snapshot()
        return [frame, Global.cam_manager.objects]
    elif sensor == Sensor.IR:
        return ""
    elif sensor == Sensor.SR:
        return ""
