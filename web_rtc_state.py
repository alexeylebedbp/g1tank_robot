class WebRTCState:
    def __init__(self, remoteSDP: str):
        self.remoteSDP:str = remoteSDP
        self.peerConnection = None
        self.localSDP: str
