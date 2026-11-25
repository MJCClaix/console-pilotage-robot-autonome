from pathlib import Path

import pytest
from conftest import FakeRobot, wait_until

from robot_cli.cli import build_parser, main
from robot_core.client import RobotClient
from robot_core.instructions import Axis, Move, Sleep
from robot_core.protocol import STOP_FRAME, encode_move
from robot_web.app import create_app
from robot_web.controller import RobotController
from robot_web.script_store import ScriptStore


def _move_frames(robot: FakeRobot) -> int:
    return sum(1 for frame in robot.frames() if frame == encode_move(Axis.FORWARD, 100))


def test_default_sends_the_command_once(robot: FakeRobot) -> None:
    with RobotClient(robot.settings()) as client:
        client.run([Move(axis=Axis.FORWARD, intensity=100, duration=0.05)])
    assert wait_until(lambda: len(robot.frames()) >= 3)
    assert _move_frames(robot) == 1


def test_repeat_sends_the_command_n_times_then_stops_repeating(robot: FakeRobot) -> None:
    # 0,3 s de mouvement : sans renvoi périodique, la commande ne doit apparaître que 3 fois.
    with RobotClient(robot.settings()) as client:
        client.run([Move(axis=Axis.FORWARD, intensity=100, duration=0.3, repeat=3)])
    assert wait_until(lambda: len(robot.frames()) >= 7)
    frames = robot.frames()
    assert _move_frames(robot) == 3
    assert frames[:3] == [encode_move(Axis.FORWARD, 100)] * 3
    assert frames[3:] == [STOP_FRAME] * (len(frames) - 3)


def test_sleep_holds_no_move_after_a_move(robot: FakeRobot) -> None:
    with RobotClient(robot.settings()) as client:
        client.run([Move(axis=Axis.FORWARD, intensity=100, duration=0.05), Sleep(duration=0.3)])
    assert wait_until(lambda: len(robot.frames()) >= 3)
    assert _move_frames(robot) == 1


def test_cli_repeat_option_defaults_to_one() -> None:
    assert build_parser().parse_args(["send", "--forward", "5", "1"]).repeat == 1
    assert build_parser().parse_args(["send", "--forward", "5", "1", "--repeat", "4"]).repeat == 4


def test_cli_rejects_out_of_range_repeat(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["send", "--forward", "5", "1", "--repeat", "0"]) == 1
    assert "repeat" in capsys.readouterr().err


def test_web_rejects_out_of_range_repeat(tmp_path: Path, robot: FakeRobot) -> None:
    app = create_app(
        controller=RobotController(settings_loader=robot.settings),
        store=ScriptStore(tmp_path / "scripts"),
        settings_path=tmp_path / "settings.json",
    )
    client = app.test_client()
    too_many = {"axis": "forward", "intensity": 1, "duration": 0.01, "repeat": 11}
    assert client.post("/api/send", json=too_many).status_code == 400
    ok = {"axis": "forward", "intensity": 1, "duration": 0.01, "repeat": 2}
    assert client.post("/api/send", json=ok).status_code == 200
    assert wait_until(lambda: not client.get("/api/status").get_json()["running"])

