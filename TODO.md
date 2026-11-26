# TODO

## Bugs connus

- **Arrêt des commandes `settings`/`-h` du terminal web** : elles restent dans un sous-processus. Sans effet sur le robot, à traiter seulement si elles deviennent longues.

- **Commandes de plus de ~3 s non arrêtables tant que le firmware de l'ESP coupe la connexion.**
  Le récepteur ferme la connexion après 3 s sans donnée. Le firmware doit être modifié
  pour ne plus fermer la connexion (en cours côté ESP).

## Fonctionnalités à prévoir

- Définir la plage d'intensité réelle attendue par le contrôleur moteur (±255 supposé).
