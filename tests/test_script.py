import pytest

from robot_console.errors import ScriptError
from robot_console.instructions import Axis, Move, Sleep
from robot_console.script import parse_script


def test_parses_all_instructions_and_ignores_comments() -> None:
    script = """
    # commentaire
    forward(100, 2)   # avance
    translate(-50, 1.5)
    rotate(255, 0.5)
    sleep(3)
    """
    assert parse_script(script) == [
        Move(axis=Axis.FORWARD, intensity=100, duration=2.0),
        Move(axis=Axis.TRANSLATION, intensity=-50, duration=1.5),
        Move(axis=Axis.ROTATION, intensity=255, duration=0.5),
        Sleep(duration=3.0),
    ]


@pytest.mark.parametrize(
    ("line", "number"),
    [
        ("jump(1, 1)", 2),
        ("forward(100)", 2),
        ("forward(300, 1)", 2),
        ("forward(1, -1)", 2),
        ("forward 100 1", 2),
        ("sleep(abc)", 2),
    ],
)
def test_errors_report_line_number(line: str, number: int) -> None:
    with pytest.raises(ScriptError, match=f"ligne {number}"):
        parse_script(f"sleep(1)\n{line}")
