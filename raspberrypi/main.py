"""Main gateway runner for ElderSafe Gateway.

Usage: `python3 main.py`

This script subscribes to `elder/sensor/motion` and acts on camera verification
and publishes environment data periodically to `sensor/env`.
"""
import time
import json
import threading
import config
from modules.hardware_ctrl import HardwareManager
from modules.vision_ai import VisionSystem
from modules.mqtt_handler import MQTTHandler


hw = HardwareManager(config)
vision = VisionSystem()


def on_mqtt_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = None

    print(f"[MQTT] Received on {topic}: {payload}")

    if topic == config.TOPIC_MOTION and payload:
        try:
            g_val = float(payload.get('g_value', 0))
        except Exception:
            g_val = 0

        if g_val > config.G_FORCE_LIMIT:
            print('[LOGIC] High impact detected -> trigger vision verification')
            ai_result = vision.analyze_scene()
            if ai_result:
                mqtt.publish(config.TOPIC_CAM, ai_result)

    elif topic == config.TOPIC_CAM and payload:
        if str(payload.get('fall_detected')) == '1':
            print('[LOGIC] Confirmed fall -> triggering emergency protocol')
            # run emergency in separate thread so env loop continues
            threading.Thread(target=handle_emergency, args=(mqtt,)).start()


def handle_emergency(mqtt_client):
    hw.trigger_emergency()
    # Publish an immediate env/state message so central system knows
    mqtt_client.publish(config.TOPIC_ENV, {"event": "fall", "ts": time.time()})
    time.sleep(60)
    hw.reset_emergency()


def env_loop(mqtt_client):
    while True:
        env = hw.read_env()
        env['timestamp'] = time.time()
        mqtt_client.publish(config.TOPIC_ENV, env)
        print(f"[ENV] Published: {env}")
        time.sleep(config.ENV_INTERVAL)


if __name__ == '__main__':
    mqtt = MQTTHandler(config, on_message=on_mqtt_message)
    mqtt.connect_and_start()

    # subscribe to relevant topics
    mqtt.subscribe(config.TOPIC_MOTION)
    mqtt.subscribe(config.TOPIC_CAM)

    # start env loop
    try:
        env_thread = threading.Thread(target=env_loop, args=(mqtt,), daemon=True)
        env_thread.start()

        # keep main alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down gateway')
