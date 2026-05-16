# AI Virtual Canvas Project

## Overview
This project is an interactive drawing application that uses a webcam to track hand gestures for air-drawing.

## Key Features
- **Selection Mode:** Index and Middle fingers up. Used to interact with UI buttons.
- **Drawing Mode:** Index finger up only. Draws on the digital canvas.
- **Dynamic Brush Size:** Distance between Thumb and Pinky tips controls thickness.
- **Anti-Gravity Mode:** Shifts drawn lines upward for a drifting effect.
- **Controls:** Color selection, Eraser, Clear, and Save (masterpiece.png).

## Technical Standards
- **Inference:** MediaPipe Hands (min_confidence=0.8).
- **Rendering:** OpenCV 2D rendering with NumPy-based persistent canvas.
- **Frame Rate:** Target 30+ FPS.

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python virtual_canvas.py`
3. Press 'q' to quit.
