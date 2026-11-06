from pathlib import Path

import pytest

from robot_core.errors import SettingsError
from robot_core.paths import PROJECT_ROOT
from robot_core.settings import (
    DEFAULT_SETTINGS_PATH,
    Settings,
    load_settings,
    save_settings,
    update_settings,
)


def test_default_path_is_inside_project() -> None:
    assert DEFAULT_SETTINGS_PATH.is_relative_to(PROJECT_ROOT)
    assert (PROJECT_ROOT / "pyproject.toml").exists()


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "absent.json") == Settings()


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config" / "settings.json"
    settings = Settings(host="10.0.0.5", port=8080, timeout=1.5)
    save_settings(settings, path)
    assert load_settings(path) == settings


def test_update_ignores_none_and_validates() -> None:
    updated = update_settings(Settings(), host="robot.local", port=None)
    assert updated.host == "robot.local"
    assert updated.port == Settings().port
    with pytest.raises(SettingsError):
        update_settings(Settings(), port=70000)


def test_invalid_file_raises_settings_error(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"port": 0}', encoding="utf-8")
    with pytest.raises(SettingsError):
        load_settings(path)
