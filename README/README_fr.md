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
> purement et simplement** depuis n'importe où (Windows ; macOS nécessite l’autorisation Accessibilité — voir *Aide → Comment forcer la fermeture*).

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
- **Enregistrer une zone** — Enregistrement : sélectionnez une zone puis le GIF ou AVI de destination avant le début de la capture. Annuler ne lance pas l’enregistrement. Les images sont écrites progressivement en arrière-plan ; la file est limitée à trois images et 64 MiB. Une image trop grande est refusée. Une file pleine ignore des captures tout en conservant le temps de lecture écoulé. Cadence, limites de durée et de nombre d’images et incrustation de caméra sont conservées. L’arrêt finalise de façon asynchrone ; le fichier remplace atomiquement la destination seulement après réussite. Annulation et erreurs suppriment le temporaire et préservent la destination existante.
- **Caméra** — votre webcam dans un cercle, une boîte arrondie ou un rectangle, affichée localement
  et jamais enregistrée. Toute entrée vidéo fonctionne, y compris les cartes d'acquisition, et la
  liste des périphériques se rafraîchit sans redémarrer puisque les cartes sont généralement branchées
  alors que l'application tourne déjà.
- **Caméra virtuelle** — envoyez une région, superpositions comprises, comme une webcam que Zoom,
  Teams ou Discord peuvent sélectionner comme source vidéo. Nécessite le paquet optionnel
  `pyvirtualcam` et un pilote de caméra virtuelle (OBS en installe un) ; sans
  l'un ou l'autre, le bouton l'indique plutôt que d'échouer en silence.
- **Lire le texte** — Texte à l’écran : Outils → Lire du texte utilise d’abord l’OCR locale : Windows.Media.Ocr sous Windows, Vision sous macOS, ou Tesseract installé avec ses données linguistiques. L’extraction locale ne demande ni consentement cloud ni ANTHROPIC_API_KEY ; un résultat vide réussi n’envoie pas de capture. Traductions et questions peuvent envoyer le texte reconnu à Anthropic seulement avec votre clé et un consentement distinct pour le texte. Le recours aux captures après un échec local demande son propre consentement et la clé. Le résultat indique le moteur et les erreurs ; le consentement peut y être retiré.
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
| `F12` | Quitter immédiatement (Windows / macOS*) |

Le transport média envoie les touches multimédias du système, il atteint donc tout lecteur qui
les écoute. Déplacer une fenêtre conserve ses proportions au lieu de la faire claquer
d'un côté à l'autre, ce que fait le propre `Win+Shift+Arrow` de Windows.

Les mêmes actions — et rien de plus — sont ce que pilotent les télécommandes :

- **Votre téléphone** (Paramètres → Télécommande) — FrontEngine sert une petite page sur
  votre réseau local ; ouvrez le lien sur un téléphone et les boutons pilotent ces
  actions.
- **Un contrôleur MIDI** — Appuyez sur Learn, actionnez un potentiomètre ou un pad et associez une action. Windows utilise winmm intégré ; macOS utilise CoreMIDI avec l’option macos. Le potentiomètre déclenche une fois en haut ; relâcher un pad ne compte pas comme un nouvel appui.

---

## Préréglages et automatisation

Les **Préréglages** capturent les réglages de chaque page d'un seul coup. Enregistrez, chargez, supprimez,
exportez et importez-les depuis le menu **Préréglages**, appliquez-en un au lancement, ou
restaurez automatiquement la session précédente. Un préréglage peut être exporté comme un
Plugins : activer leur chargement ne les autorise pas. plugin.json ou le fichier associé à un plugin unique déclare version, identité, point d’entrée et capacités ; l’accord est vérifié avant l’import Python et lié à l’empreinte du contenu. Code ou déclaration modifiés demandent un nouvel accord ; les anciens plugins exigent une confiance totale explicite. Paramètres → Révoquer les autorisations des plugins efface les accords stockés ; redémarrez pour décharger le code en cours. Les plugins Python gardent tous les privilèges de l’application : déclaration et consentement ne sont pas un bac à sable système.

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
| **Lire le texte** (Outils) | Anthropic API | Texte à l’écran : Outils → Lire du texte utilise d’abord l’OCR locale : Windows.Media.Ocr sous Windows, Vision sous macOS, ou Tesseract installé avec ses données linguistiques. L’extraction locale ne demande ni consentement cloud ni ANTHROPIC_API_KEY ; un résultat vide réussi n’envoie pas de capture. Traductions et questions peuvent envoyer le texte reconnu à Anthropic seulement avec votre clé et un consentement distinct pour le texte. Le recours aux captures après un échec local demande son propre consentement et la clé. Le résultat indique le moteur et les erreurs ; le consentement peut y être retiré. |
| **Chat de l'animal** | Votre message va à l'API d'Anthropic | Même clé, même règle ; désactivé par défaut. |
| **Météo** (source de texte) | Les coordonnées vont à Open-Meteo | Pas de clé, pas de compte, aucune donnée identifiante ; seulement ce que vous avez saisi comme lieu. |
| **Télécommande téléphone** | HTTPS | Commande par téléphone : Paramètres → Commande à distance propose uniquement HTTPS, un jeton renouvelé à chaque démarrage et une liste fixe d’actions. Le téléphone ne fait pas automatiquement confiance au certificat autosigné. Exportez le certificat public et comparez l’empreinte SHA-256 affichée avant l’importation ou l’approbation dans les réglages du téléphone/navigateur. La clé privée reste dans le dossier de données utilisateur. Un changement d’IP, l’expiration ou une régénération peuvent nécessiter une nouvelle approbation. Un échec de TLS ne revient jamais à HTTP. |

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
| Superpositions et interface communes | ✅ | ✅ | ✅ |
| Audio système, spectre et microphone | ✅ | backend* | — |
| Métadonnées de lecture en cours | ✅ | — | — |
| Géométrie, disposition et déplacement entre écrans | ✅ | backend* | — |
| Copie de fenêtre en direct | ✅ | backend* | — |
| Fenêtres tierces : premier plan / opacité | ✅ | — | — |
| Exclure les superpositions des captures | ✅ | — | — |
| Commande MIDI | ✅ | backend* | — |
| Touches multimédias | ✅ | backend* | — |
| Bureau virtuel / choix du Space | ✅ | — | — |
| Sortie d’urgence F12 | ✅ | backend* | — |
| Animal sur les autres fenêtres | ✅ | backend* | wmctrl |

* Les entrées macOS « backend » nécessitent l’option macos, macOS 13+ et les autorisations correspondantes. Elles décrivent des frameworks publics implémentés, pas une validation native depuis ce poste Windows ; voir les notes ci-dessous.

Là où une fonction ne peut pas fonctionner, le bouton l'indique plutôt que d'échouer en silence.

---

## Exécution, confidentialité et interopérabilité

Enregistrement : sélectionnez une zone puis le GIF ou AVI de destination avant le début de la capture. Annuler ne lance pas l’enregistrement. Les images sont écrites progressivement en arrière-plan ; la file est limitée à trois images et 64 MiB. Une image trop grande est refusée. Une file pleine ignore des captures tout en conservant le temps de lecture écoulé. Cadence, limites de durée et de nombre d’images et incrustation de caméra sont conservées. L’arrêt finalise de façon asynchrone ; le fichier remplace atomiquement la destination seulement après réussite. Annulation et erreurs suppriment le temporaire et préservent la destination existante.

Commande par téléphone : Paramètres → Commande à distance propose uniquement HTTPS, un jeton renouvelé à chaque démarrage et une liste fixe d’actions. Le téléphone ne fait pas automatiquement confiance au certificat autosigné. Exportez le certificat public et comparez l’empreinte SHA-256 affichée avant l’importation ou l’approbation dans les réglages du téléphone/navigateur. La clé privée reste dans le dossier de données utilisateur. Un changement d’IP, l’expiration ou une régénération peuvent nécessiter une nouvelle approbation. Un échec de TLS ne revient jamais à HTTP.

Texte à l’écran : Outils → Lire du texte utilise d’abord l’OCR locale : Windows.Media.Ocr sous Windows, Vision sous macOS, ou Tesseract installé avec ses données linguistiques. L’extraction locale ne demande ni consentement cloud ni ANTHROPIC_API_KEY ; un résultat vide réussi n’envoie pas de capture. Traductions et questions peuvent envoyer le texte reconnu à Anthropic seulement avec votre clé et un consentement distinct pour le texte. Le recours aux captures après un échec local demande son propre consentement et la clé. Le résultat indique le moteur et les erreurs ; le consentement peut y être retiré.

Animaux puppet : installez l’option puppet et un moteur Imervue disponible, puis choisissez ou déposez un fichier original Imervue .puppet v1 sur la page Animal. Les anciens packs d’images et de sprites restent utilisables. Les puppets utilisent le canevas, les animations et les expressions d’Imervue, peuvent être clonés ou fermés et suivent les contrôles de superposition et préréglages. Un .petscript.json facultatif utilise le moteur de script existant d’Imervue ; les packs FrontEngine pet.json ne sont pas des puppets. Versions inconnues, chemins dangereux et ressources invalides sont refusés avant le chargement du moteur.

Scènes : la page Scène accepte l’ancien JSON de correspondance des entrées, un document versionné frontengine.scene et les paquets portables .fescene. Une entrée PUPPET contient position, taille, opacité, paramètres numériques finis et animation, expression ou script facultatifs. Les chemins JSON sont relatifs au fichier de scène. .fescene inclut les médias référencés, le .puppet original et le .petscript.json facultatif pour changer d’ordinateur. L’importation vérifie chemins, liens symboliques, versions et limites d’extraction. Une scène FrontEngine reste un paquet de scène ; .puppet reste un personnage Imervue.

macOS : l’option macos vise macOS 13+ et les frameworks publics PyObjC. Les moteurs proposent ScreenCaptureKit pour l’écran/fenêtre et l’audio système, le microphone, la géométrie Quartz, le déplacement/disposition des fenêtres via Accessibilité, CoreMIDI, les touches média et la sortie F12. Enregistrement de l’écran, Accessibilité et Microphone sont vérifiés séparément ; suivez Réglages Système → Confidentialité et sécurité et redémarrez si demandé. Opacité/premier plan forcé des fenêtres d’autres apps, choix des Spaces et exclusion des captures d’autres apps restent indisponibles. Les autorisations natives, le matériel et les performances macOS n’ont pas été vérifiés depuis ce poste Windows. Paramètres → Autorisations et capacités macOS indique pour chaque fonction disponible, indisponible ou non prise en charge, avec la raison liée à l’autorisation ou à l’installation.

Plugins : activer leur chargement ne les autorise pas. plugin.json ou le fichier associé à un plugin unique déclare version, identité, point d’entrée et capacités ; l’accord est vérifié avant l’import Python et lié à l’empreinte du contenu. Code ou déclaration modifiés demandent un nouvel accord ; les anciens plugins exigent une confiance totale explicite. Paramètres → Révoquer les autorisations des plugins efface les accords stockés ; redémarrez pour décharger le code en cours. Les plugins Python gardent tous les privilèges de l’application : déclaration et consentement ne sont pas un bac à sable système.

Rendu : Paramètres → Rendu des superpositions propose Automatique, GPU ou Logiciel et affiche le moteur réellement utilisé. Le compositeur GPU utilise textures OpenGL, shaders et framebuffers pour l’ordre, les transformations, l’opacité et le découpage ; un échec d’initialisation revient au logiciel avec une raison. Le contenu QPainter peut encore être rasterisé sur CPU avant l’envoi ; les widgets web/vidéo/natifs peuvent utiliser des fenêtres séparées. La capture et l’enregistrement peuvent relire les images GPU vers le CPU. Cela ne promet ni capture sans copie ni accélération mesurée.

Les projections WinRT de l’OCR sont incluses dans l’installation normale de FrontEngine sous Windows ; installez les langues de reconnaissance Windows nécessaires. Tesseract demande un exécutable et des données linguistiques installés séparément. L’option puppet installe Imervue>=1.0.90 ; macos installe les frameworks publics PyObjC pour macOS 13+. Utilisez les commandes ci-dessous. docs/formats/ contient les exemples puppet, pet.json, petscript et scènes.

```bash
pip install "frontengine[puppet]"
pip install "frontengine[macos]"
```

[.puppet / pet.json / .petscript.json / .fescene](../docs/formats/interoperability.md)

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

Les manifestes Workshop sont versionnés et validés avant utilisation. Les fichiers JSON de métadonnées inconnues ne sont pas considérés comme des préréglages. Les paquets refusent les chemins dangereux, le dépassement des limites de ressources et les collisions de noms de médias.

Préréglages → Gérer le Workshop ouvre le gestionnaire Steam ; Scène et Animal offrent aussi un accès. Windows x64 nécessite un client Steam connecté pour App 2793470 et steam_api64.dll. Publiez des scènes .fescene/JSON, des ZIP de préréglages ou des dossiers d’animaux en sprites avec un aperçu PNG/JPEG de moins de 1 Mo. Les nouveaux éléments sont privés ; les mises à jour vérifient le propriétaire. Les envois affichent progression et accord, conservent les ID pour réessayer et continuent si la fenêtre est masquée. Vérifiez dans Steam tout résultat interrompu. Les abonnements sont validés et copiés dans des dossiers de versions séparés ; un conflit local permet de choisir la version téléchargée ou locale. Le chargement remplit la page correspondante ; lancez la lecture depuis celle-ci. Les préréglages nécessitent un nouveau nom. L’import hors ligne reste disponible. Pour Steam, ajoutez --steam-runtime CHEMIN_DLL à exe/build_exe.py ; la DLL accompagne l’exécutable, même avec --onefile. Le SDK et le fichier de développement steam_appid.txt sont exclus.

Windows inclut désormais winrt-Windows.Media.Control pour afficher titre et artiste via SMTC dans le widget de lecture ; l’ancien winsdk reste une alternative. Sans session multimédia, le résultat est vide ; le nom de l’application audio reste disponible en secours.

La construction de l’exécutable vérifie dépendances et versions avant compilation ; installez d’abord requirements.txt dans cet environnement.

Scène → Éditeur visuel propose liste et aperçu des calques image/GIF/texte, déplacement groupé, redimensionnement par le coin, position/taille/échelle/rotation/ordre/opacité, alignement, verrouillage, visibilité, duplication et 100 annulations/rétablissements (Ctrl+Z/Ctrl+Y). Exportez directement .fescene ; l’onglet Script permet aussi de modifier et appliquer le JSON. La lecture restitue taille, échelle, rotation et visibilité explicites. Le JSON externe ouvre un nouvel historique ; les champs existants restent intacts.

Ouvrez Commandes dans le menu ou utilisez Ctrl+K / Ctrl+Maj+P dans FrontEngine. Recherchez dans la langue actuelle, les libellés anglais ou les noms stables ; les flèches sélectionnent et Entrée exécute. Navigation, capture, notes, filtre, Workshop et actions globales sont disponibles. Les actions préréglage/qualité acceptent une valeur. Favoris et 20 dernières commandes persistent ; paramètres et recherche ne sont pas enregistrés.

Texte → TXT / JSON / CSV local affiche un fichier UTF-8 avec champ et intervalle de 1–3600 secondes. JSON : /clé/index (ex. /build/tasks) ; CSV : en-têtes uniques, colonne affichée par lignes. Champ vide : fichier entier. Lecture en arrière-plan, une tâche par source, limite 1 MiB et 65 536 caractères. Les erreurs de fichier/champ, format, accès et taille sont explicites ; la correction rétablit automatiquement le résultat. Les préréglages gardent fichier/champ/intervalle. Une scène portable copie le fichier : partager le paquet partage cet instantané.

Outils → Palette de couleurs collecte les clics si la collecte est activée. Nommez/groupez, modifiez les hex exacts, recherchez, copiez et supprimez ; les échantillons récents sont réutilisables. Jusqu’à 512 couleurs et 50 échantillons distincts sont sauvegardés localement. Les noms sont uniques par groupe, sans distinction de casse ; les doublons sont refusés. CSS/JSON conservent RGB ; les collisions CSS reçoivent un numéro. Export atomique. Commandes ouvre aussi la palette.

Préréglages → Versions des préréglages conserve jusqu’à 50 instantanés de réglages distincts par préréglage après redémarrage. L’enregistrement conserve les configurations précédente et nouvelle, sans doublons. La sélection affiche les différences de champs avec les réglages actuels des pages. L’aperçu applique exactement cette configuration aux contrôles ; Annuler, Échap ou fermer rétablit les réglages initiaux. Restaurer applique et enregistre la version ; les réglages des pages sont rétablis si l’application ou l’enregistrement échoue. Les instantanés contiennent les chemins des médias, sans copier les fichiers ; l’aperçu n’ouvre pas de superpositions. Les préréglages JSON/ZIP existants restent compatibles. L’historique, sous presets/.versions, est conservé après suppression pour réutiliser le même nom.

Compagnon → Identités enregistre une UUID, un nom, l’humeur, la satiété et l’affection propres à chaque sprite ou puppet. Choisissez une identité enregistrée avant de le créer pour reprendre après redémarrage ; Nouveau compagnon recommence. Seule la première identité migre une fois les anciennes valeurs communes. Cloner copie les valeurs actuelles vers une nouvelle identité ; nourrir ne change pas les autres compagnons. Renommez, actualisez, exportez ou importez des sauvegardes JSON individuelles ; l’import crée toujours une nouvelle identité. Une identité ne peut être active qu’une fois. Les sauvegardes ne contiennent ni images, scripts, ni historique de discussion ; les préréglages portables excluent les IDs locaux. Jusqu’à 256 identités sont conservées dans les réglages ; les changements des sprites sont enregistrés après un bref délai et à la fermeture. Nourrir un puppet ne modifie que les valeurs sauvegardées, pas les mouvements ni la taille Imervue.

Image → Comparer les images montre deux références dans une vue commune avec zoom et déplacement : côte à côte, superposition transparente, séparateur coulissant ou différence absolue RVB. Alignez en haut à gauche ou au centre sans redimensionner, ou ajustez B dans A en conservant les proportions. La molette zoome les deux ; le curseur règle l’opacité de B ou le séparateur. Transparence et marges sont comparées sur blanc ; noir signifie RVB identique. Seule la première image animée est utilisée. Décodage, alignement et calcul travaillent en arrière-plan, avec une seule demande en cours et uniquement la dernière sélection appliquée ; opacité/séparateur réutilisent les images. Limites : 64 MiB par fichier, 8 192 pixels par dimension et 16 777 216 pixels par image/canevas. Un échec conserve la paire précédente ; fermer libère les images et ignore les résultats tardifs.

Réglages → Règles ajoute priorité (-1000…1000), délai (0…86400 secondes entières), aperçu des conditions et historique de session. Les règles déclenchées vont de la priorité faible à forte, dans l’ordre du tableau à égalité ; les valeurs fortes passent en dernier. Le délai utilise une horloge monotone : une transition bloquée est consommée, et son expiration ne lance rien tant que les conditions restent vraies. L’aperçu vérifie les lignes non enregistrées sans action ni transition consommée. Les 200 derniers rapports gardent conditions, contexte et résultats envoyé/exécuté/échec/délai uniquement en mémoire. Les lignes nommées invalides empêchent l’enregistrement. Jusqu’à 200 règles ont des identités distinctes même avec le même nom ; les conditions non affichées survivent aux modifications. Les échecs déclarés sont enregistrés sans arrêter les règles suivantes.

Les règles chargent, lisent ou arrêtent une scène et affichent, masquent, déplacent ou changent l’opacité d’un calque nommé. Sélectionnez la ligne puis Choisir une scène / un calque pour parcourir JSON, .fescene ou .puppet et choisir l’écran principal/tous/un indice et un calque de l’éditeur. Un chemin vide lit la scène actuelle. Les fichiers sont lus en arrière-plan ; un candidat échoué préserve la lecture existante. La dernière demande remplace celles en attente ; les actions de calque suivantes attendent et échouent avec elle. Les calques verrouillés ou absents sont refusés. Les modifications sont annulables et actualisent la lecture ; opacité 0–100, position ±100000. Arrêter annule les demandes et ferme la lecture ; les ressources de l’éditeur restent jusqu’au remplacement ou à la fermeture. L’historique reflète le résultat asynchrone réel. Palette de commandes : chemin ou {"path":"scene.fescene","screen":"primary"}, clé du calque pour afficher/masquer, {"layer":"title","opacity":50} ou {"layer":"title","x":20,"y":30}.

Scène → Script → Modèles de scène (aussi dans la palette de commandes) propose Bureau de travail, Enseignement et Concentration avec texte traduit et modifiable. Prévisualisez, choisissez l’écran principal ou son numéro puis Appliquer et lire ; les proportions s’adaptent à la taille logique disponible. Les modèles incluent leurs ressources. Les ressources absentes sont indiquées par calque/champ/chemin et bloquent l’application. La transaction de scène remplace éditeur et lecture ; une préparation échouée préserve la scène précédente. Modifiez le texte, ajoutez des médias et exportez en JSON ou .fescene portable. Fermer la bibliothèque annule seulement sa propre application en attente. Concentration propose des rappels modifiables ; planification et minuteries restent des outils distincts.

Scène → Éditeur visuel ajoute vidéo, web, Puppet et audio aux images/GIF/textes. Activez explicitement les aperçus : huit sources maximum, muettes avant Écouter, suspendues si masquées, libérées en désactivant ou fermant. Images limitées à 1280 pixels par côté ; les erreurs sont affichées. La lecture des scènes nommées compose vidéos, surface propre du moteur web et images Puppet hors écran Imervue avec tous les calques visuels dans l’ordre z ; l’audio reste invisible. Double-cliquez un calque web/Puppet en lecture ou choisissez Interagir dans l’éditeur pour ouvrir la même fenêtre native. Puppet exige OpenGL natif et le moteur optionnel ; les aperçus n’exécutent pas de scripts et les animaux de scène utilisent un état temporaire. Les fenêtres web/vidéo/Puppet indépendantes restent disponibles. JSON/.fescene conserve tous les types et références pris en charge.

Outils → Enregistrement de zone propose GIF ou AVI muet (Motion JPEG), 1–20 ips, Pause/Reprendre et Annuler. Le statut affiche secondes effectives, images acceptées et ignorées. Les pauses ne comptent ni dans la lecture ni dans la durée ; arrêt possible en pause. AVI : une heure, 72 000 images et 2 GiB maximum ; GIF : 120 secondes/600 images. Les deux utilisent une file de trois images/64 MiB et une sortie atomique. AVI garde un JPEG et écrit l’index sur disque ; les intervalles ignorés répètent la dernière image. Erreurs de codage, taille ou disque et annulation préservent la destination existante. Pas d’audio.

Scène → Éditeur visuel → Chronologie édite x/y/opacité d’un calque déverrouillé, avec modèles de fondu et glissement. Temps uniques croissants : 0–3600 secondes, 128 images clés par calque ; opacité 0–100, position ±100000, linear ou smooth. Cellules vides : canal inchangé. Application annulable ; JSON/.fescene conserve les pistes. Parcourez, lisez, suspendez, reprenez ou relisez l’aperçu sans enregistrer les positions temporaires ; réinitialisez avant modification. Lecture : commandes propres et horloge monotone commune aux écrans. Masquage suspend le temps ; pause explicite conservée après affichage. Les médias suivent la pause ; relire concerne les pistes. Les actions de scène dissolvent un ancien instantané pendant 0,5 seconde, libèrent les moteurs et démarrent à zéro. Anciennes scènes compatibles.

Scène → Sortie indépendante affiche la scène de l’éditeur en 640×480, 1280×720 ou 1920×1080 pixels, indépendamment de position, masquage et DPI du bureau. Aperçu sans caméra ; envoi explicite avec pyvirtualcam et pilote compatible. Ouverture/envoi/fermeture sur un seul worker avec la dernière image RGB en attente ; appareil lent ignore les intermédiaires. Sans audio. IMAGE/GIF/TEXT et VIDEO/WEB/PUPPET natifs respectent l’ordre des calques ; SOUND invisible. Puppet exige moteur optionnel et OpenGL natif ; erreurs affichées. Jusqu’à 256 calques, huit sources natives et 16 mégapixels de raster total. Arrêt, Escape, fermeture ou modification libèrent moteurs et demandent fermeture caméra ; redémarrez après modification. Lecteurs fermés avant libération des paquets.

Animal → Création de pack associe walk/idle/sleep/climb/fall/drag, prévisualise taille et vitesse de marche et exporte un dossier portable avec pet.json. Au moins une action ; les actions absentes sont signalées et utilisent le repli du chargeur. PNG/JPEG/GIF/WebP : 64 MiB et 16 mégapixels par fichier, 256 MiB au total. Import/export en arrière-plan, annulable, sans écraser les dossiers existants. Dossiers déplaçables, sélectionnables dans Animal et partageables comme packs Workshop. Import conserve uniquement sprites choisis, nom, taille et vitesse, sans sons, scripts ni dialogue. Imervue .puppet garde son format de création distinct. Fermer/Escape libère les animations et annule les opérations.

Outils → Modifier la dernière capture ouvre une copie indépendante avec recadrage, flèches, numéros, texte et masquage noir opaque. Glissez sur l’aperçu redimensionné ; coordonnées et sortie restent en pixels physiques. Annulation, réinitialisation et original en lecture seule. Copier/enregistrer PNG/épingler utilise toujours le même résultat aplati, même en vue originale. Masquage peint en dernier ; PNG sans original ni couches cachées. Capture brute séparée en mémoire. Sauvegarde PNG atomique. Limites : 16 mégapixels, 1000 marques, 2000 caractères/texte, 20 états d’annulation. Fermeture/remplacement libère le document.

Présentation → Tableau possède des pages éditables indépendantes, modes dessin/sélection, multiséléction Maj, déplacement/suppression de traits et 20 états d’annulation au total. Bouton central déplace, molette zoome ; sélection/mouvement en coordonnées de toile, vue propre à chaque page. Sauver/ouvrir .fewhiteboard JSON versionné conserve traits vectoriels/vues pour poursuivre les éditions. Un travailleur valide et lit/écrit ; erreurs préservent tableau/fichier. PNG de page exclut contrôles/sélection/transformation, avec marges de plume complètes. Limites : 50 pages, 2000 traits/page, 100000 points, huit MiB JSON ; PNG 8192 pixels/côté et 16 mégapixels. Fermer/Escape annule les écritures et ignore les lectures tardives.

Réglages → Historique d’images est facultatif séparément et désactivé ; ouvrir ne surveille ni ne lit le presse-papiers. Appliquer active capture et stockage SQLite local optionnel. 10–200 images, 8–128 MiB de PNG ; favoris protégés mais comptés dans les limites, nouveaux éléments refusés si favoris pleins. Chaque image : 16 MP/huit MiB encodée. Un travailleur compresse, crée miniatures et écrit ; dernière image en attente, résultats regroupés, intermédiaires ignorés si lent. Favoris/suppression/effacement, copie originale, épinglage et tableau en mémoire. Effacer inclut favoris et libère pages ; désactiver stockage supprime base, historique courant en mémoire conservé. clipboard-images.sqlite3 près des réglages, base jusqu’à 132 MiB plus journaux temporaires possibles. Aucun envoi/OCR automatique. Quitter déconnecte et demande nettoyage asynchrone.

Outils → OCR en direct affiche le texte près d’une zone fixe. Initialement manuel/local ; auto explicite 5–60 secondes, copie texte actuel/historique, vingt résultats uniques en mémoire. Identique/vide non dupliqué. Quatre fenêtres, un job chacune, capture 16 MP/huit MiB encodée, 20000 caractères ; tâches lentes sautent demandes. Local n’appelle jamais cloud même avec consentement global. Repli cloud explicite utilise consentement capture/identifiants ScreenTextService et vérification séparée ; aucun dialogue automatique/traduction/envoi de texte. Chaque actualisation cloud peut envoyer la zone. Chevauchement refusé contre rétroaction. Windows/X11 : Qt local écran ; Mac : capture native asynchrone unique, flux arrêté après image. Masquer arrête capture/minuteurs ; fermer/Escape libère sources/historique, ignore résultats tardifs sans attendre. Requête API déjà envoyée peut finir. Nettoyage collectif inclut fenêtres ; pas de reprise capture automatique.

Paramètres → Historique et recherche de captures nécessite une activation séparée ; ouvrir ne conserve/reconnaît rien. Seulement les captures de zone explicites des Outils, OCR locale en worker sans presse-papiers ni cloud. Recherche sans casse ; échec OCR conserve l’image avec motif en infobulle. Date locale exacte YYYY-MM-DD, champs vides pour tout. Copie, épinglage, tableau de références, favoris et suppression. Option capture-history.sqlite3 près des paramètres : 10–200 captures / 8–128 MiB PNG, 16 MP/huit MiB par image, base 132 MiB maximum plus journaux. Supprimer retire le texte, vider inclut favoris, arrêter conservation supprime la base. Dernière capture en attente uniquement ; fermer abandonne attente/résultats sans attendre l’OCR active.
