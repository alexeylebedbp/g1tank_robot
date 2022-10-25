import platform
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.rtcrtpsender import RTCRtpSender
from credentials import *

class WebrtcState:
    def __init__(self, transport):
        self.relay = None
        self.cam = None
        self.transport = transport
        self.peer_connection = None

    def create_local_tracks(self):
        options = {"framerate": "24", "video_size": "320x240"}
        if self.relay is None:
            if platform.system() == "Darwin":
                self.cam = MediaPlayer("default", format="avfoundation", options=options)
            elif platform.system() == "Windows":
                self.cam = MediaPlayer("video=Integrated Camera", format="dshow", options=options)
            else:
                self.cam = MediaPlayer("/dev/video0", format="v4l2", options=options)
            self.relay = MediaRelay()
        
        return None, self.relay.subscribe(self.cam.video)

    async def create_offer(self):
        self.peer_connection = RTCPeerConnection()

        @self.peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is %s" % self.peer_connection.connectionState)
            if self.peer_connection.connectionState == "failed":
                await self.peer_connection.close()

        audio, video = self.create_local_tracks()

        if audio:
            self.peer_connection.addTrack(audio)
        if video:
            self.peer_connection.addTrack(video)

        offer = await self.peer_connection.createOffer()
        await self.peer_connection.setLocalDescription(offer)

        return {
            ACTION: WEBRTC_OFFER,
            SDP: self.peer_connection.localDescription.sdp,
            ICE_CANDIDATE_TYPE: self.peer_connection.localDescription.type
        }

    async def on_answer(self, remoteSDP):
        answer = RTCSessionDescription(sdp=remoteSDP, type="answer")
        await self.peer_connection.setRemoteDescription(answer)

    async def close(self):
        await self.peer_connection.close()
        self.relay = None
        if self.cam:
            if self.cam.audio:
                self.cam.audio.stop()
            if self.cam.video:
                self.cam.video.stop()
        self.cam = None
