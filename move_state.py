from ast import parse
import enum
from enum import Enum, unique
from weakref import WeakKeyDictionary
import RPi.GPIO as GPIO
import asyncio

@unique
class MoveDirectionStateVal(Enum):
    STAY = 0
    FORWARD = 1
    BACKWARD = -1

class MoveDirectionState:
    def __init__(self):
        self.dict_values = WeakKeyDictionary()

    def __get__(self, instance, owner_class):
        if instance is None:
            return self
        else:
            return self.dict_values.get(instance)

    def __set__(self, instance, newValue: MoveDirectionStateVal):
        self.dict_values[instance] = newValue

@unique
class MoveCommand(Enum):
    FORWARD = 0
    BACKWARD = 1
    LEFT = 2
    RIGHT = 3

class MoveState:

    linear = MoveDirectionState()
    rotate = MoveDirectionState()

    def __init__(self):
        self.motor_forward_timeouts = []
        self.motor_backward_timeouts = []
        self.motor_frequency = 0.5
        self.motor_is_queued = False
        self.motor_is_busy = False
        self.IN1 = 20
        self.IN2 = 21
        self.IN3 = 19
        self.IN4 = 26
        self.ENA = 16
        self.ENB = 13
        self.pwm_ENA = None
        self.pwm_ENB = None
        self.linear = MoveDirectionStateVal.STAY
        self.rotate = MoveDirectionStateVal.STAY
        GPIO.setwarnings(False)
    
    def state_to_default(self):
        self.linear = MoveDirectionStateVal.STAY
        self.rotate = MoveDirectionStateVal.STAY

    def motor_init(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ENA,GPIO.OUT,initial=GPIO.HIGH)
        GPIO.setup(self.IN1,GPIO.OUT,initial=GPIO.LOW)
        GPIO.setup(self.IN2,GPIO.OUT,initial=GPIO.LOW)
        GPIO.setup(self.ENB,GPIO.OUT,initial=GPIO.HIGH)
        GPIO.setup(self.IN3,GPIO.OUT,initial=GPIO.LOW)
        GPIO.setup(self.IN4,GPIO.OUT,initial=GPIO.LOW)
        self.pwm_ENA = GPIO.PWM(self.ENA, 2000)
        self.pwm_ENB = GPIO.PWM(self.ENB, 2000)

    async def motor_forward(self):
        print("Motor forward!")
        self.motor_is_busy = True
        self.motor_forward_timeouts.append(1)
        self.motor_init()
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwm_ENA.start(50)
        self.pwm_ENB.start(50)
        while len(self.motor_forward_timeouts) != 0:
            self.motor_forward_timeouts.pop()
            await asyncio.sleep(self.motor_frequency)
        self.pwm_ENA.stop()
        self.pwm_ENB.stop()
        GPIO.cleanup()
        self.motor_is_busy = False
        if self.motor_is_queued:
            self.motor_is_queued = False
            asyncio.ensure_future(self._on_state_change())
        self.state_to_default()

    async def motor_backward(self):
        print("Motor backward!")
        self.motor_is_busy = True
        self.motor_backward_timeouts.append(1)
        self.motor_init()
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        self.pwm_ENA.start(50)
        self.pwm_ENB.start(50)
        while len(self.motor_backward_timeouts) != 0:
            self.motor_backward_timeouts.pop()
            await asyncio.sleep(self.motor_frequency)
        self.pwm_ENA.stop()
        self.pwm_ENB.stop()
        GPIO.cleanup()
        self.motor_is_busy = False
        if self.motor_is_queued:
            self.motor_is_queued = False
            asyncio.ensure_future(self._on_state_change())
        self.state_to_default()

    def parse_command(self, cmd: str):
        if cmd == "forward":
            return MoveCommand.FORWARD
        elif cmd == "backward":
            return MoveCommand.BACKWARD
        elif cmd == "left":
            return MoveCommand.LEFT
        elif cmd == "right":
            return MoveCommand.RIGHT
        else:
            return None

    async def move(self, command: str):
        command = self.parse_command(command)
        if command == MoveCommand.FORWARD:
            asyncio.ensure_future(self._on_forward())
        elif command == MoveCommand.BACKWARD:
            asyncio.ensure_future(self._on_backward())
        elif command == MoveCommand.LEFT:
            asyncio.ensure_future(self._on_left())
        elif command == MoveCommand.RIGHT:
            asyncio.ensure_future(self._on_right())
        else:
            print("Incorrect move command")

    async def _on_state_change(self):
        if self.linear == MoveDirectionStateVal.FORWARD and self.rotate == MoveDirectionStateVal.STAY:
            asyncio.ensure_future(self.motor_forward())
        elif self.linear == MoveDirectionStateVal.BACKWARD and self.rotate == MoveDirectionStateVal.STAY:
            asyncio.ensure_future(self.motor_backward())

    async def _on_forward(self):
        print("MoveCommand.FORWARD")
        if self.rotate == MoveDirectionStateVal.STAY and self.linear == MoveDirectionStateVal.FORWARD:
            if len(self.motor_forward_timeouts) == 0:
                self.motor_forward_timeouts.append(1)
            return
        if self.linear == MoveDirectionStateVal.BACKWARD:
            self.linear = MoveDirectionStateVal.STAY
        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.FORWARD
        self.rotate = MoveDirectionStateVal.STAY

        if not self.motor_is_busy:
            asyncio.ensure_future(self._on_state_change())
        else:
            self.motor_is_queued = True

    async def _on_backward(self):
        print("MoveCommand.BACKWARD")
        if self.rotate == MoveDirectionStateVal.STAY and self.linear == MoveDirectionStateVal.BACKWARD:
            if len(self.motor_backward_timeouts) == 0:
                self.motor_backward_timeouts.append(1)
            return
        if self.linear == MoveDirectionStateVal.FORWARD:
            self.linear = MoveDirectionStateVal.STAY
        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.BACKWARD
        self.rotate = MoveDirectionStateVal.STAY

        if not self.motor_is_busy:
            asyncio.ensure_future(self._on_state_change())
        else:
            self.motor_is_queued = True

    async def _on_left(self):
        print("MoveCommand.LEFT")
        if self.rotate == MoveDirectionStateVal.STAY:
            self.rotate = MoveDirectionStateVal.BACKWARD

        if self.rotate == MoveDirectionStateVal.FORWARD:
            self.rotate = MoveDirectionStateVal.STAY

    async def _on_right(self):
        print("MoveCommand.RIGHT")
        if self.rotate == MoveDirectionStateVal.STAY:
            self.rotate = MoveDirectionStateVal.FORWARD

        if self.rotate == MoveDirectionStateVal.BACKWARD:
            self.rotate = MoveDirectionStateVal.STAY