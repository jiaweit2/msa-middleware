import json
import os
import time
import sys

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(curr_dir, "annotators"))
sys.path.insert(0, os.path.join(curr_dir, "sensors"))

with open(os.path.join(curr_dir, "global-conf.json")) as f:
    conf = json.load(f)

# Load server
PUB_URL = "tcp://" + conf["server_ip"] + ":9101"
SUB_URL = "tcp://" + conf["server_ip"] + ":9102"


def preload(id_):
    # Load annotators
    annotator_presets = {}
    if id_ in conf["annotator_presets"]:
        name, complexity, sensor = conf["annotator_presets"][id_]
        annotator_presets[name] = [__import__(name).main, int(complexity), sensor]

    # Load available sensors
    sensor_presets = {}
    if id_ in conf["sensor_presets"]:
        name, src = conf["sensor_presets"][id_]
        sensor_presets[name] = [__import__(name), src]

    # Load rules
    rules = conf["rules"]

    return annotator_presets, sensor_presets, rules