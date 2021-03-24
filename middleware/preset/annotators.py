import cv2
import numpy as np
from middleware.node.const import *
from middleware.preset.utils import *


# Preset Annotators
def YOLO(frame, draw_bb=False):
    res = {}
    blob = cv2.dnn.blobFromImage(
        frame,
        scalefactor=1 / 255,
        size=(416, 416),
        mean=(0, 0, 0),
        swapRB=True,
        crop=False,
    )
    net.setInput(blob)
    outputs = net.forward(output_layers)
    boxes = []
    for output in outputs:
        for detect in output:
            scores = detect[5:]
            class_id = np.argmax(scores)
            conf = scores[class_id]
            if conf > 0.4 and (
                classes[class_id] in res
                and conf > res[classes[class_id]]
                or classes[class_id] not in res
            ):
                res[class_id] = conf
                if draw_bb:
                    w = int(detect[2] * frame.shape[1])
                    h = int(detect[3] * frame.shape[0])
                    x = int(detect[0] * frame.shape[1] - w / 2)
                    y = int(detect[1] * frame.shape[0] - h / 2)
                    boxes.append([x, y, x + w, y + h, class_id])
    if draw_bb:
        # No-max suppression
        for x, y, xw, yh, class_id in non_max_suppression_fast(np.array(boxes), 0.3):
            draw_bounding_box(frame, class_id, x, y, xw, yh)

    return res


def IR(data):
    return {"person": 0.4}


def SR(data):
    return {"person": 0.99}


annotator_presets = {
    "YOLO": [YOLO, 5],
    "IR": [IR, 2],
    "SR": [SR, 2],
}
annotator_to_sensor = {
    "YOLO": Sensor.CAM,
    "IR": Sensor.IR,
    "SR": Sensor.SR,
}

if __name__ == "__main__":
    import cv2

    cap = cv2.VideoCapture(CAM_DATA_PATH)
    while True:
        ret, frame = cap.read()
        print(YOLO(frame, True))
        cv2.imshow("frame", frame)
        cv2.waitKey(30)
