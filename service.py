import abc
import threading
import time


class Service(abc.ABC):

    def __init__(self, timewait: float = 5.0):
        self._thread = None
        self._keep_running = False
        self._timewait = timewait

    def start(self):
        self._keep_running = True
        self._thread = threading.Thread(target=self._loop)
        self._thread.start()

    def stop(self):
        self._keep_running = False

    def join(self):
        self._thread.join()

    def _loop(self):
        while self._keep_running:
            self._job()

            if self._timewait > 0:
                time.sleep(self._timewait)

    def _job(self):
        raise NotImplementedError
