# console-pilotage-robot-autonome

Deux applications indépendantes pour piloter le robot par WiFi.

## Installation

```
uv sync
```

## Lancer

| Application | Fichier | Exemple |
|-------------|---------|---------|
| CLI | `run_cli.py` | `.venv/bin/python run_cli.py send --forward 150 2` |
| Web | `run_web.py` | `.venv/bin/python run_web.py` puis http://127.0.0.1:5000 |

Aide de la CLI : `.venv/bin/python run_cli.py -h`.

Lancée sans argument, la CLI ouvre une console rbs (comme la console Python) :

```
$ .venv/bin/python run_cli.py
>>> forward(150, 2)
>>> rotate(-100, 0.5)
>>> exit()
```
