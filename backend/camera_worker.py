import cv2
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal

class VideoStreamWorker(QThread):
    image_ready = pyqtSignal(np.ndarray)

    def __init__(self, video_path):
        super().__init__()
        self.active = True
        self.video_path = video_path

    def run(self):
        """Streams the video file."""
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            print(f"Error: Could not open video file {self.video_path}")
            return

        while self.active:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
                continue

            self.image_ready.emit(frame.copy())
            time.sleep(0.033) # Simulate ~30 FPS

        cap.release()

    def stop(self):
        self.active = False