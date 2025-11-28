# config.py

# MQTT Settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_MOTION = "elder/sensor/motion"
TOPIC_CAM = "elder/sensor/cam"
TOPIC_ENV = "sensor/env"

# GPIO Pins (BCM)
PIN_BUZZER = 21
PIN_SERVO = 22
PIN_DHT = 15
PIN_SMOKE = 17

# Thresholds
G_FORCE_LIMIT = 2.5

# Environment publish interval (seconds)
ENV_INTERVAL = 5
