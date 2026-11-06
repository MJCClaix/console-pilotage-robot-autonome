# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commandes

- Installer : `uv sync` (venv `.venv`, Python 3.14)
- Tests : `.venv/bin/python -m pytest` ; un seul test : `.venv/bin/python -m pytest tests/test_script.py::test_errors_report_line_number`
- CLI : `.venv/bin/robot-console {send,file,settings}` (`send --forward I D --translate I D --rotate I D`, `file script.rbs`, `settings --host --port --timeout`)

## Architecture (`src/robot_console/`)

Logique séparée de la CLI : `cli.py` ne fait que l'analyse d'arguments.
- `instructions.py` : modèles pydantic `Move` / `Sleep` (frozen), `Axis` en `StrEnum`, validation (intensité ±255 à vérifier côté robot).
- `protocol.py` : trame de 12 octets = 3 entiers 32 bits signés big-endian `[avant/arrière][translation][rotation]` (récepteur ESP8266, TCP, défaut 192.168.1.3:80).
- `client.py` : `RobotClient` ; renvoie la trame toutes les 0,5 s (le récepteur coupe après 3 s sans données) et envoie une trame d'arrêt en sortie.
- `script.py` : langage `.rbs` (`forward/translate/rotate(intensité, durée)`, `sleep(durée)`, `#` commentaires).
- `settings.py` : modèle pydantic `Settings`, persisté dans `config/settings.json` à la racine du projet.

## Conventions

- Répondre en français.
- Python : pas d'interpréteur système ; utiliser l'interpréteur d'un venv local (jamais `python`/`pip` du système).
- Se référer à la documentation officielle des bibliothèques ; ne pas inventer d'API.
