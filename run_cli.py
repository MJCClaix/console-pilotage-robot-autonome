"""Lanceur de l'application CLI.

Usage (depuis la racine du projet) :
    .venv/bin/python run_cli.py send --forward 150 2
    .venv/bin/python run_cli.py file scripts/demo.rbs
    .venv/bin/python run_cli.py settings --host 192.168.1.3
    .venv/bin/python run_cli.py -h
"""

import signal
import sys

from robot_cli.cli import main

if __name__ == "__main__":
    # Un parent qui ignore SIGINT (ex. processus lancé en arrière-plan) se transmettrait ici :
    # on rétablit Ctrl-C pour que l'interruption arrête proprement le robot.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    sys.exit(main())
