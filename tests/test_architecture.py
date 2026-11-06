"""Vérifie l'indépendance des applications : core <- cli, core <- web, jamais cli <-> web."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
ALLOWED = {
    "robot_core": set(),
    "robot_cli": {"robot_core"},
    "robot_web": {"robot_core"},
}


def _imported_packages(package: str) -> set[str]:
    imported: set[str] = set()
    for path in (SRC / package).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
    return {name for name in imported if name.startswith("robot_") and name != package}


@pytest.mark.parametrize("package", ALLOWED)
def test_package_only_imports_allowed_packages(package: str) -> None:
    assert _imported_packages(package) <= ALLOWED[package]
