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
- Raspberry Pi → MQTT Broker → Central Server (processed data)
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
- GPIO pins: Buzzer(21), Servo(22), DHT(15), Smoke(17)
- Thresholds: G_FORCE_LIMIT = 2
- Intervals: ENV_INTERVAL = 5 seconds

#### Modules

##### `hardware_ctrl.py` - Hardware Manager
**Features**:
- GPIO control for buzzer and servo.
- DHT22 temperature/humidity sensor reading.
- Mock smoke sensor (random values).
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

## Current State & Gaps

### Implemented Features
- ✅ ESP32 sensor reading and MQTT publishing
- ✅ Raspberry Pi MQTT subscription and basic logic
- ✅ Hardware control with mock fallbacks
- ✅ Basic vision heuristics
- ✅ Environmental sensor reading

### Missing/Incomplete Features
- ❌ InfluxDB integration (client installed but not used)
- ❌ Real emotion detection model (currently random)
- ❌ Advanced fall detection (pose estimation)
- ❌ Grafana visualization setup
- ❌ TLS/encryption for MQTT
- ❌ LWT (Last Will and Testament) for connection monitoring
- ❌ Battery optimization for ESP32
- ❌ Error handling and logging improvements
- ❌ Configuration management (hardcoded values)
- ❌ Testing framework

### Known Issues
- Vision system uses basic heuristics, not robust AI.
- No data persistence beyond MQTT.
- GPIO errors on some Raspberry Pi setups.
- No reconnection logic for MQTT broker failures.
- Environmental loop runs indefinitely without error recovery.

## Development Recommendations

### Immediate Priorities
1. **Implement Real AI Models**:
   - Replace mock emotion detection with DeepFace or TensorFlow Lite.
   - Add pose estimation for better fall detection.

2. **Database Integration**:
   - Set up InfluxDB Docker container.
   - Implement data insertion from MQTT messages.
   - Add Grafana dashboard configuration.

3. **Robustness Improvements**:
   - Add MQTT reconnection with exponential backoff.
   - Implement proper error logging.
   - Add health checks and monitoring.

4. **Security**:
   - Add MQTT TLS encryption.
   - Secure WiFi credentials (environment variables).
   - Implement authentication.

### Testing Strategy
- Unit tests for individual modules.
- Integration tests for MQTT communication.
- Hardware simulation for GPIO testing.
- Mock sensors for development environment.

### Deployment Considerations
- Docker container for Raspberry Pi services.
- PlatformIO for ESP32 firmware management.
- Environment-specific configurations.
- Automated setup scripts.

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