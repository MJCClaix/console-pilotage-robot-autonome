"""Stockage des scripts `.rbs` dans un dossier du projet."""

import re
from pathlib import Path

from robot_core.errors import ScriptError
from robot_core.paths import SCRIPTS_DIR
from robot_core.script import SCRIPT_EXTENSION, parse_script

# Nom restreint : empêche toute sortie du dossier (pas de "/" ni de "..").
_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


class ScriptNotFoundError(ScriptError):
    """Le script demandé n'existe pas."""


class ScriptStore:
    """Liste, lit, écrit et supprime des scripts par leur nom (sans extension)."""

    def __init__(self, directory: Path = SCRIPTS_DIR) -> None:
        self._directory = directory

    def names(self) -> list[str]:
        """Noms des scripts disponibles, triés."""
        if not self._directory.is_dir():
            return []
        return sorted(
            path.stem
            for path in self._directory.glob(f"*{SCRIPT_EXTENSION}")
            if _NAME_PATTERN.fullmatch(path.stem)
        )

    def read(self, name: str) -> str:
        """Contenu d'un script."""
        path = self._path(name)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise ScriptNotFoundError(f"script introuvable : {name}") from None
        except OSError as error:
            raise ScriptError(f"lecture impossible ({name}) : {error}") from error

    def write(self, name: str, content: str) -> None:
        """Enregistre un script après avoir vérifié sa syntaxe."""
        path = self._path(name)
        parse_script(content)
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
        except OSError as error:
            raise ScriptError(f"écriture impossible ({name}) : {error}") from error

    def delete(self, name: str) -> None:
        """Supprime un script."""
        path = self._path(name)
        try:
            path.unlink()
        except FileNotFoundError:
            raise ScriptNotFoundError(f"script introuvable : {name}") from None
        except OSError as error:
            raise ScriptError(f"suppression impossible ({name}) : {error}") from error

    def _path(self, name: str) -> Path:
        if not _NAME_PATTERN.fullmatch(name):
            raise ScriptError(
                f"nom de script invalide : {name!r} "
                "(1 à 64 lettres, chiffres, '-' ou '_')"
            )
        return self._directory / f"{name}{SCRIPT_EXTENSION}"
