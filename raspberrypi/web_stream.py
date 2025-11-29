import cv2
from flask import Flask, Response, render_template, jsonify
import mediapipe as mp
import numpy as np
import time
import paho.mqtt.client as mqtt
import json

# --- INITIALIZATION & GLOBAL STATE ---
app = Flask(__name__)

# Camera setup (USB webcam)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
time.sleep(0.5)  # Warm-up time

# MediaPipe setup
mp_pose = mp.solutions.pose
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# GLOBAL STATES
fall_status = "Status: OK"
global_temperature = "N/A"
global_humidity = "N/A"
global_smoke_status = "SMOKE_OK"
global_critical_alert = "ALERT_OK"
global_latest_g_force = 0.0
global_expression = "Neutral"

# --- MQTT SETUP ---
MQTT_BROKER = "localhost"
PORT = 1883
ENV_TOPIC = "elder/gateway/env"
CAM_TOPIC = "elder/gateway/cam"
MOTION_TOPIC = "elder/sensor/motion"

def on_connect(client, userdata, flags, rc):
    print("MQTT Connected:", rc)
    client.subscribe([
        (ENV_TOPIC, 0),
        (CAM_TOPIC, 0),
        (MOTION_TOPIC, 0)
    ])

def on_message(client, userdata, msg):
    global global_temperature, global_humidity, global_smoke_status
    global global_critical_alert, global_latest_g_force, global_expression

    try:
        data = json.loads(msg.payload.decode())

        if msg.topic == ENV_TOPIC:
            global_temperature = str(data.get('temp', 'N/A'))
            global_humidity = str(data.get('humidity', 'N/A'))
            smoke = data.get('smoke', 0)
            global_smoke_status = "SMOKE_DETECTED" if smoke == 1 else "SMOKE_OK"

        elif msg.topic == CAM_TOPIC:
            fall = data.get('fall_detected', '0')
            global_critical_alert = "FALL DETECTED" if fall == '1' else "ALERT_OK"
            global_expression = data.get('emotions', 'Neutral')

        elif msg.topic == MOTION_TOPIC:
            global_latest_g_force = data.get("g_force", 0.0)
    except Exception as e:
        print("MQTT processing error:", e)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, PORT, 60)
mqtt_client.loop_start()

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

# --------------------------------------------------
# FALL DETECTION
# --------------------------------------------------
def fall_classifier(r, w, h):
    if not r.pose_landmarks:
        return "Status: NO POSE"

    ar = w / h
    if ar > 1.3:
        return "!!! FALL DETECTED !!!"

    return "Status: OK"

# --------------------------------------------------
# MAIN VIDEO STREAM LOOP
# --------------------------------------------------
def generate_frames():
    global fall_status, global_expression

    with mp_pose.Pose(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose, \
         mp_face_mesh.FaceMesh(max_num_faces=1,
                               refine_landmarks=True,
                               min_detection_confidence=0.5,
                               min_tracking_confidence=0.5) as face:

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Pose
            pose_result = pose.process(rgb)
            if pose_result.pose_landmarks:
                xs = [lm.x * w for lm in pose_result.pose_landmarks.landmark]
                ys = [lm.y * h for lm in pose_result.pose_landmarks.landmark]
                x1, y1 = int(min(xs)), int(min(ys))
                x2, y2 = int(max(xs)), int(max(ys))
                fall_status = fall_classifier(pose_result, x2-x1, y2-y1)
                color = (0,255,0) if "OK" in fall_status else (0,0,255)
                cv2.rectangle(frame,(x1,y1),(x2,y2),color,3)
                cv2.putText(frame, fall_status,(x1,y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,0.7,color,2)

            # FaceMesh → Expression
            face_result = face.process(rgb)
            expression = "No Face"
            if face_result.multi_face_landmarks:
                lm = face_result.multi_face_landmarks[0].landmark
                expression = classify_emotion(lm)
            global_expression = expression
            cv2.putText(frame,f"Expr: {expression}",(10,30),
                        cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2)

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
    global global_temperature, global_humidity, fall_status
    global global_smoke_status, global_critical_alert
    global global_latest_g_force, global_expression

    return jsonify({
        "temperature": global_temperature,
        "humidity": global_humidity,
        "fall_status": fall_status,
        "smoke_status": global_smoke_status,
        "critical_alert": global_critical_alert,
        "g_force_latest": global_latest_g_force,
        "expression": global_expression
    })

# --------------------------------------------------
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        mqtt_client.loop_stop()
        cap.release()