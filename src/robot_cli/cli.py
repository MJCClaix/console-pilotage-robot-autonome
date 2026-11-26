"""Interface en ligne de commande ; la logique métier vit dans les autres modules."""

import argparse
import contextlib
import io
import sys
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from robot_cli.repl import ConsoleSession, run_console
from robot_cli.web import DEFAULT_WEB_PORT, start_web
from robot_core.client import RobotClient
from robot_core.errors import RobotConsoleError
from robot_core.instructions import MAX_REPEAT, Axis, Instruction, parse_move
from robot_core.script import SCRIPT_EXTENSION, load_script
from robot_core.settings import load_settings, save_settings, update_settings

# Ordre d'exécution lorsque plusieurs options de `send` sont combinées.
_SEND_ORDER = (Axis.FORWARD, Axis.TRANSLATION, Axis.ROTATION)

# Sous-commandes qui pilotent le robot (elles peuvent être interrompues par `cancel`).
DRIVING_COMMANDS = frozenset({"send", "file"})

_AXIS_HELP = {
    Axis.FORWARD: "avancer (intensité négative pour reculer)",
    Axis.TRANSLATION: "translation latérale",
    Axis.ROTATION: "rotation sur place",
}


def build_parser() -> argparse.ArgumentParser:
    """Construit l'analyseur d'arguments (sous-commandes send, file, settings, web)."""
    parser = argparse.ArgumentParser(
        prog="robot-console",
        description="Pilotage d'un robot autonome par WiFi.",
        epilog="Sans argument, lance une console interactive rbs (forward(150, 2), sleep(1)...).",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    send = commands.add_parser("send", help="envoyer des déplacements au robot")
    for axis in _SEND_ORDER:
        send.add_argument(
            f"--{axis}",
            nargs=2,
            metavar=("INTENSITE", "DUREE"),
            help=f"{_AXIS_HELP[axis]} ; durée en secondes",
        )
    send.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help=f"envoyer la commande N fois au début (1 à {MAX_REPEAT}, défaut 1)",
    )

    file = commands.add_parser(
        "file", help=f"exécuter un script d'instructions ({SCRIPT_EXTENSION})"
    )
    file.add_argument("path", type=Path, help="chemin du fichier de script")

    settings = commands.add_parser(
        "settings", help="afficher ou modifier les réglages de connexion"
    )
    settings.add_argument("--host", help="adresse IP ou nom d'hôte du robot")
    settings.add_argument("--port", type=int, help="port TCP du robot")
    settings.add_argument(
        "--timeout", type=float, help="délai de connexion, en secondes"
    )

    web = commands.add_parser(
        "web", help="démarrer l'interface web et l'ouvrir dans le navigateur"
    )
    web.add_argument(
        "--port", type=int, default=DEFAULT_WEB_PORT, help="port du serveur web (défaut : 5000)"
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    cancel: threading.Event | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Point d'entrée ; renvoie le code de sortie du processus.

    Sans aucun argument, lance la console interactive rbs.

    `cancel` interrompt une commande qui pilote le robot (utilisé par l'interface web,
    qui exécute la CLI dans son propre processus). `out` et `err` remplacent les sorties
    standard, pour récupérer le texte affiché.
    """
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    arguments = sys.argv[1:] if argv is None else list(argv)
    if not arguments:
        with ConsoleSession(load_settings()) as session:
            return run_console(session, commands={"web": _open_web, "web()": _open_web})

    # argparse écrit son aide et ses erreurs sur les sorties standard ; on les capture aussi.
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        return _dispatch(arguments, cancel, out, err)


def run_in_process(argv: Sequence[str], cancel: threading.Event) -> tuple[str, int]:
    """Exécute la CLI dans le processus courant ; renvoie (texte affiché, code de sortie).

    argparse quitte par `SystemExit` (aide, erreur d'usage) : on le convertit en code de sortie.
    """
    buffer = io.StringIO()
    try:
        exit_code = main(argv, cancel=cancel, out=buffer, err=buffer)
    except SystemExit as exit_request:
        exit_code = int(exit_request.code or 0)
    return buffer.getvalue().rstrip(), exit_code


def _dispatch(
    arguments: Sequence[str],
    cancel: threading.Event | None,
    out: TextIO,
    err: TextIO,
) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        match args.command:
            case "send":
                _run_send(parser, args, cancel)
            case "file":
                _run_file(args, cancel)
            case "settings":
                _run_settings(args, out)
            case "web":
                _open_web(args.port, out)
    except RobotConsoleError as error:
        print(f"erreur : {error}", file=err)
        return 1
    except OSError as error:
        print(f"erreur de connexion : {error}", file=err)
        return 1
    except KeyboardInterrupt:
        print("interrompu, robot arrêté.", file=err)
        return 130
    if args.command in DRIVING_COMMANDS and cancel is not None and cancel.is_set():
        print("interrompu, robot arrêté.", file=err)
        return 130
    return 0


def _run_send(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    cancel: threading.Event | None,
) -> None:
    instructions: list[Instruction] = []
    for axis in _SEND_ORDER:
        raw = getattr(args, axis)
        if raw is not None:
            instructions.append(parse_move(axis, *raw, repeat=args.repeat))
    if not instructions:
        parser.error("send : indiquer au moins une option parmi --forward, --translate, --rotate")
    _execute(instructions, cancel)


def _run_file(args: argparse.Namespace, cancel: threading.Event | None) -> None:
    _execute(load_script(args.path), cancel)


def _run_settings(args: argparse.Namespace, out: TextIO) -> None:
    current = load_settings()
    updated = update_settings(
        current, host=args.host, port=args.port, timeout=args.timeout
    )
    if updated != current:
        save_settings(updated)
    print(f"host    : {updated.host}", file=out)
    print(f"port    : {updated.port}", file=out)
    print(f"timeout : {updated.timeout}", file=out)


def _open_web(port: int = DEFAULT_WEB_PORT, out: TextIO | None = None) -> None:
    target = out if out is not None else sys.stdout
    print(f"interface web lancée : {start_web(port)}", file=target)


def _execute(instructions: list[Instruction], cancel: threading.Event | None) -> None:
    with RobotClient(load_settings(), cancel) as client:
        client.run(instructions)
