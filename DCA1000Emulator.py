import json
import socket

from PacketFormatError import PacketFormatError

class DCA1000Emulator:

    HW_CONFIG_FILE = "BoardSettings.json"
    EEPROM_CONFIG_FILE = "EEPROM.json"
    COMMAND_REQ_MAX_SIZE = 512

    # FPGA hardcoded data
    FPGA_IP = "192.168.33.180"
    SYSTEM_IP = "192.168.33.30"
    CONFIG_PORT = 4096

    # Packet format constants
    PACKET_HEADER = 0xA55A
    PACKET_FOOTER = 0xEEAA

    # Packet command codes
    CODE_RESET_RADAR = 0x0002
    CODE_FPGA_VERSION = 0x000E

    # FPGA version constants
    FPGA_VERSION_MAJOR = 2
    FPGA_VERSION_MINOR = 9

    def __init__(self):
        # Create UDP sockets
        self.config_rx_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
        self.config_rx_socket.setblocking(False)
        self.config_tx_socket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)

    def run(self):
        try:
            self.boot()
            # Bind sockets
            self.config_rx_socket.bind(self.dca_address)
            print(f"UDP socket bound to {self.dca_address[0]}:"
                                      f"{self.dca_address[1]}.")

            while True:
                try:
                    self.receive_packet()
                    self.check_header()
                    self.check_footer()
                    self.process()
                    self.send_response()
                except PacketFormatError as e:
                    print(e)
                    self.buffer = bytes()
                    self.command_code = 0
                    self.status = bytes()
        except KeyboardInterrupt:
            print("Program interrupted by user.")
            self.config_rx_socket.close()
            self.config_tx_socket.close()
            print(f"Closed UDP sockets.")

    def boot(self):
        print("Starting DCA1000.")
        with open(self.HW_CONFIG_FILE, "r") as file:
            json_board_config = json.load(file)
        if json_board_config["switch2"]["SW2.5"] == "CONFIG_VIA_HW":
            if json_board_config["switch2"]["SW2.6"] == "GND":
                print("Using default ethernet configuration.")
                dca_ip = self.FPGA_IP
                cli_ip = self.SYSTEM_IP
                config_port = self.CONFIG_PORT
            else:
                print("Using EEPROM ethernet configuration.")
                with open(self.EEPROM_CONFIG_FILE, "r") as file:
                    json_eeprom_config = json.load(file)
                dca_ip = json_eeprom_config["FPGAIP"]
                cli_ip = json_eeprom_config["SystemIP"]
                config_port = json_eeprom_config["ConfigPort"]
            self.dca_address = (dca_ip, config_port)
            self.cli_address = (cli_ip, config_port)
        else:
            # TODO: add ethernet config update functionality
            raise NotImplementedError()

    def receive_packet(self):
        while True:
            try:
                (self.buffer, client_address) = \
                    self.config_rx_socket.recvfrom(self.COMMAND_REQ_MAX_SIZE)
            except BlockingIOError:
                pass
            else:
                print(f"Received packet from {client_address}.")
                break

    def check_header(self):
        if self.read_bytes(2) != self.PACKET_HEADER:
            raise PacketFormatError("packet header")

    def process(self):
        self.command_code = self.read_bytes(2)
        match self.command_code:
            case self.CODE_RESET_RADAR:
                print("Processing reset radar EVM command")
                self.reset_radar_EVM()
            case self.CODE_FPGA_VERSION:
                print("Processing read FPGA version command")
                self.read_fpga_version()
            case _:
                raise PacketFormatError("command code")

    def reset_radar_EVM(self):
        _ = self.read_bytes(2)  # Ignore data size field
        self.status = 0  # Success

    def read_fpga_version(self):
        _ = self.read_bytes(2)  # Ignore data size field
        minor_field = f'{self.FPGA_VERSION_MINOR:07b}'
        major_field = f'{self.FPGA_VERSION_MAJOR:07b}'
        rec_play_field = f'0'  # Record bit
        self.status = int(f'0{rec_play_field}{minor_field}{major_field}', 2)

    def check_footer(self):
        if int.from_bytes(self.buffer[-2:], 'little') != self.PACKET_FOOTER:
            raise PacketFormatError("packet footer")
        self.buffer = self.buffer[:-2]

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