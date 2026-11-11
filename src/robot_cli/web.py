"""Lancement de l'interface web depuis la CLI, dans un processus séparé.

La CLI n'importe pas `robot_web` (les deux applications sont indépendantes) : elle lance
l'interface comme un autre programme. Le serveur ouvre lui-même la page dans le navigateur.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

from robot_core.errors import RobotConsoleError
from robot_core.paths import PROJECT_ROOT

DEFAULT_WEB_PORT = 5000

# Même nom que l'exécutable construit par build_exes.py (voir robot_web/terminal.py).
WEB_EXECUTABLE_NAME = "interface-pilotage.exe" if sys.platform == "win32" else "interface-pilotage"

_STARTUP_TIMEOUT = 15.0
_POLL_INTERVAL = 0.2
# Détache le serveur de la CLI : il reste lancé après la fermeture du terminal.
_WINDOWS_DETACH_FLAGS = (
    getattr(subprocess, "DETACHED_PROCESS", 0)
    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
)


def web_command() -> tuple[str, ...]:
    """Commande qui lance l'interface web : l'exécutable si l'application est gelée."""
    if getattr(sys, "frozen", False):
        return (str(Path(sys.executable).with_name(WEB_EXECUTABLE_NAME)),)
    return (sys.executable, str(PROJECT_ROOT / "run_web.py"))


def start_web(port: int = DEFAULT_WEB_PORT) -> str:
    """Démarre le serveur web sur `port` et renvoie son adresse une fois joignable."""
    url = f"http://127.0.0.1:{port}/"
    if _is_listening(port):
        raise RobotConsoleError(f"l'interface web tourne déjà : {url}")
    process = subprocess.Popen(
        [*web_command(), "--port", str(port)],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_WINDOWS_DETACH_FLAGS,
        start_new_session=sys.platform != "win32",
    )
    deadline = time.monotonic() + _STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RobotConsoleError(
                f"l'interface web s'est arrêtée au démarrage (code {process.returncode})"
            )
        if _is_listening(port):
            return url
        time.sleep(_POLL_INTERVAL)
    raise RobotConsoleError(
        f"l'interface web ne répond pas sur {url} après {_STARTUP_TIMEOUT:.0f} s"
    )


def _is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0
