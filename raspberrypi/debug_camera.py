#!/usr/bin/env python3
"""Debug script for camera testing."""

import cv2
from picamera2 import Picamera2
import time

def test_camera():
    print("Testing Pi Camera...")
    picam2 = Picamera2()
    try:
        picam2.configure(
            picam2.create_preview_configuration(
                main={"format": "XRGB8888", "size": (640, 480)}
            )
        )
        picam2.start()
        time.sleep(0.5)  # Warm-up

        print("Pi Camera started successfully")

        # Test capturing frames
        for i in range(5):
            frame_raw = picam2.capture_array()
            if frame_raw is not None:
                print(f"Frame {i+1}: {frame_raw.shape}")
            else:
                print(f"Frame {i+1}: Failed to capture")
            time.sleep(0.5)

        # Show live feed for 10 seconds
        print("Showing live feed for 10 seconds (close window to continue)...")
        start_time = time.time()
        while time.time() - start_time < 10:
            frame_raw = picam2.capture_array()
            if frame_raw.shape[2] == 4:
                frame = cv2.cvtColor(frame_raw, cv2.COLOR_BGRA2BGR)
            else:
                frame = frame_raw.copy()
            cv2.imshow('Pi Camera Debug', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()
        picam2.stop()
        print("Pi Camera test complete")

    except Exception as e:
        print(f"Pi Camera error: {e}")

if __name__ == "__main__":
    test_camera()

if __name__ == "__main__":
    test_camera()