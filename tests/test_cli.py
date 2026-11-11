from pathlib import Path

import pytest

from robot_cli import cli
from robot_cli.cli import main
from robot_core.errors import RobotConsoleError


def test_send_requires_an_option(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["send"])
    assert exit_info.value.code == 2
    assert "au moins une option" in capsys.readouterr().err


def test_file_cannot_be_combined_with_send_options() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["file", "script.rbs", "--rotate", "1", "1"])
    assert exit_info.value.code == 2


def test_out_of_range_intensity_is_rejected_before_connecting(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["send", "--forward", "300", "1"]) == 1
    assert "erreur" in capsys.readouterr().err


def test_missing_script_file_gives_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["file", "/nonexistent/script.rbs"]) == 1
    assert "lecture impossible" in capsys.readouterr().err


def test_invalid_script_reports_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = tmp_path / "bad.rbs"
    script.write_text("sleep(1)\njump(1, 1)\n", encoding="utf-8")
    assert main(["file", str(script)]) == 1
    assert "ligne 2" in capsys.readouterr().err


def test_invalid_setting_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["settings", "--port", "0"]) == 1
    assert "port" in capsys.readouterr().err


def test_web_subcommand_starts_interface_on_given_port(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    started: list[int] = []

    def fake_start(port: int) -> str:
        started.append(port)
        return f"http://127.0.0.1:{port}/"

    monkeypatch.setattr(cli, "start_web", fake_start)
    assert cli.main(["web", "--port", "5001"]) == 0
    assert started == [5001]
    assert "http://127.0.0.1:5001/" in capsys.readouterr().out


def test_web_subcommand_reports_startup_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failing_start(port: int) -> str:
        raise RobotConsoleError("l'interface web tourne déjà")

    monkeypatch.setattr(cli, "start_web", failing_start)
    assert cli.main(["web"]) == 1
    assert "tourne déjà" in capsys.readouterr().err
