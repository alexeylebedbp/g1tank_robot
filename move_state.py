from ast import parse
import enum
from enum import Enum, unique
import RPi.GPIO as GPIO
import asyncio

@unique
class MoveDirectionStateVal(Enum):
    STAY = 0
    FORWARD = 1
    BACKWARD = -1

@unique
class MoveDirectionStateType(Enum):
    LINEAR = 0
    ROTATE = 1

class MoveDirectionState:
    value: MoveDirectionStateVal
    type: MoveDirectionStateType

    def __init__(self, type: MoveDirectionStateType):
        self.value = MoveDirectionStateVal.STAY
        self.type = type

    def __get__(self, instance, owner_class):
        if instance is None:
            return self
        else:
            return self.value

    def __set__(self, instance, newValue: MoveDirectionStateVal):
        self.value = newValue

@unique
class MoveCommand(Enum):
    FORWARD = 0
    BACKWARD = 1
    LEFT = 2
    RIGHT = 3

class MoveState:

    linear = MoveDirectionState(MoveDirectionStateType.LINEAR)
    rotate = MoveDirectionState(MoveDirectionStateType.ROTATE)

    def __init__(self):
        self.IN1 = 20
        self.IN2 = 21
        self.IN3 = 19
        self.IN4 = 26
        self.ENA = 16
        self.ENB = 13
        self.pwm_ENA = None
        self.pwm_ENB = None
        GPIO.setwarnings(False)
   

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
        self.motor_init()
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        #PWM duty cycle is set to 100（0--100）
        self.pwm_ENA.start(50)
        self.pwm_ENB.start(50)
        await asyncio.sleep(2)
        self.pwm_ENA.stop()
        self.pwm_ENB.stop()
        GPIO.cleanup()


    def parse_command(self, cmd: str):
        print("cmd 46", cmd)
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
        print("FIRING MOTOR!!!!!!", self.linear == MoveDirectionStateVal.FORWARD)
        if self.linear == MoveDirectionStateVal.FORWARD:
            asyncio.ensure_future(self.motor_forward())

    async def _on_forward(self):
        print("MoveCommand.FORWARD")
        if self.linear == MoveDirectionStateVal.BACKWARD:
            self.linear = MoveDirectionStateVal.STAY
        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.FORWARD
        self.rotate = MoveDirectionStateVal.STAY
        asyncio.ensure_future(self._on_state_change())


    async def _on_backward(self):
        print("MoveCommand.BACKWARD")
        if self.linear == MoveDirectionStateVal.FORWARD:
            self.linear = MoveDirectionStateVal.STAY
        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.BACKWARD
        self.rotate = MoveDirectionStateVal.STAY

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