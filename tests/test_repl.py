import io
from collections.abc import Iterator, Sequence

import pytest
from conftest import FakeRobot, wait_until

from robot_cli import cli
from robot_cli.repl import PROMPT, run_console
from robot_core.client import RobotClient
from robot_core.instructions import Axis, Instruction, Move, Sleep
from robot_core.protocol import STOP_FRAME, encode_move


class ScriptedInput:
    """Remplace `input()` : renvoie les lignes données, ou lève l'exception donnée."""

    def __init__(self, lines: Sequence[str | type[BaseException]]) -> None:
        self._lines: Iterator[str | type[BaseException]] = iter(lines)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        item = next(self._lines, EOFError)
        if isinstance(item, str):
            return item
        raise item


def scripted(*lines: str | type[BaseException]) -> ScriptedInput:
    return ScriptedInput(lines)


class Recorder:
    """Faux exécuteur : enregistre les instructions, ou échoue avec l'erreur donnée."""

    def __init__(self, fail_with: BaseException | None = None) -> None:
        self.executed: list[Instruction] = []
        self._fail_with = fail_with

    def __call__(self, instructions: Sequence[Instruction]) -> None:
        if self._fail_with is not None:
            raise self._fail_with
        self.executed.extend(instructions)


def test_each_line_is_one_instruction() -> None:
    recorder = Recorder()
    read = scripted("forward(150, 2)", "", "  # commentaire", "sleep(1)  # pause", "exit()")
    assert run_console(recorder, read) == 0
    assert recorder.executed == [
        Move(axis=Axis.FORWARD, intensity=150, duration=2.0),
        Sleep(duration=1.0),
    ]
    assert set(read.prompts) == {PROMPT}


@pytest.mark.parametrize("quit_word", ["exit()", "quit()", "exit", "quit"])
def test_exit_words_quit(quit_word: str) -> None:
    recorder = Recorder()
    assert run_console(recorder, scripted(quit_word, "forward(1, 1)")) == 0
    assert recorder.executed == []


def test_ctrl_d_quits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_console(Recorder(), scripted(EOFError)) == 0
    assert "Console rbs" in capsys.readouterr().out


def test_ctrl_c_at_prompt_keeps_the_console_alive() -> None:
    recorder = Recorder()
    run_console(recorder, scripted(KeyboardInterrupt, "sleep(1)", "exit()"))
    assert recorder.executed == [Sleep(duration=1.0)]


def test_help_prints_instructions(capsys: pytest.CaptureFixture[str]) -> None:
    run_console(Recorder(), scripted("help()", "exit()"))
    assert "rotate(intensité, durée)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "line", ["jump(1, 1)", "forward(1)", "forward(999, 1)", "forward 1 1", "sleep(abc)"]
)
def test_errors_are_reported_and_console_continues(
    line: str, capsys: pytest.CaptureFixture[str]
) -> None:
    recorder = Recorder()
    run_console(recorder, scripted(line, "sleep(2)", "exit()"))
    assert "erreur" in capsys.readouterr().err
    assert recorder.executed == [Sleep(duration=2.0)]


def test_connection_error_does_not_quit(capsys: pytest.CaptureFixture[str]) -> None:
    recorder = Recorder(fail_with=ConnectionRefusedError("refusé"))
    assert run_console(recorder, scripted("sleep(1)", "exit()")) == 0
    assert "erreur de connexion : refusé" in capsys.readouterr().err


def test_interrupting_a_move_returns_to_prompt(capsys: pytest.CaptureFixture[str]) -> None:
    recorder = Recorder(fail_with=KeyboardInterrupt())
    assert run_console(recorder, scripted("forward(1, 30)", "exit()")) == 0
    assert "interrompu" in capsys.readouterr().err


def test_main_without_arguments_starts_the_console(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("help()\n"))  # puis fin de flux (Ctrl-D)
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "Console rbs" in out
    assert "forward(intensité, durée)" in out


def test_console_drives_a_robot_end_to_end(robot: FakeRobot) -> None:
    def execute(instructions: Sequence[Instruction]) -> None:
        with RobotClient(robot.settings()) as client:
            client.run(instructions)

    run_console(execute, scripted("forward(50, 0.05)", "exit()"))
    assert wait_until(lambda: robot.frames()[-1:] == [STOP_FRAME])
    assert robot.frames()[0] == encode_move(Axis.FORWARD, 50)
