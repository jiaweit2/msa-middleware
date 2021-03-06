import os
from middleware.node.const import *

# Preset Annotators
def YOLO(data):
    import cv2
    import numpy as np

    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    net = cv2.dnn.readNet(os.environ["WEIGHT_URL"], os.environ["CFG_URL"])
    classes = []
    with open(os.environ["CLASS_URL"], "r") as f:
        classes = [line.strip() for line in f.readlines()]
    layers_names = net.getLayerNames()
    output_layers = [layers_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    blob = cv2.dnn.blobFromImage(
        img,
        scalefactor=0.00392,
        size=(320, 320),
        mean=(0, 0, 0),
        swapRB=True,
        crop=False,
    )
    net.setInput(blob)
    outputs = net.forward(output_layers)
    res = {}
    for output in outputs:
        for detect in output:
            scores = detect[5:]
            class_id = np.argmax(scores)
            conf = scores[class_id]
            if conf > 0.3:
                res[classes[class_id]] = float(conf)
    return res


def IR(data):
    return {"person": 0.4}


def SR(data):
    return {"person": 0.99}


annotator_presets = {"YOLO": [YOLO, 5], "IR": [IR, 2], "SR": [SR, 2]}
annotator_to_sensor = {"YOLO": "Camera", "IR": "Infrared", "SR": "Sonar"}
