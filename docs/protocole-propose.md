# Proposition de protocole WiFi PC ↔ robot

> **Statut : proposition, non implémentée.** L'outil actuel utilise encore le protocole existant
> du récepteur `WiFiClient.ino` (voir la section « Protocole actuel »).

## 1. Protocole actuel (rappel)

- TCP, port 80, IP fixe `192.168.1.3`, un seul client à la fois.
- Trame de 12 octets, sans en-tête : 3 entiers 32 bits signés big-endian
  `[avant/arrière][translation][rotation]`.
- Aucune réponse. Fermeture de la connexion après 3 s sans données.
- L'ESP8266 retransmet les 3 valeurs en `int16` little-endian au contrôleur (I2C, adresse 27).

## 2. Défauts à corriger

| # | Défaut | Conséquence |
|---|--------|-------------|
| 1 | Pas d'en-tête ni de délimiteur | Un octet perdu décale toutes les trames suivantes, sans reprise possible |
| 2 | Pas de somme de contrôle ni de validation | Une trame corrompue est transmise telle quelle aux moteurs |
| 3 | Aucune réponse du robot | Le PC ne sait pas si l'ordre est reçu ni exécuté |
| 4 | Pas d'arrêt de sécurité côté ESP | Si le lien coupe, la dernière commande peut rester active (selon le contrôleur, non vérifié) |
| 5 | Pas d'authentification | Tout client du réseau peut piloter le robot |
| 6 | Code de décodage trompeur (`decode_int16`), mot de passe WiFi en dur, `delay(50)` dans la boucle | Maintenabilité et réactivité réduites |
| 7 | Endianness différente entre TCP (big) et I2C (little) | Risque d'erreur |

## 3. Protocole proposé

On garde **TCP** (fiable, ordonné, simple sur ESP8266). On change le format des messages et
le comportement de sécurité.

### 3.1 Format d'un message

Tous les entiers sont **big-endian**.

```
offset  taille  champ
0       2       en-tête fixe : 0xAA 0x55
2       1       version du protocole (1)
3       1       type de message
4       1       numéro de séquence (0-255, incrémenté à chaque message du PC)
5       1       longueur de la charge utile (N)
6       N       charge utile
6+N     2       CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) sur les octets 2 à 5+N
```

La longueur explicite permet de faire évoluer les types de messages sans casser l'analyse.

### 3.2 Types de messages

Du PC vers le robot :

| Type | Nom | Charge utile |
|------|-----|--------------|
| `0x01` | MOVE | 3 × `int16` : avant/arrière, translation, rotation (6 octets) |
| `0x02` | STOP | vide : arrêt immédiat |
| `0x03` | PING | vide |

Du robot vers le PC :

| Type | Nom | Charge utile |
|------|-----|--------------|
| `0x81` | ACK | vide ; la séquence reprend celle du message acquitté |
| `0x82` | NACK | 1 octet de code d'erreur (voir 3.4) |
| `0x83` | PONG | vide |

Exemple, MOVE avant = 100, séquence 7 :

```
AA 55 | 01 | 01 | 07 | 06 | 00 64 00 00 00 00 | CRC16
```

Soit 14 octets au total pour un MOVE.

### 3.3 Comportement du récepteur (ESP8266)

1. **Synchronisation** : lire les octets jusqu'à trouver `AA 55`, puis lire l'en-tête et la
   longueur, puis la charge utile et le CRC.
2. **Validation** : si le CRC, la version ou le type est invalide, rejeter le message, répondre
   NACK et reprendre la recherche de `AA 55` à l'octet suivant l'en-tête rejeté.
3. **Exécution** : transmettre MOVE/STOP au contrôleur par I2C, puis répondre ACK.
4. **Watchdog** : si aucun message valide n'est reçu pendant **300 ms** (valeur à ajuster),
   envoyer `(0, 0, 0)` au contrôleur. Le PC doit donc renvoyer MOVE en continu
   (toutes les 100 ms environ) tant qu'une commande est active.
5. **Perte de connexion** : à la fermeture de la connexion TCP, envoyer aussi `(0, 0, 0)`.
6. **Bornes** : borner les valeurs reçues à la plage acceptée par le contrôleur
   (±255 à confirmer) et répondre NACK au-delà.

### 3.4 Codes d'erreur NACK

| Code | Signification |
|------|---------------|
| `0x01` | CRC invalide |
| `0x02` | Version non supportée |
| `0x03` | Type de message inconnu |
| `0x04` | Valeur hors limites |
| `0x05` | Longueur de charge utile incorrecte |

### 3.5 Comportement du client (PC)

- Envoie MOVE toutes les ~100 ms pendant la durée d'une instruction, puis STOP.
- Compare le numéro de séquence des ACK/NACK reçus ; signale une erreur si les ACK cessent ou
  si un NACK arrive.
- Envoie STOP à la sortie, y compris sur erreur ou Ctrl-C (comme aujourd'hui).

## 4. Sécurité d'accès

À décider, par ordre de simplicité croissante :
- sortir le mot de passe WiFi du code source (fichier de configuration non versionné) ;
- accepter uniquement l'adresse IP du PC de pilotage ;
- ajouter un jeton partagé en début de connexion.

## 5. Alternatives écartées

- **UDP** : envoi continu sans connexion, adapté avec watchdog, mais impose de gérer pertes et
  réordonnancements ; TCP suffit ici.
- **HTTP/JSON ou WebSocket** : plus lisible, mais plus lourd pour un ESP8266, sans bénéfice ici.

## 6. Points à valider avant implémentation

- Comportement du contrôleur I2C quand plus aucune trame n'arrive (code non consulté).
- Plage réelle d'intensité acceptée (±255 supposé).
- Sens exact des trois valeurs (avant/arrière, translation, rotation, d'après les commentaires
  `wheelSpeed`, `wheelAngle`, `wheelRotation`).
- Le firmware de l'ESP8266 appartient à un autre dépôt : sa modification doit être convenue
  avec son propriétaire.

## 7. Impact sur la console

Seul `src/robot_console/protocol.py` (encodage) et `client.py` (cadence, lecture des ACK)
changeraient ; la CLI, les instructions et le langage `.rbs` restent identiques.
