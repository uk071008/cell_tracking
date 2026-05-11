from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSlider, QGroupBox, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor

class CameraDisplay(QLabel):
    clicked_pos = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True) 
        self.roi_rect = None
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
            
            if self.roi_rect:
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
        self.setWindowTitle("CellTracker Pro - ROI Focus")
        self.setMinimumSize(1100, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar)

        self.btn_raw = QPushButton("Show Raw Image")
        self.btn_set_roi = QPushButton("Set ROI")
        self.btn_processed = QPushButton("Show Processed Image")
        self.btn_bg_remove = QPushButton("Remove Background")
        self.btn_bg_remove.setCheckable(True)

        self.sidebar_layout.addWidget(QLabel("VIEW MODES"))
        self.sidebar_layout.addWidget(self.btn_raw)
        self.sidebar_layout.addWidget(self.btn_set_roi)
        self.sidebar_layout.addWidget(self.btn_processed)
        self.sidebar_layout.addSpacing(20)
        self.sidebar_layout.addWidget(QLabel("PROCESSING"))
        self.sidebar_layout.addWidget(self._create_camera_controls())
        self.sidebar_layout.addWidget(self.btn_bg_remove)
        self.sidebar_layout.addStretch()

        # Connect internal buttons to signals
        self.btn_raw.clicked.connect(self.show_raw_requested.emit)
        self.btn_set_roi.clicked.connect(self.enable_crosshair)
        self.btn_processed.clicked.connect(self.show_processed_requested.emit)

        # --- Display ---
        self.display_container = QVBoxLayout()
        self.camera_view = CameraDisplay()
        self.display_container.addWidget(self.camera_view)
        self.status_label = QLabel("Status: Ready")
        self.display_container.addWidget(self.status_label)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.display_container)

    def enable_crosshair(self):
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

    def _create_camera_controls(self):
        group = QGroupBox("Camera Settings")
        layout = QVBoxLayout()

        # Exposure Slider (Belichtungszeit)
        self.label_expo = QLabel("Exposure: 200ms")
        self.slider_expo = QSlider(Qt.Orientation.Horizontal)
        self.slider_expo.setRange(1, 1000) # 1ms bis 1000ms
        self.slider_expo.setValue(200)
        layout.addWidget(self.label_expo)
        layout.addWidget(self.slider_expo)

        # Gain Slider (Verstärkung)
        self.label_gain = QLabel("Gain: 100%")
        self.slider_gain = QSlider(Qt.Orientation.Horizontal)
        self.slider_gain.setRange(100, 500) # 100% bis 500%
        self.slider_gain.setValue(100)
        layout.addWidget(self.label_gain)
        layout.addWidget(self.slider_gain)

        # Color Correction (White Balance / Temperature)
        self.label_color = QLabel("Color Temp: 6500K")
        self.slider_color = QSlider(Qt.Orientation.Horizontal)
        self.slider_color.setRange(2000, 15000)
        self.slider_color.setValue(6500)
        layout.addWidget(self.label_color)
        layout.addWidget(self.slider_color)
        
        self.btn_capture_ref = QPushButton("Capture Reference (Dirt Calibration)")
        layout.addWidget(self.btn_capture_ref)

        group.setLayout(layout)
        return group