from robot_console.instructions import Axis
from robot_console.protocol import STOP_FRAME, encode_frame, encode_move


def test_frame_is_twelve_bytes_big_endian() -> None:
    assert encode_frame(1, 2, 3) == bytes([0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3])


def test_negative_values_use_twos_complement() -> None:
    assert encode_frame(-1)[:4] == b"\xff\xff\xff\xff"


def test_move_fills_only_its_axis() -> None:
    assert encode_move(Axis.TRANSLATION, 5) == encode_frame(0, 5, 0)
    assert encode_move(Axis.ROTATION, -5) == encode_frame(0, 0, -5)


def test_stop_frame_is_all_zero() -> None:
    assert STOP_FRAME == bytes(12)
