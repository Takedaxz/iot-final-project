"""Simple Vision system with graceful fallback when OpenCV isn't available.

This module exposes `VisionSystem.analyze_scene()` which captures one frame
and returns a dict: {"fall_detected": "0|1", "emotions": "happy|sad|neutral"}
In environments without camera/opencv, it returns mocked results.
"""
import random

try:
    import cv2
    HAVE_CV = True
except Exception:
    HAVE_CV = False


class VisionSystem:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        if HAVE_CV:
            # attempt to load cascade for face detection if possible
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except Exception:
                self.face_cascade = None
        else:
            print("[VISION] OpenCV not available; using mock vision outputs.")

    def analyze_scene(self):
        """Capture an image and run quick heuristics for fall verification and emotion.

        Returns a dict e.g. {"fall_detected":"1","emotions":"sad"}
        """
        if HAVE_CV:
            cam = cv2.VideoCapture(self.camera_index)
            ret, frame = cam.read()
            cam.release()
            if not ret or frame is None:
                return None

            # Basic heuristic: if face found and bounding box aspect ratio suggests lying
            fall_flag = False
            emotion = "neutral"

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = []
            try:
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            except Exception:
                faces = []

            # If no faces or wide bounding box, guess fall
            if len(faces) == 0:
                fall_flag = True
            else:
                # choose first face and inspect width/height
                (x, y, w, h) = faces[0]
                ratio = w / float(h) if h != 0 else 0
                if ratio > 1.2:  # wider than tall -> possibly lying
                    fall_flag = True

            # Emotion: placeholder random choice (replace with model in real project)
            emotions_list = ["happy", "sad", "neutral"]
            emotion = random.choice(emotions_list)

            return {"fall_detected": "1" if fall_flag else "0",
                    "emotions": emotion}

        # Fallback mocked result
        emotions_list = ["happy", "sad", "neutral"]
        return {"fall_detected": random.choice(["0", "1"]), "emotions": random.choice(emotions_list)}
