import aiohttp
import asyncio
import enum
import json
from enum import Enum, unique
from credentials import *


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
        print("Websocket Reconnect attempt. Count: ", self.reconnectCount, "Timeout:", self.current)
        if self.current < self.max:
            self.current *= 2

    def reset(self):
        self.current = self.initial
        self.reconnectCount = 0


class TransportEventSubscriber:
    def __init__(self):
        pass

    def on_poor_network_signal(self):
        pass

    def on_move(self, direction: str):
        pass

    async def on_ws_close(self):
        pass

    async def on_offer_request(self):
        pass

    async def on_answer(self, sdp: str):
        pass

    async def on_remote_ice(self):
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
            print("Websocket Connecting: ", self.host)
            self.ws = await self.connector.ws_connect(self.host)
            self.state = TransportState.CONNECTED
            await self._on_connect()
            await self.reconnect()
        except Exception as e:
            print(e.__class__.__name__, str(e))
            await self.car.on_ws_close()
            await asyncio.sleep(self.timeout.current)
            await self.reconnect()

    def send(self, message):
        asyncio.ensure_future(self.ws.send_str(json.dumps(message)))

    async def close(self):
        self.timeout.current = None
        await self.ws.close()
        self.state = TransportState.DISCONNECTED

    @staticmethod
    def parse_message(message: str):
        parsed = json.loads(message)
        action = parsed.get(ACTION)
        if not action:
            print("Websocket Parse err: invalid message format")
            return None
        else:
            return parsed

    async def _on_message(self):
        async for msg in self.ws:
            print(msg)
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close cmd':
                    print("Websocket closed")
                    await self.close()
                    break
                else:
                    print(msg.data)
                    if msg.data == PING:
                        asyncio.ensure_future(self.ws.send_str(PONG))
                    elif msg.data == POOR_NETWORK_DETECTED:
                        self.car.on_poor_network_signal()
                    else:
                        parsed = self.parse_message(msg.data)
                        if parsed.get(ACTION) == MOVE:
                            self.car.on_move(parsed.get(DIRECTION))
                        elif parsed.get(ACTION) == WEBRTC_ANSWER:
                            await self.car.on_answer(parsed.get(SDP))
                        elif parsed.get(ACTION) == OFFER_REQUEST:
                            await self.car.on_offer_request()
                    
            elif msg.type == aiohttp.WSMsgType.ERROR or msg.tp == aiohttp.WSMsgType.CLOSED:
                self.state = TransportState.ERROR
                await self.car.on_ws_close()
                break

    async def _on_connect(self):
        auth_message = {ACTION: AUTH_SESSION, CAR_ID: self.car_id}
        asyncio.ensure_future(self.ws.send_str(json.dumps(auth_message)))
        self.timeout.reset()
        await self._on_message()
