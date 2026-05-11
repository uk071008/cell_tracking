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
        
        # Pfade für Mock-Daten
        self.grey_img_path = "data/mock_dirt_grey.png"
        self.white_img_path = "data/mock_calibration_white.png"
        
        self.streamer = VideoStreamWorker(self.grey_img_path)
        
        # State Management
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
        # Speichere immer den letzten Raw-Frame
        self.last_full_frame = frame.copy()
        
        # 1. Processing Logic (z.B. Background Removal)
        processed_frame = frame.copy()
        if self.ui.btn_bg_remove.isChecked():
            # (Subtraktions-Logik hier, falls aktiv)
            pass 

        # --- 2. HIER IST DIE KORREKTUR FÜR DEN ROI-CROP ---
        
        if self.view_mode == "PROCESSED" and self.roi_center:
            # Zeige nur den ROI-Ausschnitt
            roi_manager = ROIManager(size=self.roi_size)
            display_img = roi_manager.get_crop(processed_frame, self.roi_center[0], self.roi_center[1])
        else:
            # Im RAW Modus oder wenn keine ROI gesetzt ist: Zeige das Vollbild
            display_img = processed_frame

        # Sende das (richtig beschnittene) Bild an die UI
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

if __name__ == "__main__":
    tracker = CellTrackerApp()
    sys.exit(tracker.run())