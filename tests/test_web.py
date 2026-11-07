import sys
import threading
from pathlib import Path

import pytest
from conftest import FakeRobot, wait_until
from flask import Flask
from flask.testing import FlaskClient

from robot_core.settings import Settings
from robot_web.app import create_app
from robot_web.controller import RobotController
from robot_web.script_store import ScriptStore

FAKE_CLI = """
import signal, sys, time
signal.signal(signal.SIGINT, signal.default_int_handler)
args = sys.argv[1:]
if "slow" in args:
    print("début", flush=True)
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("interrompu")
        sys.exit(130)
if "fail" in args:
    print("erreur : boum", file=sys.stderr)
    sys.exit(1)
print("args:", *args)
"""


@pytest.fixture
def app(controller: RobotController, tmp_path: Path) -> Flask:
    fake_cli = tmp_path / "fake_cli.py"
    fake_cli.write_text(FAKE_CLI, encoding="utf-8")
    return create_app(
        controller=controller,
        store=ScriptStore(tmp_path / "scripts"),
        settings_path=tmp_path / "settings.json",
        cli_command=(sys.executable, str(fake_cli)),
    )


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def test_index_and_static_are_served(client: FlaskClient) -> None:
    assert b"Console robot" in client.get("/").data
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200


def test_send_then_busy_message(client: FlaskClient) -> None:
    long_move = {"axis": "forward", "intensity": 10, "duration": 30}
    assert client.post("/api/send", json=long_move).status_code == 200
    refused = client.post("/api/send", json=long_move)
    assert refused.status_code == 409
    assert "déjà en cours" in refused.get_json()["error"]
    assert client.post("/api/script/run", json={"content": "sleep(1)"}).status_code == 409

    assert client.post("/api/stop", json={}).get_json() == {"stopped": True}
    assert wait_until(lambda: not client.get("/api/status").get_json()["running"])
    assert client.get("/api/status").get_json()["outcome"] == "stopped"


@pytest.mark.parametrize(
    "payload",
    [
        {"axis": "forward", "intensity": 999, "duration": 1},
        {"axis": "fly", "intensity": 1, "duration": 1},
        {"axis": "forward", "intensity": 1, "duration": -1},
    ],
)
def test_send_validates_payload(client: FlaskClient, payload: dict[str, object]) -> None:
    assert client.post("/api/send", json=payload).status_code == 400


def test_script_run_and_parse_errors(client: FlaskClient) -> None:
    response = client.post("/api/script/parse", json={"content": "forward(1, 1)\nsleep(2)"})
    assert response.get_json()["instructions"] == [
        {"type": "move", "axis": "forward", "intensity": 1, "duration": 1.0},
        {"type": "sleep", "duration": 2.0},
    ]
    bad = client.post("/api/script/run", json={"content": "forward(1, 1)\nnope()"})
    assert bad.status_code == 400
    assert "ligne 2" in bad.get_json()["error"]


def test_script_crud(client: FlaskClient) -> None:
    assert client.get("/api/scripts").get_json() == {"names": []}
    assert client.put("/api/scripts/demo", json={"content": "sleep(1)"}).status_code == 200
    assert client.get("/api/scripts").get_json() == {"names": ["demo"]}
    assert client.get("/api/scripts/demo").get_json()["content"] == "sleep(1)\n"
    assert client.put("/api/scripts/demo", json={"content": "oops"}).status_code == 400
    assert client.delete("/api/scripts/demo", json={}).status_code == 200
    assert client.get("/api/scripts/demo").status_code == 404


def test_script_names_cannot_escape_directory(client: FlaskClient) -> None:
    assert client.put("/api/scripts/..%2Fevil", json={"content": "sleep(1)"}).status_code in {400, 404}
    assert client.put("/api/scripts/a.b", json={"content": "sleep(1)"}).status_code == 400


def test_settings_roundtrip(client: FlaskClient) -> None:
    assert client.get("/api/settings").get_json()["port"] == 80
    updated = client.put("/api/settings", json={"host": "10.0.0.9", "port": 8080})
    assert updated.get_json() == {"host": "10.0.0.9", "port": 8080, "timeout": 3.0}
    assert client.get("/api/settings").get_json()["host"] == "10.0.0.9"
    assert client.put("/api/settings", json={"port": 0}).status_code == 400


def test_requests_are_guarded(client: FlaskClient, robot: FakeRobot) -> None:
    assert client.get("/api/status", headers={"Host": "evil.example"}).status_code == 403
    form = client.post("/api/stop", data="x=1", content_type="application/x-www-form-urlencoded")
    assert form.status_code == 415


def test_terminal_passes_arguments_to_the_cli(client: FlaskClient) -> None:
    quick = client.post("/api/terminal", json={"line": "settings --host 'a b'"}).get_json()
    assert quick == {"output": "args: settings --host a b", "exit_code": 0}
    driving = client.post("/api/terminal", json={"line": "send --forward 1 1"}).get_json()
    assert driving == {"output": "args: send --forward 1 1", "exit_code": 0}
    assert client.get("/api/status").get_json()["outcome"] == "completed"


def test_terminal_reports_cli_failure_and_bad_quotes(client: FlaskClient) -> None:
    failed = client.post("/api/terminal", json={"line": "fail"}).get_json()
    assert failed == {"output": "erreur : boum", "exit_code": 1}
    assert client.post("/api/terminal", json={"line": "send 'x"}).get_json()["exit_code"] == 2
    assert client.post("/api/terminal", json={"line": "  "}).get_json() == {"output": "", "exit_code": 0}


def test_terminal_driving_command_is_refused_while_busy_and_can_be_stopped(
    client: FlaskClient,
) -> None:
    responses: list[dict[str, object]] = []
    thread = threading.Thread(
        target=lambda: responses.append(
            client.post("/api/terminal", json={"line": "send slow"}).get_json()
        )
    )
    thread.start()
    assert wait_until(lambda: client.get("/api/status").get_json()["running"])

    refused = client.post("/api/send", json={"axis": "forward", "intensity": 1, "duration": 1})
    assert refused.status_code == 409
    assert client.post("/api/terminal", json={"line": "send again"}).status_code == 409
    # une commande non motrice reste possible pendant l'exécution
    assert client.post("/api/terminal", json={"line": "settings"}).get_json()["exit_code"] == 0

    assert client.post("/api/stop", json={}).get_json() == {"stopped": True}
    thread.join(timeout=10)
    assert responses and responses[0]["exit_code"] == 130
    assert "interrompu" in str(responses[0]["output"])
    assert client.get("/api/status").get_json()["outcome"] == "stopped"


def test_terminal_runs_the_real_cli() -> None:
    app = create_app(controller=RobotController(lambda: Settings()))
    client = app.test_client()
    helped = client.post("/api/terminal", json={"line": "-h"}).get_json()
    assert helped["exit_code"] == 0
    assert "send" in helped["output"]
    bad = client.post("/api/terminal", json={"line": "settings --port 0"}).get_json()
    assert bad["exit_code"] == 1
    assert "port" in bad["output"]


class _FakeUname:
    """Imite le résultat de ``platform.uname()`` : seul ``release`` est utilisé."""

    def __init__(self, release: str) -> None:
        self.release = release


def _stub_server(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int]]:
    """Remplace le serveur Flask pour inspecter l'hôte et le port utilisés par ``main``."""
    runs: list[tuple[str, int]] = []
    monkeypatch.setattr(
        Flask, "run", lambda self, host, port, threaded: runs.append((host, port))
    )
    return runs


def test_main_opens_browser_on_page_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from robot_web import app as web_app

    runs = _stub_server(monkeypatch)
    scheduled: list[tuple[float, tuple[str]]] = []

    class RecordingTimer:
        def __init__(self, interval: float, function, args: tuple[str]) -> None:
            scheduled.append((interval, args))

        def start(self) -> None:
            pass

    monkeypatch.setattr(web_app.threading, "Timer", RecordingTimer)
    web_app.main(["--port", "8080"])
    assert scheduled == [(1.0, ("http://127.0.0.1:8080/",))]
    assert runs == [("127.0.0.1", 8080)]


def test_main_no_browser_flag_skips_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    from robot_web import app as web_app

    runs = _stub_server(monkeypatch)
    monkeypatch.setattr(
        web_app.threading,
        "Timer",
        lambda *args, **kwargs: pytest.fail("le navigateur ne doit pas être lancé"),
    )
    web_app.main(["--no-browser"])
    assert runs == [("127.0.0.1", 5000)]


def test_open_browser_uses_windows_under_wsl(monkeypatch: pytest.MonkeyPatch) -> None:
    from robot_web import app as web_app

    commands: list[list[str]] = []
    monkeypatch.setattr(web_app.platform, "uname", lambda: _FakeUname("5.15.0-microsoft-standard-WSL2"))
    monkeypatch.setattr(web_app.subprocess, "run", lambda cmd, **kwargs: commands.append(cmd))
    monkeypatch.setattr(web_app.webbrowser, "open", lambda url: pytest.fail("pas de webbrowser sous WSL"))
    web_app._open_browser("http://127.0.0.1:5000/")
    assert commands == [["cmd.exe", "/c", "start", "", "http://127.0.0.1:5000/"]]


def test_open_browser_uses_webbrowser_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    from robot_web import app as web_app

    opened: list[str] = []
    monkeypatch.setattr(web_app.platform, "uname", lambda: _FakeUname("6.8.0-generic"))
    monkeypatch.setattr(web_app.subprocess, "run", lambda *a, **k: pytest.fail("pas de cmd.exe hors WSL"))
    monkeypatch.setattr(web_app.webbrowser, "open", opened.append)
    web_app._open_browser("http://127.0.0.1:5000/")
    assert opened == ["http://127.0.0.1:5000/"]
