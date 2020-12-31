import zmq
import time
from middleware.node.const import *


def publisher_init():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a publisher socket
    publisher = context.socket(zmq.PUB)
    print("Connecting to: %s" % PUB_URL)
    publisher.connect(PUB_URL)
    return publisher


def subscribe():
    # Create a 0MQ Context
    context = zmq.Context()
    # Create a subscriber socket
    subscriber = context.socket(zmq.SUB)
    print("Connecting to: %s" % SUB_URL)
    subscriber.connect(SUB_URL)

    # Perform the subscribe
    subscriber.setsockopt(zmq.SUBSCRIBE, b"query_result")

    message = subscriber.recv_multipart()
    body = message[2].decode("utf-8")
    print("Query result: ")
    print(body)


if __name__ == "__main__":
    query = ""
    with open("application/data/query") as f:
        lines = f.readlines()
        query += (
            lines[1].split("=")[0].strip()
            + "\t"
            + lines[0].strip()
            + "\t"
            + "".join(lines[1:])
        )
    publisher = publisher_init()
    print_and_pub("system", "Preparing to publish...", publisher)
    time.sleep(3)
    print_and_pub("query", query, publisher, "0001")
    subscribe()
