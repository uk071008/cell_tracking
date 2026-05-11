from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
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

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.position().toPoint()
        if self.crosshair_enabled:
            self.update() 

    def mousePressEvent(self, event):
        if self.crosshair_enabled and event.button() == Qt.MouseButton.LeftButton:
            x, y = event.position().x(), event.position().y()
            self.roi_rect = QRect(int(x - self.roi_size/2), int(y - self.roi_size/2), self.roi_size, self.roi_size)
            self.clicked_pos.emit(int(x), int(y))
            self.crosshair_enabled = False # Deaktivieren nach Klick
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Zeichne ROI Box falls vorhanden
        if self.roi_rect:
            pen = QPen(QColor(0, 255, 0), 2)
            painter.setPen(pen)
            painter.drawRect(self.roi_rect)

        # Zeichne Fadenkreuz
        if self.crosshair_enabled:
            pen = QPen(QColor(250, 179, 135), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            # Vertikale Linie
            painter.drawLine(self.mouse_pos.x(), 0, self.mouse_pos.x(), self.height())
            # Horizontale Linie
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
        self.camera_view.setPixmap(pixmap)