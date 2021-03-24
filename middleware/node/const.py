from enum import Enum

PUB_URL = "tcp://10.0.0.1:9101"
SUB_URL = "tcp://10.0.0.1:9102"
ELECTION_RES_TIMEOUT = 5
ELECTION_WAIT_TIMEOUT = 12
CAM_DATA_PATH = "./application/data/footage-480p.mp4"

PRECESION = 10
PACKETSIZE = 1000
PACKETCOUNT = 1000

# Sensor Manager
Sensor = Enum("Sensor", "CAM IR SR")
CAM_PREPROC_NAMES = ["sky", "ground", "road"]