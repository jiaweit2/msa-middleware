import zmq
import time
import cv2
import numpy as np
from middleware.node.utils import *
from middleware.custom.initialize import PUB_URL, SUB_URL


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
        while True:
            message = subscriber.recv_multipart()

            ####   Customization for streaming   ####

            # Detect network bandwidth and send any streaming strategy instruction
            # print_and_pub(
            #     stream_sender,
            #     str("Network Adaptation Instruction"),
            #     publisher,
            #     "bw", # Use this topic to instruct on bandwidth
            # )

            # Stream Post-Processing

            # Annotation

            # Show the current frame

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
    with open("../../application/data/query") as f:
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
