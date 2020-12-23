import time


class Member:
    def __init__(self, _id):
        self.id = _id
        self.failed = False
        self.last_updated = int(time.time())
        self.last_sent = 0

PUB_URL = "tcp://localhost:9101"
SUB_URL = "tcp://localhost:9102"
ELECTION_RES_TIMEOUT = 5
ELECTION_WAIT_TIMEOUT = 12
