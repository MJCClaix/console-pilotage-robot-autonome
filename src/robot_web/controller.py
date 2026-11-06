"""Exécution asynchrone et interruptible d'instructions (utilisée par l'interface web)."""

import contextlib
import threading
from collections.abc import Callable, Iterator, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from robot_core.client import RobotClient
from robot_core.errors import RobotConsoleError
from robot_core.instructions import Instruction
from robot_core.settings import Settings, load_settings


class BusyError(RobotConsoleError):
    """Une exécution est déjà en cours."""


class RunOutcome(StrEnum):
    """Issue de la dernière exécution terminée."""

    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class RunStatus(BaseModel):
    """Instantané de l'état d'exécution, sérialisable en JSON."""

    model_config = ConfigDict(frozen=True)

    running: bool = False
    label: str = ""
    step: int = 0
    total: int = 0
    run_id: int = 0
    outcome: RunOutcome | None = None
    error: str | None = None


class RobotController:
    """Lance une seule exécution à la fois, dans un thread, et permet de l'interrompre."""

    def __init__(self, settings_loader: Callable[[], Settings] = load_settings) -> None:
        self._load_settings = settings_loader
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._status = RunStatus()

    def run(self, instructions: Sequence[Instruction], label: str = "commande") -> None:
        """Démarre l'exécution ; lève `BusyError` si une autre est en cours."""
        settings = self._load_settings()
        cancel = self._begin(label, len(instructions))
        threading.Thread(
            target=self._worker,
            args=(settings, list(instructions), cancel),
            daemon=True,
        ).start()

    @contextlib.contextmanager
    def exclusive(self, label: str) -> Iterator[threading.Event]:
        """Réserve le robot le temps d'un bloc exécuté par l'appelant (ex. un sous-processus).

        Lève `BusyError` si une exécution est en cours. L'événement fourni est positionné
        par `stop()` : le bloc doit alors s'interrompre de lui-même.
        """
        cancel = self._begin(label, total=0)
        with self._track(cancel):
            yield cancel

    def stop(self) -> bool:
        """Demande l'arrêt ; renvoie `False` s'il n'y avait rien à arrêter."""
        with self._lock:
            if not self._status.running:
                return False
            self._cancel.set()
            return True

    def status(self) -> RunStatus:
        """Renvoie l'état courant."""
        with self._lock:
            return self._status

    def _begin(self, label: str, total: int) -> threading.Event:
        """Prend la main sur le robot ; lève `BusyError` si une exécution est en cours."""
        with self._lock:
            if self._status.running:
                raise BusyError(
                    f"exécution déjà en cours ({self._status.label}) : "
                    "l'interrompre avant d'en lancer une autre"
                )
            self._cancel = cancel = threading.Event()
            self._status = RunStatus(
                running=True,
                label=label,
                total=total,
                run_id=self._status.run_id + 1,
            )
            return cancel

    @contextlib.contextmanager
    def _track(self, cancel: threading.Event) -> Iterator[None]:
        """Enregistre l'issue de l'exécution, quoi qu'il arrive dans le bloc."""
        outcome = RunOutcome.COMPLETED
        error: str | None = None
        try:
            yield
            if cancel.is_set():
                outcome = RunOutcome.STOPPED
        except Exception as exc:
            outcome = RunOutcome.ERROR
            error = str(exc) or type(exc).__name__
            raise
        finally:
            self._update(running=False, outcome=outcome, error=error)

    def _update(self, **changes: object) -> None:
        with self._lock:
            self._status = self._status.model_copy(update=changes)

    def _worker(
        self,
        settings: Settings,
        instructions: list[Instruction],
        cancel: threading.Event,
    ) -> None:
        # L'erreur est déjà enregistrée dans l'état par `_track` : le thread s'arrête là.
        with contextlib.suppress(Exception), self._track(cancel):
            with RobotClient(settings, cancel) as client:
                client.run(instructions, on_step=lambda step: self._update(step=step))
