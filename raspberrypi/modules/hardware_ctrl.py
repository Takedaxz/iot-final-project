"""Hardware controller with safe fallbacks for non-Pi environments."""
import time
import random

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except Exception:
    ON_PI = False

try:
    import adafruit_dht
    HAVE_DHT = True
except Exception:
    HAVE_DHT = False

try:
    import board
    HAVE_BOARD = True
except Exception:
    HAVE_BOARD = False

try:
    from gpiozero import ADS1115
    HAVE_ADC = True
except Exception:
    HAVE_ADC = False


class HardwareManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self._buzzer_on = False
        # Initialize GPIO if available. Some RPi.GPIO installs raise runtime
        # errors (e.g. when missing peripheral access). Handle gracefully and
        # fall back to mock mode.
        self._gpio_ready = False
        if ON_PI:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.cfg.PIN_BUZZER, GPIO.OUT)
                GPIO.setup(self.cfg.PIN_SERVO, GPIO.OUT)
                self.servo = GPIO.PWM(self.cfg.PIN_SERVO, 50)
                self.servo.start(0)
                self._gpio_ready = True
            except Exception as e:
                # Could be RuntimeError: Cannot determine SOC peripheral base address
                print(f"[HARDWARE] GPIO init failed, falling back to mock mode: {e}")
                self._gpio_ready = False
        else:
            print("[HARDWARE] Running in mock mode (not a Raspberry Pi).")

        # DHT device will be created lazily to avoid runtime errors on non-Pi
        self._dht = None

        # ADC for analog sensors
        self._adc_smoke = None
        if HAVE_ADC and ON_PI:
            try:
                smoke_channel = getattr(self.cfg, 'SMOKE_ADC_CHANNEL', 0)
                self._adc_smoke = ADS1115(channel=smoke_channel)
            except Exception as e:
                print(f"[HARDWARE] ADC init failed, falling back to mock smoke: {e}")
                self._adc_smoke = None
        else:
            print("[HARDWARE] ADS1115 not available, using mock smoke sensor.")

    def _init_dht(self):
        if HAVE_DHT and self._dht is None:
            try:
                pin = getattr(self.cfg, 'PIN_DHT', None)
                # map numeric BCM pin to board.D{n} if needed
                if isinstance(pin, int) and HAVE_BOARD:
                    board_attr = f'D{pin}'
                    pin_obj = getattr(board, board_attr, None)
                else:
                    pin_obj = pin

                self._dht = adafruit_dht.DHT22(pin_obj)
            except Exception:
                self._dht = None

    def trigger_emergency(self):
        """Activate buzzer and open the door (servo)."""
        print("[ACTUATOR] Emergency: buzzer ON, opening door (servo -> 90°)")
        self._buzzer_on = True
        if self._gpio_ready:
            try:
                GPIO.output(self.cfg.PIN_BUZZER, GPIO.HIGH)
                # Move servo to ~90 degrees (approx duty cycle 7.5)
                self.servo.ChangeDutyCycle(7.5)
                time.sleep(1)
                self.servo.ChangeDutyCycle(0)
            except Exception as e:
                print(f"[HARDWARE] trigger_emergency GPIO error: {e}")
        else:
            # mock action
            pass

    def reset_emergency(self):
        """Reset buzzer and close the door."""
        print("[ACTUATOR] Reset: buzzer OFF, closing door (servo -> 0°)")
        self._buzzer_on = False
        if self._gpio_ready:
            try:
                GPIO.output(self.cfg.PIN_BUZZER, GPIO.LOW)
                self.servo.ChangeDutyCycle(2.5)
                time.sleep(1)
                self.servo.ChangeDutyCycle(0)
            except Exception as e:
                print(f"[HARDWARE] reset_emergency GPIO error: {e}")

    def read_env(self):
        """Read environment sensors: DHT and mock smoke. Returns a dict."""
        # DHT
        temp = None
        hum = None
        if HAVE_DHT:
            self._init_dht()
            if self._dht is not None:
                try:
                    temp = self._dht.temperature
                    hum = self._dht.humidity
                except Exception:
                    temp = None
                    hum = None

        # Smoke sensor: read from ADC if available, else mock
        if self._adc_smoke is not None:
            try:
                # MCP3008 returns 0-1, scale to 0-1023 like Arduino ADC
                smoke_level = int(self._adc_smoke.value * 1023)
            except Exception:
                smoke_level = random.randint(0, 200)
        else:
            smoke_level = random.randint(0, 200)

        return {"temp": (round(temp, 1) if temp is not None else "N/A"),
                "humidity": (round(hum, 1) if hum is not None else "N/A"),
                "smoke": smoke_level}
