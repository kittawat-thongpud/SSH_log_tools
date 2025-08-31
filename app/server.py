import threading
import logging
from werkzeug.serving import make_server
from typing import Optional


class ServerThread:
    def __init__(self, app, host: str = "127.0.0.1", port: int = 5000):
        self.app = app
        self.host = host
        self.port = port
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._log = logging.getLogger(__name__)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._log.info("Starting WSGI server on %s:%s", self.host, self.port)
        self._server = make_server(self.host, self.port, self.app)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._log.info("Server thread started")

    def stop(self):
        if self._server:
            try:
                self._log.info("Shutting down server")
                self._server.shutdown()
            finally:
                self._server = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
            self._log.info("Server thread terminated")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
