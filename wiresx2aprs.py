import argparse
import configparser
import datetime
import logging
from abc import ABC

import pytz

from aprsclient import APRSClient
from service import Service

_logger = logging.getLogger(__name__)


class WiresX2APRS(Service, ABC):

    def __init__(self, argv):
        super().__init__()

        self._argv = argv
        self._config = configparser.ConfigParser()

        self._aprs = APRSClient()

    def start(self):
        _logger.info("Starting Wires-X to APRS")

        self._parse_argv()

        address = self._config.get("APRS-IS", "Address")
        port = int(self._config.get("APRS-IS", "Port"))
        callsign = self._config.get("APRS-IS", "Callsign")
        password = self._config.get("APRS-IS", "Password")
        packet_filter = self._config.get("APRS-IS", "Filter")

        self._aprs.config(address, port, callsign, password, packet_filter)
        # self._aprs.start()
        # self._aprs.login()

        super().start()

    def stop(self):
        _logger.info("Stop Wires-X to APRS")

        self._aprs.stop()
        super().stop()

    def _parse_argv(self):
        _logger.info("Parsing arguments on command line")

        parser = argparse.ArgumentParser()

        parser.add_argument("-c", "--config",
                            default="config.ini",
                            type=str,
                            help="Config file")

        parsed_args = parser.parse_args(self._argv[1:])
        args = vars(parsed_args)

        config_file_path = args["config"]

        _logger.debug("Reading and aprsing config file: %s", config_file_path)
        self._config.read(config_file_path)

        _logger.info("Wires-X log file path: %s" % self._config.get("Wires-X", "LogFilePath"))

    def _job(self):
        _logger.info("Reading Wires-X log file")

        wiresx_logfile_path = self._config.get("Wires-X", "LogFilePath")

        _logger.debug("Opening file")
        fd = open(wiresx_logfile_path, "r")

        records = []

        for rawline in fd.readlines():
            _logger.debug("Parsing line: %s" % rawline.strip())
            record = self._parse_wiresx_line(rawline)

            _logger.debug("Adding record: %s" % record)
            records.append(record)

        _logger.debug("Sorting records by datetime")
        records.sort(key=lambda x: x["datetime"], reverse=True)
        print(records)

        _logger.debug("Closing file")
        fd.close()

    def _parse_wiresx_line(self, rawline):
        line = rawline
        if isinstance(line, bytes):
            line = line.decode()

        line = line.strip()
        items = line.split("%")

        position = items[6].strip()
        latitude, longitude = self._parse_position(position)

        values = {
            "callsign": items[0].strip().upper(),
            "serial": items[1].strip(),
            "description": items[2].strip(),
            "datetime": datetime.datetime.strptime(items[3].strip(), "%Y/%m/%d %H:%M:%S").replace(tzinfo=pytz.utc),
            "source": items[4].strip(),
            "data": items[5].strip(),
            "latitude": latitude,
            "longitude": longitude,
            "extra1": items[7].strip(),
            "extra2": items[8].strip(),
            "extra3": items[9].strip(),
            "extra4": items[10].strip(),
            "extra5": items[11].strip()
        }

        return values

    def _parse_position(self, position=""):
        # N:39 17' 59" / E:009 12' 28"

        latitude = 0
        longitude = 0

        if "'" in position and "\"" in position and "/" in position:
            items = position.split("/")

            raw_latitude = items[0].strip()
            raw_longitude = items[1].strip()

            latitude = self._parse_position_item(raw_latitude)
            longitude = self._parse_position_item(raw_longitude)

        return latitude, longitude

    def _parse_position_item(self, raw_item):
        args = raw_item.split(":")

        arg_sign = args[0]
        arg_value = args[1]

        elems = arg_value.split(" ")
        value = int(elems[0])
        value += float(60 / int(elems[1].replace("'", "")))
        value += float(60 / int(elems[2].replace("\"", ""))) / 60

        if arg_sign.upper() in ["S", "W"]:
            value *= -1

        return value
