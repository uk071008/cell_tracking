import sys
import os
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal

# Add the vendor directory to the system path so toupcam can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
vendor_dir = os.path.abspath(os.path.join(current_dir, '..', 'vendor', 'ToupTek'))
sys.path.append(vendor_dir)

import toupcam

class VideoStreamWorker(QThread):
    image_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.active = False
        self.camera = None
        self.buf = None
        self.img_width = 0
        self.img_height = 0

    @staticmethod
    def _camera_callback(event, ctx):
        """
        Static callback triggered by the ToupTek SDK.
        'ctx' is the reference to the VideoStreamWorker instance.
        """
        if event == toupcam.TOUPCAM_EVENT_IMAGE:
            ctx._process_new_frame()

    def _process_new_frame(self):
        """Pulls the image from the camera buffer and emits it."""
        if self.camera is None or not self.active:
            return
        
        try:
            # 24 indicates 24 bits per pixel (RGB/BGR format)
            self.camera.PullImageV3(self.buf, 0, 24, 0, None)
            
            # Convert the raw byte buffer into a structured NumPy array
            img = np.frombuffer(self.buf, dtype=np.uint8)
            img = img.reshape((self.img_height, self.img_width, 3))
            
            # The ToupTek SDK outputs BGR by default, matching OpenCV
            self.image_ready.emit(img.copy())
            
        except Exception as e:
            print(f"Error reading frame from camera buffer: {e}")

    def run(self):
        """Initializes the camera hardware and keeps the thread alive."""
        # 1. Detect connected ToupTek/Bresser cameras
        available_cameras = toupcam.Toupcam.EnumV2()
        if not available_cameras:
            print("Hardware Error: No compatible camera detected.")
            return

        # 2. Open the first available camera
        self.camera = toupcam.Toupcam.Open(available_cameras[0].id)
        if self.camera is None:
            print("Hardware Error: Could not connect to the camera.")
            return
        # 2. Open the first available camera
        self.camera = toupcam.Toupcam.Open(available_cameras[0].id)
        if self.camera is None:
            print("Hardware Error: Could not connect to the camera.")
            return

        try:
            self.camera.put_AutoExpoEnable(1) #1 enables auto-exposure, 0 would disable it
            print("Auto-Exposure activated.")
        except Exception as e:
            print(f"Warning: Auto-Exposure could not be activated: {e}")

        # 3. Retrieve the current resolution
        self.img_width, self.img_height = self.camera.get_Size()
        
        # 4. Allocate a memory buffer (Width * Height * 3 bytes for color)
        buffer_size = self.img_width * self.img_height * 3
        self.buf = bytes(buffer_size)

        self.active = True
        
        # 5. Start the continuous pull mode with the callback function
        self.camera.StartPullModeWithCallback(self._camera_callback, self)

        # 6. Keep the QThread running while active
        while self.active:
            time.sleep(0.1)

        # 7. Clean up resources upon thread termination
        self.camera.Close()
        self.camera = None

    def stop(self):
        """Safely stops the camera stream and terminates the thread."""
        self.active = False
        self.wait()

    def set_exposure(self, ms):
        if self.camera:
            self.camera.put_AutoExpoEnable(0) 
            self.camera.put_ExpoTime(ms * 1000)

    def set_gain(self, percent):
        if self.camera:
            self.camera.put_ExpoAGain(percent)

    def set_white_balance(self, temp):
        if self.camera:
            self.camera.put_TempTint(temp, 1000)