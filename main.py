import sys
import cv2
import time
import numpy as np
import traceback
import socket
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPixmap

from frontend.main_window import MainWindow
from backend.camera_worker import VideoStreamWorker
from processing.background_remover import StaticBackgroundSubtractor
from frontend.styles import get_stylesheet
from processing.roi_manager import ROIManager
from backend.stage_control import MicosStageController

# ---------------------------------------------------------
# GLOBAL CRASH HANDLER (FAIL-SAFE)
# ---------------------------------------------------------
def global_crash_handler(exc_type, exc_value, exc_tb):
    """Intercepts fatal crashes and stops the stage immediately."""
    print("CRITICAL ERROR: Python crashed. Sending emergency stop to stage!", file=sys.stderr)
    try:
        emergency_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        emergency_sock.settimeout(2.0)
        emergency_sock.connect(("141.51.197.172", 23))  # Corrected Corvus IP
        emergency_sock.sendall(b"\x03")  # Send Venus-1 abort command
        emergency_sock.close()
        print("Emergency stop command sent to stage.", file=sys.stderr)
    except Exception as e:
        print(f"Failed to send emergency stop command: {e}", file=sys.stderr)

    # Print the actual traceback to the console for debugging
    traceback.print_exception(exc_type, exc_value, exc_tb)

# Register the hook before the application starts
sys.excepthook = global_crash_handler

# ---------------------------------------------------------
# MAIN APPLICATION CLASS
# ---------------------------------------------------------
class CellTrackerApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(get_stylesheet())
        
        self.fgbg = StaticBackgroundSubtractor()
        self.ui = MainWindow()
        
        # --- Camera & Processing Initialization ---
        self.streamer = VideoStreamWorker()

        self.ui.slider_expo.valueChanged.connect(self.update_camera_settings)
        self.ui.slider_gain.valueChanged.connect(self.update_camera_settings)
        self.ui.slider_color.valueChanged.connect(self.update_camera_settings)
        self.ui.btn_capture_ref.clicked.connect(self.capture_reference)

        # --- Stage Controller Initialization ---
        self.stage = MicosStageController()
        self.stage.connect()
        
        # Hardware limits (update these to your physical axes limits)
        self.stage_min_x = 0.0
        self.stage_min_y = 0.0
        self.stage_min_z = 0.0
        
        self.stage_max_x = 100.0
        self.stage_max_y = 100.0
        self.stage_max_z = 20.0

        self.current_pos = [0.0, 0.0, 0.0]

        # Stage Movement Connections
        self.ui.btn_stage_up.clicked.connect(self.move_stage_up)
        self.ui.btn_stage_down.clicked.connect(self.move_stage_down)
        self.ui.btn_stage_left.clicked.connect(self.move_stage_left)
        self.ui.btn_stage_right.clicked.connect(self.move_stage_right)
        self.ui.btn_stage_z_up.clicked.connect(self.move_stage_z_up)
        self.ui.btn_stage_z_down.clicked.connect(self.move_stage_z_down)
        self.ui.btn_stage_stop.clicked.connect(self.stage.stop_motion)
        self.ui.btn_apply_speed.clicked.connect(self.update_stage_speed)
        
        self.ui.btn_goto.clicked.connect(self.move_stage_absolute)
        self.ui.btn_home_stage.clicked.connect(self.start_homing_sequence)
        
        # Stage Zeroing & Barrier Connections
        self.ui.btn_set_zero.clicked.connect(self.set_zero)
        self.ui.btn_set_left.clicked.connect(self.set_left_barrier)
        self.ui.btn_set_right.clicked.connect(self.set_right_barrier)
        self.ui.btn_set_top.clicked.connect(self.set_top_barrier)
        self.ui.btn_set_bottom.clicked.connect(self.set_bottom_barrier)
        self.ui.btn_set_z_up.clicked.connect(self.set_z_up_barrier)
        self.ui.btn_set_z_down.clicked.connect(self.set_z_down_barrier)

        # --- Unit Toggle Connection ---
        self.ui.radio_mm.toggled.connect(self.check_stage_status)
        self.ui.radio_mm.toggled.connect(self.update_unit_displays)
        self.ui.radio_um.toggled.connect(self.update_unit_displays)
        
        self.update_unit_displays()

        # --- State Management ---
        self.reference_image = None
        self.view_mode = "RAW" # "RAW" or "PROCESSED"
        self.roi_center = None
        self.roi_size = 200
        self.last_full_frame = None

        # --- Signals ---
        self.streamer.image_ready.connect(self.handle_frame)
        self.ui.btn_raw.clicked.connect(self.set_raw_mode)
        self.ui.btn_processed.clicked.connect(self.set_processed_mode)
        self.ui.camera_view.clicked_pos.connect(self.save_roi_coords)
        
        # Start the video stream
        self.streamer.start()
        self.update_camera_settings()

        self.check_stage_status()

    # ---------------------------------------------------------
    # STAGE BARRIER & ZEROING METHODS
    # ---------------------------------------------------------
    def set_zero(self):
        pos = self.stage.query_position()
        if pos:
            if self.stage.set_current_as_zero():
                # Shift BOTH the maximum and minimum hardware limits!
                self.stage_max_x -= pos[0]
                self.stage_max_y -= pos[1]
                self.stage_max_z -= pos[2]
                
                self.stage_min_x -= pos[0]
                self.stage_min_y -= pos[1]
                self.stage_min_z -= pos[2]
                
                self.check_stage_status()
                self.ui.status_label.setText("Status: Stage center defined. All limits shifted.")

    def set_left_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_x_min = pos[0]
            self.ui.status_label.setText(f"Status: Left barrier (X-) set at X={pos[0]:.2f}mm")

    def set_right_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_x_max = pos[0]
            self.ui.status_label.setText(f"Status: Right barrier (X+) set at X={pos[0]:.2f}mm")

    def set_top_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_y_max = pos[1]
            self.ui.status_label.setText(f"Status: Top barrier (Y+) set at Y={pos[1]:.2f}mm")

    def set_bottom_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_y_min = pos[1]
            self.ui.status_label.setText(f"Status: Bottom barrier (Y-) set at Y={pos[1]:.2f}mm")

    def set_z_up_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_z_max = pos[2]
            self.ui.status_label.setText(f"Status: Z-Up barrier set at Z={pos[2]:.2f}mm")

    def set_z_down_barrier(self):
        pos = self.stage.query_position()
        if pos:
            self.stage.soft_limit_z_min = pos[2]
            self.ui.status_label.setText(f"Status: Z-Down barrier set at Z={pos[2]:.2f}mm")

    # ---------------------------------------------------------
    # STAGE MOVEMENT METHODS
    # ---------------------------------------------------------
    def start_homing_sequence(self):
            self.ui.status_label.setText("Status: Homing in progress, DO NOT MOVE stage manually!")
            self.stage.home_axes()
            self.current_pos = [0.0, 0.0, 0.0]

    def get_step_in_mm(self):
        val = self.ui.spin_step.value()
        if self.ui.radio_um.isChecked():
            return val / 1000.0
        return val

    def move_stage_up(self):
        self.stage.move_relative(0, self.get_step_in_mm(), 0)
        self.check_stage_status()
        
    def move_stage_down(self):
        self.stage.move_relative(0, -self.get_step_in_mm(), 0)
        self.check_stage_status()

    def move_stage_left(self):
        self.stage.move_relative(self.get_step_in_mm(), 0, 0)
        self.check_stage_status()

    def move_stage_right(self):
        self.stage.move_relative(-self.get_step_in_mm(), 0, 0)
        self.check_stage_status()

    def move_stage_z_up(self):
        self.stage.move_relative(0, 0, self.get_step_in_mm())
        self.check_stage_status()

    def move_stage_z_down(self):
        self.stage.move_relative(0, 0, -self.get_step_in_mm())
        self.check_stage_status()

    # ---------------------------------------------------------
    # UNIT HANDLING & SPEED
    # ---------------------------------------------------------
    def update_unit_displays(self):
        """Changes the unit suffixes in the input fields."""
        if self.ui.radio_mm.isChecked():
            self.ui.spin_step.setSuffix(" mm")
            self.ui.spin_speed.setSuffix(" mm/s")
        else:
            self.ui.spin_step.setSuffix(" µm")
            self.ui.spin_speed.setSuffix(" µm/s")

    def get_speed_in_mm_s(self):
        """Calculates the speed in mm/s."""
        val = self.ui.spin_speed.value()
        if self.ui.radio_um.isChecked():
            return val / 1000.0
        return val
    
    def move_stage_absolute(self):
        """Reads target coordinates, verifies hardware limits, and executes the move."""
        target_x = self.ui.spin_goto_x.value()
        target_y = self.ui.spin_goto_y.value()
        target_z = self.ui.spin_goto_z.value()
        
        # --- 1. HARDWARE LIMIT CHECK (The Real World) ---
        if not (self.stage_min_x <= target_x <= self.stage_max_x):
            self.ui.status_label.setText(f"CRITICAL ERROR: X:{target_x} is outside physical limits ({self.stage_min_x:.1f} to {self.stage_max_x:.1f})")
            return
            
        if not (self.stage_min_y <= target_y <= self.stage_max_y):
            self.ui.status_label.setText(f"CRITICAL ERROR: Y:{target_y} is outside physical limits ({self.stage_min_y:.1f} to {self.stage_max_y:.1f})")
            return
            
        if not (self.stage_min_z <= target_z <= self.stage_max_z):
            self.ui.status_label.setText(f"CRITICAL ERROR: Z:{target_z} is outside physical limits ({self.stage_min_z:.1f} to {self.stage_max_z:.1f})")
            return

        self.ui.status_label.setText(f"Status: Moving to Absolute X:{target_x} Y:{target_y} Z:{target_z}")
        
        # --- 2. VIRTUAL BARRIER CHECK & EXECUTION (The Backend) ---
        success = self.stage.move_absolute(target_x, target_y, target_z)
        
        if success:
            # Wait a brief moment for the motors to start, then refresh the UI
            time.sleep(0.5)
            self.check_stage_status()
        else:
            self.ui.status_label.setText("STAGE ERROR: Absolute move blocked by virtual barrier!")

    def update_stage_speed(self):
        """Sends the speed to the controller."""
        speed_mm = self.get_speed_in_mm_s()
    
        self.stage.set_velocity(speed_mm, speed_mm, speed_mm)
        
        unit = "mm/s" if self.ui.radio_mm.isChecked() else "µm/s"
        display_val = self.ui.spin_speed.value()
        self.ui.status_label.setText(f"Status: Stage speed set to {display_val} {unit} ({speed_mm} mm/s internal)")

    def check_stage_status(self):
        """Updates position, limits, applies unit conversions, and checks for errors."""
        pos = self.stage.query_position()
        if pos:
            self.current_pos = pos
            
            # Determine the multiplier based on the UI toggle
            is_um = self.ui.radio_um.isChecked()
            mult = 1000.0 if is_um else 1.0
            unit_str = "um" if is_um else "mm"
            
            # 1. Update the Current Position Display
            cur_x = pos[0] * mult
            cur_y = pos[1] * mult
            cur_z = pos[2] * mult
            self.ui.label_current_pos.setText(f"Pos: X: {cur_x:.3f}  Y: {cur_y:.3f}  Z: {cur_z:.3f} {unit_str}")

            # 2. Update the Remaining Limits Display (matching the selected unit)
            rem_x = (self.stage_max_x - pos[0]) * mult
            rem_y = (self.stage_max_y - pos[1]) * mult
            rem_z = (self.stage_max_z - pos[2]) * mult
            self.ui.label_limits.setText(f"Remaining: X: {rem_x:.1f}  Y: {rem_y:.1f}  Z: {rem_z:.1f} {unit_str}")

        # 3. Check Venus-1 Error buffer and route to the main status bar
        err = self.stage.get_error()
        if err:
            try:
                if float(err) != 0.0:
                    # Override the standard status message with a prominent error
                    self.ui.status_label.setText(f"STAGE ERROR: Code {err} - Check hardware limits!")
            except ValueError:
                # Catch text-based errors like "Communication error"
                self.ui.status_label.setText(f"STAGE ERROR: {err}")

    # ---------------------------------------------------------
    # CAMERA & IMAGE PROCESSING METHODS
    # ---------------------------------------------------------
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

    def capture_reference(self):
        """Captures the current frame to use as a flat-field correction map."""
        if self.last_full_frame is not None:
            # Store as float32 for division math, replace 0s with 1s to prevent division by zero
            self.reference_image = self.last_full_frame.copy().astype(np.float32)
            self.reference_image[self.reference_image == 0] = 1 
            self.ui.status_label.setText("Status: Dirt calibration reference saved!")

    def set_raw_mode(self):
        self.view_mode = "RAW"
        self.ui.camera_view.roi_visible = True
        self.ui.camera_view.update()  # Force redraw to show ROI
        self.ui.status_label.setText("Status: Showing Raw Feed")

    def set_processed_mode(self):
        if self.roi_center is None:
            self.ui.status_label.setText("Status: Please set ROI first!")
            return
        self.view_mode = "PROCESSED"
        self.ui.camera_view.roi_visible = False
        self.ui.camera_view.update()  # Force redraw to hide ROI
        self.ui.status_label.setText("Status: Showing ROI Processed")

    def save_roi_coords(self, x, y):
        self.roi_center = (x, y)
        self.ui.status_label.setText(f"Status: ROI set to {self.roi_center}")

    def handle_frame(self, frame):
        self.last_full_frame = frame.copy()
        processed_frame = frame.copy()

        # --- Flat-Field Correction (Dirt Removal) ---
        if self.reference_image is not None:
            # Calculate mean brightness to maintain overall exposure level
            mean_ref = np.mean(self.reference_image)
            # Divide raw image by reference map and normalize
            corrected = (processed_frame.astype(np.float32) / self.reference_image) * mean_ref
            processed_frame = np.clip(corrected, 0, 255).astype(np.uint8)

        # 1. Processing Logic (e.g., Background Removal)
        if self.ui.btn_bg_remove.isChecked():
            pass 

        # 2. View Mode Logic
        if self.view_mode == "PROCESSED" and self.roi_center:
            roi_manager = ROIManager(size=self.roi_size)
            display_img = roi_manager.get_crop(processed_frame, self.roi_center[0], self.roi_center[1])
        else:
            display_img = processed_frame

        self._update_ui(display_img)
        
    def _update_ui(self, cv_img):
        try:
            img = cv_img.copy()
            h, w = img.shape[:2]
            
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                qimg = QImage(img.data, w, h, w * 3, QImage.Format.Format_RGB888)
            else:
                qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)

            pixmap = QPixmap.fromImage(qimg.copy()) 
            self.ui.update_frame(pixmap)
            
        except Exception as e:
            print(f"UI Update Fehler: {e}")

    def run(self):
        self.ui.show()
        return self.app.exec()

# ---------------------------------------------------------
# EXECUTION ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    tracker = CellTrackerApp()
    sys.exit(tracker.run())