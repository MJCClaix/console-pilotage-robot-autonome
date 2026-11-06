"""Application Flask : API JSON + page unique de pilotage."""

import argparse
import shlex
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from flask import Flask, abort, jsonify, render_template, request
from flask.typing import ResponseReturnValue
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from robot_core.errors import RobotConsoleError, describe_validation_error
from robot_core.instructions import Instruction, Move
from robot_core.script import parse_script
from robot_core.settings import (
    DEFAULT_SETTINGS_PATH,
    load_settings,
    save_settings,
    update_settings,
)
from robot_web.controller import BusyError, RobotController
from robot_web.script_store import ScriptNotFoundError, ScriptStore
from robot_web.terminal import (
    DEFAULT_CLI_COMMAND,
    DRIVING_COMMANDS,
    QUICK_COMMAND_TIMEOUT,
    run_cli,
)

# Seuls ces noms d'hôte sont servis : protège contre le "DNS rebinding".
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_DEFAULT_WEB_PORT = 5000


def create_app(
    controller: RobotController | None = None,
    store: ScriptStore | None = None,
    settings_path: Path = DEFAULT_SETTINGS_PATH,
    cli_command: Sequence[str] = DEFAULT_CLI_COMMAND,
) -> Flask:
    """Crée l'application ; les dépendances sont injectables pour les tests."""
    app = Flask(__name__)
    controller = controller if controller is not None else RobotController()
    store = store if store is not None else ScriptStore()

    @app.before_request
    def guard() -> None:
        # Le robot est physique : on refuse les hôtes inattendus et les POST non-JSON
        # (un formulaire d'un autre site ne peut pas envoyer de JSON sans pré-vérification CORS).
        if urlsplit(f"//{request.host}").hostname not in _LOCAL_HOSTS:
            abort(403, "hôte non autorisé")
        if request.method in {"POST", "PUT", "DELETE"} and not request.is_json:
            abort(415, "contenu JSON attendu")

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    # --- État et exécution -------------------------------------------------

    @app.get("/api/status")
    def status() -> ResponseReturnValue:
        return jsonify(controller.status().model_dump(mode="json"))

    @app.post("/api/stop")
    def stop() -> ResponseReturnValue:
        return jsonify(stopped=controller.stop())

    @app.post("/api/send")
    def send() -> ResponseReturnValue:
        move = Move.model_validate(_json_body())
        controller.run([move], label="commande")
        return jsonify(started=True)

    @app.post("/api/script/run")
    def run_script() -> ResponseReturnValue:
        instructions = parse_script(_text_field("content"))
        controller.run(instructions, label="script")
        return jsonify(started=True, total=len(instructions))

    @app.post("/api/script/parse")
    def parse() -> ResponseReturnValue:
        instructions = parse_script(_text_field("content"))
        return jsonify(instructions=[_serialize(item) for item in instructions])

    # --- Scripts enregistrés ----------------------------------------------

    @app.get("/api/scripts")
    def list_scripts() -> ResponseReturnValue:
        return jsonify(names=store.names())

    @app.get("/api/scripts/<name>")
    def read_script(name: str) -> ResponseReturnValue:
        return jsonify(name=name, content=store.read(name))

    @app.put("/api/scripts/<name>")
    def write_script(name: str) -> ResponseReturnValue:
        store.write(name, _text_field("content"))
        return jsonify(name=name, saved=True)

    @app.delete("/api/scripts/<name>")
    def delete_script(name: str) -> ResponseReturnValue:
        store.delete(name)
        return jsonify(name=name, deleted=True)

    # --- Réglages ---------------------------------------------------------

    @app.get("/api/settings")
    def get_settings() -> ResponseReturnValue:
        return jsonify(load_settings(settings_path).model_dump())

    @app.put("/api/settings")
    def put_settings() -> ResponseReturnValue:
        current = load_settings(settings_path)
        updated = update_settings(current, **_json_body())
        if updated != current:
            save_settings(updated, settings_path)
        return jsonify(updated.model_dump())

    # --- Terminal (lance l'application CLI) -------------------------------

    @app.post("/api/terminal")
    def terminal() -> ResponseReturnValue:
        try:
            args = shlex.split(_text_field("line"))
        except ValueError as error:
            return jsonify(output=f"erreur : {error}", exit_code=2)
        if not args:
            return jsonify(output="", exit_code=0)

        if args[0] in DRIVING_COMMANDS:
            # Commande qui pilote le robot : refusée si une exécution est en cours,
            # et interrompue par `stop()` (équivalent d'un Ctrl-C).
            with controller.exclusive("terminal") as cancel:
                result = run_cli(cli_command, args, cancel)
        else:
            result = run_cli(
                cli_command, args, threading.Event(), timeout=QUICK_COMMAND_TIMEOUT
            )
        return jsonify(output=result.output, exit_code=result.exit_code)

    # --- Erreurs ----------------------------------------------------------

    @app.errorhandler(BusyError)
    def on_busy(error: BusyError) -> ResponseReturnValue:
        return jsonify(error=str(error)), 409

    @app.errorhandler(ScriptNotFoundError)
    def on_not_found(error: ScriptNotFoundError) -> ResponseReturnValue:
        return jsonify(error=str(error)), 404

    @app.errorhandler(RobotConsoleError)
    def on_console_error(error: RobotConsoleError) -> ResponseReturnValue:
        return jsonify(error=str(error)), 400

    @app.errorhandler(ValidationError)
    def on_validation_error(error: ValidationError) -> ResponseReturnValue:
        return jsonify(error=describe_validation_error(error)), 400

    @app.errorhandler(HTTPException)
    def on_http_error(error: HTTPException) -> ResponseReturnValue:
        return jsonify(error=error.description), error.code or 500

    return app


def main(argv: Sequence[str] | None = None) -> None:
    """Lance le serveur de développement, accessible uniquement depuis cette machine."""
    parser = argparse.ArgumentParser(
        prog="robot-console-web", description="Interface web de pilotage du robot."
    )
    parser.add_argument("--port", type=int, default=_DEFAULT_WEB_PORT)
    args = parser.parse_args(argv)
    create_app().run(host="127.0.0.1", port=args.port, threaded=True)


def _json_body() -> dict[str, Any]:
    payload = request.get_json()
    if not isinstance(payload, dict):
        abort(400, "objet JSON attendu")
    return payload


def _text_field(key: str) -> str:
    value = _json_body().get(key)
    if not isinstance(value, str):
        abort(400, f"champ texte {key!r} requis")
    return value


def _serialize(instruction: Instruction) -> dict[str, Any]:
    kind = "move" if isinstance(instruction, Move) else "sleep"
    return {"type": kind, **instruction.model_dump(mode="json")}
