# TODO

## Bugs connus

- **Arrêt impossible sous Windows pour les commandes lancées depuis le terminal web.**
  `src/robot_web/terminal.py` interrompt `send` et `file` avec `send_signal(SIGINT)`,
  signal non supporté sous Windows. Le bouton Arrêt ne stoppe donc pas le robot dans ce cas.
  Le test `test_terminal_driving_command_is_refused_while_busy_and_can_be_stopped` échoue sous Windows.
  Piste : exécuter `send` et `file` dans le processus de l'interface web avec le contrôleur
  (`controller.run` / événement d'annulation), et déplacer la conversion `send` → instructions dans `robot_core`.

- **Commandes de plus de ~3 s non arrêtables tant que le firmware de l'ESP coupe la connexion.**
  Le récepteur ferme la connexion après 3 s sans donnée. Le firmware doit être modifié
  pour ne plus fermer la connexion (en cours côté ESP).

## Fonctionnalités à prévoir

- Paramètre `repeat` absent de la syntaxe `.rbs` (seul `send --repeat` et le champ « Envois » existent).
- Définir la plage d'intensité réelle attendue par le contrôleur moteur (±255 supposé).
