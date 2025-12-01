"""Hardware controller with safe fallbacks for non-Pi environments."""
import time
import random

try:
    from gpiozero import Buzzer, Servo, Button
    HAVE_GPIOZERO = True
except Exception:
    HAVE_GPIOZERO = False

try:
    import adafruit_ads1x15.ads1115 as ADS
    import busio
    HAVE_ADC = True
except Exception:
    HAVE_ADC = False

try:
    import adafruit_dht
    HAVE_DHT = True
    print("[DEBUG] adafruit_dht imported successfully")
except Exception as e:
    HAVE_DHT = False
    print(f"[DEBUG] adafruit_dht import failed: {e}")

try:
    import board
    HAVE_BOARD = True
except Exception:
    HAVE_BOARD = False


class HardwareManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self._buzzer_on = False
        # Initialize GPIO devices if available
        self._gpio_ready = False
        self.buzzer = None
        self.servo = None
        self.smoke_sensor = None
        if HAVE_GPIOZERO:
            try:
                self.buzzer = Buzzer(self.cfg.PIN_BUZZER)
                self.servo = Servo(self.cfg.PIN_SERVO)
                self.smoke_sensor = Button(self.cfg.PIN_SMOKE, pull_up=True)
                self._gpio_ready = True
            except Exception as e:
                print(f"[HARDWARE] GPIO init failed, falling back to mock mode: {e}")
                self._gpio_ready = False
        else:
            print("[HARDWARE] gpiozero not available, using mock mode.")

        # DHT device will be created lazily to avoid runtime errors on non-Pi
        self._dht = None

        # No ADC needed for digital smoke

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

                # print(f"[DEBUG] Initializing DHT on pin {pin} (board.{board_attr})")
                self._dht = adafruit_dht.DHT11(pin_obj)
                # print("[DEBUG] DHT initialized successfully")
            except Exception as e:
                print(f"[DEBUG] DHT init failed: {e}")
                self._dht = None

    def trigger_emergency(self):
        """Activate buzzer and open the door (servo)."""
        print("[ACTUATOR] Emergency: buzzer ON, opening door (servo -> 90°)")
        self._buzzer_on = True
        if self._gpio_ready:
            try:
                self.buzzer.on()
                self.servo.max()
                time.sleep(1)
                self.servo.detach()
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
                self.buzzer.off()
                self.servo.min()
                time.sleep(1)
                self.servo.detach()
            except Exception as e:
                print(f"[HARDWARE] reset_emergency GPIO error: {e}")

    def read_env(self):
        """Read environment sensors: DHT and smoke via digital input. Returns a dict."""
        # DHT
        temp = None
        hum = None
        if HAVE_DHT:
            self._init_dht()
            if self._dht is not None:
                for attempt in range(3):  # Retry up to 3 times
                    try:
                        temp = self._dht.temperature
                        hum = self._dht.humidity
                        # print(f"[DEBUG] DHT read: temp={temp}, hum={hum}")
                        break  # Success, exit retry loop
                    except Exception as e:
                        print(f"[DEBUG] DHT read failed (attempt {attempt+1}): {e}")
                        time.sleep(2)  # Wait before retry
                else:
                    print("[DEBUG] DHT read failed after 3 attempts")
                    temp = None
                    hum = None

        # Smoke sensor: read from digital input if available, else mock
        if self.smoke_sensor is not None:
            try:
                smoke_level = 1 if self.smoke_sensor.is_pressed else 0  # 1 if smoke detected
            except Exception:
                smoke_level = random.randint(0, 1)
        else:
            smoke_level = random.randint(0, 1)

        return {"temp": (round(temp, 1) if temp is not None else "N/A"),
                "humidity": (round(hum, 1) if hum is not None else "N/A"),
                "smoke": smoke_level}
