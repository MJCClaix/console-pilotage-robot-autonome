# Console de pilotage (CLI) : guide d'utilisation

La console de pilotage envoie des instructions de déplacement au robot par WiFi. Elle a quatre commandes : `send`, `file`, `settings` et `web`. Sans argument, elle ouvre une console interactive dans le langage rbs.

## Lancer la console

### Version installée (Windows)

Après installation avec `robot-console-setup.exe`, la commande `console-pilotage` est disponible dans tout nouveau terminal :

```
console-pilotage -h
```

### Depuis les sources (développement)

Depuis la racine du projet, avec le venv du projet :

```
.venv/bin/python run_cli.py -h
```

> L'aide affiche le nom de programme `robot-console`, qui désigne la même application.

## Vue d'ensemble

| Commande | Rôle |
|---|---|
| `send` | envoyer un ou plusieurs déplacements directement |
| `file` | exécuter un script `.rbs` |
| `settings` | afficher ou modifier la connexion au robot |
| `web` | démarrer l'interface web et l'ouvrir dans le navigateur |
| *(aucune)* | ouvrir la console interactive rbs |

Codes de sortie : `0` en cas de succès, `1` en cas d'erreur (instruction invalide, réglages invalides, connexion impossible), `2` pour une mauvaise syntaxe de commande, `130` si la commande a été interrompue avec Ctrl-C.

## Les déplacements

Un déplacement se définit par trois éléments :

- l'**axe** : `forward` (avancer), `translate` (translation latérale) ou `rotate` (rotation sur place) ;
- l'**intensité** : un entier de `-255` à `255`. Une valeur négative inverse le sens (`forward(-150, 2)` recule) ;
- la **durée** : un nombre de secondes, positif ou nul (`2`, `1.5`). Une durée de `0` n'envoie rien.

Une **pause** s'écrit `sleep(durée)`. Pendant la pause, le robot est à l'arrêt.

Les intensités décimales (`150.5`) sont refusées, car le robot attend des entiers.

## `send` : envoyer des déplacements

```
console-pilotage send --forward 150 2
console-pilotage send --rotate -100 0.5
console-pilotage send --forward 150 2 --translate -120 1.5 --rotate 100 1
```

Options (au moins une est obligatoire, chacune prend l'intensité puis la durée) :

| Option | Axe |
|---|---|
| `--forward INTENSITE DUREE` | avancer / reculer |
| `--translate INTENSITE DUREE` | translation latérale |
| `--rotate INTENSITE DUREE` | rotation sur place |

Si plusieurs options sont données, les mouvements s'enchaînent dans l'ordre : `forward`, puis `translate`, puis `rotate`, quel que soit l'ordre de la ligne de commande.

## `file` : exécuter un script

```
console-pilotage file examples\demo.rbs
console-pilotage file C:\chemin\vers\mon_parcours.rbs
```

Le chemin est relatif au dossier courant, ou absolu. L'extension attendue est `.rbs`, mais elle n'est pas vérifiée.

Le script est entièrement analysé avant le départ : une erreur de syntaxe n'envoie aucun mouvement au robot, et le message indique le numéro de ligne.

### Langage `.rbs`

Une instruction par ligne. Les lignes vides sont ignorées. Le caractère `#` démarre un commentaire jusqu'à la fin de la ligne.

```
# Exemple de script de pilotage
forward(150, 2.0)    # avance pendant 2 s
sleep(0.5)
rotate(100, 1.0)
translate(-120, 1.5)
forward(-150, 2.0)   # recule
```

| Instruction | Effet |
|---|---|
| `forward(intensité, durée)` | avancer (intensité négative : reculer) |
| `translate(intensité, durée)` | translation latérale |
| `rotate(intensité, durée)` | rotation sur place |
| `sleep(durée)` | pause |

Les instructions sont exécutées dans l'ordre du fichier. Chaque instruction attend la fin de sa durée avant de passer à la suivante.

## `settings` : connexion au robot

```
console-pilotage settings
console-pilotage settings --host 192.168.1.3 --port 80 --timeout 3
```

Sans option, la commande affiche les réglages actuels. Avec une ou plusieurs options, elle les enregistre. Les réglages sont stockés dans `config/settings.json`, à côté de l'exécutable ou à la racine du projet.

| Option | Défaut | Rôle |
|---|---|---|
| `--host` | `192.168.1.3` | adresse IP ou nom d'hôte du robot |
| `--port` | `80` | port TCP du robot (1 à 65535) |
| `--timeout` | `3` | délai de connexion, en secondes (strictement positif) |

Un réglage invalide est refusé et rien n'est enregistré.

## `web` : interface web

```
console-pilotage web
console-pilotage web --port 8080
```

Démarre le serveur de l'interface web sur `http://127.0.0.1:5000/` (port 5000 par défaut), et l'interface s'ouvre dans le navigateur par défaut. Le serveur reste lancé après la fermeture du terminal.

- Le serveur n'écoute que sur la machine locale (`127.0.0.1`).
- La commande refuse de démarrer si le port est déjà utilisé, et indique l'adresse de l'interface déjà lancée.
- Pour arrêter le serveur, il faut terminer son processus (il n'existe pas encore de commande d'arrêt).

## Console interactive rbs

Lancée sans argument :

```
console-pilotage
```

```
Console rbs : tape une instruction à la fois, par exemple forward(150, 2).
help() pour l'aide, exit() ou Ctrl-D pour quitter.
>>> forward(150, 2)
>>> sleep(1)
>>> rotate(-100, 0.5)
>>> exit()
```

- Chaque ligne est une instruction `.rbs`, exécutée immédiatement. Les erreurs sont affichées sans quitter la console.
- `help()` affiche l'aide des instructions.
- `web()` (ou `web`) démarre l'interface web, comme la commande `web`.
- `exit()`, `quit()` ou Ctrl-D quittent la console.
- Ctrl-C à l'invite abandonne la ligne en cours sans quitter. Pendant un mouvement, Ctrl-C arrête le robot.
- La flèche haut rappelle les lignes précédentes lorsque `readline` est disponible (Linux et WSL).

La console ne contient pas les commandes `send`, `file` ou `settings` : elle ne fait que des instructions et `web()`.

## Interruption

Pendant une commande, Ctrl-C envoie une trame d'arrêt au robot avant de quitter : le message `interrompu, robot arrêté.` s'affiche et le code de sortie est `130`.

## Connexion au robot

- La CLI ouvre une connexion TCP vers le robot à partir des réglages.
- Pendant un mouvement, la trame est renvoyée environ toutes les 0,5 s : le récepteur coupe la connexion après 3 s sans données.
- À la fin d'un mouvement, une trame d'arrêt est envoyée.

## Aide

```
console-pilotage -h
console-pilotage send -h
console-pilotage file -h
console-pilotage settings -h
console-pilotage web -h
```
