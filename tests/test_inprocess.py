import threading
from pathlib import Path

import pytest
from conftest import FakeRobot, wait_until
from flask.testing import FlaskClient

from robot_cli.cli import run_in_process
from robot_core.protocol import STOP_FRAME, encode_move
from robot_core.instructions import Axis
from robot_web.app import create_app
from robot_web.controller import RobotController
from robot_web.script_store import ScriptStore


@pytest.fixture(autouse=True)
def _use_fake_robot_settings(robot: FakeRobot, monkeypatch: pytest.MonkeyPatch) -> None:
    # La CLI lit config/settings.json (ou 192.168.1.3 par défaut) : on la force sur le faux robot
    # pour ne jamais envoyer de trame au vrai robot pendant les tests.
    monkeypatch.setattr("robot_cli.cli.load_settings", robot.settings)


def _client(tmp_path: Path, robot: FakeRobot, runner) -> FlaskClient:  # type: ignore[no-untyped-def]
    app = create_app(
        controller=RobotController(settings_loader=robot.settings),
        store=ScriptStore(tmp_path / "scripts"),
        settings_path=tmp_path / "settings.json",
        driving_runner=runner,
    )
    return app.test_client()


def test_driving_command_runs_the_real_cli_in_process(tmp_path: Path, robot: FakeRobot) -> None:
    client = _client(tmp_path, robot, run_in_process)
    response = client.post("/api/terminal", json={"line": "send --forward 100 0.05"}).get_json()
    assert response == {"output": "", "exit_code": 0}
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
    assert robot.frames()[0] == encode_move(Axis.FORWARD, 100)


def test_cli_errors_are_returned_in_the_terminal_output(tmp_path: Path, robot: FakeRobot) -> None:
    client = _client(tmp_path, robot, run_in_process)
    missing = client.post("/api/terminal", json={"line": "send"}).get_json()
    assert missing["exit_code"] == 2
    assert "au moins une option" in missing["output"]
    bad = client.post("/api/terminal", json={"line": "send --forward 300 1"}).get_json()
    assert bad["exit_code"] == 1
    assert "erreur" in bad["output"]


def test_stop_interrupts_a_cli_command_running_in_process(tmp_path: Path, robot: FakeRobot) -> None:
    client = _client(tmp_path, robot, run_in_process)
    responses: list[dict[str, object]] = []
    thread = threading.Thread(
        target=lambda: responses.append(
            client.post("/api/terminal", json={"line": "send --rotate 50 30"}).get_json()
        )
    )
    thread.start()
    assert wait_until(lambda: client.get("/api/status").get_json()["running"])
    assert client.post("/api/stop", json={}).get_json() == {"stopped": True}
    thread.join(timeout=10)
    assert responses and responses[0]["exit_code"] == 130
    assert "interrompu" in str(responses[0]["output"])
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
    assert client.get("/api/status").get_json()["outcome"] == "stopped"
