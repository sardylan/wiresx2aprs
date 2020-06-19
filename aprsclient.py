import logging
import socket
from abc import ABC

from service import Service

_logger = logging.getLogger(__name__)


class APRSClient(Service, ABC):

    def __init__(self):
        super().__init__(0)

        self._address = ""
        self._port = 12345
        self._callsign = ""
        self._password = ""
        self._filter = ""

        self._aprs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        _logger.info("Start APRS connection to server")

        self._aprs_socket.connect((self._address, self._port))

        super().start()

    def stop(self):
        _logger.info("Stop APRS connection to server")

        self._aprs_socket.close()
        super().stop()

    def config(self, address, port, callsign, password, packet_filter):
        self._address = address
        self._port = port
        self._callsign = callsign
        self._password = password
        self._filter = packet_filter

    def send(self, data=""):
        _logger.debug("Sending data to APRS-IS: %s" % data.strip())

        if not data:
            return

        self._aprs_socket.send(data.encode())

    def login(self):
        data = "USER %s PASS %s VERS 1.0 filter %s\r\n" % (
            self._callsign,
            self._password,
            self._filter
        )
        self.send(data)

    def _job(self):
        data = self._aprs_socket.recv(4096)
        msg = data.decode().strip()
        _logger.info("APRS-IS data received: %s" % msg)
