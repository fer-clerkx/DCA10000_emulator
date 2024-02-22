class PacketFormatError(Exception):
    def __init__(self, message):
        self.message = f"Incorrect {message}, packet dropped."
        super().__init__(self.message)