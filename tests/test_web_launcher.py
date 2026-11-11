import socket
import sys
from pathlib import Path

import pytest

from robot_cli import web
from robot_core.errors import RobotConsoleError


def test_dev_command_runs_run_web_script() -> None:
    assert web.web_command() == (sys.executable, str(web.PROJECT_ROOT / "run_web.py"))


def test_start_refuses_when_port_is_already_listening() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RobotConsoleError, match="tourne déjà"):
            web.start_web(port)
