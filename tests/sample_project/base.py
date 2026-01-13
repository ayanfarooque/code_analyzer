class BaseService:
    def __init__(self):
        self.connected = False

    def connect(self):
        print("Connecting...")
        self.connected = True

    def disconnect(self):
        print("Disconnecting...")
        self.connected = False