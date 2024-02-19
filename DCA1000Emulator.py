import json
import socket

class DCA1000Emulator:

    CONFIG_FILE = "ConfigFile.json"
    COMMAND_REQ_MAX_SIZE = 512

    # Packet format constants
    PACKET_HEADER = 0xA55A
    PACKET_FOOTER = 0xEEAA

    # Packet command codes
    CODE_FPGA_VERSION = 0x000E

    # FPGA version constants
    FPGA_VERSION_MAJOR = 2
    FPGA_VERSION_MINOR = 9

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
                self.check_header()
                self.process()
                self.check_footer()
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

    def check_header(self):
        if self.read_bytes(2) != self.PACKET_HEADER:
            print("Incorrect packet header, packet dropped.")
            self.buffer = bytes()

    def process(self):
        command_code = self.read_bytes(2)
        match command_code:
            case self.CODE_FPGA_VERSION:
                print("Processing read FPGA version command")
                _ = self.read_fpga_version()  # Ignore response data for now
            case _:
                print("Incorrect command code, packet dropped.")
                self.buffer = bytes()

    def read_fpga_version(self):
        _ = self.read_bytes(2)  # Ignore data size field
        minor_field = f'{self.FPGA_VERSION_MINOR:07b}'
        major_field = f'{self.FPGA_VERSION_MAJOR:07b}'
        return int(f'00{minor_field}{major_field}', 2).to_bytes(2, 'little')

    def check_footer(self):
        if self.read_bytes(2) != self.PACKET_FOOTER:
            print("Incorrect packet footer, packet dropped.")
            # TODO: throw exception

    def read_bytes(self, num_bytes):
        value = int.from_bytes(self.buffer[:num_bytes], 'little')
        self.buffer = self.buffer[num_bytes:]
        return value