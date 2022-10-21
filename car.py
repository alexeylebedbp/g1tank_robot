from move_state import MoveState
from lights_state import LightsState
from transport_state import Transport, TransportEventSubscriber
from web_rtc_state import WebrtcState
from credentials import credentials
import asyncio

class Car(TransportEventSubscriber):
    def __init__(self):
        self.lightsState = LightsState()
        self.transport = Transport(
            car=self,
            host=credentials["host"],
            car_id=credentials["car_id"],
            initialTimeout=int(credentials["initial_reconnect_timeout"]),
            maxTimeout=int(credentials["max_reconnect_timeout"])
        )
        self.webrtcState = None
        self.moveState = MoveState()
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.loop.run_until_complete(self.transport.connect())

    def onRed(self):
        asyncio.ensure_future(self.lightsState.red())

    def onMove(self, direction: str):
        asyncio.ensure_future(self.moveState.move(direction))

    async def on_offer_request(self):
        self.webrtcState = WebrtcState(self.transport)
        webrtc_offer = await self.webrtcState.create_offer()
        self.transport.send({
            "action": "webrtc_offer",
            "car_id": credentials["car_id"],
            "sdp": webrtc_offer["sdp"],
            "type": webrtc_offer["type"],
        })

    async def on_answer(self, sdp):
        await self.webrtcState.on_answer(sdp)

    async def on_remote_ice(self):
        pass
    


car = Car()
car.run()