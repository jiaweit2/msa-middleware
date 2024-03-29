import os
import sys

import cv2
import numpy as np


net = cv2.dnn.readNetFromDarknet(os.environ["CFG_URL"], os.environ["WEIGHT_URL"])
layers_names = net.getLayerNames()
output_layers = [layers_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
classes = []
with open(os.environ["CLASS_URL"], "r") as f:
    classes = [line.strip() for line in f.readlines()]
COLORS = np.random.uniform(0, 255, size=(len(classes), 3))


def draw_bounding_box(img, class_id, x, y, x_plus_w, y_plus_h):
    label = str(classes[class_id])
    color = COLORS[class_id]
    cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color, 1)
    cv2.putText(img, label, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


# Malisiewicz et al.
def non_max_suppression_fast(boxes, overlap_threshold):
    # if there are no boxes, return an empty list
    if len(boxes) == 0:
        return []
    # if the bounding boxes integers, convert them to floats --
    # this is important since we'll be doing a bunch of divisions
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")
    # initialize the list of picked indexes
    pick = []
    # grab the coordinates of the bounding boxes
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    # compute the area of the bounding boxes and sort the bounding
    # boxes by the bottom-right y-coordinate of the bounding box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)
    # keep looping while some indexes still remain in the indexes
    # list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the
        # index value to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        # find the largest (x, y) coordinates for the start of
        # the bounding box and the smallest (x, y) coordinates
        # for the end of the bounding box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        # compute the ratio of overlap
        overlap = (w * h) / area[idxs[:last]]
        # delete all indexes from the index list that have
        idxs = np.delete(
            idxs, np.concatenate(([last], np.where(overlap > overlap_threshold)[0]))
        )
    # return only the bounding boxes that were picked using the
    # integer data type
    return boxes[pick].astype("int")


# Preset Annotators
def main(frame, draw_bb=False):
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
        return frame

    return res
