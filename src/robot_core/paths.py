"""Emplacements des fichiers du projet."""

from pathlib import Path

# Racine du projet : src/robot_core/paths.py -> parents[2].
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
