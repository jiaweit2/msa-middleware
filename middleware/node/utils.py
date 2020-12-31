import cv2
from middleware.node.const import *
from middleware.node.annotate import *


def list_to_str(arr):
    s = ""
    for a in arr:
        if s != "":
            s += ","
        s += str(a)
    return s


def get_latest_data(sensor_type):
    if sensor_type == "Camera":
        # image loading
        img = cv2.imread(CAM_DATA_PATH)
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        # height, width, channels = img.shape
        data = cv2.imencode(".jpg", img)[1].tobytes()
        return YOLO_Annotate(data)


def post_process_coa(variables):
    for var in variables:
        if len(variables[var]) > 0 and variables[var][-1] != ")":
            variables[var] = "And(" + variables[var] + ")"
