from move_state import MoveState
from lights_state import LightsState
from transport_state import Transport, TransportEventSubscriber
from web_rtc_state import WebrtcState
from credentials import *
import asyncio
from typing import Union

class Car(TransportEventSubscriber):

    def __init__(self):
        super().__init__()
        self.lightsState = LightsState()
        self.transport = Transport(
            car=self,
            host=CREDENTIALS[HOST],
            car_id=CREDENTIALS[CAR_ID],
            initialTimeout=int(CREDENTIALS[INITIAL_RECONNECT_TIMEOUT]),
            maxTimeout=int(CREDENTIALS[MAX_RECONNECT_TIMEOUT])
        )
        self.webrtcState: Union[WebrtcState, None] = None
        self.moveState = MoveState()
        self.loop = asyncio.get_event_loop()

    def run(self):
        self.loop.run_until_complete(self.transport.connect())

    def on_poor_network_signal(self):
        asyncio.ensure_future(self.lightsState.red())

    def on_move(self, direction: str):
        asyncio.ensure_future(self.moveState.move(direction))

    async def on_offer_request(self):
        self.webrtcState = WebrtcState(self.transport)
        webrtc_offer = await self.webrtcState.create_offer()
        self.transport.send({
            ACTION: WEBRTC_OFFER,
            CAR_ID: CREDENTIALS[CAR_ID],
            SDP: webrtc_offer[SDP],
            "type": webrtc_offer["type"],
        })

    async def on_answer(self, sdp):
        await self.webrtcState.on_answer(sdp)

    async def on_remote_ice(self):
        pass

car = Car()
car.run()
