import cv2
import numpy as np
import time
from skimage.metrics import structural_similarity

# from middleware.node.utils import async_run_after

backSub = cv2.createBackgroundSubtractorMOG2()
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
MIN_SIZE = 25 * 25  # px^2
W_THRESHOLD = 0.8
DIST_THRESHOLD = 100
REFRESH_RATE = 1  # Snapshot every X seconds
LIVENESS = 600


def prep_frame(frame):
    if type(frame) == str:
        frame = cv2.imread(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame, gray


class CamManager:
    def __init__(self, annotate, src):
        self.src = src
        self.annotate = annotate
        self.objects = {}
        self.obj_id = 0

        self.capture = cv2.VideoCapture(self.src)
        if not self.capture.isOpened():
            print("Cannot open camera")
            exit()
        self.fps = int(self.capture.get(cv2.CAP_PROP_FPS))
        self.res_w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.num_frame = 0

        # Preprocessing
        self.run()
        # async_run_after(0, self.run)
        # async_run_after(0, self.clear)

    def run(self):
        while True:
            print(len(self.objects))
            frame = self.snapshot()
            self.background_subtract(frame)
            time.sleep(REFRESH_RATE)

    def snapshot(self):
        self.capture.set(1, self.num_frame)
        ret, frame = self.capture.read()
        if not ret:
            return None
        self.num_frame += self.fps * REFRESH_RATE
        return frame

    def background_subtract(self, frame):
        mask = backSub.apply(frame)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mask, connectivity=4
        )
        for i in range(1, num_labels):
            x, y, w, h, size = stats[i]
            if self.res_w > w and size > MIN_SIZE:
                # Crop parts of images that are larger than MIN_SIZE
                subframe = frame[y : y + h, x : x + w]
                self.cache_obj(centroids[i], x, y, w, h, subframe)

    def cache_obj(self, cen, x, y, w, h, subframe):
        for obj_id in self.objects:
            cen_ = self.objects[obj_id][1]
            w_, h_ = self.objects[obj_id][4:6]
            if (
                abs(w_ - w) < (w_ * W_THRESHOLD)
                and np.linalg.norm(cen - cen_) < DIST_THRESHOLD
            ):
                # Same objects
                self.objects[obj_id][1] = cen
                self.objects[obj_id][4] = (w + self.objects[obj_id][4]) / 2
                self.objects[obj_id][5] = (h + self.objects[obj_id][5]) / 2
                cv2.imshow(
                    "OLD",
                    subframe,
                )
                cv2.waitKey(1000)
                return
        self.objects[self.obj_id] = [int(time.time()), cen, x, y, w, h, None]
        self.obj_id += 1
        cv2.imshow("NEW", subframe)
        cv2.waitKey(1000)

    def clear(self):
        while True:
            curr_time = int(time.time())
            self.annotate([self.snapshot(), self.objects], True)
            time.sleep(LIVENESS)


if __name__ == "__main__":
    cam = CamManager(lambda x: {}, "/Users/mike/Desktop/footage.mp4")