# AGENT.md - ElderSafe AI Project Technical Documentation

## Project Analysis Summary

This document provides a comprehensive technical overview of the ElderSafe AI project for AI agents to understand, maintain, and extend the codebase. The project is an IoT elder safety system with two main components: an ESP32-based smart cane and a Raspberry Pi gateway with AI vision capabilities.

## Architecture Overview

### System Components
1. **Smart Cane (ESP32)**: Mobile sensor node that detects motion and sound, publishes to MQTT.
2. **Home Gateway (Raspberry Pi)**: Central processing unit that handles AI vision, hardware control, and data logging.
3. **MQTT Broker**: Message routing between devices.
4. **InfluxDB**: Time-series database for sensor data storage (planned but not fully implemented).

### Communication Flow
- ESP32 → MQTT Broker → Raspberry Pi (motion data)
- Raspberry Pi → MQTT Broker → Central Server (processed data, env data, forwarded motion)
- Raspberry Pi ↔ Hardware (GPIO control for actuators)

## Codebase Analysis

### ESP32 Firmware (`src/main.cpp`)
**Purpose**: Reads MPU6050 accelerometer and microphone, calculates G-force, publishes MQTT messages.

**Key Functions**:
- `setup()`: Initializes WiFi, MQTT, MPU6050 sensor.
- `loop()`: Continuously reads sensors, publishes data every 1 second.
- `reconnect()`: Handles MQTT reconnection.

**Libraries Used**:
- `Adafruit_MPU6050`: Accelerometer/gyroscope sensor.
- `PubSubClient`: MQTT client.
- `ArduinoJson`: JSON serialization.

**Current Implementation Notes**:
- Publishes raw sensor data without filtering.
- No battery management or sleep modes.
- Hardcoded WiFi credentials and MQTT broker IP.

### Raspberry Pi Gateway (`raspberrypi/`)

#### Main Application (`main.py`)
**Purpose**: Orchestrates MQTT communication, vision processing, and emergency responses.

**Key Logic**:
- Subscribes to `elder/sensor/motion` and `elder/sensor/cam`.
- On high G-force (>2), triggers vision analysis.
- On confirmed fall, activates emergency protocol (buzzer + servo).
- Runs environmental monitoring loop in background.

**Threads**:
- Main thread: MQTT handling.
- Env thread: Periodic sensor publishing.
- Emergency thread: Hardware activation with timeout.

#### Configuration (`config.py`)
**Settings**:
- MQTT broker: localhost:1883
- GPIO pins: Buzzer(21), Servo(22), DHT(27), Smoke(17)
- Thresholds: G_FORCE_LIMIT = 2
- Intervals: ENV_INTERVAL = 5 seconds
- Topics: motion="elder/sensor/motion", cam="elder/gateway/cam", env="elder/gateway/env", cloud_motion="elder/cloud/motion"

#### Modules

##### `hardware_ctrl.py` - Hardware Manager
**Features**:
- GPIO control for buzzer and servo.
- DHT11 temperature/humidity sensor reading.
- Smoke sensor (digital): 1 if detected, 0 otherwise.
- Graceful fallback to mock mode when not on Raspberry Pi.

**Safety Features**:
- Exception handling for GPIO failures.
- Lazy initialization of DHT sensor.

##### `mqtt_handler.py` - MQTT Handler
**Features**:
- Simple wrapper around paho-mqtt.
- JSON serialization for dict payloads.
- Connection management.

##### `vision_ai.py` - Vision System
**Features**:
- OpenCV-based face detection using Haar cascades.
- Heuristic fall detection based on face bounding box aspect ratio.
- Mock emotion detection (random selection).
- Fallback to random results when OpenCV unavailable.

**Current Limitations**:
- Basic heuristics, not real AI/ML models.
- No emotion detection model implemented.
- Single frame analysis, no temporal tracking.

## Dependencies & Requirements

### ESP32 (`platformio.ini`)
- espressif32 platform
- Arduino framework
- Libraries: MPU6050, PubSubClient, ArduinoJson

### Raspberry Pi (`requirements.txt`)
- paho-mqtt: MQTT communication
- opencv-python: Computer vision
- influxdb-client: Database (not used yet)
- adafruit-circuitpython-dht: Temperature sensor
- RPi.GPIO, gpiozero: Hardware control

## Current System Status (Updated 2025-11-29)

### Implemented Features ✅
- ✅ ESP32 sensor reading and MQTT publishing (`elder/sensor/motion`)
- ✅ Raspberry Pi MQTT subscription, processing, and forwarding (`elder/cloud/motion`)
- ✅ Vision AI heuristics for fall detection (basic face detection)
- ✅ Hardware control: DHT11 temp/humidity, digital smoke sensor
- ✅ Environmental monitoring and publishing (`elder/gateway/env`)
- ✅ Emergency protocol (buzzer/servo actuators, commented for testing)
- ✅ **Web streaming with live Pi Camera feed and emotion detection** (dashboard at http://<pi-ip>:5000)
- ✅ MQTT-based pub/sub architecture for real-time communication

### Current Architecture
- **ESP32 (Edge)**: Publishes motion/sound data to `elder/sensor/motion`
- **Raspberry Pi (Gateway)**:
  - Subscribes to `elder/sensor/motion`, forwards to `elder/cloud/motion`
  - Processes high G-force events, triggers vision analysis
  - Publishes vision results to `elder/gateway/cam`
  - Publishes env data to `elder/gateway/env` every 5 seconds
  - **Runs web stream at http://<pi-ip>:5000** with live camera, MediaPipe AI, and dashboard
- **Topics**:
  - `elder/sensor/motion`: Raw motion from ESP32
  - `elder/cloud/motion`: Forwarded motion for cloud
  - `elder/gateway/cam`: Vision/fall detection results
  - `elder/gateway/env`: Temp, humidity, smoke data
- **Hardware**: DHT11 (GPIO 15), MQ smoke DO (GPIO 17), actuators ready

### Known Issues
- Actuators (buzzer/servo) commented out for testing
- Vision uses basic heuristics, not robust AI
- No data persistence or cloud integration yet
- GPIO errors possible on some Pi setups

## Development Roadmap

### Immediate Next Steps (Priority 1-3)
1. **InfluxDB Integration**:
   - Set up InfluxDB Docker container
   - Configure MQTT subscription to `elder/cloud/#` topics
   - Store motion, env, and vision data as time-series

2. **Grafana Dashboard**:
   - Connect Grafana to InfluxDB
   - Create dashboard for real-time monitoring (temp, smoke, motion charts)
   - Add alerts for smoke detection and high G-force

3. **Enhanced Vision AI**:
   - Replace mock emotion detection with DeepFace or TensorFlow Lite
   - Implement pose estimation for better fall detection
   - Add temporal tracking for motion analysis

### Medium-Term Improvements (Priority 4-6)
4. **Security & Reliability**:
   - Add MQTT TLS encryption
   - Implement LWT for device monitoring
   - Add reconnection logic with exponential backoff

5. **Actuator Integration**:
   - Uncomment and test buzzer/servo GPIO code
   - Add timeout and reset logic for emergency responses

6. **Testing & CI/CD**:
   - Unit tests for modules (hardware, vision, MQTT)
   - Integration tests for end-to-end MQTT flow
   - GitHub Actions for automated testing

### Long-Term Enhancements (Priority 7+)
7. **ESP32 Optimizations**:
   - Battery management and sleep modes
   - Over-the-air updates

8. **Cloud Deployment**:
   - Docker containerization for Pi services
   - Cloud MQTT broker (e.g., AWS IoT, HiveMQ)
   - REST API for external integrations

9. **Advanced Features**:
   - Multi-camera support
   - Machine learning model training on collected data
   - Mobile app for caregiver notifications

### Deployment Considerations
- Docker for InfluxDB/Grafana on Pi or separate server
- Environment-specific configs (dev/prod)
- Automated setup scripts for new deployments

## File Structure Reference

```
IoT-final/
├── platformio.ini              # ESP32 build config
├── src/
│   └── main.cpp                # ESP32 firmware
├── raspberrypi/
│   ├── main.py                 # Gateway main app
│   ├── config.py               # Configuration
│   ├── requirements.txt        # Python deps
│   └── modules/
│       ├── __init__.py
│       ├── hardware_ctrl.py    # GPIO/hardware control
│       ├── mqtt_handler.py     # MQTT wrapper
│       └── vision_ai.py        # Computer vision
└── test/                       # Testing (empty)
```

This documentation should be updated as the project evolves. Focus on completing the AI models and database integration for a functional prototype.</content>
<parameter name="filePath">c:\Users\Patta\OneDrive\Documents\PlatformIO\Projects\IoT-final\AGENT.md