"""Construit les deux exécutables autonomes avec PyInstaller.

Usage (depuis la racine du projet, avec le venv du projet) :
    .venv/bin/python build_exes.py

Produit `dist/console-pilotage` et `dist/interface-pilotage` (suffixe `.exe` sous Windows).
Les deux exécutables doivent rester dans le même dossier : l'interface web lance
`console-pilotage` à côté d'elle, et `config/` et `scripts/` sont créés à côté d'eux.

PyInstaller ne fait pas de compilation croisée : construire sous Windows donne un `.exe`
Windows, sous Linux (WSL) un exécutable Linux.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
WEB_TEMPLATES = SRC_DIR / "robot_web" / "templates"
WEB_STATIC = SRC_DIR / "robot_web" / "static"

# Le terminal de interface-pilotage n'ouvre pas de fenêtre : interface-pilotage est compilé en mode fenêtré
# (--noconsole). console-pilotage garde sa console, elle sert à taper des commandes.
BUILDS = (
    ("console-pilotage", PROJECT_ROOT / "run_cli.py", (), False),
    (
        "interface-pilotage",
        PROJECT_ROOT / "run_web.py",
        (
            f"{WEB_TEMPLATES}{os.pathsep}robot_web/templates",
            f"{WEB_STATIC}{os.pathsep}robot_web/static",
        ),
        True,
    ),
)


def build(name: str, entry: Path, data_files: tuple[str, ...], windowed: bool) -> None:
    """Lance PyInstaller pour un point d'entrée, dans un dossier de build temporaire."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--name",
        name,
        "--paths",
        str(SRC_DIR),
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(PROJECT_ROOT / "build"),
        "--specpath",
        str(PROJECT_ROOT / "build"),
    ]
    if windowed:
        command.append("--noconsole")
    for data in data_files:
        command += ["--add-data", data]
    command.append(str(entry))
    print(f"-> {name}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    for name, entry, data_files, windowed in BUILDS:
        build(name, entry, data_files, windowed)
    shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True)
    print(f"Exécutables créés dans {DIST_DIR}")


if __name__ == "__main__":
    main()
