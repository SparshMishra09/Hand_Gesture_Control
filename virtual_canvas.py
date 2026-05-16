"""
AI Virtual Canvas - Premium Edition
An interactive, high-performance air-drawing application with:
- Intelligent Shape Snapping (Circle, Square, Triangle)
- Rainbow & Neon Glow Brushes
- Palm-to-Erase Gesture (All 5 fingers up)
- Premium Glassmorphism UI with smooth transitions
- Real-time Hand Tracking Visualization
"""

import os
import sys
import math
import time
import numpy as np
import cv2

# --- Robust MediaPipe Import Handling ---
try:
    import mediapipe as mp
    # Try standard path first, then fall back to internal python path
    try:
        from mediapipe.solutions import hands as mp_hands
        from mediapipe.solutions import drawing_utils as mp_drawing
    except (ImportError, AttributeError):
        from mediapipe.python.solutions import hands as mp_hands
        from mediapipe.python.solutions import drawing_utils as mp_drawing
except Exception as e:
    print(f"\n[!] Critical: Failed to load MediaPipe: {e}")
    sys.exit(1)

# --- Utility Functions ---
def draw_rounded_rect(img, pt1, pt2, color, thickness, r):
    x1, y1 = pt1
    x2, y2 = pt2
    # Draw the core rectangles
    cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, thickness)
    cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, thickness)
    # Draw the corners
    cv2.circle(img, (x1 + r, y1 + r), r, color, thickness)
    cv2.circle(img, (x2 - r, y1 + r), r, color, thickness)
    cv2.circle(img, (x1 + r, y2 - r), r, color, thickness)
    cv2.circle(img, (x2 - r, y2 - r), r, color, thickness)

class PremiumCanvas:
    def __init__(self):
        # Initialize Webcam
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened(): self.cap = cv2.VideoCapture(0)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        ret, frame = self.cap.read()
        self.h, self.w = frame.shape[:2]
        
        # Layers
        self.canvas = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        self.glow_layer = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        
        # MediaPipe
        self.mp_hands = mp_hands
        self.mp_draw = mp_drawing
        self.hands_detector = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=1,
            model_complexity=1, min_detection_confidence=0.8, min_tracking_confidence=0.8
        )
        
        # UI State
        self.active_category = 'Colors'
        self.draw_color = (255, 0, 0)
        self.brush_mode = 'Solid' # Solid, Rainbow, Neon
        self.brush_size = 5
        self.hue = 0
        self.prev_x, self.prev_y = 0, 0
        self.smooth_x, self.smooth_y = 0, 0
        self.current_stroke = []
        
        # Menus
        self.categories = ['Colors', 'Brushes', 'Actions']
        self.menu_items = {
            'Colors': [
                {'label': 'Red', 'color': (0, 0, 255)},
                {'label': 'Green', 'color': (0, 255, 0)},
                {'label': 'Blue', 'color': (255, 0, 0)},
                {'label': 'Yellow', 'color': (0, 255, 255)},
                {'label': 'Magenta', 'color': (255, 0, 255)},
                {'label': 'Cyan', 'color': (255, 255, 0)}
            ],
            'Brushes': [
                {'label': 'Solid', 'icon': 'S'},
                {'label': 'Rainbow', 'icon': 'R'},
                {'label': 'Neon', 'icon': 'N'}
            ],
            'Actions': [
                {'label': 'Clear', 'action': 'clear'},
                {'label': 'Save', 'action': 'save'}
            ]
        }

    def detect_gesture(self, landmarks):
        # Index
        idx_up = landmarks[8].y < landmarks[6].y
        # Middle
        mid_up = landmarks[12].y < landmarks[10].y
        # Ring
        ring_up = landmarks[16].y < landmarks[14].y
        # Pinky
        pinky_up = landmarks[20].y < landmarks[18].y
        
        # PALM ERASE: All 4 main fingers extended
        if idx_up and mid_up and ring_up and pinky_up:
            return 'ERASE'
        
        # SELECTION MODE: Index and Middle up
        if idx_up and mid_up:
            return 'SELECT'
            
        # DRAW MODE: Only Index up
        if idx_up and not mid_up:
            return 'DRAW'
            
        return 'IDLE'

    def process_shape(self):
        if len(self.current_stroke) < 20: return
        
        pts = np.array(self.current_stroke, dtype=np.int32)
        epsilon = 0.04 * cv2.arcLength(pts, True)
        approx = cv2.approxPolyDP(pts, epsilon, True)
        
        color = self.get_current_color()
        if len(approx) == 3: # Triangle
            cv2.drawContours(self.canvas, [approx], 0, color, self.brush_size)
        elif len(approx) == 4: # Square/Rectangle
            x, y, w, h = cv2.boundingRect(pts)
            cv2.rectangle(self.canvas, (x, y), (x + w, y + h), color, self.brush_size)
        elif len(approx) > 6: # Circle
            (x, y), radius = cv2.minEnclosingCircle(pts)
            center = (int(x), int(y))
            cv2.circle(self.canvas, center, int(radius), color, self.brush_size)

    def get_current_color(self):
        if self.brush_mode == 'Rainbow' or self.brush_mode == 'Neon':
            hsv = np.uint8([[[self.hue % 180, 255, 255]]])
            return tuple(map(int, cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]))
        return self.draw_color

    def draw_ui(self, frame):
        overlay = frame.copy()
        draw_rounded_rect(overlay, (20, 20), (self.w - 20, 140), (40, 40, 40), -1, 20)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        for i, cat in enumerate(self.categories):
            x = 50 + i * 150
            color = (255, 255, 255) if self.active_category == cat else (150, 150, 150)
            cv2.putText(frame, cat, (x, 60), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 1, cv2.LINE_AA)
            if self.active_category == cat:
                cv2.line(frame, (x, 70), (x + 80, 70), (255, 255, 255), 2)

        items = self.menu_items[self.active_category]
        for i, item in enumerate(items):
            x = 50 + i * 100
            y = 100
            if 'color' in item:
                cv2.circle(frame, (x + 30, y), 20, item['color'], -1)
                if self.draw_color == item['color']:
                    cv2.circle(frame, (x + 30, y), 25, (255, 255, 255), 2)
            else:
                color = (255, 255, 255) if (self.brush_mode == item['label'] or item.get('action')) else (150, 150, 150)
                cv2.putText(frame, item['label'], (x, y + 5), cv2.FONT_HERSHEY_DUPLEX, 0.5, color, 1, cv2.LINE_AA)

    def handle_click(self, x, y):
        for i, cat in enumerate(self.categories):
            cx = 50 + i * 150
            if cx <= x <= cx + 120 and 30 <= y <= 80:
                self.active_category = cat
                return

        items = self.menu_items[self.active_category]
        for i, item in enumerate(items):
            ix = 50 + i * 100
            if ix <= x <= ix + 80 and 80 <= y <= 130:
                if 'color' in item: self.draw_color = item['color']
                elif 'action' in item:
                    if item['action'] == 'clear': self.canvas[:] = 0; self.glow_layer[:] = 0
                    if item['action'] == 'save': cv2.imwrite('masterpiece.png', self.final_composite)
                elif 'label' in item and self.active_category == 'Brushes':
                    self.brush_mode = item['label']
                time.sleep(0.2)

    def run(self):
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)
            self.hue += 2
            
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands_detector.process(rgb)
            
            gesture = 'IDLE'
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Robust HAND_CONNECTIONS access via the hands module itself
                    self.mp_draw.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                    )
                    
                    lms = hand_landmarks.landmark
                    gesture = self.detect_gesture(lms)
                    
                    raw_x, raw_y = int(lms[8].x * self.w), int(lms[8].y * self.h)
                    self.smooth_x = int(0.6 * raw_x + 0.4 * self.smooth_x)
                    self.smooth_y = int(0.6 * raw_y + 0.4 * self.smooth_y)
                    
                    if gesture == 'DRAW':
                        if self.prev_x == 0: self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                        color = self.get_current_color()
                        target = self.glow_layer if self.brush_mode == 'Neon' else self.canvas
                        cv2.line(target, (self.prev_x, self.prev_y), (self.smooth_x, self.smooth_y), color, self.brush_size)
                        self.current_stroke.append((self.smooth_x, self.smooth_y))
                        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                    elif gesture == 'ERASE':
                        palm_x, palm_y = int(lms[9].x * self.w), int(lms[9].y * self.h)
                        cv2.circle(self.canvas, (palm_x, palm_y), 60, (0, 0, 0), -1)
                        cv2.circle(self.glow_layer, (palm_x, palm_y), 65, (0, 0, 0), -1)
                        cv2.circle(frame, (palm_x, palm_y), 60, (255, 255, 255), 2)
                        self.prev_x = 0
                    elif gesture == 'SELECT':
                        cv2.circle(frame, (self.smooth_x, self.smooth_y), 10, (255, 0, 255), -1)
                        self.handle_click(self.smooth_x, self.smooth_y)
                        if self.current_stroke:
                            self.process_shape()
                            self.current_stroke = []
                        self.prev_x = 0
                    else:
                        if self.current_stroke:
                            self.process_shape()
                            self.current_stroke = []
                        self.prev_x = 0

            glow_blurred = cv2.GaussianBlur(self.glow_layer, (25, 25), 0)
            gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            
            self.final_composite = cv2.addWeighted(frame, 1.0, glow_blurred, 1.0, 0)
            self.final_composite = np.where(mask[:, :, None] == 255, self.canvas, self.final_composite)
            self.draw_ui(self.final_composite)
            
            cv2.imshow("Premium AI Canvas", self.final_composite)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    PremiumCanvas().run()
