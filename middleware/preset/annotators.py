import os
from middleware.node.const import *

import cv2
import numpy as np

net = cv2.dnn.readNetFromDarknet(os.environ["CFG_URL"], os.environ["WEIGHT_URL"])
layers_names = net.getLayerNames()
output_layers = [layers_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
classes = []
with open(os.environ["CLASS_URL"], "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Preset Annotators
def YOLO(data, update=False):
    frame, objects = data
    res = {}

    for id_ in objects:
        ts, cen, x, y, w, h, annotated = objects[id_]
        if not update and annotated:
            res.update(annotated)
            continue

        subframe = frame[y : y + h, x : x + w]
        blob = cv2.dnn.blobFromImage(
            subframe,
            scalefactor=0.00392,
            size=(320, 320),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False,
        )
        net.setInput(blob)
        outputs = net.forward(output_layers)
        empty_subframe = True
        for output in outputs:
            for detect in output:
                scores = detect[5:]
                class_id = np.argmax(scores)
                conf = scores[class_id]
                if conf > 0.3:
                    if classes[class_id] in res:
                        res[classes[class_id]] = max(
                            res[classes[class_id]], float(conf)
                        )
                    else:
                        res[classes[class_id]] = float(conf)
                    empty_subframe = False
        if empty_subframe and update:
            del objects[id_]
    print(res)
    if update:
        return objects
    return res


def IR(data):
    return {"person": 0.4}


def SR(data):
    return {"person": 0.99}


annotator_presets = {"YOLO": [YOLO, 5], "IR": [IR, 2], "SR": [SR, 2]}
annotator_to_sensor = {"YOLO": Sensor.CAM, "IR": Sensor.IR, "SR": Sensor.SR}

if __name__ == "__main__":
    import cv2

    img = cv2.imread(CAM_DATA_PATH)
    img = cv2.resize(img, None, fx=0.4, fy=0.4)
    # height, width, channels = img.shape
    data = cv2.imencode(".jpg", img)[1].tobytes()
    print(YOLO(data))