import cv2
import numpy as np

class StaticBackgroundSubtractor:
    """Handles static background subtraction ('White Paper Method')."""
    def __init__(self):
        self.reference_image = None

    def set_reference(self, image):
        """Sets the reference image (the white paper model)."""
        if image is None:
            self.reference_image = None
            return
        
        # Convert to gray if necessary to match pipeline
        if len(image.shape) == 3:
            self.reference_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            self.reference_image = image.copy()
        
        # Apply slight blur to reference to reduce single-pixel noise
        self.reference_image = cv2.GaussianBlur(self.reference_image, (5, 5), 0)
        print("Static Background Model captured.")

    def apply(self, frame):
        """Subtracts reference from frame and returns foreground mask."""
        if self.reference_image is None or frame is None:
            # If no model captured, foreground is everything (binary white mask)
            # Or just return None to indicate no processing.
            return None

        # Prepare current frame
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame

        # Simple absolute difference
        diff = cv2.absdiff(gray_frame, self.reference_image)
        
        # Threshold to get binary mask. Adjust '15' based on noise levels.
        _, mask = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)
        
        return mask