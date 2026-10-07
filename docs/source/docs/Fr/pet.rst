Page Mascotte
-------------

Un compagnon qui vit sur le bureau.

* Choisir l'image de la mascotte - une seule image.
* Choisir un pack de mascotte… - un dossier contenant les images walk / idle /
  sleep / climb / fall / drag, pour qu'elle s'anime.
* Choisir un son (facultatif) - ce qu'elle joue.
* Faire apparaître la mascotte - la poser à l'écran. Une nouvelle pression en
  ajoute une autre.
* Taille, vitesse.
* Comportement - marcher au sol, errer librement, ou suivre le curseur.
* Grimper aux murs - le long des bords de fenêtres.
* S'asseoir sur les fenêtres - se poser sur le bord supérieur des autres fenêtres.
* Bulles de dialogue - de courtes remarques au fil de la journée, quand on la
  nourrit, et ainsi de suite.
* Rester tranquille pendant la frappe - le compagnon s'arrête tant que vous tapez
  et repart une ou deux secondes après, pour ne pas traverser la ligne que vous
  êtes en train de lire.
* Lire à voix haute - dire ces remarques.
* Jouer à chat - deux mascottes ou plus se poursuivent.
* Réagir au son - la mascotte bouge en rythme. Elle peut suivre vos
  **haut-parleurs** ou votre **microphone** ; dans les deux cas elle ne lit
  qu'un niveau, un simple nombre, et n'enregistre jamais ce qui est dit.
  Windows et macOS (option macos et autorisation ; macOS natif non vérifié ici).
* Discussion IA (clé API requise) - lui parler. Cela lit la variable
  d'environnement ANTHROPIC_API_KEY ; la clé n'est jamais enregistrée.
* Minuteur de concentration (min) - un minuteur de travail que la mascotte tient
  pour vous, avec des pauses.

Déposez un fichier sur la mascotte pour la nourrir, ou une image ou un pack
pour changer son apparence.

Animaux puppet : installez l’option puppet et un moteur Imervue disponible, puis choisissez ou déposez un fichier original Imervue .puppet v1 sur la page Animal. Les anciens packs d’images et de sprites restent utilisables. Les puppets utilisent le canevas, les animations et les expressions d’Imervue, peuvent être clonés ou fermés et suivent les contrôles de superposition et préréglages. Un .petscript.json facultatif utilise le moteur de script existant d’Imervue ; les packs FrontEngine pet.json ne sont pas des puppets. Versions inconnues, chemins dangereux et ressources invalides sont refusés avant le chargement du moteur.

:doc:`runtime_interoperability`

Compagnon → Identités enregistre une UUID, un nom, l’humeur, la satiété et l’affection propres à chaque sprite ou puppet. Choisissez une identité enregistrée avant de le créer pour reprendre après redémarrage ; Nouveau compagnon recommence. Seule la première identité migre une fois les anciennes valeurs communes. Cloner copie les valeurs actuelles vers une nouvelle identité ; nourrir ne change pas les autres compagnons. Renommez, actualisez, exportez ou importez des sauvegardes JSON individuelles ; l’import crée toujours une nouvelle identité. Une identité ne peut être active qu’une fois. Les sauvegardes ne contiennent ni images, scripts, ni historique de discussion ; les préréglages portables excluent les IDs locaux. Jusqu’à 256 identités sont conservées dans les réglages ; les changements des sprites sont enregistrés après un bref délai et à la fermeture. Nourrir un puppet ne modifie que les valeurs sauvegardées, pas les mouvements ni la taille Imervue.

Animal → Création de pack associe walk/idle/sleep/climb/fall/drag, prévisualise taille et vitesse de marche et exporte un dossier portable avec pet.json. Au moins une action ; les actions absentes sont signalées et utilisent le repli du chargeur. PNG/JPEG/GIF/WebP : 64 MiB et 16 mégapixels par fichier, 256 MiB au total. Import/export en arrière-plan, annulable, sans écraser les dossiers existants. Dossiers déplaçables, sélectionnables dans Animal et partageables comme packs Workshop. Import conserve uniquement sprites choisis, nom, taille et vitesse, sans sons, scripts ni dialogue. Imervue .puppet garde son format de création distinct. Fermer/Escape libère les animations et annule les opérations.
