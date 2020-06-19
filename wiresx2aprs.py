import argparse
import configparser
import datetime
import logging
import re
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

        self._datetime_timezone = pytz.utc

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
        self._aprs.start()
        self._aprs.login()

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

        tz_name = self._config.get("Wires-X", "Timezone")
        self._datetime_timezone = pytz.timezone(tz_name)

        _logger.info("Wires-X log file path: %s" % self._config.get("Wires-X", "LogFilePath"))

    def _job(self):
        _logger.info("Reading Wires-X log file")

        records = self._parse_wiresx_log()

        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        now = now_utc.astimezone(self._datetime_timezone)
        margin = datetime.timedelta(minutes=5)

        for record in records:
            if record["latitude"] and record["longitude"]:
                _logger.info("Evaluating time for %s" % record["callsign"])

                if record["datetime"] + margin < now:
                    _logger.info("Too old record for %s" % record["callsign"])
                    continue

                self._send_record_to_aprs(record)

        _logger.debug("Closing file")

    def _parse_wiresx_log(self):
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

        fd.close()

        return records

    def _parse_wiresx_line(self, rawline):
        line = rawline
        if isinstance(line, bytes):
            line = line.decode()

        line = line.strip()
        items = line.split("%")

        position = items[6].strip()
        latitude, longitude, latitude_aprs, longitude_aprs = self._parse_position(position)

        record_datetime = datetime.datetime.strptime(
            items[3].strip(),
            "%Y/%m/%d %H:%M:%S"
        ).replace(tzinfo=self._datetime_timezone)

        values = {
            "callsign": items[0].strip().upper(),
            "serial": items[1].strip(),
            "description": items[2].strip(),
            "datetime": record_datetime,
            "source": items[4].strip(),
            "data": items[5].strip(),
            "latitude": latitude,
            "longitude": longitude,
            "latitude_aprs": latitude_aprs,
            "longitude_aprs": longitude_aprs,
            "extra1": items[7].strip(),
            "extra2": items[8].strip(),
            "extra3": items[9].strip(),
            "extra4": items[10].strip(),
            "extra5": items[11].strip()
        }

        return values

    def _parse_position(self, position=""):
        latitude = 0
        longitude = 0
        latitude_aprs = ""
        longitude_aprs = ""

        if "'" in position and "\"" in position and "/" in position:
            items = position.split("/")

            raw_latitude = items[0].strip()
            raw_longitude = items[1].strip()

            latitude, latitude_aprs = self._parse_position_item(raw_latitude)
            longitude, longitude_aprs = self._parse_position_item(raw_longitude)

        return latitude, longitude, latitude_aprs, longitude_aprs

    def _parse_position_item(self, raw_item):
        args = raw_item.split(":")

        arg_sign = args[0]
        arg_value = args[1]

        elems = arg_value.split(" ")

        degrees = elems[0]
        minutes = elems[1].replace("'", "")
        seconds = elems[2].replace("\"", "")
        sign = arg_sign.upper()

        value = int(degrees)
        value += float(int(minutes) / 60.0)
        value += float(int(seconds) / 60.0) / 60

        if sign in ["S", "W"]:
            value *= -1

        value_aprs = "%02d%02d.%02d%s" % (int(degrees), int(minutes), int(seconds), sign)

        return value, value_aprs

    def _send_record_to_aprs(self, record):
        _logger.info("Sending record to APRS for %s" % record["callsign"])

        callsign_items = re.split(r"[^a-zA-Z0-9]", record["callsign"])
        callsign = callsign_items[0]

        data = "%s-MP>APRS,TCPIP*:!%s/%s} %s" % (
            callsign,
            record["latitude_aprs"],
            record["longitude_aprs"],
            self._config.get("APRS-IS", "Comment"),
        )

        self._aprs.send(data)
