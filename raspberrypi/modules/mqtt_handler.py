"""Simple MQTT helper for publishing and subscribing."""
import json
import paho.mqtt.client as mqtt


class MQTTHandler:
    def __init__(self, cfg, on_message=None):
        self.cfg = cfg
        self.client = mqtt.Client()
        if on_message:
            self.client.on_message = on_message
        self.client.on_connect = self._on_connect

    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected with result code {rc}")

    def connect_and_start(self):
        self.client.connect(self.cfg.MQTT_BROKER, self.cfg.MQTT_PORT, 60)
        self.client.loop_start()

    def publish(self, topic, payload, qos=0, retain=False):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic):
        self.client.subscribe(topic)
