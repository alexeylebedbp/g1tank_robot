import aiohttp
import asyncio
import enum
import json
from enum import Enum, unique


@unique
class TransportState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = -1


class ReconnectTimeout:
    def __init__(self, initialTimeout: int, maxTimeout: int):
        self.initial = initialTimeout
        self.max = maxTimeout
        self.current = self.initial
        self.reconnectCount = 0

    def next(self):
        self.reconnectCount += 1
        print("Reconnect attempt. Count: ", self.reconnectCount, "Timeout:", self.current)
        if self.current < self.max:
            self.current *= 2

    def reset(self):
        self.current = self.initial
        self.reconnectCount = 0


class TransportEventSubscriber:
    def __init__(self):
        pass

    def onRed(self):
        pass

    def onMove(self):
        pass

class Transport:
    def __init__(self, car: TransportEventSubscriber, host, car_id, initialTimeout: int, maxTimeout: int):
        self.ws = None
        self.host = host
        self.car_id = car_id
        self.state: TransportState = TransportState.DISCONNECTED
        self.timeout = ReconnectTimeout(initialTimeout, maxTimeout)
        self.connector = None
        self.car = car

    async def reconnect(self):
        if self.timeout.current is not None:
            self.timeout.next()
            await self.connect()

    async def connect(self):
        try:
            self.state: TransportState = TransportState.CONNECTING
            self.connector = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout.current))
            print("Connecting: ", self.host)
            self.ws = await self.connector.ws_connect(self.host)
            self.state = TransportState.CONNECTED
            await self._on_connect()
            await self.reconnect()
        except Exception as e:
            print(e.__class__.__name__, str(e))
            await asyncio.sleep(self.timeout.current)
            await self.reconnect()

    def close(self):
        self.timeout.current = None
        self.ws.close()
        self.state = TransportState.DISCONNECTED

    def parse_message(self, message: str):
        parsed = json.loads(message)
        action = parsed.get("action")
        if not action:
            print("Parse err: invalid message format")
            return None
        else:
            return parsed
        

    async def _on_message(self):
        async for msg in self.ws:
            print(msg)
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close cmd':
                    print("WS is closed")
                    await self.ws.close()
                    break
                else:
                    if msg.data == "__ping__":
                        asyncio.ensure_future(self.ws.send_str("__pong__"))
                    elif msg.data == "red":
                        self.car.onRed()
                    else:
                        parsed = self.parse_message(msg.data)
                        if parsed["action"] == "move":
                            self.car.onMove(parsed.get("direction"))
                    
            elif msg.type == aiohttp.WSMsgType.ERROR or msg.tp == aiohttp.WSMsgType.CLOSED:
                self.state = TransportState.ERROR
                break

    async def _on_connect(self):
        message = {
            "action": "auth_session", 
            "car_id": self.car_id
        }
        asyncio.ensure_future(self.ws.send_str(json.dumps(message)))
        self.timeout.reset()
        await self._on_message()
