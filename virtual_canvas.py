"""
AI Virtual Canvas
An interactive application using OpenCV and MediaPipe for air-drawing.
Includes Exponential Moving Average (EMA) for smooth landmark tracking.
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
    try:
        from mediapipe.solutions import hands as mp_hands
        from mediapipe.solutions import drawing_utils as mp_drawing
    except (ImportError, AttributeError):
        # Fallback for certain Windows/Python 3.12 environments
        from mediapipe.python.solutions import hands as mp_hands
        from mediapipe.python.solutions import drawing_utils as mp_drawing
except Exception as e:
    print(f"\n[!] Critical: Failed to load MediaPipe: {e}")
    print("[*] Troubleshooting: Ensure 'pip install mediapipe==0.10.13' was successful.")
    sys.exit(1)

class VirtualCanvas:
    def __init__(self):
        # Initialize Webcam
        # Use CAP_DSHOW on Windows to prevent startup delays and ensure consistency
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback to default backend if DSHOW fails
            self.cap = cv2.VideoCapture(0)
            
        if not self.cap.isOpened():
            raise Exception("Failed to open the webcam. Please ensure it is connected and accessible.")
        
        # Performance settings
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Failed to read from the webcam.")
            
        self.height, self.width, _ = frame.shape
        
        # Digital Canvas layer
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # MediaPipe Hands instance
        self.mp_hands = mp_hands
        self.mp_draw = mp_drawing
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # State Management
        self.prev_x, self.prev_y = 0, 0
        self.draw_color = (255, 0, 0) # Blue (BGR)
        self.brush_size = 5
        self.anti_gravity = False
        self.mode = "Starting..."
        
        # Smoothing (EMA) factor
        self.smooth_x, self.smooth_y = 0, 0
        self.alpha = 0.5 
        
        self.colors = {
            'Blue': (255, 0, 0),
            'Green': (0, 255, 0),
            'Red': (0, 0, 255),
            'Yellow': (0, 255, 255),
            'Eraser': (0, 0, 0)
        }
        
        # UI Layout (Fixed to top bar)
        self.ui_boxes = {
            'Blue': {'rect': (20, 20, 100, 80), 'color': self.colors['Blue'], 'type': 'color'},
            'Green': {'rect': (110, 20, 190, 80), 'color': self.colors['Green'], 'type': 'color'},
            'Red': {'rect': (200, 20, 280, 80), 'color': self.colors['Red'], 'type': 'color'},
            'Yellow': {'rect': (290, 20, 370, 80), 'color': self.colors['Yellow'], 'type': 'color'},
            'Eraser': {'rect': (380, 20, 480, 80), 'color': (150, 150, 150), 'type': 'tool', 'label': 'Eraser'},
            'Gravity': {'rect': (490, 20, 610, 80), 'color': (180, 80, 80), 'type': 'toggle', 'label': 'Gravity'},
            'Clear': {'rect': (620, 20, 720, 80), 'color': (80, 80, 180), 'type': 'action', 'label': 'Clear'},
            'Save': {'rect': (730, 20, 830, 80), 'color': (80, 180, 80), 'type': 'action', 'label': 'Save'}
        }

    def draw_ui(self, frame):
        for key, box in self.ui_boxes.items():
            x1, y1, x2, y2 = box['rect']
            
            # Draw Selection Highlight
            is_active = False
            if box['type'] == 'color' and self.draw_color == box['color'] and self.draw_color != (0,0,0):
                is_active = True
            elif key == 'Eraser' and self.draw_color == (0,0,0):
                is_active = True
            elif key == 'Gravity' and self.anti_gravity:
                is_active = True
                
            if is_active:
                cv2.rectangle(frame, (x1-5, y1-5), (x2+5, y2+5), (255, 255, 255), 3)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), box['color'], -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
            
            label = box.get('label', key)
            cv2.putText(frame, label, (x1 + 10, y1 + 40), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

    def check_ui(self, x, y):
        for key, box in self.ui_boxes.items():
            x1, y1, x2, y2 = box['rect']
            if x1 <= x <= x2 and y1 <= y <= y2:
                if box['type'] == 'color':
                    self.draw_color = box['color']
                elif key == 'Eraser':
                    self.draw_color = (0, 0, 0)
                elif key == 'Gravity':
                    self.anti_gravity = not self.anti_gravity
                    time.sleep(0.3) # Prevent rapid toggling
                elif key == 'Clear':
                    self.canvas = np.zeros_like(self.canvas)
                    time.sleep(0.3)
                elif key == 'Save':
                    return 'Save'
        return None

    def apply_smoothing(self, x, y):
        if self.smooth_x == 0 and self.smooth_y == 0:
            self.smooth_x, self.smooth_y = x, y
        else:
            self.smooth_x = int(self.alpha * x + (1 - self.alpha) * self.smooth_x)
            self.smooth_y = int(self.alpha * y + (1 - self.alpha) * self.smooth_y)
        return self.smooth_x, self.smooth_y

    def run(self):
        while True:
            success, frame = self.cap.read()
            if not success: break
            
            frame = cv2.flip(frame, 1)
            
            # Apply Anti-Gravity Effect
            if self.anti_gravity:
                shift = 4
                new_canvas = np.zeros_like(self.canvas)
                new_canvas[:-shift, :] = self.canvas[shift:, :]
                self.canvas = new_canvas

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            curr_action = None

            if results.multi_hand_landmarks:
                for hand_lms in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                    
                    def get_pt(idx):
                        lm = hand_lms.landmark[idx]
                        return int(lm.x * self.width), int(lm.y * self.height)
                    
                    idx_tip = get_pt(8)
                    idx_pip = get_pt(6)
                    mid_tip = get_pt(12)
                    mid_pip = get_pt(10)
                    thumb_tip = get_pt(4)
                    pinky_tip = get_pt(20)
                    
                    sx, sy = self.apply_smoothing(idx_tip[0], idx_tip[1])
                    
                    idx_up = idx_tip[1] < idx_pip[1]
                    mid_up = mid_tip[1] < mid_pip[1]
                    
                    # Brush Size mapped to Thumb-Pinky distance
                    dist = math.hypot(thumb_tip[0] - pinky_tip[0], thumb_tip[1] - pinky_tip[1])
                    self.brush_size = int(np.interp(dist, [30, 200], [2, 40]))
                    
                    if idx_up and mid_up:
                        self.mode = "Selection"
                        self.prev_x, self.prev_y = 0, 0
                        cv2.circle(frame, (sx, sy), 10, (255, 0, 255), cv2.FILLED)
                        curr_action = self.check_ui(sx, sy)
                    elif idx_up and not mid_up:
                        self.mode = "Drawing"
                        if self.prev_x == 0 and self.prev_y == 0:
                            self.prev_x, self.prev_y = sx, sy
                        
                        thickness = self.brush_size if self.draw_color != (0,0,0) else self.brush_size * 2
                        cv2.line(self.canvas, (self.prev_x, self.prev_y), (sx, sy), self.draw_color, thickness)
                        self.prev_x, self.prev_y = sx, sy
                    else:
                        self.mode = "Neutral"
                        self.prev_x, self.prev_y = 0, 0
            else:
                self.mode = "Idle"
                self.prev_x, self.prev_y = 0, 0

            # Layer Blending Masking
            gray_canvas = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray_canvas, 1, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)
            
            frame_bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
            composite = cv2.add(frame_bg, self.canvas)
            
            self.draw_ui(composite)
            
            if curr_action == 'Save':
                cv2.imwrite('masterpiece.png', composite)
                cv2.putText(composite, "SAVED!", (self.width//2 - 50, self.height//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Virtual Canvas", composite)
                cv2.waitKey(500)

            cv2.putText(composite, f"Mode: {self.mode} | Size: {self.brush_size}", (20, self.height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("Virtual Canvas", composite)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        app = VirtualCanvas()
        app.run()
    except Exception as e:
        print(f"\n[!] Application Error: {e}")
