"""Simple Vision system with graceful fallback when OpenCV isn't available.

This module exposes `VisionSystem.analyze_scene()` which captures one frame
and returns a dict: {"fall_detected": "0|1"}
In environments without camera/opencv, it returns mocked results.
"""
import random

try:
    import cv2
    HAVE_CV = True
except Exception:
    HAVE_CV = False


class VisionSystem:
    def __init__(self, camera_index=0, picam2=None):
        self.camera_index = camera_index
        self.picam2 = picam2  # Use Pi Camera if provided
        if HAVE_CV:
            # attempt to load cascade for face detection if possible
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except Exception:
                self.face_cascade = None
        else:
            print("[VISION] OpenCV not available; using mock vision outputs.")

    def analyze_scene(self):
        """Capture an image and run quick heuristics for fall verification.

        Returns a dict e.g. {"fall_detected":"1"}
        """
        if HAVE_CV:
            if self.picam2:
                # Use Pi Camera
                try:
                    frame_raw = self.picam2.capture_array()
                    if frame_raw.shape[2] == 4:
                        frame = cv2.cvtColor(frame_raw, cv2.COLOR_BGRA2BGR)
                    else:
                        frame = frame_raw.copy()
                except Exception:
                    return None
            else:
                # Fallback to USB camera
                cam = cv2.VideoCapture(self.camera_index)
                ret, frame = cam.read()
                cam.release()
                if not ret or frame is None:
                    return None

            # Basic heuristic: if face found and bounding box aspect ratio suggests lying
            fall_flag = False
            confidence = 0.0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = []
            try:
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            except Exception:
                faces = []

            # If no faces -> weaker signal (no face might mean occlusion or turned away)
            if len(faces) == 0:
                fall_flag = True
                # moderate confidence when no face is detected (heuristic)
                confidence = 0.6
            else:
                # choose first face and inspect width/height
                (x, y, w, h) = faces[0]
                ratio = w / float(h) if h != 0 else 0
                # map ratio to confidence: ratio <=1.0 -> 0, ratio >=1.3 -> ~0.95
                if ratio <= 1.0:
                    confidence = 0.0
                else:
                    # linear map from 1.0..1.3 -> 0..0.95
                    confidence = min(0.95, max(0.0, (ratio - 1.0) / (1.3 - 1.0) * 0.95))
                if ratio > 1.2:  # wider than tall -> possibly lying
                    fall_flag = True

            return {"fall_detected": "1" if fall_flag else "0", "confidence": float(round(confidence, 2))}

        # Fallback mocked result (include a mock confidence)
        mock_flag = random.choice(["0", "1"])
        mock_conf = round(random.uniform(0.0, 1.0), 2)
        return {"fall_detected": mock_flag, "confidence": float(mock_conf)}
