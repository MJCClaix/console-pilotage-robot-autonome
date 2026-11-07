"""Lanceur de l'application web.

Usage (depuis la racine du projet) :
    .venv/bin/python run_web.py            # http://127.0.0.1:5000
    .venv/bin/python run_web.py --port 8080
    .venv/bin/python run_web.py --no-browser   # sans ouvrir le navigateur
"""

from robot_web.app import main

if __name__ == "__main__":
    main()
