"""Client TCP exécutant des instructions sur le robot."""

import contextlib
import select
import socket
import threading
from collections.abc import Callable, Iterable
from types import TracebackType
from typing import Self

from robot_core.instructions import Instruction, Move, Sleep
from robot_core.protocol import STOP_FRAME, encode_move
from robot_core.settings import Settings

# Écart entre deux envois successifs d'une même commande (répétitions au début).
REPEAT_GAP = 0.05


class RobotClient:
    """Connexion au robot, à utiliser comme gestionnaire de contexte.

    Une commande est envoyée `repeat` fois au début, puis rien pendant sa durée.
    Le robot s'arrête à la fin de la durée grâce à une trame d'arrêt. Le récepteur
    coupe la connexion après 3 s sans donnée : une commande de plus de 3 s ne peut donc
    pas être arrêtée à temps par ce client (voir CLAUDE.md).

    À la sortie du contexte (y compris sur erreur ou Ctrl-C), une trame d'arrêt est
    envoyée. Positionner `cancel` interrompt l'exécution en cours.
    """

    def __init__(
        self, settings: Settings, cancel: threading.Event | None = None
    ) -> None:
        self._settings = settings
        self._cancel = cancel if cancel is not None else threading.Event()
        self._socket: socket.socket | None = None

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        """Vrai si une connexion est ouverte (sans vérifier qu'elle est encore vivante)."""
        return self._socket is not None

    def open(self) -> None:
        """Ouvre la connexion ; sans effet si elle est déjà ouverte."""
        if self._socket is not None:
            return
        self._socket = socket.create_connection(
            (self._settings.host, self._settings.port),
            timeout=self._settings.timeout,
        )

    def close(self) -> None:
        """Envoie une trame d'arrêt puis ferme la connexion ; sans effet si elle est fermée."""
        if self._socket is None:
            return
        with contextlib.suppress(OSError):
            self._socket.sendall(STOP_FRAME)
        self._socket.close()
        self._socket = None

    def is_alive(self) -> bool:
        """Vrai si la connexion est ouverte et que le récepteur ne l'a pas fermée.

        Le récepteur ferme la connexion après 3 s d'inactivité : le socket devient alors
        lisible avec une fin de flux (`recv` renvoie b""), ce qu'on détecte ici sans envoyer de donnée.
        """
        if self._socket is None:
            return False
        readable, _, _ = select.select([self._socket], [], [], 0)
        if not readable:
            return True
        try:
            return self._socket.recv(1, socket.MSG_PEEK) != b""
        except OSError:
            return False

    def run(
        self,
        instructions: Iterable[Instruction],
        on_step: Callable[[int], None] | None = None,
    ) -> None:
        """Exécute les instructions une à une ; `on_step` reçoit le rang (à partir de 1)."""
        for step, instruction in enumerate(instructions, start=1):
            if self._cancel.is_set():
                return
            if on_step is not None:
                on_step(step)
            self._execute(instruction)

    def _execute(self, instruction: Instruction) -> None:
        match instruction:
            case Move(axis=axis, intensity=intensity, duration=duration, repeat=repeat):
                self._send_burst(encode_move(axis, intensity), repeat)
                self._cancel.wait(duration)
                # Arrêt explicite à la fin de la durée : sans lui, le robot garde la dernière trame.
                self._send_burst(STOP_FRAME, repeat)
            case Sleep(duration=duration):
                self._send_burst(STOP_FRAME, 1)
                self._cancel.wait(duration)

    def _send_burst(self, frame: bytes, count: int) -> None:
        """Envoie `frame` `count` fois, espacées de `REPEAT_GAP`."""
        if self._socket is None:
            raise RuntimeError("client non connecté : utiliser `with RobotClient(...)`")
        for index in range(count):
            if index:
                self._cancel.wait(REPEAT_GAP)
            self._socket.sendall(frame)
