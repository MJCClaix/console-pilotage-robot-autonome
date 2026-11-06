import pytest
from conftest import FakeRobot, wait_until

from robot_web.controller import BusyError, RobotController, RunOutcome
from robot_core.instructions import Axis, Move, Sleep
from robot_core.protocol import STOP_FRAME
from robot_core.settings import Settings

LONG_MOVE = [Move(axis=Axis.FORWARD, intensity=10, duration=30)]


def test_run_completes(controller: RobotController, robot: FakeRobot) -> None:
    controller.run([Sleep(duration=0.05)], label="script")
    assert wait_until(lambda: not controller.status().running)
    status = controller.status()
    assert status.outcome is RunOutcome.COMPLETED
    assert status.run_id == 1
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])


def test_second_run_is_refused_while_running(controller: RobotController) -> None:
    controller.run(LONG_MOVE, label="script")
    with pytest.raises(BusyError, match="script"):
        controller.run(LONG_MOVE)
    assert controller.stop() is True
    assert wait_until(lambda: not controller.status().running)


def test_stop_interrupts_quickly(controller: RobotController) -> None:
    controller.run(LONG_MOVE)
    assert controller.stop() is True
    assert wait_until(lambda: not controller.status().running, timeout=2)
    assert controller.status().outcome is RunOutcome.STOPPED


def test_stop_when_idle_does_nothing(controller: RobotController) -> None:
    assert controller.stop() is False


def test_connection_failure_is_reported() -> None:
    # Port 1 sur localhost : connexion refusée.
    controller = RobotController(lambda: Settings(host="127.0.0.1", port=1, timeout=0.5))
    controller.run(LONG_MOVE)
    assert wait_until(lambda: not controller.status().running)
    status = controller.status()
    assert status.outcome is RunOutcome.ERROR
    assert status.error


def test_can_run_again_after_finish(controller: RobotController) -> None:
    controller.run([Sleep(duration=0.01)])
    assert wait_until(lambda: not controller.status().running)
    controller.run([Sleep(duration=0.01)])
    assert wait_until(lambda: controller.status().run_id == 2 and not controller.status().running)
