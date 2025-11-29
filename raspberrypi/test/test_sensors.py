#!/usr/bin/env python3
"""Simple test script for DHT22 and smoke sensors."""

import time
import random

try:
    import adafruit_dht
    HAVE_DHT = True
    print("[DEBUG] adafruit_dht imported successfully")
except Exception as e:
    HAVE_DHT = False
    print(f"[DEBUG] adafruit_dht import failed: {e}")

try:
    import adafruit_ads1x15.ads1115 as ADS
    import busio
    HAVE_ADC = True
except Exception as e:
    HAVE_ADC = False
    print(f"[DEBUG] ADS1115 import failed: {e}")

try:
    import board
    HAVE_BOARD = True
except Exception:
    HAVE_BOARD = False
    print("[DEBUG] board import failed")

# Configuration
DHT_PIN = 15  # GPIO pin for DHT11
SMOKE_ADC_CHANNEL = 0  # ADS1115 channel for smoke sensor

def test_dht():
    """Test DHT11 sensor."""
    if not HAVE_DHT or not HAVE_BOARD:
        print("DHT test skipped: libraries not available")
        return

    try:
        pin_obj = getattr(board, f'D{DHT_PIN}', None)
        if pin_obj is None:
            print(f"Invalid pin: D{DHT_PIN}")
            return

        dht = adafruit_dht.DHT11(pin_obj)
        print("Testing DHT11...")

        for i in range(5):
            try:
                temp = dht.temperature
                hum = dht.humidity
                print(f"DHT Read {i+1}: Temp={temp:.1f}°C, Humidity={hum:.1f}%")
            except Exception as e:
                print(f"DHT Read {i+1} failed: {e}")
            time.sleep(2)

    except Exception as e:
        print(f"DHT test error: {e}")

def test_smoke():
    """Test smoke sensor via digital input."""
    try:
        import gpiozero
        smoke_sensor = gpiozero.Button(17, pull_up=True)  # GPIO 17
        print("Testing smoke sensor (digital)...")

        for i in range(10):
            try:
                smoke_detected = smoke_sensor.is_pressed
                print(f"Smoke Read {i+1}: Detected={smoke_detected}")
            except Exception as e:
                print(f"Smoke Read {i+1} failed: {e}")
            time.sleep(1)

    except Exception as e:
        print(f"Smoke test error: {e}")

if __name__ == "__main__":
    print("Starting sensor tests...")
    test_dht()
    print()
    test_smoke()
    print("Tests complete.")