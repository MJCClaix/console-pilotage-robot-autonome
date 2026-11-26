import threading
from pathlib import Path

import pytest
from conftest import FakeRobot, wait_until

from robot_core.client import RobotClient
from robot_core.errors import InstructionError
from robot_core.instructions import Axis, Move, Sleep
from robot_core.protocol import STOP_FRAME, encode_move
from robot_core.script import parse_line
from robot_web.app import create_app
from robot_web.controller import RobotController
from robot_web.script_store import ScriptStore


def test_rbs_accepts_optional_repeat() -> None:
    assert parse_line("forward(150, 2, 3)") == Move(axis=Axis.FORWARD, intensity=150, duration=2.0, repeat=3)
    assert parse_line("rotate(-100, 0.5)") == Move(axis=Axis.ROTATION, intensity=-100, duration=0.5)


@pytest.mark.parametrize("line", ["forward(1, 1, 11)", "forward(1, 1, 0)", "forward(1, 1, x)", "forward(1)"])
def test_rbs_rejects_invalid_repeat(line: str) -> None:
    with pytest.raises(InstructionError):
        parse_line(line)


def test_chained_moves_have_no_stop_frame_between_them(robot: FakeRobot) -> None:
    with RobotClient(robot.settings()) as client:
        client.run(
            [
                Move(axis=Axis.FORWARD, intensity=100, duration=0.05),
                Move(axis=Axis.ROTATION, intensity=50, duration=0.05),
            ]
        )
    assert wait_until(lambda: len(robot.frames()) >= 3)
    frames = robot.frames()
    assert frames[0] == encode_move(Axis.FORWARD, 100)
    assert frames[1] == encode_move(Axis.ROTATION, 50)  # pas de trame nulle entre les deux
    assert frames[2] == STOP_FRAME                       # arrêt à la fin de la série


def test_interrupting_a_chain_still_stops_the_robot(robot: FakeRobot) -> None:
    cancel = threading.Event()
    threading.Timer(0.1, cancel.set).start()
    with RobotClient(robot.settings(), cancel) as client:
        client.run(
            [
                Move(axis=Axis.FORWARD, intensity=100, duration=30),
                Move(axis=Axis.ROTATION, intensity=50, duration=30),
            ]
        )
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
    assert encode_move(Axis.ROTATION, 50) not in robot.frames()


def test_web_list_parse_returns_repeat(tmp_path: Path, robot: FakeRobot) -> None:
    app = create_app(
        controller=RobotController(settings_loader=robot.settings),
        store=ScriptStore(tmp_path / "scripts"),
        settings_path=tmp_path / "settings.json",
    )
    response = app.test_client().post("/api/script/parse", json={"content": "forward(1, 1, 3)"})
    assert response.get_json()["instructions"][0]["repeat"] == 3
