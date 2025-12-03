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

            # Improved heuristic: combine face bounding-box aspect ratio and face size
            # to produce a more stable confidence score in [0.0, 1.0]. If no face
            # is detected we return a moderate confidence (occlusion could mean
            # the person is facing away or lying). We also print debug info so
            # you can tune thresholds.
            fall_flag = False
            confidence = 0.0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = []
            try:
                if self.face_cascade is not None:
                    faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            except Exception:
                faces = []

            frame_h, frame_w = frame.shape[0], frame.shape[1]
            frame_area = max(1.0, float(frame_w * frame_h))

            if len(faces) == 0:
                # No face found — this is a weaker but meaningful signal for lying
                fall_flag = True
                confidence = 0.6
                print(f"[VISION_DBG] faces=0 -> conf={confidence}")
            else:
                (x, y, w, h) = faces[0]
                ratio = (w / float(h)) if h != 0 else 0.0
                face_area = float(w * h)
                # face size relative to frame: normalized by an expected max face area
                # (tunable; 0.12 corresponds to a fairly close face). Clamp to [0,1]
                face_area_norm = min(1.0, max(0.0, face_area / (0.12 * frame_area)))

                # ratio score: 0 when ratio<=1 (taller than wide), 1 when ratio>=1.5
                ratio_score = 0.0
                if ratio > 1.0:
                    ratio_score = min(1.0, (ratio - 1.0) / (1.5 - 1.0))

                # combine signals (weights tuned empirically). Favor face size when ratio is weak.
                confidence = 0.6 * face_area_norm + 0.4 * ratio_score
                confidence = float(round(min(0.99, max(0.0, confidence)), 2))

                # decide fall flag: require a reasonably strong ratio OR very large face area
                if ratio_score >= 0.7 or face_area_norm >= 0.9:
                    fall_flag = True

                print(f"[VISION_DBG] faces={len(faces)} ratio={ratio:.2f} face_area_norm={face_area_norm:.3f} ratio_score={ratio_score:.3f} conf={confidence}")

            return {"fall_detected": "1" if fall_flag else "0", "confidence": confidence}

        # Fallback mocked result (include a mock confidence)
        mock_flag = random.choice(["0", "1"])
        mock_conf = round(random.uniform(0.0, 1.0), 2)
        return {"fall_detected": mock_flag, "confidence": float(mock_conf)}
