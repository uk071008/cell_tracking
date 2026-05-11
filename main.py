import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPixmap

from frontend.main_window import MainWindow
from backend.camera_worker import VideoStreamWorker
from processing.background_remover import StaticBackgroundSubtractor
from frontend.styles import get_stylesheet
from processing.roi_manager import ROIManager

class CellTrackerApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(get_stylesheet())
        
        self.fgbg = StaticBackgroundSubtractor()
        self.ui = MainWindow()
        
        self.streamer = VideoStreamWorker()

        self.ui.slider_expo.valueChanged.connect(self.update_camera_settings)
        self.ui.slider_gain.valueChanged.connect(self.update_camera_settings)
        self.ui.slider_color.valueChanged.connect(self.update_camera_settings)

        self.ui.btn_capture_ref.clicked.connect(self.capture_reference)

        # State Management
        self.reference_image = None
        self.view_mode = "RAW" # "RAW" oder "PROCESSED"
        self.roi_center = None
        self.roi_size = 200
        self.last_full_frame = None

        # Signals
        self.streamer.image_ready.connect(self.handle_frame)
        self.ui.show_raw_requested.connect(self.set_raw_mode)
        self.ui.show_processed_requested.connect(self.set_processed_mode)
        self.ui.camera_view.clicked_pos.connect(self.save_roi_coords)

        self.streamer.start()

        self.update_camera_settings()
    def capture_reference(self):
            """Captures the current frame to use as a flat-field correction map."""
            if self.last_full_frame is not None:
                # Store as float32 for division math, replace 0s with 1s to prevent division by zero
                self.reference_image = self.last_full_frame.copy().astype(np.float32)
                self.reference_image[self.reference_image == 0] = 1 
                self.ui.status_label.setText("Status: Dirt calibration reference saved!")
    def set_raw_mode(self):
        self.view_mode = "RAW"
        self.ui.status_label.setText("Status: Showing Raw Feed")

    def set_processed_mode(self):
        if self.roi_center is None:
            self.ui.status_label.setText("Status: Please set ROI first!")
            return
        self.view_mode = "PROCESSED"
        self.ui.status_label.setText("Status: Showing ROI Processed")

    def save_roi_coords(self, x, y):
        self.roi_center = (x, y)
        self.ui.status_label.setText(f"Status: ROI set to {self.roi_center}")

    def handle_frame(self, frame):
            self.last_full_frame = frame.copy()
            processed_frame = frame.copy()

            # --- Flat-Field Correction (Dirt Removal) ---
            if self.reference_image is not None:
                # Calculate the mean brightness of the reference to maintain exposure levels
                mean_ref = np.mean(self.reference_image)
                
                # Divide raw image by reference map (removes shadows/dirt) and normalize
                corrected = (processed_frame.astype(np.float32) / self.reference_image) * mean_ref
                
                # Clip values back to standard image range 0-255
                processed_frame = np.clip(corrected, 0, 255).astype(np.uint8)

            # 1. Processing Logic (e.g., Background Removal)
            if self.ui.btn_bg_remove.isChecked():
                pass 

            if self.view_mode == "PROCESSED" and self.roi_center:
                roi_manager = ROIManager(size=self.roi_size)
                display_img = roi_manager.get_crop(processed_frame, self.roi_center[0], self.roi_center[1])
            else:
                display_img = processed_frame

            self._update_ui(display_img)
        
    def _update_ui(self, cv_img):
            try:
                # WICHTIG: Erzeuge eine Kopie des Ausschnitts, damit der Speicherbereich stabil ist
                img = cv_img.copy()
                h, w = img.shape[:2]
                
                if len(img.shape) == 3:
                    # BGR (OpenCV) zu RGB (Qt)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    qimg = QImage(img.data, w, h, w * 3, QImage.Format.Format_RGB888)
                else:
                    qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)

                # .copy() am Ende des QImage ist der entscheidende Trick gegen Abstürze!
                pixmap = QPixmap.fromImage(qimg.copy()) 
                self.ui.update_frame(pixmap)
                
            except Exception as e:
                print(f"UI Update Fehler: {e}")

    def run(self):
        self.ui.show()
        return self.app.exec()
    



    def update_camera_settings(self):
  
        expo = self.ui.slider_expo.value()
        gain = self.ui.slider_gain.value()
        color = self.ui.slider_color.value()

        self.ui.label_expo.setText(f"Exposure: {expo}ms")
        self.ui.label_gain.setText(f"Gain: {gain}%")
        self.ui.label_color.setText(f"Color Temp: {color}K")

        self.streamer.set_exposure(expo)
        self.streamer.set_gain(gain)
        self.streamer.set_white_balance(color)

if __name__ == "__main__":
    tracker = CellTrackerApp()
    sys.exit(tracker.run())