# AGENT.md - ElderSafe AI Project Technical Documentation

## Project Analysis Summary

This document provides a concise, up-to-date technical overview of the ElderSafe AI project intended for maintainers and agents. The project is an IoT elder safety system with two main components: an ESP32-based smart cane and a Raspberry Pi gateway with vision and local logging.

## Architecture Overview

### System Components
1. **Smart Cane (ESP32)**: Mobile sensor node that detects motion and sound and publishes to MQTT (`elder/sensor/motion`).
2. **Home Gateway (Raspberry Pi)**: Central processing unit that handles vision processing, hardware control, MQTT forwarding, and time-series logging.
3. **MQTT Broker**: Message routing between devices and cloud forwarding topics.
4. **InfluxDB**: Local time-series database used by the gateway; the code writes `motion`, `camera` and `environment` points.

### Communication Flow
- ESP32 → MQTT Broker → Raspberry Pi (motion data)
- Raspberry Pi → MQTT Broker → Cloud topic (forwarded motion) and other consumers
- Raspberry Pi ↔ Hardware (GPIO control for actuators)
- Raspberry Pi → InfluxDB (local time-series writes)

## Codebase Analysis

### ESP32 Firmware (`src/main.cpp`)
**Purpose**: Reads MPU6050 accelerometer and microphone, calculates G-force, and publishes MQTT messages.

**Key Functions**:
- `setup()`: Initializes WiFi, MQTT, MPU6050 sensor.
- `loop()`: Continuously reads sensors and publishes data (interval configured on device).
- `reconnect()`: Handles MQTT reconnection.

**Notes**:
- Publishes raw sensor data without advanced filtering on the device.
- No battery management or aggressive sleep implemented yet.

### Raspberry Pi Gateway (`raspberrypi/`)

#### Main Application (`main.py`)
**Purpose**: Orchestrates MQTT communication, vision processing for live stream (emotion labels), emergency responses, environment reads, and DB writes.

**Key Logic (current)**:
- Subscribes to `elder/sensor/motion` and `elder/gateway/cam` topics.
- On high G-force (> `config.G_FORCE_LIMIT`) the gateway now triggers the emergency protocol immediately. Vision verification has been removed — emergency is threshold-driven.
- Emergency protocol activates hardware (buzzer, servo) and sets an RGB LED visual alert; it also publishes an immediate environment/state message to `elder/gateway/env` so central systems are notified.
- Periodic environment publishing and DB writes run in background threads.

**Threads**:
- Main thread: Flask app and MQTT initialization.
- Env thread: Periodic sensor publishing and InfluxDB writes.
- Emotion thread: Periodic emotion publish and InfluxDB writes.
- Emergency handling runs in its own short-lived thread when triggered.

#### Configuration (`config.py`)
**Key settings**:
- MQTT broker: `localhost:1883` (configurable)
- GPIO pins: buzzer, servo, DHT, smoke, RGB pins available in `config.py`
- Thresholds: `G_FORCE_LIMIT` controls emergency trigger (default 2)
- ENV publishing interval: `ENV_INTERVAL` (default 5s)
- InfluxDB database name: `INFLUXDB_BUCKET` (default `eldersafe`)

#### Modules

##### `hardware_ctrl.py` - Hardware Manager
**Features (current)**:
- GPIO control for buzzer and servo (via `gpiozero`).
- DHT11 temperature/humidity reading with a retry loop (3 attempts) to mitigate DHT timing "full buffer" errors.
- Smoke sensor reading (digital/ADC fallback).
- RGB LED control (via `gpiozero.RGBLED`) for visual emergency indication.
- Mock/fallback behavior when running off-target (development machines without GPIO).

**Safety**:
- Exception handling on hardware init and sensor reads.
- Reset methods to turn actuators off after emergency.

##### `mqtt_handler.py` - MQTT Handler
**Features**:
- Thin wrapper around `paho-mqtt` to publish JSON payloads and handle subscriptions.

##### `vision_ai.py` - Vision System
**Features (current)**:
- MediaPipe/OpenCV face-landmark analysis runs in the live stream to produce heuristic `expression` labels.

**Limitations**:
- The system no longer relies on vision to confirm falls — emergency is threshold-driven. Vision still runs for emotion/overlay in the stream and periodic publishes.
- Emotion detection is heuristic and not an ML model; consider TFLite/DeepFace replacements for production.

## Data & Storage

- The gateway writes time-series points to a local InfluxDB instance (default DB `eldersafe`). Measurements written include `environment`, `motion`, `camera`, and `cloud_motion`.
- The Flask endpoint `/dashboard_data` queries InfluxDB (last 24h) and returns JSON for the frontend charts.
- The live UI (`/env_status_api`) returns the most recent global variables updated by `env_loop` and MQTT handlers (fast polling endpoint used by `index.html`).
- Motion events are also forwarded to a cloud topic (`elder/cloud/motion`) via MQTT so cloud consumers receive raw motion data.

## Frontend

- Static frontend files live under `frontend/` (not Flask templates in `templates/`): `index.html`, `dashboard.html`, `styles.css`, and `config.js`.
- `config.js` exposes `BASE_URL` so the frontend can work with tunnels (Cloudflare / cloudflared) or local endpoints.
- Dashboard charts use Chart.js (category X-axis with formatted labels) and a client-side SMA implementation for trends to avoid date-adapter version mismatches.
- The live feed endpoint is `/video_feed` (multipart MJPEG stream used by `index.html`).

## Networking & CORS

- Flask config includes explicit CORS origins to allow frontend access (e.g., the tunnel URL, `localhost`).
- MQTT forwarding continues to publish to `TOPIC_CLOUD_MOTION` for cloud integrations.

## Current System Status (Updated 2025-12-01)

### Implemented Features ✅
- ✅ ESP32 sensor reading and MQTT publishing (`elder/sensor/motion`).
- ✅ MQTT forwarding of raw motion to a cloud topic (`elder/cloud/motion`).
- ✅ Immediate emergency trigger on high G-force (vision verification removed).
- ✅ Hardware control for buzzer, servo, and RGB LED for visual alerts.
- ✅ DHT11 robustness via retry logic and smoke detection.
- ✅ Local InfluxDB writes for `environment`, `motion`, `camera` and `cloud_motion`.
- ✅ Flask web server that serves a live camera stream and frontend static pages; `/env_status_api` and `/dashboard_data` endpoints for the UI.

### Known Issues / Next Steps
- Confirm InfluxDB persistence and retention policies in deployment.
- Replace heuristic emotion detection with a small ML model or TFLite for better accuracy.
- Physically validate actuator wiring (buzzer, servo, RGB) and ensure correct PWM-capable GPIO pins are used.
- Improve error handling around InfluxDB queries and empty datasets returned to the frontend.

## Development Roadmap (short)
1. Verify InfluxDB and dashboard queries; add unit tests for DB query handling.
2. Improve vision/emotion model and add temporal smoothing.
3. Harden MQTT reconnection and add TLS/LWT for production.

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
└── frontend/                    # Static frontend files: index.html, dashboard.html, config.js, styles.css
```

This documentation should be updated as the project evolves. Focus next on DB verification and improving vision/emotion detection for reliability.
<parameter name="filePath">c:\Users\Patta\OneDrive\Documents\PlatformIO\Projects\IoT-final\AGENT.md