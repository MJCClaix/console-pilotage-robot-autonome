import socket
import threading

from robot_console.client import RobotClient
from robot_console.instructions import Axis, Move, Sleep
from robot_console.protocol import STOP_FRAME, encode_move
from robot_console.settings import Settings


def _receive_all(server: socket.socket, received: bytearray) -> None:
    connection, _ = server.accept()
    with connection:
        while chunk := connection.recv(1024):
            received.extend(chunk)


def test_client_sends_frames_then_stop_frame() -> None:
    received = bytearray()
    with socket.create_server(("127.0.0.1", 0)) as server:
        port = server.getsockname()[1]
        thread = threading.Thread(target=_receive_all, args=(server, received))
        thread.start()
        settings = Settings(host="127.0.0.1", port=port)
        with RobotClient(settings, sleep=lambda _: None) as client:
            client.run(
                [Move(axis=Axis.FORWARD, intensity=100, duration=0.01), Sleep(duration=0.01)]
            )
        thread.join(timeout=2)

    frames = [bytes(received[i : i + 12]) for i in range(0, len(received), 12)]
    assert frames[0] == encode_move(Axis.FORWARD, 100)
    assert frames[-1] == STOP_FRAME
