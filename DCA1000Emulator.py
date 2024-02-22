import json
import socket

class DCA1000Emulator:

    CONFIG_FILE = "ConfigFile.json"
    COMMAND_REQ_MAX_SIZE = 512
    CLI_IP_ADDR = "169.254.235.8"

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
        ip_addr = json_config["DCA1000Config"]\
            ["ethernetConfig"]["DCA1000IPAddress"]
        config_port = json_config["DCA1000Config"]\
            ["ethernetConfig"]["DCA1000ConfigPort"]

        self.dca_address = (ip_addr, config_port)
        self.cli_address = (self.CLI_IP_ADDR, config_port)

        # Create UDP sockets
        self.config_rx_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
        self.config_rx_socket.setblocking(False)
        self.config_tx_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)

    def run(self):
        try:
            # Bind sockets
            self.config_rx_socket.bind(self.dca_address)
            print(f"UDP socket bound to {self.dca_address[0]}:"
                                      f"{self.dca_address[1]}.")

            while True:
                self.receive_packet()
                self.check_header()
                self.process()
                self.check_footer()
                self.send_response()
        except KeyboardInterrupt:
            print("Program interrupted by user.")
            self.config_rx_socket.close()
            self.config_tx_socket.close()
            print(f"Closed UDP sockets.")

    def receive_packet(self):
        while True:
            try:
                (self.buffer, client_address) = \
                    self.config_rx_socket.recvfrom(self.COMMAND_REQ_MAX_SIZE)
            except BlockingIOError:
                pass
            else:
                print(f"Received packet from {client_address}.")
                if client_address == self.dca_address:
                    break
                else:
                    print("Incorrect client address, packet dropped.")
                    self.buffer = bytes()

    def check_header(self):
        if self.read_bytes(2) != self.PACKET_HEADER:
            print("Incorrect packet header, packet dropped.")
            self.buffer = bytes()

    def process(self):
        self.command_code = self.read_bytes(2)
        match self.command_code:
            case self.CODE_FPGA_VERSION:
                print("Processing read FPGA version command")
                self.read_fpga_version()
            case _:
                print("Incorrect command code, packet dropped.")
                self.buffer = bytes()

    def read_fpga_version(self):
        _ = self.read_bytes(2)  # Ignore data size field
        minor_field = f'{self.FPGA_VERSION_MINOR:07b}'
        major_field = f'{self.FPGA_VERSION_MAJOR:07b}'
        rec_play_field = f'0'  # Record bit
        self.status = int(f'0{rec_play_field}{minor_field}{major_field}', 2)

    def check_footer(self):
        if self.read_bytes(2) != self.PACKET_FOOTER:
            print("Incorrect packet footer, packet dropped.")
            # TODO: throw exception

    def send_response(self):
        packet = (self.PACKET_HEADER.to_bytes(2, 'little')
                  + self.command_code.to_bytes(2, 'little')
                  + self.status.to_bytes(2, 'little')
                  + self.PACKET_FOOTER.to_bytes(2, 'little'))
        print("Sending response packet.")
        self.config_tx_socket.sendto(packet, self.cli_address)

    def read_bytes(self, num_bytes):
        value = int.from_bytes(self.buffer[:num_bytes], 'little')
        self.buffer = self.buffer[num_bytes:]
        return value