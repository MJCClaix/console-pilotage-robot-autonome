"""Mini langage de script (`.rbs`) pour enchaîner des instructions.

Syntaxe, une instruction par ligne ; `#` démarre un commentaire :

    forward(200, 2.0)     # avancer (négatif pour reculer)
    translate(-150, 1)
    rotate(100, 0.5)
    sleep(1.5)
"""

import re
from pathlib import Path

from robot_console.errors import InstructionError, ScriptError
from robot_console.instructions import Axis, Instruction, parse_move, parse_sleep

SCRIPT_EXTENSION = ".rbs"

_CALL_PATTERN = re.compile(r"^(?P<name>\w+)\s*\((?P<args>[^()]*)\)$")
_MOVE_NAMES = {axis.value: axis for axis in Axis}


def parse_line(line: str) -> Instruction | None:
    """Analyse une ligne ; renvoie `None` pour une ligne vide ou commentée."""
    code = line.split("#", 1)[0].strip()
    if not code:
        return None

    match = _CALL_PATTERN.match(code)
    if match is None:
        raise InstructionError(f"syntaxe invalide : {code!r}")

    name = match["name"]
    args = [arg.strip() for arg in match["args"].split(",")] if match["args"].strip() else []

    if name in _MOVE_NAMES:
        _expect_arguments(name, args, 2)
        return parse_move(_MOVE_NAMES[name], args[0], args[1])
    if name == "sleep":
        _expect_arguments(name, args, 1)
        return parse_sleep(args[0])
    raise InstructionError(f"instruction inconnue : {name!r}")


def parse_script(text: str) -> list[Instruction]:
    """Analyse un script complet ; les erreurs indiquent le numéro de ligne."""
    instructions: list[Instruction] = []
    for number, line in enumerate(text.splitlines(), start=1):
        try:
            instruction = parse_line(line)
        except InstructionError as error:
            raise ScriptError(f"ligne {number} : {error}") from error
        if instruction is not None:
            instructions.append(instruction)
    return instructions


def load_script(path: Path) -> list[Instruction]:
    """Lit et analyse un fichier de script."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ScriptError(f"lecture impossible ({path}) : {error}") from error
    return parse_script(text)


def _expect_arguments(name: str, args: list[str], expected: int) -> None:
    if len(args) != expected:
        raise InstructionError(
            f"{name}() attend {expected} argument(s), {len(args)} reçu(s)"
        )
