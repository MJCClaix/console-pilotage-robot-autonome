"""Emplacements des fichiers du projet."""

import sys
from pathlib import Path

# Racine du projet : src/robot_core/paths.py -> parents[2].
# Exécutable PyInstaller : config/ et scripts/ sont à côté de l'exécutable.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
