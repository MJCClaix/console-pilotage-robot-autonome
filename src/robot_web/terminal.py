"""Terminal de la page web : lance l'application CLI telle quelle, en sous-processus.

L'application web ne connaît pas la grammaire de la CLI : elle transmet les arguments
au vrai `run_cli.py` et affiche sa sortie.
"""

import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass

from robot_core.paths import PROJECT_ROOT

DEFAULT_CLI_COMMAND = (sys.executable, str(PROJECT_ROOT / "run_cli.py"))

# Seules ces sous-commandes de la CLI pilotent le robot : elles doivent réserver le
# robot (une seule exécution à la fois). Les autres (settings, -h...) sont instantanées.
DRIVING_COMMANDS = frozenset({"send", "file"})

QUICK_COMMAND_TIMEOUT = 10.0
_POLL_INTERVAL = 0.1
_INTERRUPT_GRACE = 3.0
_TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class TerminalResult:
    """Sortie (stdout et stderr mêlés) et code de retour d'une commande."""

    output: str
    exit_code: int


def run_cli(
    command: Sequence[str],
    args: Sequence[str],
    cancel: threading.Event,
    timeout: float | None = None,
) -> TerminalResult:
    """Exécute la CLI ; `cancel` ou le dépassement de `timeout` l'interrompt.

    L'interruption envoie SIGINT (équivalent d'un Ctrl-C), ce qui laisse la CLI envoyer
    la trame d'arrêt au robot avant de quitter ; un SIGKILL n'intervient qu'en dernier recours.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    with subprocess.Popen(
        [*command, *args],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as process:
        while True:
            try:
                output, _ = process.communicate(timeout=_POLL_INTERVAL)
                return TerminalResult(output.rstrip(), process.returncode)
            except subprocess.TimeoutExpired:
                timed_out = deadline is not None and time.monotonic() > deadline
                if cancel.is_set() or timed_out:
                    return _interrupt(process, timed_out)


def _interrupt(process: subprocess.Popen[str], timed_out: bool) -> TerminalResult:
    process.send_signal(signal.SIGINT)
    try:
        output, _ = process.communicate(timeout=_INTERRUPT_GRACE)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
    text = output.rstrip()
    if timed_out:
        text = f"{text}\ndélai dépassé".strip()
        return TerminalResult(text, _TIMEOUT_EXIT_CODE)
    return TerminalResult(text, process.returncode)
