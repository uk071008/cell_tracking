from PyQt6.QtWidgets import (QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFrame, QSlider, QGroupBox, QSizePolicy, 
                             QGridLayout, QDoubleSpinBox, QToolBox, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor

class CameraDisplay(QLabel):
    clicked_pos = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True) 
        self.roi_rect = None
        self.roi_visible = True
        self.crosshair_enabled = False
        self.mouse_pos = QPoint(0, 0)
        self.roi_size = 200
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self.ratio_x = 1.0
        self.ratio_y = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position().toPoint()
        if self.crosshair_enabled:
            self.update() 

    def mousePressEvent(self, event):
        if self.crosshair_enabled and event.button() == Qt.MouseButton.LeftButton:
            # Get click coordinates on the visible UI element
            ui_x = event.position().x()
            ui_y = event.position().y()
            
            # Map UI coordinates back to the original RAW image resolution
            real_x = int((ui_x - self.offset_x) * self.ratio_x)
            real_y = int((ui_y - self.offset_y) * self.ratio_y)
            
            self.roi_rect = QRect(int(ui_x - self.roi_size/2), int(ui_y - self.roi_size/2), self.roi_size, self.roi_size)
            self.clicked_pos.emit(real_x, real_y)
            
            self.crosshair_enabled = False 
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        if self.roi_rect and self.roi_visible:
            pen = QPen(QColor(0, 255, 0), 2)
            painter.setPen(pen)
            painter.drawRect(self.roi_rect)

        if self.crosshair_enabled:
            pen = QPen(QColor(250, 179, 135), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(self.mouse_pos.x(), 0, self.mouse_pos.x(), self.height())
            painter.drawLine(0, self.mouse_pos.y(), self.width(), self.mouse_pos.y())


class MainWindow(QMainWindow):
    set_roi_requested = pyqtSignal()
    show_raw_requested = pyqtSignal()
    show_processed_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cell Mapper")
        self.setMinimumSize(1100, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setMinimumWidth(320) 
        self.sidebar.setMaximumWidth(400) 
        self.sidebar_layout = QVBoxLayout(self.sidebar)

        # --- Accordion Menu (QToolBox) ---
        self.toolbox = QToolBox()

        # Add the three categories
        self.toolbox.addItem(self._create_camera_controls(), "Camera Settings")
        self.toolbox.addItem(self._create_tracking_controls(), "Tracking & View")
        self.toolbox.addItem(self._create_stage_controls(), "Stage Control")

        self.sidebar_layout.addWidget(self.toolbox, 1) 
        

    # --- Main Display Area ---
        self.display_container = QVBoxLayout()
        self.camera_view = CameraDisplay()
        
        self.display_container.addWidget(self.camera_view, 1)
        
        self.status_label = QLabel("Status: Ready")

        self.status_label.setStyleSheet("padding: 5px; border-top: 1px solid #555;")
        
        self.display_container.addWidget(self.status_label, 0)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.display_container)

    # ---------------------------------------------------------
    # UI COMPONENT CREATION METHODS
    # ---------------------------------------------------------
    def _create_camera_controls(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Exposure Slider
        self.label_expo = QLabel("Exposure: 200ms")
        self.slider_expo = QSlider(Qt.Orientation.Horizontal)
        self.slider_expo.setRange(1, 1000)
        self.slider_expo.setValue(200)
        layout.addWidget(self.label_expo)
        layout.addWidget(self.slider_expo)

        # Gain Slider
        self.label_gain = QLabel("Gain: 100%")
        self.slider_gain = QSlider(Qt.Orientation.Horizontal)
        self.slider_gain.setRange(100, 500)
        self.slider_gain.setValue(100)
        layout.addWidget(self.label_gain)
        layout.addWidget(self.slider_gain)

        # Color Correction
        self.label_color = QLabel("Color Temp: 6500K")
        self.slider_color = QSlider(Qt.Orientation.Horizontal)
        self.slider_color.setRange(2000, 15000)
        self.slider_color.setValue(6500)
        layout.addWidget(self.label_color)
        layout.addWidget(self.slider_color)
        
        layout.addSpacing(10)
        self.btn_capture_ref = QPushButton("Capture Reference (Dirt Calibration)")
        layout.addWidget(self.btn_capture_ref)
        
        layout.addStretch()
        return widget

    def _create_tracking_controls(self):
        widget = QWidget()  
        layout = QVBoxLayout(widget)

        # View Modes
        layout.addWidget(QLabel("VIEW MODES:"))
        self.btn_raw = QPushButton("Show Raw Image")
        self.btn_set_roi = QPushButton("Set ROI")
        self.btn_processed = QPushButton("Show Processed Image")
        
        self.btn_raw.clicked.connect(self.show_raw_requested.emit)
        self.btn_set_roi.clicked.connect(self.enable_crosshair)
        self.btn_processed.clicked.connect(self.show_processed_requested.emit)
        
        layout.addWidget(self.btn_raw)
        layout.addWidget(self.btn_set_roi)
        layout.addWidget(self.btn_processed)

        layout.addSpacing(15)

        # Processing & Tracking
        layout.addWidget(QLabel("PROCESSING:"))
        self.btn_bg_remove = QPushButton("Remove Background")
        self.btn_bg_remove.setCheckable(True)
        layout.addWidget(self.btn_bg_remove)

        self.btn_start_tracking = QPushButton("Start Tracking")
        self.btn_stop_tracking = QPushButton("Stop Tracking")
        self.btn_start_tracking.setCheckable(True)
        self.btn_stop_tracking.setCheckable(True)

        layout.addWidget(self.btn_start_tracking)
        layout.addWidget(self.btn_stop_tracking)
        
        layout.addStretch()
        return widget

    def _create_stage_controls(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Unit toggle
        unit_layout = QHBoxLayout()
        self.radio_mm = QRadioButton("mm")
        self.radio_um = QRadioButton("µm")
        self.radio_mm.setChecked(True)
        self.unit_group = QButtonGroup()
        self.unit_group.addButton(self.radio_mm)
        self.unit_group.addButton(self.radio_um)
        unit_layout.addWidget(QLabel("Units:"))
        unit_layout.addWidget(self.radio_mm)
        unit_layout.addWidget(self.radio_um)
        layout.addLayout(unit_layout)

        # Velocity control
        step_speed_layout = QGridLayout() # FIXED: Added parentheses
        
        step_speed_layout.addWidget(QLabel("Step Size:"), 0, 0)
        self.spin_step = QDoubleSpinBox()
        self.spin_step.setRange(0.001, 100.0)
        self.spin_step.setDecimals(3)
        self.spin_step.setValue(0.100)
        step_speed_layout.addWidget(self.spin_step, 0, 1)

        step_speed_layout.addWidget(QLabel("Speed:"), 1, 0)
        self.spin_speed = QDoubleSpinBox() # FIXED: Created the widget
        self.spin_speed.setRange(0.01, 10.0)
        self.spin_speed.setDecimals(2)
        self.spin_speed.setValue(1.0)
        step_speed_layout.addWidget(self.spin_speed, 1, 1)

        self.btn_apply_speed = QPushButton("Set Velocity")
        step_speed_layout.addWidget(self.btn_apply_speed, 1, 2)
        layout.addLayout(step_speed_layout)

        # Dpad
        nav_layout = QGridLayout()
        self.btn_stage_up = QPushButton("Y+")
        self.btn_stage_down = QPushButton("Y-")
        self.btn_stage_left = QPushButton("X-")
        self.btn_stage_right = QPushButton("X+")
        self.btn_stage_stop = QPushButton("STOP")
        self.btn_stage_stop.setStyleSheet("background-color: red; color: white; font-weight: bold;")

        self.btn_stage_z_up = QPushButton("Z+")
        self.btn_stage_z_down = QPushButton("Z-")

        nav_layout.addWidget(self.btn_stage_up, 0, 1)
        nav_layout.addWidget(self.btn_stage_left, 1, 0)
        nav_layout.addWidget(self.btn_stage_right, 1, 2)
        nav_layout.addWidget(self.btn_stage_down, 2, 1)
        nav_layout.addWidget(self.btn_stage_stop, 1, 1)

        nav_layout.addWidget(self.btn_stage_z_up, 0, 4)
        nav_layout.addWidget(self.btn_stage_z_down, 1, 4) 

        layout.addLayout(nav_layout)

        # --- Absolute Positioning (Go To) ---
        layout.addSpacing(15)
        layout.addWidget(QLabel("Go To Absolute Position (mm):"))
        
        goto_layout = QGridLayout()
        self.spin_goto_x = QDoubleSpinBox()
        self.spin_goto_y = QDoubleSpinBox()
        self.spin_goto_z = QDoubleSpinBox()
        
        # Set a safe, wide range for the inputs (-200 to +200 mm)
        for spin in [self.spin_goto_x, self.spin_goto_y, self.spin_goto_z]:
            spin.setRange(-200.0, 200.0) 
            spin.setDecimals(3)
            spin.setValue(0.000)
            
        goto_layout.addWidget(QLabel("X:"), 0, 0)
        goto_layout.addWidget(self.spin_goto_x, 0, 1)
        goto_layout.addWidget(QLabel("Y:"), 0, 2)
        goto_layout.addWidget(self.spin_goto_y, 0, 3)
        goto_layout.addWidget(QLabel("Z:"), 0, 4)
        goto_layout.addWidget(self.spin_goto_z, 0, 5)
        
        self.btn_goto = QPushButton("GO")
        self.btn_goto.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold;")
        goto_layout.addWidget(self.btn_goto, 0, 6)
        
        layout.addLayout(goto_layout)
        
        # 4. Position, Limit & Error Display
        layout.addSpacing(10)
        
        self.label_current_pos = QLabel("Pos: X: 0.000  Y: 0.000  Z: 0.000 mm")
        self.label_current_pos.setStyleSheet("font-size: 14px; font-weight: bold; color: #2ecc71;") # Bright green for visibility
        layout.addWidget(self.label_current_pos)

        self.label_limits = QLabel("Remaining: X:? Y:? Z:?")
        self.label_limits.setStyleSheet("color: gray;")
        layout.addWidget(self.label_limits)

        # Homing
        self.btn_home_stage = QPushButton("Home Stage")
        self.btn_home_stage.setStyleSheet("background-color: #ff9900; color: black; font-weight: bold;")
        layout.addWidget(self.btn_home_stage)
        layout.addSpacing(15)

        # Barriers
        self.btn_set_zero = QPushButton("Set Current Position as Zero")
        self.btn_set_zero.setStyleSheet("background-color: #3498db; color: white;")
        layout.addWidget(self.btn_set_zero)

        barrier_layout = QGridLayout()
        self.btn_set_left = QPushButton("Set Limit X-")
        self.btn_set_right = QPushButton("Set Limit X+")
        self.btn_set_top = QPushButton("Set Limit Y+")
        self.btn_set_bottom = QPushButton("Set Limit Y-")
        self.btn_set_z_up = QPushButton("Set Limit Z+")
        self.btn_set_z_down = QPushButton("Set Limit Z-")

        barrier_layout.addWidget(self.btn_set_left, 0, 0)
        barrier_layout.addWidget(self.btn_set_right, 0, 1)
        barrier_layout.addWidget(self.btn_set_top, 1, 0)
        barrier_layout.addWidget(self.btn_set_bottom, 1, 1)
        barrier_layout.addWidget(self.btn_set_z_up, 2, 0)
        barrier_layout.addWidget(self.btn_set_z_down, 2, 1)

        layout.addLayout(barrier_layout)
        
        layout.addStretch()
        return widget

    # ---------------------------------------------------------
    # UTILITY METHODS
    # ---------------------------------------------------------
    def enable_crosshair(self):
        self.camera_view.roi_visible = True
        self.camera_view.crosshair_enabled = True
        self.camera_view.setCursor(Qt.CursorShape.CrossCursor)
        self.status_label.setText("Status: Select ROI center on image...")

    def update_frame(self, pixmap):
        # Scale the pixmap to fit the current window size while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.camera_view.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.camera_view.setPixmap(scaled_pixmap)
        
        # Calculate scaling ratios and offsets so mouse clicks remain accurate on the raw image
        self.camera_view.ratio_x = pixmap.width() / scaled_pixmap.width()
        self.camera_view.ratio_y = pixmap.height() / scaled_pixmap.height()
        self.camera_view.offset_x = (self.camera_view.width() - scaled_pixmap.width()) / 2
        self.camera_view.offset_y = (self.camera_view.height() - scaled_pixmap.height()) / 2