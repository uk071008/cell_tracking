import cv2
import numpy as np
import os

os.makedirs('data', exist_ok=True)

def draw_optical_donut(img, x, y, radius, intensity, is_white_bg=False):
    """Zeichnet einen optischen Donut-Effekt."""
    # Auf grauem Grund ist der Dreck dunkler als der Hintergrund, 
    # auf weißem Grund noch viel dunkler.
    
    # Äußerer Ring (Diffus)
    alpha = 0.7
    overlay = img.copy()
    cv2.circle(overlay, (x, y), radius, (intensity), -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    # Innerer Kern (Dunkler)
    inner_radius = int(radius * 0.4)
    inner_color = int(intensity * 0.5) if not is_white_bg else int(intensity * 0.3)
    cv2.circle(img, (x, y), inner_radius, inner_color, -1)
    return img

def generate_clean_mock_set(width=1280, height=720):
    # Gemeinsame Parameter für den Dreck
    dirt_data = []
    for _ in range(12):
        dirt_data.append({
            'pos': (np.random.randint(100, width-100), np.random.randint(100, height-100)),
            'radius': np.random.randint(20, 45),
            'base_intensity': np.random.randint(60, 90) # Dunkelheitswert
        })

    # --- BILD 1: Grauer Hintergrund (Arbeitsbild) ---
    # Ein ruhiges, mittleres Grau (z.B. Wert 160)
    grey_bg = np.full((height, width), 160, dtype=np.uint8)
    
    for d in dirt_data:
        draw_optical_donut(grey_bg, d['pos'][0], d['pos'][1], d['radius'], d['base_intensity'])
    
    # Sehr feines Gaußsches Rauschen hinzufügen
    noise = np.random.normal(0, 2, (height, width)).astype(np.uint8)
    grey_bg = cv2.add(grey_bg, noise)
    # Finaler Blur für optische Weichheit
    grey_bg = cv2.GaussianBlur(grey_bg, (11, 11), 0)
    cv2.imwrite("data/mock_dirt_grey.png", grey_bg)

    # --- BILD 2: Weißer Hintergrund (Kalibrierung) ---
    white_bg = np.full((height, width), 245, dtype=np.uint8)
    
    for d in dirt_data:
        # Der gleiche Dreck, aber auf Weiß etwas "härter" gezeichnet
        draw_optical_donut(white_bg, d['pos'][0], d['pos'][1], d['radius'], d['base_intensity'] - 20, is_white_bg=True)
        
    white_bg = cv2.GaussianBlur(white_bg, (11, 11), 0)
    cv2.imwrite("data/mock_calibration_white.png", white_bg)
    
    print("Bilder generiert: 'mock_dirt_grey.png' und 'mock_calibration_white.png'")

if __name__ == "__main__":
    generate_clean_mock_set()