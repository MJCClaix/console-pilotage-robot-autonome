import threading

from conftest import FakeRobot, wait_until

from robot_core.client import RobotClient
from robot_core.instructions import Axis, Move, Sleep
from robot_core.protocol import STOP_FRAME, encode_move


def test_client_sends_frames_then_stop_frame(robot: FakeRobot) -> None:
    with RobotClient(robot.settings()) as client:
        client.run(
            [Move(axis=Axis.FORWARD, intensity=100, duration=0.05), Sleep(duration=0.05)]
        )
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
    assert robot.frames()[0] == encode_move(Axis.FORWARD, 100)


def test_cancel_interrupts_a_long_move(robot: FakeRobot) -> None:
    cancel = threading.Event()
    steps: list[int] = []
    threading.Timer(0.2, cancel.set).start()
    with RobotClient(robot.settings(), cancel) as client:
        client.run(
            [Move(axis=Axis.ROTATION, intensity=50, duration=30), Sleep(duration=30)],
            on_step=steps.append,
        )
    assert steps == [1]  # la seconde instruction n'a jamais démarré
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
