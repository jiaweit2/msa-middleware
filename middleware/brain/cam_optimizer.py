import cv2
from middleware.node.const impipport *


def cam_preprocess():
    background_subtract()


def background_subtract():
    backSub = cv2.createBackgroundSubtractorMOG2()
    capture = cv2.VideoCapture("/Users/mike/Downloads/footage.mp4")
    if not capture.isOpened():
        print("Cannot open camera")
        exit()
        
    while True:
        ret, frame = capture.read()
        if frame is None:
            break
        fgMask = backSub.apply(frame)
        frame2 = cv2.bitwise_and(frame, frame, mask=fgMask)

        cv2.imshow("Frame", frame)
        cv2.imshow("FG Mask", frame2)
        keyboard = cv2.waitKey(30)
        if keyboard == "q" or keyboard == 27:
            break


if __name__ == "__main__":
    background_subtract()
