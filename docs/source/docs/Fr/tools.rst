Page Outils
-----------

* Mesurer - cliquez pour mesurer, le clic droit efface. Ce que vous mesurez part
  directement dans le presse-papiers.

    * Pipette - la couleur sous le curseur, copiée en #rrggbb, rgb(...),
      hsl(...) ou en propriété CSS personnalisée.
    * Règle en pixels - la distance entre deux points.
    * Rapporteur - l'angle entre trois.

* Capture de zone - tracez une zone ; elle arrive dans le presse-papiers, et
  « Copier la dernière » l'y remet.

  Épingler la dernière place la capture au-dessus de tout dans une petite fenêtre :
  déplaçable, redimensionnable à la molette, fermée par double-clic ou Échap - une
  spécification, une référence de couleur ou un message d'erreur à côté du travail.
* Texte à l’écran : Outils → Lire du texte utilise d’abord l’OCR locale : Windows.Media.Ocr sous Windows, Vision sous macOS, ou Tesseract installé avec ses données linguistiques. L’extraction locale ne demande ni consentement cloud ni ANTHROPIC_API_KEY ; un résultat vide réussi n’envoie pas de capture. Traductions et questions peuvent envoyer le texte reconnu à Anthropic seulement avec votre clé et un consentement distinct pour le texte. Le recours aux captures après un échec local demande son propre consentement et la clé. Le résultat indique le moteur et les erreurs ; le consentement peut y être retiré.
* Enregistrement : sélectionnez une zone puis le GIF de destination avant le début de la capture. Annuler ne lance pas l’enregistrement. Les images sont écrites progressivement en arrière-plan ; la file est limitée à trois images et 64 MiB. Une image trop grande est refusée. Une file pleine ignore des captures tout en conservant le temps de lecture écoulé. Cadence, limites de durée et de nombre d’images et incrustation de caméra sont conservées. L’arrêt finalise de façon asynchrone ; le fichier remplace atomiquement la destination seulement après réussite. Annulation et erreurs suppriment le temporaire et préservent la destination existante.
* Caméra virtuelle - envoyer une zone, calques compris, comme une webcam que
  Zoom, Teams ou Discord peuvent choisir comme source vidéo. Nécessite le paquet
  optionnel pyvirtualcam et un pilote de caméra virtuelle ; à défaut, le bouton
  le dit.
* Caméra - afficher n'importe quelle entrée vidéo, y compris les cartes
  d'acquisition, en cercle, rectangle arrondi ou rectangle, avec bordure et
  miroir. Elle n'est affichée qu'en local et rien n'est enregistré.
* Épingler une fenêtre… - garder la fenêtre d'une autre application au premier
  plan et régler sa transparence. Windows uniquement.
* Dupliquer une fenêtre… - une seconde petite fenêtre affiche en direct la fenêtre
  choisie, tandis que l'originale reste à sa place. Pratique pour surveiller une
  vidéo ou une compilation tout en travaillant. Faites glisser pour la déplacer,
  double-cliquez pour la fermer. Windows et macOS (option macos et autorisation ; macOS natif non vérifié ici).

  Un duplicata peut n'afficher qu'une partie de la fenêtre - moitié haute ou
  basse, un côté, ou le centre - pour isoler une colonne de discussion ou une
  barre de progression. La zone est retenue en proportion : redimensionner
  l'original montre toujours la même partie.
* Disposition des fenêtres - retenir où sont les fenêtres et les y remettre.

:doc:`runtime_interoperability`
