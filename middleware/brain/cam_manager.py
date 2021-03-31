import cv2
import numpy as np
import time
from threading import RLock, Thread
from middleware.node.utils import async_run_after, print_and_pub

backSub = cv2.createBackgroundSubtractorMOG2()
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
MIN_SIZE = 25 * 25  # px^2
W_THRESHOLD = 0.8
DIST_THRESHOLD = 100
REFRESH_RATE = 1  # Snapshot every X seconds
MODE_HIGHEST = 1


class CamManager:
    def __init__(self, _id, src):
        self.curr_id = _id
        self.src = src
        self.lock = RLock()

        self.capture = cv2.VideoCapture(self.src)
        if not self.capture.isOpened():
            print("Cannot open camera")
            exit()
        self.fps = int(self.capture.get(cv2.CAP_PROP_FPS))
        self.res_w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))

        self.num_frame = 1

        # Preprocessing
        # self.run()
        # async_run_after(0, self.run)

        # Current modes:
        #       0: Send entire frame
        #       1: Only send updated subframe when necessary
        self.stream_mode = 0
        self.stream_metas = None
        self.stream_thread = None

    def stream(self, metas, t=0):
        self.stream_metas = metas
        self.stream_thread = async_run_after(t, self.send_stream)

    def send_stream(self):
        to, topic, publisher = self.stream_metas
        body = ""
        cnt0 = 0
        cnt1 = 0
        print("Cam Stream starts...")
        while True:
            frame = self.snapshot()
            if frame is None:
                return
            mode = self.stream_mode
            if mode == 0:
                body = cv2.imencode(".png", frame)[1].tobytes()
            elif mode == 1:
                updated_subframe = self.background_subtract(frame)
                if len(updated_subframe) == 0 and  self.num_frame == 1+self.fps * REFRESH_RATE:
                    updated_subframe = [cv2.imencode(".png", frame)[1].tobytes()]
                body = b"delim2".join(updated_subframe)

            time.sleep(REFRESH_RATE)

            if len(body) == 0:
                continue
            err = print_and_pub(
                topic,
                body,
                publisher,
                str(round(time.time(), 3)) + "\t" + self.curr_id + "\t" + str(mode),
            )

            if err is not None:
                # Change in network, abort
                print("Cam Stream Aborts")
                return

            if mode == 0:
                cnt0 += 1
            else:
                cnt1 += 1
            print(cnt0, cnt1)

    def adapt(self, diff, reset_publisher):
        print("Adapt to network")
        if diff < 0 and self.stream_mode < MODE_HIGHEST:
            self.stream_mode = min(self.stream_mode + 1, MODE_HIGHEST)
            async_run_after(0, reset_publisher)
        elif diff > 0:
            self.stream_mode = max(self.stream_mode - 1, 0)

    def run(self):
        while True:
            frame = self.snapshot()
            self.background_subtract(frame)
            time.sleep(REFRESH_RATE)

    def snapshot(self):
        with self.lock:
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
        # cv2.imshow("f", mask)
        # cv2.waitKey(1000)
        updated_subframe = []
        for i in range(1, num_labels):
            x, y, w, h, size = stats[i]
            if size > MIN_SIZE and self.res_w > w:
                # Crop parts of images that are larger than MIN_SIZE
                subframe = frame[y : y + h, x : x + w]
                updated_subframe.append(
                    str(x).encode("utf-8")
                    + b"delim1"
                    + str(y).encode("utf-8")
                    + b"delim1"
                    + cv2.imencode(".png", subframe)[1].tobytes()
                )
        return updated_subframe


if __name__ == "__main__":
    cam = CamManager("0001", "./application/data/footage-480p.mp4")
