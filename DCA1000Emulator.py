import json
import socket

class DCA1000Emulator:

    CONFIG_FILE = "ConfigFile.json"
    COMMAND_REQ_MAX_SIZE = 512

    def __init__(self):
        # Parse JSON file
        print(f"Parsing {self.CONFIG_FILE}.")
        with open(self.CONFIG_FILE) as config_file:
            json_config = json.load(config_file)
        self.ip_addr = json_config["DCA1000Config"]\
            ["ethernetConfig"]["DCA1000IPAddress"]
        self.config_port = json_config["DCA1000Config"]\
            ["ethernetConfig"]["DCA1000ConfigPort"]

        # Create UDP sockets
        self.config_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.config_socket.setblocking(False)

    def run(self):
        try:
            # Bind sockets
            self.config_socket.bind((self.ip_addr, self.config_port))
            print(f"UDP socket bound to {self.ip_addr}:{self.config_port}.")

            while True:
                self.receive_packet()
        except KeyboardInterrupt:
            print("Program interrupted by user.")
            self.config_socket.close()
            print(f"Closed UDP socket.")

    def receive_packet(self):
        while True:
            try:
                (self.buffer, client_address) = \
                    self.config_socket.recvfrom(self.COMMAND_REQ_MAX_SIZE)
            except BlockingIOError:
                pass
            else:
                print(f"Received packet from {client_address}.")
                if client_address == (self.ip_addr, self.config_port):
                    break
                else:
                    print("Incorrect client address, packet dropped.")
                    self.buffer = bytes()