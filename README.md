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

## Exécutables

```bash
.venv/bin/python build_exes.py
```

Crée `dist/console-pilotage` et `dist/interface-pilotage` (`.exe` sous Windows). Les deux doivent rester dans le même dossier : l'interface web lance `console-pilotage` à côté d'elle. Le dossier `dist/` n'est pas versionné. PyInstaller ne fait pas de compilation croisée : construire sous Windows pour obtenir des `.exe` Windows.

### Installeur Windows

Après `build_exes.py`, depuis PowerShell à la racine du projet :

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\robot-console.iss
```

Crée `installer\Output\robot-console-setup.exe` (non versionné). L'installation se fait par utilisateur, sans droits administrateur, dans `%LOCALAPPDATA%\Programs\RobotConsole`. L'option « Lancer la CLI du robot au démarrage de Windows » ajoute un raccourci dans le dossier Démarrage de l'utilisateur ; la CLI s'ouvre alors dans une fenêtre console (sans argument, c'est la console interactive).
