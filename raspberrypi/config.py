# config.py
#source .venv/bin/activate
# MQTT Settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_MOTION = "elder/sensor/motion"
TOPIC_CAM = "elder/gateway/cam"
TOPIC_ENV = "elder/gateway/env"
TOPIC_CLOUD_MOTION = "elder/cloud/motion"

# GPIO Pins (BCM)
PIN_BUZZER = 21
PIN_SERVO = 22
PIN_DHT = 15
PIN_SMOKE = 17

# ADC Settings for analog sensors
SMOKE_ADC_CHANNEL = 0  # ADS1115 channel for smoke sensor (AO pin)

# Thresholds
G_FORCE_LIMIT = 2
MIC_THRESHOLD = 150

# Environment publish interval (seconds)
ENV_INTERVAL = 5

# InfluxDB Settings
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = ""  # For InfluxDB 1.x, no token needed
INFLUXDB_ORG = ""  # Not used in 1.x
INFLUXDB_BUCKET = "eldersafe"  # Database name
