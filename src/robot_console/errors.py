"""Exceptions propres à la console de pilotage."""

from pydantic import ValidationError


class RobotConsoleError(Exception):
    """Erreur de base de la console, affichable telle quelle à l'utilisateur."""


class InstructionError(RobotConsoleError):
    """Instruction invalide (valeur hors limites, format incorrect)."""


class ScriptError(RobotConsoleError):
    """Erreur de syntaxe dans un fichier de script."""


class SettingsError(RobotConsoleError):
    """Réglages de connexion illisibles ou invalides."""


def describe_validation_error(error: ValidationError) -> str:
    """Résume une erreur de validation pydantic en une phrase lisible."""
    return "; ".join(
        f"{'.'.join(map(str, detail['loc']))} : {detail['msg']}"
        for detail in error.errors()
    )
