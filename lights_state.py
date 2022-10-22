import RPi.GPIO as GPIO
import asyncio

class LightsState:
    def __init__(self):
        self.LED_R: int = 22
        self.LED_G: int = 27
        self.LED_B: int = 24


    def _setup(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.LED_R, GPIO.OUT)
        GPIO.setup(self.LED_G, GPIO.OUT)
        GPIO.setup(self.LED_B, GPIO.OUT)

    def _cleanup(self):
        GPIO.cleanup()

    async def red(self):
        self._setup()
        
        try:
            GPIO.output(self.LED_R, GPIO.HIGH)
            GPIO.output(self.LED_G, GPIO.LOW)
            GPIO.output(self.LED_B, GPIO.LOW)
            await asyncio.sleep(10)
            GPIO.output(self.LED_R, GPIO.LOW)
            GPIO.output(self.LED_G, GPIO.LOW)
            GPIO.output(self.LED_B, GPIO.LOW)
        except Exception as e:
            print("Lights Component: " ,str(e))

        self._cleanup()