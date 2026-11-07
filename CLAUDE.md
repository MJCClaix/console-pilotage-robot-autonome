# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commandes

- Installer : `uv sync` (venv `.venv`, Python 3.14)
- Tests : `.venv/bin/python -m pytest` ; un seul test : `.venv/bin/python -m pytest tests/test_script.py::test_errors_report_line_number`
- Application CLI : `.venv/bin/python run_cli.py {send,file,settings}` (`send --forward I D --translate I D --rotate I D`, `file script.rbs`, `settings --host --port --timeout`) ; sans argument : console interactive rbs (`>>>`)
- Application web : `.venv/bin/python run_web.py [--port 5000]` (écoute uniquement sur 127.0.0.1)

Il n'y a que ces deux lanceurs (`run_cli.py`, `run_web.py`, à la racine) : pas de scripts `robot-*` ni de `python -m`.

## Architecture (`src/`)

Trois paquets : une bibliothèque partagée et deux applications **indépendantes**. Règle : `robot_cli` et `robot_web` importent `robot_core`, jamais l'un l'autre (vérifié par `tests/test_architecture.py`).

### `robot_core/` — bibliothèque partagée
- `instructions.py` : modèles pydantic `Move` / `Sleep` (frozen), `Axis` en `StrEnum`, validation (intensité ±255 à vérifier côté robot).
- `protocol.py` : trame de 12 octets = 3 entiers 32 bits signés big-endian `[avant/arrière][translation][rotation]` (récepteur ESP8266, TCP, défaut 192.168.1.3:80).
- `client.py` : `RobotClient` ; renvoie la trame toutes les 0,5 s (le récepteur coupe après 3 s sans données) et envoie une trame d'arrêt en sortie. Interruptible via un `threading.Event` (`cancel`).
- `script.py` : langage `.rbs` (`forward/translate/rotate(intensité, durée)`, `sleep(durée)`, `#` commentaires).
- `settings.py` : modèle pydantic `Settings`, persisté dans `config/settings.json` à la racine du projet.
- `paths.py` : racine du projet, `config/`, `scripts/`. `errors.py` : exceptions.

### `robot_cli/` — application CLI
- `cli.py` : analyse des arguments (`send`, `file`, `settings`) et exécution synchrone. `main()` est appelé par `run_cli.py` ; sans argument il lance la console rbs.
- `repl.py` : console interactive rbs (`run_console`), une instruction `.rbs` par ligne (`parse_line`), `help()`, `exit()`/Ctrl-D ; connexion ouverte à chaque instruction (le récepteur coupe après 3 s d'inactivité) ; erreurs affichées sans quitter, Ctrl-C interrompt le mouvement.

### `robot_web/` — application web (Flask)
- `app.py` : `create_app()`, API JSON (`/api/status|stop|send|script/*|scripts|settings|terminal`). Refuse les hôtes non locaux (403) et les requêtes POST/PUT/DELETE non-JSON (415) : le robot est physique, ne pas affaiblir ces garde-fous. `main()` est appelé par `run_web.py`.
- `controller.py` : `RobotController`, une seule exécution à la fois (`BusyError` sinon) : en thread (`run`) ou réservée par l'appelant (`exclusive`) ; `stop()`, état `RunStatus`.
- `script_store.py` : scripts enregistrés dans `scripts/*.rbs` (noms restreints à `[A-Za-z0-9_-]`).
- `terminal.py` : terminal de la page. Lance le vrai `run_cli.py` en sous-processus (sortie renvoyée telle quelle) ; aucune connaissance de la grammaire de la CLI, sauf `DRIVING_COMMANDS = {send, file}` qui réservent le robot via `controller.exclusive()`. L'arrêt envoie SIGINT (la CLI envoie alors la trame d'arrêt), SIGKILL en dernier recours.
- `templates/index.html`, `static/app.css`, `static/app.js` : page unique, sans dépendance front.

## Conventions

- Répondre en français.
- Python : pas d'interpréteur système ; utiliser l'interpréteur d'un venv local (jamais `python`/`pip` du système).
- Se référer à la documentation officielle des bibliothèques ; ne pas inventer d'API.
