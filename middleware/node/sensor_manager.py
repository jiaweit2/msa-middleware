import cv2

from middleware.preset.annotators import annotator_to_sensor


class AnnotatorSet:
    def __init__(self):
        self.map = {}  # -> [func, cost] (func=None if remote)

    def run(self, annotator, k):
        if annotator in self.map:
            # Get latest data
            sensor = annotator_to_sensor[annotator]
            data = get_sensor_data(sensor)
            return (self.map[annotator][0](data))[k]
        return None

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

    def __repr__(self):
        s = ""
        for k in self.map:
            if s:
                s += ";"
            s += k + "," + str(self.map[k][1])
        return s


def get_sensor_data(sensor):
    # Retrieve latest data from sensor
    if sensor == "Camera":
        # image loading
        img = cv2.imread(CAM_DATA_PATH)
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        # height, width, channels = img.shape
        data = cv2.imencode(".jpg", img)[1].tobytes()
        return data
    elif sensor == "IR":
        return ""
    elif sensor == "SR":
        return ""