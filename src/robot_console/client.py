"""Client TCP exécutant des instructions sur le robot."""

import contextlib
import socket
import time
from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Self

from robot_console.instructions import Instruction, Move, Sleep
from robot_console.protocol import STOP_FRAME, encode_move
from robot_console.settings import Settings

# Le récepteur ferme la connexion après 3 s sans données : on renvoie donc
# la trame courante à intervalle régulier pendant toute la durée d'une instruction.
REFRESH_INTERVAL = 0.5


class RobotClient:
    """Connexion au robot, à utiliser comme gestionnaire de contexte.

    À la sortie du contexte (y compris sur erreur ou Ctrl-C), une trame
    d'arrêt est envoyée pour ne jamais laisser le robot en mouvement.
    """

    def __init__(
        self,
        settings: Settings,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._socket: socket.socket | None = None

    def __enter__(self) -> Self:
        self._socket = socket.create_connection(
            (self._settings.host, self._settings.port),
            timeout=self._settings.timeout,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._socket is None:
            return
        with contextlib.suppress(OSError):
            self._socket.sendall(STOP_FRAME)
        self._socket.close()
        self._socket = None

    def run(self, instructions: Iterable[Instruction]) -> None:
        """Exécute les instructions les unes après les autres."""
        for instruction in instructions:
            self._execute(instruction)

    def _execute(self, instruction: Instruction) -> None:
        match instruction:
            case Move(axis=axis, intensity=intensity, duration=duration):
                self._hold(encode_move(axis, intensity), duration)
            case Sleep(duration=duration):
                self._hold(STOP_FRAME, duration)

    def _hold(self, frame: bytes, duration: float) -> None:
        """Maintient une trame envoyée pendant `duration` secondes."""
        if self._socket is None:
            raise RuntimeError("client non connecté : utiliser `with RobotClient(...)`")
        deadline = time.monotonic() + duration
        while (remaining := deadline - time.monotonic()) > 0:
            self._socket.sendall(frame)
            self._sleep(min(REFRESH_INTERVAL, remaining))
