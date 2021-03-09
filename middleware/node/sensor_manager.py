import cv2

from middleware.preset.annotators import annotator_to_sensor
from middleware.node.const import *


class AnnotatorSet:
    def __init__(self):
        self.map = {}  # -> [func, cost] (func=None if remote)

    def run(self, annotator, data, k):
        annotated = self.get_annotated(annotator, data)
        return annotated[k] if k in annotated else None

    def add(self, annotator, annotator_meta):
        annotator_meta[1] = int(annotator_meta[1])
        self.map[annotator] = annotator_meta

    def remove(self, annotator):
        del self.map[annotator]

    # s: string output from __repr__()
    def update(self, s):
        if s:
            for item in s.split(";"):
                k, cost = item.split(",")
                if k not in self.map:
                    self.map[k] = [None, int(cost)]
                elif cost < self.map[k][1]:
                    self.map[k][1] = int(cost)

    def get_annotated(self, annotator, data):
        if annotator in self.map:
            return self.map[annotator][0](data)
        return {}

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1])
        return s


def get_sensor_data(annotator):
    # Retrieve latest data from sensor
    sensor = annotator_to_sensor[annotator]
    if sensor == Sensor.CAM:
        # image loading
        img = cv2.imread(CAM_DATA_PATH)
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        # height, width, channels = img.shape
        data = cv2.imencode(".jpg", img)[1].tobytes()
        return data
    elif sensor == Sensor.IR:
        return ""
    elif sensor == Sensor.SR:
        return ""
