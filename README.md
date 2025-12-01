# ElderSafe AI: Smart Cane & Ambient Intelligence with Emotion Detection

## Project Overview

ElderSafe AI is a hybrid elder safety monitoring system that integrates a "Smart Cane" (intelligent walking stick) with a "Home Gateway" (Raspberry Pi-based station). The gateway performs real-time monitoring (motion, environment), publishes/forwards MQTT messages, writes time-series data to a local InfluxDB, and serves a lightweight web UI with a live camera stream and historical charts.

## Key Features & Logic

### 1. Smart Cane (Intelligent Walking Stick - Edge Node)
- Acts as a mobile IoT device attached to the elder's walking stick.
- **Logic:**
  - Uses ESP32 to read values from MPU6050 to calculate G-Force (SVM: Sum Vector Magnitude).
  - Reads sound levels from KY-037 Microphone.
  - Sends data to MQTT Topic `elder/sensor/motion` in JSON format `{"g_value":"xx", "mic":"xx"}` for gateway processing.

### 2. Visual Intelligence & Verification (Vision System and Event Confirmation)
- Camera on Raspberry Pi operates in multitasking mode:
  - **Parallel Task 1 (Emotion):** Real-time facial analysis (heuristic) to produce an `expression` label used for monitoring and DB writes.
  - **Note:** The system previously used vision to confirm falls; it now triggers emergency immediately on a high G-force threshold. Vision remains active for emotion labeling and display but is no longer required for emergency gating.
-- **Decision:** Vision publishes periodic camera/emotion entries to the `elder/gateway/cam` topic.

### 3. Emergency Response (Automatic Response System)
- Gateway subscribes to motion topics and reacts immediately to high G-force readings.
- **Logic (current):** When `g_force` in the motion payload exceeds `config.G_FORCE_LIMIT`, the gateway:
  - Activates the buzzer.
  - Moves the servo (e.g., unlock action) and then resets it after the configured timeout.
  - Sets the RGB LED to a visible alert color (red) during the emergency.
  - Publishes a short env/state message to `elder/gateway/env` so upstream consumers are alerted.

### 4. Environmental & Data Logging (Environment Recording)
- Reads temperature/humidity (DHT with retry logic) and smoke (digital/ADC) and publishes environment state to `elder/gateway/env`.
- Gateway writes all primary telemetry to a local InfluxDB instance (`environment`, `motion`, `camera`, `cloud_motion`). The web UI queries InfluxDB via the `/dashboard_data` endpoint.

## Hardware Integration

### Node 1: The Smart Cane
- **Controller:** ESP32 (WiFi Client)
- **Sensors:**
  - **MPU6050:** Detects impact and tilt of the cane.
  - **KY-037 Microphone:** Detects sound levels (e.g., cane hitting ground or shouting).
- **Power:** Li-ion 18650 battery with charging circuit.

### Node 2: The Gateway (Raspberry Pi)
- **Controller:** Raspberry Pi 4/5
- **Sensors & Input:**
  - **Camera Module (Pi Cam / Webcam):** Main input for Computer Vision.
  - **DHT22:** Measures room temperature.
  - **MQ-2 Smoke Sensor:** Detects smoke/fire.
- **Actuators (Output):**
  - **Active Buzzer:** Siren sound.
  - **Servo Motor (MG996R):** Door lock mechanism.
- **Database:** InfluxDB (Running on Docker inside Pi).

## System Logic Flow

**Step 1: Motion Sensing (At ESP32)**
1. ESP32 reads Accel (a_x, a_y, a_z) and Mic Amplitude.
2. Calculates G = √(a_x² + a_y² + a_z²).
3. **Publish** raw data to MQTT Topic: `elder/sensor/motion`
   - *Payload:* `{"g_value": 2.8, "mic": 450}`

**Step 2: Intelligent Processing (At Raspberry Pi)**
1. **Subscribe** to `elder/sensor/motion`.
2. **Condition Check (current):**
  - If `payload.g_force > config.G_FORCE_LIMIT`: immediately trigger emergency protocol (vision confirmation removed).
  - Emotion detection runs in parallel for monitoring and DB writes but not as a gating step.
3. **Publish / Store:**
  - Motion is forwarded to the cloud topic `elder/cloud/motion` and written to InfluxDB.
  - Vision/emotion labels are published periodically to `elder/gateway/cam` and written to InfluxDB.

**Step 3: Action & Logging (At Raspberry Pi)**
1. **Actuation & Notifications:**
  - Emergency actuation (buzzer/servo/RGB) is invoked when a high G-force is detected.
  - A brief env/state message is published to `elder/gateway/env` to notify central systems.
2. **Database Storage:**
  - Motion, environment and camera/emotion data are written to InfluxDB for historical analysis and dashboarding.

## Data Structure and MQTT Topics

| Topic | Publisher | Payload Example | Purpose |
|-------|-----------|-----------------|---------|
| `elder/sensor/motion` | ESP32 (Cane) | `{"g_force": 2.85, "mic": 1024}` | Raw motion published by ESP32; gateway forwards to `elder/cloud/motion` and stores to InfluxDB. |
| `elder/gateway/env` | RPi (Gateway) | `{"temp": 28.5, "humidity": 50, "smoke": 0}` | Environment state published periodically and on-demand (emergency). |
| `elder/gateway/cam` | RPi (AI Vision) | `{"fall_detected": "0", "emotions": "Happy"}` | Periodic camera/emotion publishes and DB writes (vision used for monitoring). |

## Recommended Tech Stack

- **ESP32 Code:** C++ (Arduino IDE) or MicroPython
- **Gateway Logic:** Python (using `paho-mqtt` for data transmission)
- **Computer Vision:**
  - **OpenCV:** Basic image handling
  - **DeepFace** or **TensorFlow Lite:** Emotion Detection and Pose Estimation
- **Database:** InfluxDB (ideal for continuous sensor data)
- **Visualization:** Grafana (pull data from InfluxDB for display)

## Project Structure

- `platformio.ini`: PlatformIO configuration for ESP32 development
- `src/main.cpp`: ESP32 firmware for smart cane
- `raspberrypi/`: Raspberry Pi gateway code
  - `main.py`: Main gateway application
  - `config.py`: Configuration settings
  - `requirements.txt`: Python dependencies
  - `modules/`: Modular components
    - `hardware_ctrl.py`: Hardware control (GPIO, sensors)
    - `mqtt_handler.py`: MQTT communication
    - `vision_ai.py`: Computer vision and AI processing
  - `architecture/elder_safe_gateway.puml`: System architecture diagram

## Setup Instructions

### ESP32 (Smart Cane)
1. Install PlatformIO.
2. Open the project and upload to ESP32-S3-DevKitC-1.
3. Configure WiFi and MQTT broker IP in `src/main.cpp`.

### Raspberry Pi (Gateway)
1. Install Python 3 and required packages: `pip install -r raspberrypi/requirements.txt`
2. Run or install InfluxDB (local) and ensure a database named as in `config.INFLUXDB_BUCKET` exists (default `eldersafe`). Example quick Docker run:

```bash
docker run -d --name influx -p 8086:8086 influxdb:1.8
```

3. Configure MQTT broker and `config.py` (pins, thresholds, `INFLUXDB_BUCKET`).
4. Start the gateway:

```bash
python3 raspberrypi/main.py
```

5. Frontend: serve or open `frontend/index.html` (ensure `frontend/config.js` sets `BASE_URL` to the gateway URL or tunnel URL). The Flask app also serves the frontend templates when running.

## Note
This project is actively under development. Key changes since earlier drafts:
- InfluxDB writes have been implemented and `/dashboard_data` consumes those points.
- Emergency logic was simplified to trigger immediately on G-force; vision is still available for emotion labels and display.
- Hardware code now initializes and controls the RGB LED and improves DHT reliability with retries.

If you want, I can also:
- Add a small health-check route that returns DB connectivity and recent point counts.
- Add a script that bootstraps InfluxDB database + retention policy used by the project.