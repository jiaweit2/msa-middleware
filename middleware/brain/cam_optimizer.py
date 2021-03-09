import cv2
from middleware.node.const import *


def cam_preprocess():
    background_subtract()


def background_subtract(empty_frame, frame):
    if type(empty_frame) == str:
        empty_frame = read_from_url(empty_frame)
    if type(frame) == str:
        frame = read_from_url(frame)

    backSub = cv.createBackgroundSubtractorMOG2()
    fgMask = backSub.apply(frame)
    cv.rectangle(frame, (10, 2), (100, 20), (255, 255, 255), -1)
    cv.putText(
        frame,
        str(capture.get(cv.CAP_PROP_POS_FRAMES)),
        (15, 15),
        cv.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 0),
    )

    cv.imshow("Frame", frame)
    cv.imshow("FG Mask", fgMask)


def read_from_url(url):
    img = cv2.imread(CAM_DATA_PATH)
    img = cv2.resize(img, None, fx=0.4, fy=0.4)
    return img