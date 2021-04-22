import json
import os
import time
import sys

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(curr_dir, "annotators"))
sys.path.insert(0, os.path.join(curr_dir, "sensors"))

with open(os.path.join(curr_dir, "confs", "global-conf.json")) as f:
    conf = json.load(f)

# Load server
PUB_URL = "tcp://" + conf["server_ip"] + ":9101"
SUB_URL = "tcp://" + conf["server_ip"] + ":9102"


def preload(id_):
    # Load confs
    try:
        with open(os.path.join(curr_dir, "confs", "conf-" + id_ + ".json")) as f:
            curr_conf = json.load(f)
    except Exception:
        print("Error loading conf file")
        return
    # Load annotators
    annotator_presets = {}
    for annotator in curr_conf["annotator_presets"]:
        name, complexity, sensor = annotator
        annotator_presets[name] = [__import__(name).main, int(complexity), sensor]

    # Load available sensors
    sensor_presets = {}
    for sensor in curr_conf["sensor_presets"]:
        name, src, pos = sensor
        pos = pos.split(",")
        sensor_presets[name] = [__import__(name), src, (float(pos[0]), float(pos[1]))]

    # Load rules
    rules = conf["rules"]

    return annotator_presets, sensor_presets, rules