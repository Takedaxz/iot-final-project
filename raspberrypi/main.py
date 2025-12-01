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
from flask_cors import CORS
import cv2
from picamera2 import Picamera2
import mediapipe as mp
import numpy as np
import time

# InfluxDB imports
from influxdb import InfluxDBClient

# Flask app
app = Flask(__name__, template_folder='../frontend')
CORS(app, origins=["https://iot-final-project-wine.vercel.app", "http://localhost:5000"])

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

# Initialize InfluxDB client
influx_client = InfluxDBClient(host='localhost', port=8086, database=config.INFLUXDB_BUCKET)

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

        # Write cloud motion to InfluxDB
        json_body = [
            {
                "measurement": "cloud_motion",
                "tags": {
                    "sensor": "esp32"
                },
                "fields": {
                    "g_force": g_val,
                    "mic": mic_val
                },
                "time": int(time.time() * 1e9)
            }
        ]
        influx_client.write_points(json_body)

        global_latest_g_force = g_val

        # Write motion to InfluxDB
        json_body = [
            {
                "measurement": "motion",
                "tags": {
                    "sensor": "esp32"
                },
                "fields": {
                    "g_force": g_val,
                    "mic": mic_val
                },
                "time": int(time.time() * 1e9)
            }
        ]
        influx_client.write_points(json_body)

        if g_val > config.G_FORCE_LIMIT:
            print('[LOGIC] High impact -> triggering emergency protocol')
            # run emergency in separate thread so env loop continues
            threading.Thread(target=handle_emergency, args=(mqtt,)).start()
            global_critical_alert = "FALL DETECTED"

            # Write fall to InfluxDB
            json_body = [
                {
                    "measurement": "camera",
                    "tags": {
                        "sensor": "picam"
                    },
                    "fields": {
                        "fall_detected": 1,
                        "emotion": global_expression
                    },
                    "time": int(time.time() * 1e9)
                }
            ]
            influx_client.write_points(json_body)
        else:
            global_critical_alert = "ALERT_OK"

    elif topic == config.TOPIC_CAM and payload:
        if str(payload.get('fall_detected')) == '1':
            print('[LOGIC] Confirmed fall -> triggering emergency protocol')
            # run emergency in separate thread so env loop continues
            threading.Thread(target=handle_emergency, args=(mqtt,)).start()

        # Write received cam data to InfluxDB
        json_body = [
            {
                "measurement": "camera",
                "tags": {
                    "sensor": "picam"
                },
                "fields": {
                    "fall_detected": int(payload.get('fall_detected', 0)),
                    "emotion": payload.get('emotions', 'Unknown')
                },
                "time": int(time.time() * 1e9)
            }
        ]
        influx_client.write_points(json_body)


def handle_emergency(mqtt_client):
    hw.trigger_emergency()
    # Publish an immediate env/state message so central system knows
    mqtt_client.publish(config.TOPIC_ENV, {"event": "fall", "ts": time.time()})
    time.sleep(3)
    hw.reset_emergency()


def emotion_publish_loop(mqtt_client):
    global global_expression
    while True:
        # Publish current emotion with no fall
        payload = {"fall_detected": "0", "emotions": global_expression}
        mqtt_client.publish(config.TOPIC_CAM, payload)
        print(f"[EMOTION] Published: {payload}")

        # Write to InfluxDB
        json_body = [
            {
                "measurement": "camera",
                "tags": {
                    "sensor": "picam"
                },
                "fields": {
                    "fall_detected": 0,
                    "emotion": global_expression
                },
                "time": int(time.time() * 1e9)
            }
        ]
        influx_client.write_points(json_body)

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

        # Write to InfluxDB
        fields = {"smoke": smoke}
        if env.get('temp') != "N/A":
            fields["temperature"] = env.get('temp')
        if env.get('humidity') != "N/A":
            fields["humidity"] = env.get('humidity')

        json_body = [
            {
                "measurement": "environment",
                "tags": {
                    "sensor": "dht"
                },
                "fields": fields,
                "time": int(env['timestamp'] * 1e9)
            }
        ]
        influx_client.write_points(json_body)


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
        # "fall_status": "Status: OK",  # Placeholder, updated from vision
        "smoke_status": global_smoke_status,
        "critical_alert": global_critical_alert,
        "g_force_latest": global_latest_g_force,
        "expression": global_expression
    })

@app.route("/dashboard_data")
def dashboard_data():
    # Query InfluxDB for last 24 hours
    temp_result = influx_client.query('SELECT * FROM environment WHERE time > now() - 24h')
    hum_result = influx_client.query('SELECT * FROM environment WHERE time > now() - 24h')
    g_force_result = influx_client.query('SELECT * FROM motion WHERE time > now() - 24h')
    fall_result = influx_client.query('SELECT * FROM camera WHERE time > now() - 24h')
    emotion_result = influx_client.query('SELECT * FROM camera WHERE time > now() - 24h')

    # Process data for JSON
    temp_data = []
    hum_data = []
    g_force_data = []
    fall_data = []
    emotion_data = []

    if temp_result:
        for point in temp_result.get_points():
            temp_data.append({"time": point['time'], "value": point.get('temperature', 0)})

    if hum_result:
        for point in hum_result.get_points():
            hum_data.append({"time": point['time'], "value": point.get('humidity', 0)})

    if g_force_result:
        for point in g_force_result.get_points():
            g_force_data.append({"time": point['time'], "value": point.get('g_force', 0)})

    if fall_result:
        for point in fall_result.get_points():
            fall_data.append({"time": point['time'], "value": point.get('fall_detected', 0)})

    # Map string emotions to numeric codes so frontend charting is consistent
    emotion_map = {
        'Neutral': 0,
        'Happy': 1,
        'Sad': 2,
        'Surprised': 3,
        'No Face': -1
    }
    if emotion_result:
        for point in emotion_result.get_points():
            raw = point.get('emotion', 'Unknown')
            # Influx may return bytes/str; ensure str
            try:
                raw_str = str(raw)
            except Exception:
                raw_str = 'Unknown'
            mapped = emotion_map.get(raw_str, -1)
            emotion_data.append({"time": point['time'], "value": mapped})

    return jsonify({
        "temp_data": temp_data,
        "hum_data": hum_data,
        "g_force_data": g_force_data,
        "fall_data": fall_data,
        "emotion_data": emotion_data
    })

@app.route("/dashboard")
def dashboard():
    # Query InfluxDB for last 24 hours
    temp_result = influx_client.query('SELECT * FROM environment WHERE time > now() - 24h')
    hum_result = influx_client.query('SELECT * FROM environment WHERE time > now() - 24h')
    g_force_result = influx_client.query('SELECT * FROM motion WHERE time > now() - 24h')
    fall_result = influx_client.query('SELECT * FROM camera WHERE time > now() - 24h')

    # Process data for charts
    temp_data = []
    hum_data = []
    g_force_data = []
    fall_data = []

    if temp_result:
        for point in temp_result.get_points():
            temp_data.append({"time": point['time'], "value": point['temperature']})

    if hum_result:
        for point in hum_result.get_points():
            hum_data.append({"time": point['time'], "value": point['humidity']})

    if g_force_result:
        for point in g_force_result.get_points():
            g_force_data.append({"time": point['time'], "value": point['g_force']})

    if fall_result:
        for point in fall_result.get_points():
            fall_data.append({"time": point['time'], "value": point['fall_detected']})

    return render_template("dashboard.html", temp_data=temp_data, hum_data=hum_data, g_force_data=g_force_data, fall_data=fall_data)


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

    # start Flask web server in main thread
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print('Shutting down gateway')
        picam2.stop()
