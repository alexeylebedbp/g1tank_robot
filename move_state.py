from ast import parse
import enum
from enum import Enum, unique
from weakref import WeakKeyDictionary
import RPi.GPIO as GPIO
import asyncio
from credentials import credentials

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

@unique
class MotorCommand(Enum):
    FORWARD = 0
    BACKWARD = 1
    LEFT = 2
    RIGHT = 3
    SPINLEFT = 4
    SPINRIGHT = 5


class MoveState:

    linear = MoveDirectionState()
    rotate = MoveDirectionState()

    def __init__(self):
        self.motor_frequency = 1/int(credentials["motor_frequency"])
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

        self. motor_gpio_config = {
            MotorCommand.FORWARD:   [GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW],
            MotorCommand.BACKWARD:  [GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH],
            MotorCommand.RIGHT:     [GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.LOW],
            MotorCommand.LEFT:      [GPIO.LOW, GPIO.LOW, GPIO.HIGH, GPIO.LOW],
            MotorCommand.SPINRIGHT: [GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.HIGH],
            MotorCommand.SPINLEFT:  [GPIO.LOW, GPIO.HIGH, GPIO.HIGH, GPIO.LOW],
        }

        self.motor_timeouts = {
            MotorCommand.FORWARD:   [],
            MotorCommand.BACKWARD:  [],
            MotorCommand.LEFT:      [],
            MotorCommand.RIGHT:     [],
            MotorCommand.SPINLEFT:  [],
            MotorCommand.SPINRIGHT: [],
        }
    
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

    async def motor_move(self, motor_command: MotorCommand):
        self.motor_is_busy = True
        self.motor_timeouts[motor_command].append(1)
        self.motor_init()
        GPIO.output(self.IN1, self.motor_gpio_config[motor_command][0])
        GPIO.output(self.IN2, self.motor_gpio_config[motor_command][1])
        GPIO.output(self.IN3, self.motor_gpio_config[motor_command][2])
        GPIO.output(self.IN4, self.motor_gpio_config[motor_command][3])
        self.pwm_ENA.start(50)
        self.pwm_ENB.start(50)
        while len(self.motor_timeouts[motor_command]) != 0:
            self.motor_timeouts[motor_command].pop()
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
            asyncio.ensure_future(self.motor_move(MotorCommand.FORWARD))
        elif self.linear == MoveDirectionStateVal.BACKWARD and self.rotate == MoveDirectionStateVal.STAY:
            asyncio.ensure_future(self.motor_move(MotorCommand.BACKWARD))
        elif self.linear == MoveDirectionStateVal.FORWARD and self.rotate == MoveDirectionStateVal.FORWARD:
            asyncio.ensure_future(self.motor_move(MotorCommand.RIGHT))
        elif self.linear == MoveDirectionStateVal.FORWARD and self.rotate == MoveDirectionStateVal.BACKWARD:
            asyncio.ensure_future(self.motor_move(MotorCommand.LEFT))
        elif self.linear == MoveDirectionStateVal.STAY and self.rotate == MoveDirectionStateVal.FORWARD:
            asyncio.ensure_future(self.motor_move(MotorCommand.SPINRIGHT))
        elif self.linear == MoveDirectionStateVal.STAY and self.rotate == MoveDirectionStateVal.BACKWARD:
            asyncio.ensure_future(self.motor_move(MotorCommand.SPINLEFT))

    async def _handle_state_change(self):
        if not self.motor_is_busy:
            asyncio.ensure_future(self._on_state_change())
        else:
            self.motor_is_queued = True

    async def _on_forward(self):
        if self.rotate == MoveDirectionStateVal.STAY and self.linear == MoveDirectionStateVal.FORWARD:
            if len(self.motor_timeouts[MotorCommand.FORWARD]) == 0:
                self.motor_timeouts[MotorCommand.FORWARD].append(1)
            return

        if self.linear == MoveDirectionStateVal.BACKWARD:
            self.linear = MoveDirectionStateVal.STAY

        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.FORWARD
        self.rotate = MoveDirectionStateVal.STAY

        asyncio.ensure_future(self._handle_state_change())

    async def _on_backward(self):
        if self.rotate == MoveDirectionStateVal.STAY and self.linear == MoveDirectionStateVal.BACKWARD:
            if len(self.motor_timeouts[MotorCommand.BACKWARD]) == 0:
                self.motor_timeouts[MotorCommand.BACKWARD].append(1)
            return

        if self.linear == MoveDirectionStateVal.FORWARD:
            self.linear = MoveDirectionStateVal.STAY

        if self.linear == MoveDirectionStateVal.STAY:
            self.linear = MoveDirectionStateVal.BACKWARD
        self.rotate = MoveDirectionStateVal.STAY

        asyncio.ensure_future(self._handle_state_change())


    async def _on_left(self):
        if self.rotate == MoveDirectionStateVal.BACKWARD and self.linear == MoveDirectionStateVal.STAY:
            if len(self.motor_timeouts[MotorCommand.SPINLEFT]) == 0:
                self.motor_timeouts[MotorCommand.SPINLEFT].append(1)
            return

        if self.rotate == MoveDirectionStateVal.BACKWARD and self.linear == MoveDirectionStateVal.FORWARD:
            if len(self.motor_timeouts[MotorCommand.LEFT]) == 0:
                self.motor_timeouts[MotorCommand.LEFT].append(1)
            return

        if self.rotate == MoveDirectionStateVal.STAY:
            self.rotate = MoveDirectionStateVal.BACKWARD

        if self.rotate == MoveDirectionStateVal.FORWARD:
            self.rotate = MoveDirectionStateVal.STAY

        asyncio.ensure_future(self._handle_state_change())

    async def _on_right(self):
        if self.rotate == MoveDirectionStateVal.FORWARD and self.linear == MoveDirectionStateVal.STAY:
            if len(self.motor_timeouts[MotorCommand.SPINRIGHT]) == 0:
                self.motor_timeouts[MotorCommand.SPINRIGHT].append(1)
            return

        if self.rotate == MoveDirectionStateVal.FORWARD and self.linear == MoveDirectionStateVal.FORWARD:
            if len(self.motor_timeouts[MotorCommand.RIGHT]) == 0:
                self.motor_timeouts[MotorCommand.RIGHT].append(1)
            return

        if self.rotate == MoveDirectionStateVal.STAY:
            self.rotate = MoveDirectionStateVal.FORWARD

        if self.rotate == MoveDirectionStateVal.BACKWARD:
            self.rotate = MoveDirectionStateVal.STAY

        asyncio.ensure_future(self._handle_state_change())