import logging
import signal
import sys

from wiresx2aprs import WiresX2APRS

logging.basicConfig(level=logging.DEBUG)

wiresx2aprs = WiresX2APRS(sys.argv)


def signal_handler(signum, frame):
    if signum == signal.SIGINT:
        wiresx2aprs.stop()


if __name__ == "__main__":
    wiresx2aprs.start()
    wiresx2aprs.join()
