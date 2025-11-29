"""Main gateway runner for ElderSafe Gateway.

Usage: `python main.py`

This script subscribes to `elder/sensor/motion` and acts on camera verification
and publishes environment data periodically to `elder/sensor/env`.
Also runs web stream at http://<pi-ip>:5000
"""
import time
import json
import threading
import config
from modules.hardware_ctrl import HardwareManager
from modules.vision_ai import VisionSystem
from modules.mqtt_handler import MQTTHandler

# Flask imports
from flask import Flask, Response, render_template, jsonify
import cv2
from picamera2 import Picamera2
import mediapipe as mp
import numpy as np
import time

# Flask app
app = Flask(__name__)

# MediaPipe
mp_face_mesh = mp.solutions.face_mesh

# Global states for web
fall_status = "Status: OK"
global_expression = "Neutral"
global_temperature = "N/A"
global_humidity = "N/A"
global_smoke_status = "SMOKE_OK"
global_critical_alert = "ALERT_OK"
global_latest_g_force = 0.0

# Camera for web stream (Pi Camera)
picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "XRGB8888", "size": (640, 480)}
    )
)
picam2.start()
time.sleep(0.5)  # Warm-up time

# Initialize hardware and vision early
hw = HardwareManager(config)
vision = VisionSystem(picam2=picam2)

# --------------------------------------------------
# FACIAL EXPRESSION DETECTION
# --------------------------------------------------
def euclidean(p1, p2):
    return np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y]))

def classify_emotion(lm):
    LEC, REC = 33, 263
    ML, MR = 61, 291
    LU, LD = 13, 14
    io = euclidean(lm[LEC], lm[REC])
    if io < 1e-6: return "Neutral"

    mw = euclidean(lm[ML], lm[MR]) / io
    mo = euclidean(lm[LU], lm[LD]) / io

    if mo > 0.08: return "Surprised"
    if mw > 0.48: return "Happy"
    if mo < 0.018 and mw < 0.36: return "Sad"
    return "Neutral"


def on_mqtt_message(client, userdata, msg):
    global global_temperature, global_humidity, global_smoke_status
    global global_critical_alert, global_latest_g_force, global_expression

    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = None

    print(f"[MQTT] Received on {topic}: {payload}")

    if topic == config.TOPIC_MOTION and payload:
        try:
            g_val = float(payload.get('g_force', 0))
            mic_val = float(payload.get('mic', 0))
        except Exception:
            g_val = 0
            mic_val = 0

        # Forward raw motion data to cloud
        mqtt.publish(config.TOPIC_CLOUD_MOTION, payload)
        print(f"[CLOUD] Forwarded motion: {payload}")

        global_latest_g_force = g_val

        if g_val > config.G_FORCE_LIMIT:
            print('[LOGIC] High impact -> trigger vision verification')
            ai_result = vision.analyze_scene()
            print(f"[VISION] Cam analysis result: {ai_result}")
            if ai_result and ai_result.get('fall_detected') == '1':
                payload = {"fall_detected": "1", "emotions": global_expression}
                mqtt.publish(config.TOPIC_CAM, payload)
                print(f"[FALL] Published confirmed fall: {payload}")
                global_critical_alert = "FALL DETECTED"
            else:
                global_critical_alert = "ALERT_OK"

    elif topic == config.TOPIC_CAM and payload:
        if str(payload.get('fall_detected')) == '1':
            print('[LOGIC] Confirmed fall -> triggering emergency protocol')
            # run emergency in separate thread so env loop continues
            threading.Thread(target=handle_emergency, args=(mqtt,)).start()


def handle_emergency(mqtt_client):
    hw.trigger_emergency()
    # Publish an immediate env/state message so central system knows
    mqtt_client.publish(config.TOPIC_ENV, {"event": "fall", "ts": time.time()})
    time.sleep(60)
    hw.reset_emergency()


def emotion_publish_loop(mqtt_client):
    global global_expression
    while True:
        # Publish current emotion with no fall
        payload = {"fall_detected": "0", "emotions": global_expression}
        mqtt_client.publish(config.TOPIC_CAM, payload)
        print(f"[EMOTION] Published: {payload}")
        time.sleep(10)  # Publish every 10 seconds


def env_loop(mqtt_client):
    global global_temperature, global_humidity, global_smoke_status

    while True:
        env = hw.read_env()
        env['timestamp'] = time.time()
        mqtt_client.publish(config.TOPIC_ENV, env)
        print(f"[ENV] Published: {env}")
        time.sleep(config.ENV_INTERVAL)

        # Update globals for web
        global_temperature = str(env.get('temp', 'N/A'))
        global_humidity = str(env.get('humidity', 'N/A'))
        smoke = env.get('smoke', 0)
        global_smoke_status = "SMOKE_DETECTED" if smoke == 1 else "SMOKE_OK"


# --------------------------------------------------
# MAIN VIDEO STREAM LOOP
# --------------------------------------------------
def generate_frames():
    global global_expression

    with mp_face_mesh.FaceMesh(max_num_faces=1,
                               refine_landmarks=True,
                               min_detection_confidence=0.5,
                               min_tracking_confidence=0.5) as face:

        while True:
            frame_raw = picam2.capture_array()

            # Convert BGRA → BGR
            if frame_raw.shape[2] == 4:
                frame = cv2.cvtColor(frame_raw, cv2.COLOR_BGRA2BGR)
            else:
                frame = frame_raw.copy()

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # FaceMesh → Expression
            face_result = face.process(rgb)
            expression = "No Face"
            if face_result.multi_face_landmarks:
                lm = face_result.multi_face_landmarks[0].landmark
                expression = classify_emotion(lm)
            global_expression = expression
            cv2.putText(frame, f"Expr: {expression}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

            ret, buf = cv2.imencode(".jpg", frame)
            if not ret: continue
            yield(b"--frame\r\nContent-Type:image/jpeg\r\n\r\n"+buf.tobytes()+b"\r\n")

# --------------------------------------------------
# FLASK ROUTES
# --------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html",
                           temp=global_temperature,
                           hum=global_humidity)

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/env_status_api")
def env_status_api():
    global global_temperature, global_humidity
    global global_smoke_status, global_critical_alert
    global global_latest_g_force, global_expression

    return jsonify({
        "temperature": global_temperature,
        "humidity": global_humidity,
        "fall_status": "Status: OK",  # Placeholder, updated from vision
        "smoke_status": global_smoke_status,
        "critical_alert": global_critical_alert,
        "g_force_latest": global_latest_g_force,
        "expression": global_expression
    })


if __name__ == '__main__':
    mqtt = MQTTHandler(config, on_message=on_mqtt_message)
    mqtt.connect_and_start()

    # subscribe to relevant topics
    mqtt.subscribe(config.TOPIC_MOTION)
    mqtt.subscribe(config.TOPIC_CAM)

    # start env loop
    env_thread = threading.Thread(target=env_loop, args=(mqtt,), daemon=True)
    env_thread.start()

    # start emotion publish loop
    emotion_thread = threading.Thread(target=emotion_publish_loop, args=(mqtt,), daemon=True)
    emotion_thread.start()

    # start Flask web server
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False), daemon=True)
    flask_thread.start()

    try:
        # keep main alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down gateway')
        picam2.stop()
