# ElderSafe AI: Smart Cane & Ambient Intelligence with Emotion Detection

## Project Overview

ElderSafe AI is a hybrid elder safety monitoring system that integrates a "Smart Cane" (intelligent walking stick) with a "Home Gateway" (Raspberry Pi-based station). The system uses AI on the edge gateway to perform two key functions simultaneously: 1) Emotion Detection to assess mental health, and 2) Fall Verification when abnormal signals are received from the smart cane, triggering emergency door unlocking and immediate alerts. All data is stored in a time-series database for long-term health analysis.

## Key Features & Logic

### 1. Smart Cane (Intelligent Walking Stick - Edge Node)
- Acts as a mobile IoT device attached to the elder's walking stick.
- **Logic:**
  - Uses ESP32 to read values from MPU6050 to calculate G-Force (SVM: Sum Vector Magnitude).
  - Reads sound levels from KY-037 Microphone.
  - Sends data to MQTT Topic `elder/sensor/motion` in JSON format `{"g_value":"xx", "mic":"xx"}` for gateway processing.

### 2. Visual Intelligence & Verification (Vision System and Event Confirmation)
- Camera on Raspberry Pi operates in multitasking mode:
  - **Parallel Task 1 (Emotion):** Real-time facial analysis of the elder to detect emotions (Happy, Sad, Neutral).
  - **Parallel Task 2 (Fall Verify):** When `g_value > 2.5` is received from the cane, the camera immediately processes posture to confirm if it's a real fall.
- **Decision:** Sends results to Topic `elder/sensor/cam` e.g. `{"fall_detected":"1", "emotions":"happy"}`.

### 3. Emergency Response (Automatic Response System)
- Gateway subscribes to Topic `elder/sensor/cam`.
- **Logic:** If flag `"fall_detected":"1"` is found:
  - **Buzzer:** Activates alert sound.
  - **Servo:** Rotates to unlock emergency door for 1 minute to allow external help.

### 4. Environmental & Data Logging (Environment Recording)
- Reads temperature/humidity (DHT) and smoke (Smoke Sensor), sends to `sensor/env`.
- Collects data from all topics (`motion`, `cam`, `env`) into **InfluxDB**.

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
2. **Condition Check:**
   - If `payload.g_value > 2.5`: Trigger fall verification function from image.
   - Simultaneously, Emotion Detection runs in parallel.
3. **Processing:**
   - AI processes image -> Detects person lying on floor (Confirmed Fall) and pained expression (Pain/Sad).
4. **Publish** results to MQTT Topic: `elder/sensor/cam`
   - *Payload:* `{"fall_detected": "1", "emotions": "sad"}`

**Step 3: Action & Logging (At Raspberry Pi)**
1. **Subscribe** to `elder/sensor/cam` and `sensor/env`.
2. **Action Logic:**
   - Check Payload: If `"fall_detected" == "1"`
   - Command GPIO -> **Buzzer ON**
   - Command GPIO -> **Servo rotate 90 degrees** (unlock door)
   - Set 1-minute timer (60s) -> Command Servo rotate back (relock door or wait for reset).
3. **Database Storage:**
   - Parse JSON data from all topics and insert into **InfluxDB** for daily activity graphs.

## Data Structure and MQTT Topics

| Topic | Publisher | Payload Example | Purpose |
|-------|-----------|-----------------|---------|
| `elder/sensor/motion` | ESP32 (Cane) | `{"g_value": 2.85, "mic": 1024}` | Sends G-force and sound values to trigger camera |
| `sensor/env` | RPi (Gateway) | `{"temp": 28.5, "smoke": 120}` | Room environment data |
| `elder/sensor/cam` | RPi (AI Vision) | `{"fall_detected": "1", "emotions": "happy"}` | AI results (fall or not, which emotion) |

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
2. Set up InfluxDB (via Docker: `docker run -p 8086:8086 influxdb:2.0`)
3. Configure MQTT broker in `raspberrypi/config.py`.
4. Run: `python3 raspberrypi/main.py`

## Note
This project is still under development. Some features like full InfluxDB integration and advanced AI models are not yet implemented.</content>
<parameter name="filePath">c:\Users\Patta\OneDrive\Documents\PlatformIO\Projects\IoT-final\README.md