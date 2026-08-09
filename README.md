# SONGVERK

Song mode externe pour Elektron Tonverk, en Web MIDI. Vanilla JS, aucune dépendance, aucune étape de build.
Pensé pour le téléphone en vertical, avec USB OTG. Un fichier JSON par song, versionnable.

## Lancer

Web MIDI exige un contexte sécurisé : `file://` ne marchera pas, il faut du HTTPS ou `localhost`.

```bash
# en local
python3 -m http.server 8080     # puis http://localhost:8080
```

En déploiement, GitHub Pages suffit (HTTPS fourni). Sur le téléphone : Chrome → menu → « Ajouter à l'écran d'accueil ».
Le service worker met tout en cache, l'app démarre ensuite hors ligne.

## Réglages côté Tonverk

Dans MIDI CONFIG :

- SYNC : `PROGRAM CHANGE RECEIVE` activé. `CLOCK RECEIVE` et `TRANSPORT RECEIVE` activés si l'app est master.
- CHANNELS : noter le canal `PROGRAM CHANGE IN` et le reporter dans les réglages de l'app.
- Les mutes passent par CC 94 sur le canal de chaque track (OS 1.3 ou plus récent). Les canaux de tracks se règlent dans l'app.

## Calibration du PC lead

Le Tonverk applique un Program Change à la frontière de pattern suivante, donc le PC doit partir **avant** la fin de la row.
`PC lead` par défaut : 150 ms. `CC offset` décale l'automation par rapport aux notes, en positif comme en négatif.

### Lead auto

La machine émet un Program Change au début de chaque nouveau pattern. Active `PROGRAM CHANGE SEND` dans
MIDI CONFIG et branche aussi sa sortie MIDI vers l'entrée du téléphone : l'app se sert de ces retours comme
boucle de mesure et n'a plus besoin d'être réglée à la main.

Pour chaque PC envoyé, l'app note la frontière visée, puis classe le retour :

| Retour | Interprétation | Action |
|---|---|---|
| moins de 80 ms après l'envoi | renvoi thru, la frontière n'est pas passée | mesure l'aller-retour |
| à moins d'une croche de la frontière | le changement a eu lieu au bon endroit | compte un succès |
| plus d'une demi-pattern après | le changement a sauté une pattern | `lead += 60 ms` |

Après huit changements à l'heure, le lead redescend de 15 ms, jusqu'à un plancher calculé
(trois fois la gigue mesurée, plus un demi-tick, plus 20 ms, jamais sous 40 ms). Le réglage converge donc
tout seul vers la plus petite anticipation qui tient, sans session de calibration dédiée.

Le bloc de mesures dans les réglages affiche en continu la gigue de l'horloge entrante, l'aller-retour,
le dernier écart de frontière et le nombre de retours reçus. Zéro retour veut dire que
`PROGRAM CHANGE SEND` est coupé ou que la sortie de la machine n'est pas branchée.

## Synchro entre plusieurs machines

Trois modes, dans la feuille Songs.

**Appareil seulement** — rien ne sort du téléphone. C'est le défaut.

**Serveur de l'app** — les songs sont stockées à côté de l'app, dans un namespace KV Cloudflare.
Aucun jeton à coller : c'est Cloudflare Access qui garde la porte. Mise en place :

1. Déployer le dossier sur Cloudflare Pages, la fonction `functions/api/[[route]].js` est reprise automatiquement.
2. Workers & Pages → KV → créer un namespace, par exemple `songverk`.
3. Dans le projet Pages → Settings → Functions → KV namespace bindings → nom de variable `SONGVERK`.
4. Zero Trust → Access → Applications → protéger le domaine avec un accès par email.

**Dépôt GitHub** — chaque envoi écrit `songs/<id>.json` et fait un commit, donc l'historique git complet
en plus de l'historique local. Il faut un jeton fine-grained limité au seul dépôt de données,
avec la permission Contents en lecture et écriture. Le jeton reste sur l'appareil.

### Fusion

`updatedAt` tranche, dernier écrit gagnant, dans les deux sens :

- song présente à distance mais pas ici → téléchargée
- distante plus récente → téléchargée, après une version automatique de la locale
- locale plus récente ou absente à distance → envoyée

`updatedAt` ne bouge que si le contenu change vraiment. Une signature du nom, de la fin de song et des rows
est comparée à chaque sauvegarde, sinon un simple réglage suffirait à faire gagner la copie locale à tort.
Les songs venues du réseau sont scellées à la réception pour ne pas être réhorodatées dans la foulée.

## Versions

Chaque song a un historique local : bouton **Enregistrer une version** avec une étiquette libre,
liste datée, restauration en un geste. Les 40 dernières sont gardées, rognées à 2 Mo.
Une version est prise automatiquement avant tout import et avant toute restauration, donc rien n'est perdu
par accident. C'est indépendant de l'export JSON, qui reste la voie vers git.

## Horloge

- **App master** : l'app génère l'horloge et le transport. Le tempo par row devient possible.
  Le scheduler travaille avec une fenêtre d'anticipation de 160 ms et envoie tout en `send(data, timestamp)`,
  donc la livraison est gérée par le navigateur et non par JavaScript, ce qui la met à l'abri du garbage collector.
- **Tonverk master** : l'app suit l'horloge entrante, estime la période par moyenne glissante et anticipe les frontières.
  Le tempo par row est ignoré dans ce mode.

## Automation

Chaque row porte autant de lanes que voulu. Une lane, c'est un track, un paramètre et une courbe dessinée sur la durée de la row.

- Crayon, ligne, points ; générateurs rampe, triangle, sinus, paliers, aléatoire ; inversion horizontale et verticale.
- Interpolation linéaire, lissée ou par paliers.
- CC 7 bits et NRPN 14 bits, envoyés uniquement quand la valeur change.
- `Résolution` fixe l'intervalle d'envoi en ticks. Un NRPN coûte quatre messages par valeur : rester large si beaucoup de lanes tournent en même temps.

## Base de paramètres

Les 896 paramètres Tonverk (474 CC, 422 NRPN, 52 sections) sont **intégrés dans `index.html`**,
dans la balise `<script type="application/json" id="paramdb">`. Aucun fichier annexe, aucun réseau.
Base générée depuis `Elektron/Tonverk.csv` du dépôt
[pencilresearch/midi](https://github.com/pencilresearch/midi).

Les noms de paramètres sont génériques dans la doc MIDI d'Elektron (« FX 1: Decay »), c'est la section
qui dit de quelle machine il s'agit. L'app affiche donc toujours la section à côté du nom, et le filtre
du sélecteur cherche dans les deux.

Pour passer à une version plus récente du CSV, soit le charger depuis les réglages de l'app,
soit le réinjecter dans le fichier :

```bash
python3 tools/embed.py Tonverk.csv
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | toute l'app : base de paramètres, modèle, moteur MIDI, UI, éditeur de courbes |
| `sw.js` | cache offline : HTML en réseau d'abord, reste en cache d'abord |
| `functions/api/[[route]].js` | API de synchro Cloudflare Pages, stockage KV |
| `manifest.webmanifest` | installation PWA, portrait, standalone |
| `tools/embed.py` | réinjecte la base dans `index.html` depuis le CSV |

## Format de song

```json
{
  "id": "a1b2c3d",
  "name": "hypnose",
  "end": "loop",
  "rows": [{
    "bank": 0, "slot": 0, "len": 16, "rep": 4, "bpm": 130,
    "label": "intro",
    "mutes": [false, true, "…"],
    "jump": { "mode": "afterN", "target": 3, "n": 2 },
    "lanes": [{
      "track": 0, "key": "c95", "interp": "lin", "res": 3, "on": true,
      "pts": [{ "x": 0, "y": 0 }, { "x": 1, "y": 0.75 }]
    }]
  }]
}
```

`x` va de 0 à 1 sur la durée de la row, `y` de 0 à 1 sur la plage du paramètre. Les valeurs restent donc
justes même si le paramètre de la lane change.

## Parti pris visuel et mouvement

Registre proche des machines Elektron : noir profond, blanc franc, capitales à fort interlettrage pour les
micro-labels, chiffres tabulaires partout. La typo est une pile système, pas la fonte propriétaire d'Elektron,
qui est sous licence.

**La couleur ne décore rien, elle dit le temps.**

| Couleur | Signification, et rien d'autre |
|---|---|
| Ambre | c'est maintenant : row en lecture, playhead, valeur envoyée |
| Vert | c'est la suite : row en file d'attente, `hold`, mutes audibles |
| Rouge | quelque chose manque : pas de sortie MIDI |
| Gris | tout le reste |

D'où la lecture au premier coup d'œil : une seule chose est ambre à l'écran à un instant donné.

**Mouvement** (jetons `--t-fast` 120 ms, `--t-base` 220 ms, `--t-sheet` 300 ms, sortie 180 ms,
entrée en `cubic-bezier(.2,0,0,1)`). Les durées suivent les fourchettes usuelles : sous 100 ms le mouvement
n'est pas perçu, au-delà de 500 ms il traîne.

- Playhead interpolé entre les ticks, donc fluide au rafraîchissement de l'écran et pas par paliers de 19 ms.
- Arête gauche de la row en lecture qui s'allume sur chaque temps et retombe en courbe cubique : le tempo se
  lit sans regarder un chiffre. C'est le retour immédiat dont dépend l'état de flow.
- Row en file d'attente : liseré vert qui respire en 1,6 s.
- Feuilles : translation de 14 px et fondu, avec flou du fond ; le contenu suit à 22 ms d'écart, six éléments au plus.
- `PLAY` et `STOP` échangent leur libellé par un glissement vertical de 120 ms, sans clignotement.
- `prefers-reduced-motion` coupe tout le mouvement décoratif et garde le playhead, qui est une information.

**Un point de justesse plutôt que d'esthétique** : le scheduler travaille jusqu'à 160 ms en avance. Le playhead
rejoue donc une piste horodatée plutôt que la position planifiée, sinon il affichait le futur.

## Responsive

Vérifié au rendu réel (Chromium headless) à 320, 360 et 412 px de large, sur les six écrans de l'app :
aucun débordement horizontal, aucun texte coupé sans ellipsis, aucune cible tactile sous 32 px.
`tools/audit.py` rejoue ce contrôle après chaque modification de l'interface.

```bash
python3 tools/audit.py          # rapport + captures dans shots/
```

## Reste à faire

- Transpose de pattern par row, si un jour la machine l'expose en MIDI.
- Lecture des lanes en mode legato entre deux rows qui partagent le même paramètre.
- Undo.
