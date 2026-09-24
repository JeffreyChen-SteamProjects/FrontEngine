# FrontEngine

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="README_zh-TW.md">繁體中文</a> ·
  <a href="README_zh-CN.md">简体中文</a> ·
  <a href="README_ja.md">日本語</a> ·
  <a href="README_ko.md">한국어</a> ·
  <a href="README_es.md">Español</a> ·
  <strong>Français</strong> ·
  <a href="README_de.md">Deutsch</a> ·
  <a href="README_pt-BR.md">Português (BR)</a> ·
  <a href="README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**Placez n'importe quoi par-dessus votre écran — ou en dessous.**

FrontEngine est une application de superposition (overlay) pour le bureau. Vidéos, images, GIF, pages web, texte,
particules, son et un animal de compagnie animé peuvent être placés au-dessus de toutes les autres fenêtres
(traversés par les clics, si bien que ce qui se trouve dessous continue de fonctionner), ou derrière elles comme un
fond d'écran animé. Autour de cela se trouve un ensemble d'outils pour l'écran lui-même : filtres de confort visuel,
annotation de présentation, mesure et capture, masques de concentration et widgets de bureau.

[Soutenez ce projet sur Steam](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [Documentation](https://frontengine.readthedocs.io/en/latest/)
 · [Regarder une démo](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](../image/FrontEngine.png)

---

## Installation

Python **3.10+**. Windows 10/11 est la cible principale ; macOS et Linux exécutent
l'application, avec les différences de plateforme listées sous [Prise en charge des plateformes](#prise-en-charge-des-plateformes).

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

Des binaires Windows précompilés sont disponibles sur la
[page des versions](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases),
et la version Steam livre la même application avec la prise en charge du Workshop.

> **Comment sortir.** Les superpositions peuvent couvrir tout l'écran, y compris la
> propre fenêtre de FrontEngine, il existe donc deux issues de secours qui ne nécessitent pas la souris :
> `Ctrl+Shift+F12` ferme toutes les superpositions, et **F12 quitte l'application
> purement et simplement** depuis n'importe où (Windows uniquement — voir *Aide → Comment forcer la fermeture*).

---

## Ce qu'il affiche à l'écran

La barre latérale regroupe les pages selon leur usage. Cette section suit ce classement.

### À l'écran

Superpositions média. Chacune choisit son moniteur (ou s'étend sur tous), retient
l'endroit où vous l'avez glissée, et possède sa propre opacité.

- **Vidéo** — avec volume, vitesse de lecture et lecture en boucle.
- **Image** — une seule image, un dossier en diaporama, ou un **tableau de
  référence** : plusieurs images sur une même toile, chacune déplaçable, l'ensemble du tableau
  étant zoomable et déplaçable.
- **Web** — une URL ou un fichier HTML local, éventuellement interactif. Le **mode tableau de bord**
  fait défiler une liste d'URL, de sorte qu'un mur d'affichage peut faire tourner les pages avec un
  raccourci ou une minuterie.
- **GIF / WebP** — des animations à une vitesse ajustable.
- **Texte** — police, couleur, contour, alignement et un défilement (marquee), affichant soit
  une chaîne fixe, soit une **source dynamique** : horloge, date, compte à rebours, chronomètre, charge
  système, ou la météo. Les sources dynamiques prennent un gabarit `{field}`, et la page
  liste les champs offerts par chacune.
- **Son** — lecture de musique et effets WAV à faible latence.
- **Scène** — combinez plusieurs des éléments ci-dessus en une seule composition décrite par un
  document JSON que vous pouvez enregistrer et partager.
- **Particule** — un effet de particules OpenGL.

<details>
<summary>Captures d'écran (le chargement des GIF peut prendre un moment)</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](../gifs/play_gif.gif) | ![WEBP](../gifs/webp.gif) |

| Video | Website |
| --- | --- |
| ![Video](../gifs/video.gif) | ![Website](../gifs/website.gif) |

</details>

### Bureau

**Animal de compagnie de bureau** — un sprite animé qui vit sur votre bureau.

- **Sprites** — un seul GIF/WebP/PNG, ou un dossier de *pack d'animal* dont les noms
  de fichiers correspondent à des états : `walk`, `idle`, `sleep`, `climb`, `fall`, `drag` (un état
  manquant retombe sur `walk`). Un `pet.json` optionnel définit la taille, la vitesse et
  s'il peut grimper, parler ou s'asseoir sur les fenêtres.
- **Comportement** — marcher sur le sol avec la gravité (lancez-le et il rebondit),
  errer librement, ou poursuivre le curseur. Les animaux au sol grimpent aux bords de l'écran et se tiennent sur
  le bord supérieur des autres fenêtres.
- **Vie** — humeur, satiété et un niveau d'affection qui persistent entre les sessions.
  Il grandit à mesure qu'il monte de niveau, parle dans des bulles, fait la sieste quand vous êtes absent et
  vous avertit d'une batterie faible.
- **Interaction** — glissez-le, faites un clic droit pour le cloner / le nourrir / définir un rappel, et
  **déposez un fichier dessus** : une image ou un pack d'animal devient son nouvel aspect, tout le
  reste est mangé. Ce qu'il mange compte — une archive est un festin, la musique le réjouit
  plus qu'elle ne le rassasie, un document est un repas modeste, un binaire est trop dur à
  mâcher.
- **Chat (jeu du loup)** — avec deux animaux ou plus à l'écran, cochez *Jouer au chat les uns avec les autres* et
  l'un devient « le loup » : il marche vers son plus proche voisin tandis que les autres s'enfuient
  dans l'autre sens, et attraper quelqu'un lui passe le rôle.
- **Réagit au son** — l'animal palpite au rythme de la sortie de vos haut-parleurs, ou de votre
  **microphone** afin qu'il bouge pendant que vous parlez. Les deux ne lisent que le *vumètre* de sortie —
  un nombre, pas de l'audio. Les pics sont lissés par une fenêtre RMS et une
  enveloppe à attaque rapide / déclin lent afin que la pulsation respire au lieu de scintiller.
  Avec plusieurs moniteurs, chaque animal suit le point de sortie audio correspondant à son propre
  écran.
- **Minuteur de concentration** — un pomodoro sur la même page, annoncé par l'animal : il vous indique
  quand la concentration se termine et quand la pause est finie.
- **Chat (conversation)** — l'animal peut vous répondre via Claude lorsque `ANTHROPIC_API_KEY` est
  défini. Désactivé sauf si vous l'activez ; voir [Ce qui quitte la machine](#ce-qui-quitte-la-machine).

**Fond d'écran** — diffusez un dossier d'images et d'animations *sous* toutes les fenêtres.
Chaque moniteur pointe vers son propre dossier avec sa propre minuterie, mélangé ou lu
récursivement, et peut palpiter avec le niveau des haut-parleurs. Un second dossier peut prendre le relais
pendant les heures calmes.

**Widgets** — quatre éléments qui se posent sur le bureau :

- **Spectre audio** — des barres ou un anneau, des bandes espacées logarithmiquement, lissées par un
  suiveur à attaque rapide / déclin lent et des marqueurs de pic qui redescendent.
- **Lecture en cours** — la piste actuelle depuis les contrôles multimédias de Windows lorsque les
  liaisons optionnelles `winsdk` sont installées ; sinon le nom de l'application qui
  produit réellement du son.
- **Moniteur système** — CPU, mémoire, disque, batterie et débit réseau sous forme de
  petites sparklines ; cochez les lignes que vous voulez. Une moyenne masque un décrochage ; une ligne
  non. Une ligne masquée continue d'enregistrer, donc la réactiver montre ce qui
  s'est passé entre-temps.
- **Notes autocollantes** — des cartes modifiables au-dessus de toutes les fenêtres, conservant leur texte,
  leur couleur et leur position entre les sessions.

### Travail

**Concentration** — deux superpositions pour quand l'écran rivalise avec votre travail. *Assombrir
les fenêtres d'arrière-plan* ombre tout sauf la fenêtre dans laquelle vous travaillez, à
une intensité ajustable. *Couvrir une distraction* masque une bande de l'écran : la
barre des tâches, un coin de notification, un bord, ou tout l'écran. Les deux laissent passer les clics,
si bien que ce qu'elles couvrent continue de fonctionner — cela cesse simplement d'attirer votre regard.

**Soin des yeux** — pour les longues sessions devant l'écran :

- **Filtre de couleur** — sept teintes, du chaud à l'ambre et au rose jusqu'au gris, à
  une intensité ajustable.
- **Règle de lecture** — assombrit la page et laisse une bande lumineuse qui suit le
  curseur.
- **Rappel de pause** — la règle 20-20-20, avec une superposition de repos lorsque l'intervalle
  est écoulé.
- **Simulation de la vision des couleurs** — protanopie, deutéranopie, tritanopie et
  achromatopsie à une sévérité ajustable, à l'aide du modèle de Machado et al. (2009).
  Contrairement aux autres superpositions, celle-ci est opaque, car montrer ce que
  voit quelqu'un d'autre signifie repeindre l'écran plutôt que de le teinter.

**Présentation** — pour les démos, les cours et les enregistrements :

- **Annotation** — dessinez sur l'écran avec un stylo, un surligneur ou une gomme, avec
  annulation et effacement.
- **Effets de curseur** — un anneau autour du pointeur, une ondulation au clic, et un
  projecteur qui assombrit tout le reste.
- **Affichage des frappes** — montre ce que vous venez d'appuyer, et quel bouton de souris
  vous avez cliqué, pour que les spectateurs puissent suivre ; cela s'estompe après quelques secondes.
  Choisissez où se place le panneau et la taille du texte, et désactivez les clics de souris
  à part.
- **Loupe** — une vue agrandie de la zone autour du curseur.
- **Tableau blanc** — une toile infinie : glissez pour vous déplacer, faites défiler pour zoomer, enregistrez ce que
  vous avez dessiné. Les traits vivent en coordonnées de toile, donc se déplacer et zoomer les laisse
  là où ils appartiennent.
- **Figer** — épinglez l'image actuelle d'un moniteur pour pouvoir continuer à travailler
  derrière une image fixe. `Ctrl+Shift+F7` la libère, ce qui importe parce que l'image
  figée couvre le bouton qui le ferait.

**Outils** — mesure, capture et gestion des fenêtres :

- **Pipette à couleur / règle de pixels / rapporteur** — cliquez pour échantillonner ou mesurer ; le
  résultat va directement dans le presse-papiers sous `#rrggbb`, `rgb(...)`, `hsl(...)` ou
  une propriété CSS personnalisée.
- **Capture de région** — tracez une zone ; elle atterrit dans le presse-papiers, peut être enregistrée
  dans un fichier, ou **épinglée** au-dessus comme une copie flottante et zoomable.
- **Enregistrer une zone** — enregistrez une région en un GIF animé, avec la caméra
  incrustée dans le coin pour un rendu de vidéo-réaction. Plafonné à la fois par la durée
  et le nombre d'images, car chaque image est conservée en mémoire.
- **Caméra** — votre webcam dans un cercle, une boîte arrondie ou un rectangle, affichée localement
  et jamais enregistrée. Toute entrée vidéo fonctionne, y compris les cartes d'acquisition, et la
  liste des périphériques se rafraîchit sans redémarrer puisque les cartes sont généralement branchées
  alors que l'application tourne déjà.
- **Caméra virtuelle** — envoyez une région, superpositions comprises, comme une webcam que Zoom,
  Teams ou Discord peuvent sélectionner comme source vidéo. Nécessite le paquet optionnel
  `pyvirtualcam` et un pilote de caméra virtuelle (OBS en installe un) ; sans
  l'un ou l'autre, le bouton l'indique plutôt que d'échouer en silence.
- **Lire le texte** — tracez une zone pour copier le texte qu'elle contient, le traduire, ou poser
  une question à son sujet. Celui-ci envoie la sélection hors de la machine ; voir
  [Ce qui quitte la machine](#ce-qui-quitte-la-machine).
- **Épingler une fenêtre** — gardez la fenêtre d'un autre programme au-dessus, ou estompez-la, pendant que vous
  travaillez en la regardant. Seuls l'empilement et l'opacité sont touchés, jamais le contenu de la fenêtre.
- **Réplique de fenêtre** — une petite copie en direct, toujours au premier plan, d'une autre fenêtre, afin que
  vous puissiez surveiller un rendu ou une discussion pendant qu'elle est enfouie.
- **Dispositions de fenêtres** — enregistrez où se trouve chaque fenêtre et remettez-les en place plus tard.
  Les fenêtres sont appariées par titre ; celle qui n'est pas à l'écran est ignorée plutôt que
  devinée.

---

## Tout contrôler à la fois

La page **Centre de contrôle** atteint chaque superposition de chaque page, quel que soit l'onglet
qui l'a ouverte : masquer, afficher, fermer, mettre en sourdine, verrouiller, réinitialiser les positions, ajuster l'opacité par paliers, et
appliquer un **niveau de qualité** (élevé / équilibré / économie) qui plafonne la
fréquence de rafraîchissement de chaque superposition et abaisse sa résolution de rendu. Il porte aussi un fond en incrustation
chroma (chroma-key) pour OBS, un basculement *Masquer de la capture*, le panneau de journal, et **Épingler à
ce bureau** — les superpositions s'écartent lorsque vous changez de bureau virtuel et
reviennent lorsque vous revenez. Le désépinglage ramène tout ce qu'il avait rangé.

Raccourcis globaux par défaut, tous réassignables depuis **Paramètres → Raccourcis** :

| Shortcut | Action |
| --- | --- |
| `Ctrl+Shift+F12` | Fermer toutes les superpositions |
| `Ctrl+Shift+F11` / `F10` | Masquer / afficher toutes les superpositions |
| `Ctrl+Shift+F9` | Tout mettre en sourdine |
| `Ctrl+Shift+↑` / `↓` | Opacité haut / bas |
| `Ctrl+Shift+L` | Verrouiller ou déverrouiller (traversé par les clics / déplaçable) |
| `Ctrl+Shift+→` | Page suivante du tableau de bord |
| `Ctrl+Shift+F8` | Afficher la fiche des raccourcis à l'écran |
| `Ctrl+Shift+F7` | Figer / défiger l'écran |
| `Ctrl+Shift+F6` / `F5` / `F4` | Lecture/pause média, piste suivante et précédente |
| `Ctrl+Shift+F3` | Déplacer la fenêtre de premier plan vers le moniteur suivant |
| `F12` | Quitter immédiatement (Windows) |

Le transport média envoie les touches multimédias du système, il atteint donc tout lecteur qui
les écoute. Déplacer une fenêtre conserve ses proportions au lieu de la faire claquer
d'un côté à l'autre, ce que fait le propre `Win+Shift+Arrow` de Windows.

Les mêmes actions — et rien de plus — sont ce que pilotent les télécommandes :

- **Votre téléphone** (Paramètres → Télécommande) — FrontEngine sert une petite page sur
  votre réseau local ; ouvrez le lien sur un téléphone et les boutons pilotent ces
  actions.
- **Un contrôleur MIDI** — appuyez sur *Apprendre*, bougez un potentiomètre ou un pad, et associez-le. Il utilise
  le winmm intégré de Windows, donc aucun paquet supplémentaire n'est nécessaire. Un potentiomètre se déclenche une fois qu'il
  atteint le sommet plutôt que de façon répétée en chemin, et relâcher un pad ne
  compte pas comme une seconde pression.

---

## Préréglages et automatisation

Les **Préréglages** capturent les réglages de chaque page d'un seul coup. Enregistrez, chargez, supprimez,
exportez et importez-les depuis le menu **Préréglages**, appliquez-en un au lancement, ou
restaurez automatiquement la session précédente. Un préréglage peut être exporté comme un
**paquet** — un zip transportant les médias qu'il référence — afin qu'il s'ouvre sur une machine
qui ne possède pas ces fichiers.

Des choses qui décident ensuite d'elles-mêmes, toutes depuis le menu **Paramètres**. La pause
intelligente est la seule qui démarre activée ; tout le reste est désactivé jusqu'à ce que vous
l'activiez.

| | |
| --- | --- |
| **Règles** | *« Quand ces conditions sont réunies, fais ceci. »* Combinez un jour de la semaine, une plage horaire et l'application qui a le focus, puis appliquez un préréglage, masquez/affichez/fermez les superpositions, ou réglez la qualité. Une condition vide signifie « n'importe », et une règle s'exécute **une fois** lorsque ses conditions commencent à être réunies plutôt que de façon répétée tant qu'elles le sont. C'est le seul endroit où les conditions se composent ; les lignes ci-dessous ne connaissent chacune qu'un seul type. |
| **Pause intelligente** | Mettez les superpositions au repos pendant qu'une application plein écran tourne, pendant que la machine est sur batterie, ou pendant qu'une application nommée a le focus. *(Activée par défaut, pour la règle plein écran.)* |
| **Profils d'application** | Appliquer un préréglage lorsque vous passez à une application donnée. |
| **Planification de préréglages** | Appliquer un préréglage certains jours de la semaine à une heure définie. |
| **Planification de thème** | Basculer entre un thème de jour et un thème de nuit selon l'horloge. |
| **Mode affichage** | Faire tourner une liste de préréglages sur une minuterie avec la fenêtre principale rangée, pour une machine laissée en marche comme écran d'affichage. |
| **Écran de veille** | Après un seuil d'inactivité, faire apparaître la vidéo / l'image / le GIF / les particules / la page web que vous avez choisie, et la retirer quand vous revenez. |
| **Rappels** | Toutes les N minutes, ou une fois par jour à une heure définie, affichés comme une notification qui se ferme d'elle-même. |
| **Garder éveillé** | Empêcher l'écran de se mettre en veille tant que des superpositions sont actives. |
| **Démarrer avec le système** | Lancer à la connexion. |
| **Temps d'écran** | Quelles applications ont eu le focus et pour combien de temps, avec une ventilation quotidienne et un récapitulatif sur sept jours. Cela se met en pause quand vous êtes éloigné du clavier, conserve 60 jours au maximum, et l'effacement supprime le fichier lui-même. |
| **Historique du presse-papiers** | Recherchez ce que vous avez copié et épinglez les phrases que vous réutilisez. Les presse-papiers contiennent régulièrement des mots de passe, donc ceci est gardé **en mémoire uniquement** sauf si vous cochez séparément « conserver entre les sessions ». |

---

## Langues

Sept : English, 繁體中文, 简体中文, Deutsch, Русский, Français, Italiano.

Choisissez-en une dans le menu **Langue** et l'interface change **immédiatement** —
sans redémarrage. Tout ce que vous aviez ouvert reste ouvert : les superpositions continuent de tourner, et les
réglages de chaque page restent exactement tels qu'ils étaient. Sur une installation Steam, le
premier lancement suit la langue propre du client Steam.

---

## Notes sur la confidentialité et les plateformes

### Ce qui quitte la machine

Tout dans FrontEngine est local sauf si c'est dans cette liste. Il y a quatre
exceptions, toutes optionnelles (opt-in) :

| Feature | Where it goes | Guard |
| --- | --- | --- |
| **Lire le texte** (Outils) | La région sélectionnée est envoyée à l'API d'Anthropic | Demande une fois avant le premier envoi et retient la réponse ; le consentement peut être retiré depuis la fenêtre de résultat. Utilise votre propre `ANTHROPIC_API_KEY`, lue depuis l'environnement et jamais écrite dans un fichier de réglages. Rien n'est envoyé sans les deux. |
| **Chat de l'animal** | Votre message va à l'API d'Anthropic | Même clé, même règle ; désactivé par défaut. |
| **Météo** (source de texte) | Les coordonnées vont à Open-Meteo | Pas de clé, pas de compte, aucune donnée identifiante ; seulement ce que vous avez saisi comme lieu. |
| **Télécommande téléphone** | Sert une page sur votre réseau local | Désactivée par défaut. Le lien porte un jeton régénéré à chaque démarrage, si bien qu'un ancien lien cesse de fonctionner, et la page ne peut demander que la liste d'actions fixe. C'est du HTTP en clair : quelqu'un d'autre sur le même réseau pourrait lire le jeton et appuyer sur les mêmes boutons — une nuisance plutôt qu'une brèche vu ce que font ces boutons, mais laissez-la désactivée sur les réseaux auxquels vous ne faites pas confiance. |

Les fonctions audio ne lisent qu'un **vumètre** de sortie — un seul nombre — sauf le
spectre, qui a besoin d'échantillons réels pour calculer les fréquences et capture donc le
flux de sortie du système. Ces échantillons sont analysés en mémoire, jamais écrits sur le
disque ni envoyés où que ce soit, et la capture s'arrête à l'instant où vous arrêtez le spectre.

Les **Plugins** sont du Python et s'exécutent avec les mêmes privilèges que FrontEngine — ils
ne peuvent pas être mis en bac à sable (sandbox). Le chargement est désactivé par défaut (Paramètres → Charger les plugins), chaque
chargement est journalisé, et un plugin défectueux est ignoré plutôt que d'arrêter l'application.
N'installez que des plugins auxquels vous faites confiance.

### Confidentialité du partage d'écran

Vos superpositions sont pour vous, pas pour les personnes avec qui vous partagez. Depuis
**Paramètres → Confidentialité du partage d'écran**, FrontEngine peut les retirer de la
capture pendant qu'une application de réunion est ouverte :

- **Elles restent sur votre propre écran.** Seule la copie capturée est vide — cela utilise
  le `WDA_EXCLUDEFROMCAPTURE` de Windows, un indicateur au niveau du système d'exploitation que les applications de conférence et
  les enregistreurs respectent.
- **Les masques sont l'exception.** Un masque de distraction existe pour couvrir quelque chose, il
  reste donc délibérément visible dans la capture.
- **Le déclencheur est votre liste.** Windows n'a pas d'API fiable pour savoir « suis-je en train d'être capturé »,
  il surveille donc les titres de fenêtres que vous nommez — ce qui attrape aussi une réunion
  tenue dans un onglet de navigateur, où l'exécutable n'est que le navigateur.

Il y a aussi un bouton manuel *Masquer de la capture* dans le centre de contrôle.

> Ceci est de la confidentialité, pas de la sécurité : cela déjoue le chemin de capture ordinaire, et cela
> ne cache jamais rien à la personne assise au bureau.

### Prise en charge des plateformes

Tout ce qui n'est pas listé ici fonctionne sur les trois plateformes.

| Feature | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Superpositions, animal, fond d'écran, présentation, soin des yeux, capture, enregistrement | ✅ | ✅ | ✅ |
| Réaction au son, spectre, synchro labiale (WASAPI) | ✅ | — | — |
| Lecture en cours (contrôles multimédias) | ✅ | — | — |
| Épingler / estomper une autre fenêtre, dispositions de fenêtres, réplique en direct | ✅ | — | — |
| Masquer les superpositions de la capture d'écran | ✅ | — | — |
| Contrôle MIDI (winmm) | ✅ | — | — |
| Touches de transport média | ✅ | — | — |
| Épingler les superpositions à un bureau virtuel | ✅ | — | — |
| Déplacer une fenêtre vers le moniteur suivant | ✅ | — | — |
| Sortie d'urgence `F12` | ✅ | — | — |
| Assombrir l'arrière-plan autour de la fenêtre *active* | ✅ | écran entier | écran entier |
| Animal se tenant sur d'autres fenêtres | ✅ | — | avec `wmctrl` |

Là où une fonction ne peut pas fonctionner, le bouton l'indique plutôt que d'échouer en silence.

---

## Extension

- **Steam Workshop** — les éléments auxquels vous êtes abonné sont récupérés depuis le propre dossier
  `steamapps/workshop/content` de Steam : les préréglages sont importés et les packs d'animaux sont
  listés avec leurs chemins, depuis **Préréglages → Importer du contenu Workshop**.
  La publication sur le Workshop nécessite le SDK Steamworks et n'est pas intégrée.
- **Plugins** — un dossier `plugins/` peut ajouter ses propres onglets, soit via un
  mappage `FRONTENGINE_TABS = {"name": WidgetClass}`, soit un point d'ancrage `register(registry)`.
  Lisez d'abord la note de confiance ci-dessus.

---

## Développement

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

La vérification statique utilise pyflakes (dans `dev_requirements.txt`), et un arbre propre n'affiche
rien du tout :

```bash
python -m pyflakes frontengine/ exe/ tests/
```

La suite de tests s'exécute entièrement hors écran et n'a besoin d'aucun affichage, carte son ni
caméra ; tout ce qui touche au monde extérieur prend une source injectable afin
qu'on puisse le tester avec une fausse.

- **Architecture** — [`architecture_explore.md`](../architecture_explore.md) cartographie
  chaque module, les couches, le contrat de superposition et les points d'extension.
  Lisez-le avant d'ajouter une page ou une superposition : plusieurs choses (le registre du
  centre de contrôle, sept dictionnaires de langue, sept arbres de documentation) doivent
  être mises à jour ensemble, et les tests l'imposent.
- **Contribuer** — voir [`CONTRIBUTING.md`](../CONTRIBUTING.md). Une fonctionnalité par
  pull request, tous les contrôles CI au vert.
- **Compiler l'exécutable Windows** — `python exe/build_exe.py`
  (Nuitka ; ajoutez `--onefile` pour un fichier unique).
- **Documentation** — les sources Sphinx dans `docs/`, publiées sur
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) dans les sept
  langues.

---

## Intégration continue et versions

Le travail suit `feature → dev → main`, et seule la dernière étape publie :

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR vers `main` ou `dev`, déclenchement manuel, ou appelé par `Nightly` | Compile, exécute les tests unitaires, puis construit un wheel à partir de *cette checkout*, l'installe et démarre l'application — sur Python 3.10 / 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Cron quotidien, déclenchement manuel | Appelle `CI`. La planification vit ici à dessein : GitHub désactive les workflows contenant un cron après ~60 jours d'inactivité, et cela emporterait sinon les contrôles de PR avec elle |
| `Release` (`release.yml`) | Une pull request **depuis `dev`** est fusionnée dans `main`, ou déclenchement manuel | Incrémente la version, la recommite avec `[skip ci]`, échange `stable.toml` → `pyproject.toml`, construit sdist + wheel, téléverse sur PyPI sous le nom `frontengine`, crée une version GitHub taguée `v<version>`, et avance `dev` en fast-forward |

La publication n'a lieu **que lorsque `dev` fusionne dans `main`**. Les fonctionnalités atterrissent sur `dev`
sans frapper de version, et une release est une pull request `dev → main` délibérée.
Une PR de fonctionnalité visant `main` par erreur fusionne quand même mais ne
publie pas — la direction de l'échec est une release manquante, pas une release non voulue.

Le segment de correctif (patch) s'incrémente automatiquement ; pour une version mineure ou majeure, exécutez
*Actions → Release → Run workflow* et choisissez le segment. Ce chemin réexécute aussi
une publication échouée sans nécessiter une nouvelle fusion.

Les versions vivent dans deux fichiers : `pyproject.toml` est le paquet de dev
(`frontengine_dev`) et `stable.toml` est le paquet publié (`frontengine`).

Un secret de dépôt est requis : `PYPI_API_TOKEN`, un jeton PyPI limité au
projet `frontengine`. Le workflow utilise `__token__` comme nom d'utilisateur twine, si bien que
seul le jeton lui-même a besoin d'être stocké.

---

## Licence

Voir [`LICENSE`](../LICENSE). Les attentes de la communauté sont dans
[`Contributor_Covenant_Code_of_Conduct.md`](../Contributor_Covenant_Code_of_Conduct.md).
