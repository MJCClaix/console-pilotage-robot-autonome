import socket
import threading
import time
from collections.abc import Callable, Iterator

import pytest

from robot_web.controller import RobotController
from robot_core.settings import Settings


class FakeRobot:
    """Faux récepteur TCP local qui enregistre tous les octets reçus."""

    def __init__(self) -> None:
        self.received = bytearray()
        self._server = socket.create_server(("127.0.0.1", 0))
        self._server.settimeout(0.1)
        self._stopped = threading.Event()
        self.port: int = self._server.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def settings(self) -> Settings:
        return Settings(host="127.0.0.1", port=self.port)

    def frames(self) -> list[bytes]:
        data = bytes(self.received)
        return [data[i : i + 12] for i in range(0, len(data), 12)]

    def close(self) -> None:
        self._stopped.set()
        self._server.close()

    def _serve(self) -> None:
        while not self._stopped.is_set():
            try:
                connection, _ = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            threading.Thread(target=self._drain, args=(connection,), daemon=True).start()

    def _drain(self, connection: socket.socket) -> None:
        with connection:
            while chunk := connection.recv(1024):
                self.received.extend(chunk)


@pytest.fixture
def robot() -> Iterator[FakeRobot]:
    fake = FakeRobot()
    yield fake
    fake.close()


@pytest.fixture
def controller(robot: FakeRobot) -> RobotController:
    return RobotController(settings_loader=robot.settings)


def wait_until(condition: Callable[[], bool], timeout: float = 3.0) -> bool:
    """Attend qu'une condition devienne vraie ; renvoie son état final."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()
