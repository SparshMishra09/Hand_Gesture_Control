import sys
import os

def debug_environment():
    print("--- AI Virtual Canvas Debugger ---")
    print(f"Python Version: {sys.version}")
    
    try:
        import numpy
        print(f"NumPy Version: {numpy.__version__}")
        if int(numpy.__version__.split('.')[0]) >= 2:
            print("[!] WARNING: NumPy 2.x detected. MediaPipe often fails with NumPy 2.0+ on Windows.")
            print("    Try: pip install \"numpy<2.0.0\"")
    except ImportError:
        print("[!] NumPy not found.")

    try:
        import cv2
        print(f"OpenCV Version: {cv2.__version__}")
    except ImportError:
        print("[!] OpenCV not found.")

    try:
        import mediapipe as mp
        print(f"MediaPipe Version: {mp.__version__}")
        try:
            from mediapipe.solutions import hands
            print("[✓] MediaPipe Solutions loaded successfully (Standard path).")
        except (AttributeError, ImportError):
            try:
                from mediapipe.python.solutions import hands
                print("[✓] MediaPipe Solutions loaded successfully (Alternative path).")
            except Exception as e:
                print(f"[!] MediaPipe Solutions failed on both paths: {e}")
    except ImportError:
        print("[!] MediaPipe not found.")

if __name__ == "__main__":
    debug_environment()
