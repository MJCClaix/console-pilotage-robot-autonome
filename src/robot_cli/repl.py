"""Console interactive rbs : une instruction du langage `.rbs` par ligne, comme un REPL Python."""

import contextlib
import sys
from collections.abc import Callable, Sequence

from robot_core.errors import RobotConsoleError
from robot_core.instructions import MAX_INTENSITY, Instruction
from robot_core.script import parse_line

PROMPT = ">>> "

BANNER = (
    "Console rbs : tape une instruction à la fois, par exemple forward(150, 2).\n"
    "help() pour l'aide, exit() ou Ctrl-D pour quitter."
)

HELP_TEXT = f"""\
Instructions (intensité de -{MAX_INTENSITY} à {MAX_INTENSITY}, durée en secondes) :
  forward(intensité, durée)     avancer (intensité négative : reculer)
  translate(intensité, durée)   translation latérale
  rotate(intensité, durée)      rotation sur place
  sleep(durée)                  pause
Console : help(), exit() ou Ctrl-D pour quitter, Ctrl-C pour interrompre un mouvement.
Un # démarre un commentaire."""

_EXIT_COMMANDS = frozenset({"exit", "quit", "exit()", "quit()"})
_HELP_COMMANDS = frozenset({"help", "help()"})


def run_console(
    execute: Callable[[Sequence[Instruction]], None],
    read_line: Callable[[str], str] = input,
) -> int:
    """Boucle de lecture : exécute chaque ligne saisie ; renvoie le code de sortie."""
    _enable_line_editing()
    print(BANNER)
    while True:
        try:
            line = read_line(PROMPT)
        except EOFError:  # Ctrl-D
            print()
            return 0
        except KeyboardInterrupt:  # Ctrl-C à l'invite : on abandonne la ligne, on ne quitte pas
            print()
            continue

        command = line.strip()
        if command in _EXIT_COMMANDS:
            return 0
        if command in _HELP_COMMANDS:
            print(HELP_TEXT)
            continue
        _run_line(line, execute)


def _run_line(line: str, execute: Callable[[Sequence[Instruction]], None]) -> None:
    """Analyse et exécute une ligne ; toute erreur est affichée sans quitter la console."""
    try:
        instruction = parse_line(line)
        if instruction is not None:
            execute([instruction])
    except RobotConsoleError as error:
        print(f"erreur : {error}", file=sys.stderr)
    except OSError as error:
        print(f"erreur de connexion : {error}", file=sys.stderr)
    except KeyboardInterrupt:
        print("interrompu, robot arrêté.", file=sys.stderr)


def _enable_line_editing() -> None:
    """Importer `readline` active l'historique et l'édition de ligne pour `input()` (Unix)."""
    with contextlib.suppress(ImportError):
        import readline  # noqa: F401
