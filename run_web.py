"""Lanceur de l'application web.

Usage (depuis la racine du projet) :
    .venv/bin/python run_web.py            # http://127.0.0.1:5000
    .venv/bin/python run_web.py --port 8080
    .venv/bin/python run_web.py --no-browser   # sans ouvrir le navigateur
"""

from robot_cli.cli import run_in_process
from robot_web.app import main

if __name__ == "__main__":
    # Ce point d'entrée relie les deux applications : la CLI tourne dans le processus web.
    main(driving_runner=run_in_process)
