"""Interface en ligne de commande ; la logique métier vit dans les autres modules."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from robot_core.client import RobotClient
from robot_core.errors import RobotConsoleError
from robot_core.instructions import Axis, Instruction, parse_move
from robot_core.script import SCRIPT_EXTENSION, load_script
from robot_core.settings import load_settings, save_settings, update_settings

# Ordre d'exécution lorsque plusieurs options de `send` sont combinées.
_SEND_ORDER = (Axis.FORWARD, Axis.TRANSLATION, Axis.ROTATION)

_AXIS_HELP = {
    Axis.FORWARD: "avancer (intensité négative pour reculer)",
    Axis.TRANSLATION: "translation latérale",
    Axis.ROTATION: "rotation sur place",
}


def build_parser() -> argparse.ArgumentParser:
    """Construit l'analyseur d'arguments (sous-commandes send, file, settings)."""
    parser = argparse.ArgumentParser(
        prog="robot-console", description="Pilotage d'un robot autonome par WiFi."
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Point d'entrée ; renvoie le code de sortie du processus."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        match args.command:
            case "send":
                _run_send(parser, args)
            case "file":
                _run_file(args)
            case "settings":
                _run_settings(args)
    except RobotConsoleError as error:
        print(f"erreur : {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"erreur de connexion : {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrompu, robot arrêté.", file=sys.stderr)
        return 130
    return 0


def _run_send(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    instructions: list[Instruction] = []
    for axis in _SEND_ORDER:
        raw = getattr(args, axis)
        if raw is not None:
            instructions.append(parse_move(axis, *raw))
    if not instructions:
        parser.error("send : indiquer au moins une option parmi --forward, --translate, --rotate")
    _execute(instructions)


def _run_file(args: argparse.Namespace) -> None:
    _execute(load_script(args.path))


def _run_settings(args: argparse.Namespace) -> None:
    current = load_settings()
    updated = update_settings(
        current, host=args.host, port=args.port, timeout=args.timeout
    )
    if updated != current:
        save_settings(updated)
    print(f"host    : {updated.host}")
    print(f"port    : {updated.port}")
    print(f"timeout : {updated.timeout}")


def _execute(instructions: list[Instruction]) -> None:
    with RobotClient(load_settings()) as client:
        client.run(instructions)
