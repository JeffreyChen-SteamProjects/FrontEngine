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
