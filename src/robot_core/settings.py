"""Réglages de connexion au robot, persistés dans un fichier JSON du projet."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from robot_core.errors import SettingsError, describe_validation_error
from robot_core.paths import CONFIG_DIR

DEFAULT_HOST = "192.168.1.3"
DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 3.0

DEFAULT_SETTINGS_PATH = CONFIG_DIR / "settings.json"


class Settings(BaseModel):
    """Paramètres de connexion TCP au robot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(default=DEFAULT_HOST, min_length=1)
    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0, allow_inf_nan=False)


def update_settings(current: Settings, **changes: Any) -> Settings:
    """Renvoie de nouveaux réglages validés ; les valeurs `None` sont ignorées."""
    values = current.model_dump()
    values.update({key: value for key, value in changes.items() if value is not None})
    try:
        return Settings.model_validate(values)
    except ValidationError as error:
        raise SettingsError(describe_validation_error(error)) from error


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> Settings:
    """Charge les réglages ; renvoie les valeurs par défaut si le fichier n'existe pas."""
    if not path.exists():
        return Settings()
    try:
        return Settings.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SettingsError(f"lecture impossible ({path}) : {error}") from error
    except ValidationError as error:
        raise SettingsError(
            f"réglages invalides ({path}) : {describe_validation_error(error)}"
        ) from error


def save_settings(settings: Settings, path: Path = DEFAULT_SETTINGS_PATH) -> None:
    """Enregistre les réglages, en créant le dossier si nécessaire."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    except OSError as error:
        raise SettingsError(f"écriture impossible ({path}) : {error}") from error
