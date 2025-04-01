import cv2
from ui import run_ui

if __name__ == "__main__":
    camera = cv2.VideoCapture(0)
    run_ui(camera)
