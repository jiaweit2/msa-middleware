import zmq
import time
import cv2
import numpy as np
from middleware.node.utils import *
from middleware.brain.cam_manager import REFRESH_RATE, MODE_HIGHEST
from middleware.preset.annotators import YOLO
from middleware.preset.utils import draw_bounding_box

bg = None
curr_mode = 0
mode_adapting = False
last_mode_mbps = 0
objects = {}


def publisher_init():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a publisher socket
    publisher = context.socket(zmq.PUB)
    print("Connecting to: %s" % PUB_URL)
    publisher.connect(PUB_URL)
    return publisher


def subscribe(is_running, publisher):
    global bg, curr_mode, mode_adapting, last_mode_mbps

    # Create a 0MQ Context
    context = zmq.Context()
    # Create a subscriber socket
    subscriber = context.socket(zmq.SUB)
    print("Connecting to: %s" % SUB_URL)
    subscriber.connect(SUB_URL)

    # Perform the subscribe
    subscriber.setsockopt(zmq.SUBSCRIBE, b"result")

    if is_running:
        cnt1 = 0
        cnt0 = 0

        while True:
            message = subscriber.recv_multipart()
            curr_ts = time.time()
            ts, sender, mode = message[1].decode("utf-8").split("\t")
            mode = int(mode)
            if curr_mode != mode:
                mode_adapting = False
                curr_mode = mode
            if mode > 0:
                body = message[2].split(b"delim2")
            else:
                body = np.frombuffer(message[2], dtype=np.uint8)
                body = cv2.imdecode(body, flags=1)

            # Set a clear background for future subframe update
            if mode == 0 and bg is None:
                bg = body.copy()

            # Adapt to network change
            latency = curr_ts - float(ts)
            size = float(len(message[2])) / 125000
            mbps = size / latency
            ideal_mbps = size / REFRESH_RATE
            print("Current mode: ", mode)
            print("Body size (mb): ", size)
            print("Latency: ", latency)
            print("Ideal Mbps: ", ideal_mbps)
            print("Mbps: ", mbps)
            print("Last Mbps: ", last_mode_mbps)
            if (not mode_adapting) and (
                (mbps > last_mode_mbps and mode > 0 and latency < REFRESH_RATE)
                or (
                    (mbps <= last_mode_mbps or latency > REFRESH_RATE * 1.5)
                    and mode < MODE_HIGHEST
                )
            ):
                print_and_pub(
                    sender,
                    str(mbps - ideal_mbps),
                    publisher,
                    "cam",
                )
                print("Mode switch request sent!")

                mode_adapting = True
                last_mode_mbps = ideal_mbps

                if mbps < ideal_mbps:
                    subscriber.close(linger=0)
                    context.destroy(linger=0)
                    print("Network is unstable, reconnect...")
                    time.sleep(REFRESH_RATE)
                    return True

            # Post processing
            if mode == 1 and bg is not None:
                frame = bg.copy()
                for elems in body:
                    x, y, subframe = elems.split(b"delim1")
                    x = int(x.decode("utf-8"))
                    y = int(y.decode("utf-8"))
                    subframe = np.frombuffer(subframe, dtype=np.uint8)
                    subframe = cv2.imdecode(subframe, flags=1)
                    h, w, _ = subframe.shape
                    frame[y : y + h, x : x + w] = subframe
            elif mode == 1:
                subframe = np.frombuffer(body[0], dtype=np.uint8)
                frame = bg = cv2.imdecode(subframe, flags=1)
                last_mode_mbps = ideal_mbps
            elif mode == 0:
                frame = body

            # Annotation
            # print(YOLO(frame, True))

            # Show
            cv2.imshow("Live Stream", frame)
            cv2.waitKey(30)

            if mode == 0:
                cnt0 += 1
            else:
                cnt1 += 1
            print(cnt0, cnt1)

            time.sleep(
                max(0, REFRESH_RATE - max(0, time.time() - curr_ts))
            )  # offset processing time

    else:
        message = subscriber.recv_multipart()
        body = message[2].decode("utf-8")
        print("Query result: ")
        print(body)

    return False


if __name__ == "__main__":
    """
    Query format:
    {position=Lat,Long}
    {status=running/static}
    /Name = Decision({
        {conditions}
    })
    """
    query = ""
    with open("application/data/query") as f:
        lines = f.readlines()
        query += (
            lines[2].split("=")[0].strip()
            + "\t"
            + "".join(lines[2:])
            + "\t"
            + lines[0].strip()
            + "\t"
            + lines[1].strip()
        )
    publisher = publisher_init()
    print_and_pub("system", "Preparing to publish...", publisher)
    time.sleep(3)
    print_and_pub("query", query, publisher, "0001")

    restart = True
    while restart:
        restart = subscribe(lines[1].strip() == "running", publisher)
