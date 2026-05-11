class ROIManager:
    def __init__(self, size=200):
        self.size = size

    def get_crop(self, frame, center_x, center_y):
        if frame is None:
            return None
            
        h, w = frame.shape[:2]
        half = self.size // 2
        
        # Boundary checks
        x1 = max(0, center_x - half)
        y1 = max(0, center_y - half)
        x2 = min(w, center_x + half)
        y2 = min(h, center_y + half)
        
        return frame[y1:y2, x1:x2]