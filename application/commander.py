import zmq
import time
import cv2
import numpy as np
from middleware.node.utils import *
from middleware.brain.cam_manager import REFRESH_RATE

NETWORK_CHECK_INTERVAL = 5


def publisher_init():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a publisher socket
    publisher = context.socket(zmq.PUB)
    print("Connecting to: %s" % PUB_URL)
    publisher.connect(PUB_URL)
    return publisher


def subscribe(is_running, publisher):
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a subscriber socket
    subscriber = context.socket(zmq.SUB)
    print("Connecting to: %s" % SUB_URL)
    subscriber.connect(SUB_URL)

    # Perform the subscribe
    subscriber.setsockopt(zmq.SUBSCRIBE, b"result")

    if is_running:
        last_check = time.time()
        bg = None
        while True:
            message = subscriber.recv_multipart()
            curr_ts = time.time()
            ts, sender, mode = message[1].decode("utf-8").split("\t")
            mode = int(mode)
            if mode > 0:
                body = message[2].split(b"delim2")
            else:
                frame = np.frombuffer(message[2], dtype=np.uint8)
                frame = cv2.imdecode(frame, flags=1)
            # Set a clear background for future subframe update
            if mode == 0 and bg is None:
                bg = frame.copy()
            print("Current mode: ", mode)
            print("Body size: ", len(message[2]))
            print("Latency: ", curr_ts - float(ts))
            # Adapt to network change
            if (
                curr_ts - float(ts) > REFRESH_RATE - 0.1
                and curr_ts - last_check > NETWORK_CHECK_INTERVAL
            ):
                print_and_pub(sender, "+", publisher, "cam")
                last_check = curr_ts
            if (
                curr_ts - float(ts) < REFRESH_RATE - 0.5
                and curr_ts - last_check > NETWORK_CHECK_INTERVAL
            ):
                print_and_pub(sender, "-", publisher, "cam")
                last_check = curr_ts

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

            # Show
            cv2.imshow("Live Stream", frame)
            cv2.waitKey(30)

            time.sleep(REFRESH_RATE)

    else:
        message = subscriber.recv_multipart()
        body = message[2].decode("utf-8")
        print("Query result: ")
        print(body)


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
    subscribe(lines[1].strip() == "running", publisher)
