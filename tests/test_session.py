import pytest
from conftest import FakeRobot, wait_until

from robot_cli.repl import ConsoleSession
from robot_core.client import RobotClient
from robot_core.instructions import Axis, Move, Sleep
from robot_core.protocol import STOP_FRAME


def test_console_session_uses_one_connection_for_all_instructions(robot: FakeRobot) -> None:
    with ConsoleSession(robot.settings()) as session:
        session([Move(axis=Axis.FORWARD, intensity=50, duration=0.01)])
        session([Sleep(duration=0.01)])
        session([Move(axis=Axis.ROTATION, intensity=20, duration=0.01)])
        assert wait_until(lambda: robot.connections >= 1)
    assert robot.connections == 1


def test_leaving_the_session_sends_a_stop_frame(robot: FakeRobot) -> None:
    with ConsoleSession(robot.settings()) as session:
        session([Move(axis=Axis.FORWARD, intensity=50, duration=0.01)])
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])


def test_session_reconnects_after_an_error(
    robot: FakeRobot, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_run = RobotClient.run
    calls = {"count": 0}

    def flaky_run(self: RobotClient, instructions, on_step=None) -> None:  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] == 1:
            raise ConnectionResetError("coupé")
        original_run(self, instructions, on_step)

    monkeypatch.setattr(RobotClient, "run", flaky_run)
    with ConsoleSession(robot.settings()) as session:
        with pytest.raises(ConnectionResetError):
            session([Sleep(duration=0.01)])
        session([Sleep(duration=0.01)])
    assert wait_until(lambda: robot.connections >= 2)
    assert robot.connections == 2
