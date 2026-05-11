def get_stylesheet():
    return """
    QMainWindow {
        background-color: #1e1e2e;
    }

    QFrame {
        background-color: #2b2b3b;
        border-radius: 10px;
        margin: 5px;
    }

    QLabel {
        color: #cdd6f4;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
        font-weight: bold;
    }

    QPushButton {
        background-color: #45475a;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
        font-size: 13px;
    }

    QPushButton:hover {
        background-color: #585b70;
    }

    QPushButton:checked {
        background-color: #fab387;
        color: #11111b;
    }

    QSlider::handle:horizontal {
        background: #fab387;
        border: 1px solid #fab387;
        width: 18px;
        margin: -2px 0;
        border-radius: 9px;
    }
    
    CameraDisplay {
        background-color: #000000;
        border: 2px solid #fab387;
    }
    """