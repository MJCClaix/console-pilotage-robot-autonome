"""Instructions de pilotage du robot, indépendantes de l'interface."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from robot_core.errors import InstructionError, describe_validation_error

# À vérifier côté contrôleur moteur : le récepteur WiFi accepte jusqu'à
# +/-32767, mais l'intensité attendue par le robot serait de +/-255.
MAX_INTENSITY = 255


class Axis(StrEnum):
    """Axes de déplacement du robot (la valeur est le nom utilisé en CLI et en script)."""

    FORWARD = "forward"
    TRANSLATION = "translate"
    ROTATION = "rotate"


class Move(BaseModel):
    """Déplacement sur un axe, à une intensité donnée, pendant une durée (secondes)."""

    model_config = ConfigDict(frozen=True)

    axis: Axis
    intensity: int = Field(ge=-MAX_INTENSITY, le=MAX_INTENSITY)
    duration: float = Field(ge=0, allow_inf_nan=False)


class Sleep(BaseModel):
    """Pause (secondes) pendant laquelle le robot est à l'arrêt."""

    model_config = ConfigDict(frozen=True)

    duration: float = Field(ge=0, allow_inf_nan=False)


Instruction = Move | Sleep


def parse_move(axis: Axis, intensity_text: str, duration_text: str) -> Move:
    """Construit un `Move` à partir de textes (arguments CLI ou script)."""
    try:
        return Move(
            axis=axis,
            intensity=_to_int(intensity_text, "intensité"),
            duration=_to_float(duration_text, "durée"),
        )
    except ValidationError as error:
        raise InstructionError(describe_validation_error(error)) from error


def parse_sleep(duration_text: str) -> Sleep:
    """Construit un `Sleep` à partir d'un texte (script)."""
    try:
        return Sleep(duration=_to_float(duration_text, "durée"))
    except ValidationError as error:
        raise InstructionError(describe_validation_error(error)) from error


def _to_int(text: str, label: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise InstructionError(f"{label} invalide : {text!r} (entier attendu)") from None


def _to_float(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise InstructionError(f"{label} invalide : {text!r} (nombre attendu)") from None
