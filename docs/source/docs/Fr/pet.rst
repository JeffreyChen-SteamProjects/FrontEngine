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

Interactions et état enregistré
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Les profils de version 2 conservent l’UUID et les statistiques de la version 1 et ajoutent l’énergie, le mode choisi, les préférences et des références d’apparence validées. 

Le menu du sprite permet de dire bonjour, caresser doucement et brosser, ainsi que de choisir les modes persistants Jouer ensemble, Travailler ensemble et Se reposer. Terminer l’interaction annule l’action en cours. Les actions minutées ne donnent leurs bénéfices qu’à leur terme ; une annulation ne donne aucune récompense. Un animal rassasié refuse la nourriture et une pause est nécessaire avant de répéter une action. Déplacer l’animal ou changer son apparence ne donne aucune récompense. Cette version ne propose pas d’interface de jouets.

Les soins suivent le temps actif, indépendamment des bulles de dialogue. Le temps passé masqué ou hors ligne ne cumule aucun soin ni récompense à rattraper. Les sprites utilisent la session d’interaction commune pour les actions du menu et les modes. Les animaux Puppet partagent cette session et les règles d’alimentation ; leurs réactions visuelles natives dépendent des capacités du moteur et du modèle.

Sélectionnez une identité sur la page Animal et ouvrez « Personnaliser l’animal », également accessible depuis son menu. Chaque identité conserve sa taille (16–512), sa vitesse (1–20), son comportement au sol/en promenade/en poursuite, l’escalade des murs, la position sur les fenêtres, les bulles, le volume (0–100), le calme pendant la saisie, le repos automatique, les lancers et les interactions sociales. « Utiliser les réglages de la page » hérite des réglages de présentation de la page ; le clonage et l’importation conservent les réglages individuels. « Appliquer » enregistre atomiquement avant de mettre à jour l’animal actif. « Annuler » ne change rien ; le rétablissement des réglages attend « Appliquer ». Un échec ou conflit conserve le brouillon. Puppet désactive les commandes non prises en charge et n’applique que la taille, les bulles et le calme pendant la saisie parmi les réglages de présentation. La garde-robe native et les illustrations en couches restent à réaliser.

Identités des animaux → Garde-robe ouvre un aperçu animé distinct des personnages installés. Installer un dossier vérifie layered-pet.json et copie les ressources dans pet-assets près des paramètres locaux. Choisissez les éléments de tête, cou, corps et dos, les actions et la direction, puis enregistrez jusqu’à 20 tenues par identité. Retirez d’abord les éléments en conflit. Appliquer enregistre et actualise le Sprite actif ; Annuler abandonne les modifications depuis la dernière application. Les ressources manquantes restent référencées ; réparez-les puis actualisez. Puppet ne prend pas en charge ces vêtements Sprite. Ajouter le personnage intégré dessine l’un des six personnages INKSIDE (MOCHI, MOSS, PIP, BOLT, INK ou GILL) avec trente pièces de garde-robe issues de quatorze tenues, ajustées à sa morphologie, puis les installe en arrière-plan avec la même validation ; fermer la garde-robe annule. Chaque personnage propose des variantes d’yeux, de bouche et de trois parties du corps ainsi que des zones recolorables, et chaque pièce suit toutes ses animations.

Les animaux prennent des poses adaptées : le mode Travail les fait s’asseoir, passer en Repos joue un court endormissement et en sortir un réveil. Jouer, la balle, le rapport et le chat coûtent un peu d’énergie ; sous 20, un animal inactif s’assoit même sans repos automatique et obéit toujours à chaque commande. L’atterrissage après un dépôt ou un lancer, la saisie d’une balle lancée et la rencontre d’un autre animal affichent de brèves réactions d’atterrissage, d’attrape et de salut sans interrompre le déplacement, les jouets ni vos commandes. Les paquets Sprite sans ces clips utilisent leurs images d’attente ou de sommeil.

La relation grandit avec l’affection en quatre étapes : Nouvelle rencontre, Familier (20), Proche (100) et En harmonie (250). L’étape apparaît dans l’état. Chaque étape a sa salutation, les animaux proches font signe et ceux en harmonie sautent de joie ; atteindre une étape la fête une seule fois, et rien n’est verrouillé ni perdu. Un animal enregistré rappelé dit bon retour, et Fermer depuis son propre menu fait un signe d’adieu avant de fermer la fenêtre. Les Puppet distinguent maintenant clic et glisser comme les Sprite : un clic salue au relâchement et seul un déplacement au-delà de la distance système déplace la fenêtre, sans récompense.

La garde-robe propose les zones de couleur déclarées par le personnage ou le vêtement. Choisissez une zone et une couleur, ou rétablissez la couleur originale. Seuls les calques de masque désignés sont colorés ; les contours et autres détails sont conservés. Les couleurs sont prévisualisées avant application et sauvegardées par identité et tenue, y compris à l’export/import. Sans zones déclarées, ces commandes restent désactivées.

Si l’enregistrement échoue à la fermeture, l’animal reste ouvert avec son état et le minuteur de nouvelle tentative. Tout fermer conserve les animaux non fermés ; quitter attend la réussite de leurs enregistrements avant de libérer les ressources. L’affection est plafonnée à la limite du format pour que les récompenses suivantes ne rendent pas le profil impossible à enregistrer.

Salutations et poursuites exigent deux animaux visibles en mode jeu, sans interaction en cours, avec les échanges autorisés, sans transport ni pause de saisie. Les animaux indisponibles quittent les cibles et rôles. Le jeu se suspend sous deux participants admissibles et reprend à leur retour. Désactiver les bulles masque le texte, sans supprimer les récompenses sociales.

Le minuteur de concentration place les animaux visibles sans interaction en mode Travail, puis Repos pendant les pauses. Arrêter rétablit les modes précédents sauf modification manuelle. Chaque tour terminé donne une seule fois 3 points d’affection et 5 d’humeur aux compagnons visibles admissibles ; arrêt anticipé ou masquage ne donne aucune récompense. Travail/Repos supprime les bavardages spontanés. Le minuteur utilise un temps écoulé monotone, indépendant de l’horloge système.

Au début de la concentration, les compagnons sont placés en bas à droite de leur écran si la place suffit. L’arrêt restaure leur position précédente seulement sans déplacement ni changement de mode manuel.

Les personnages en calques peuvent proposer des variantes de visage et de corps. La garde-robe les prévisualise par animal ; Appliquer les enregistre, et les tenues conservent personnage et éléments. Chaque variante doit couvrir toutes les images d’animation. Les graphismes définitifs des six personnages restent à produire.

Le menu des animaux Sprite propose une photo : figer l’apparence actuelle ou choisir une pose en calques, puis enregistrer un PNG transparent. Aucun pixel du bureau ni bulle de dialogue n’est inclus. Les photos Puppet utilisent un moteur Imervue compatible et initialisé pour une image transparente figée, sans capture du bureau. La validation GL native reste à faire.

Pour les Sprite, choisissez Caresser puis déplacez le pointeur en aller-retour. Trois mouvements nets déclenchent une réaction ; les petits tremblements ne comptent pas. Déplacement et jeu social sont suspendus. Quitter, masquer, changer de mode ou terminer annule la caresse inachevée. Les récompenses exigent achèvement et délai de récupération.

Les Sprite peuvent lancer et ranger une balle. Glissez puis relâchez pour relancer, clic droit pour ranger. L’animal la rapporte près du départ ; le retour donne 1 affection avec 30 secondes actives de récupération. Travail/repos, autres interactions, masquage, calme pendant la saisie ou délai dépassé annulent sans récompense. Les Puppet rapportent aussi la balle (voir plus bas).

Les animaux au sol quittent les rebords pour chercher la balle. Les perchoirs de fenêtre sont suspendus pendant le jeu puis réactivés ; le retour se fait au sol près de la position horizontale initiale.

Le point lumineux est une petite cible déplaçable à portée limitée. Les animaux au sol suivent au sol. Relâchez la cible et laissez l’animal l’atteindre pour lancer une courte réaction de jeu, récompensée après achèvement selon le délai existant. Clic droit ou Ranger termine. Une seule balle ou lumière par animal.

Le clonage utilise l’image/modèle, l’apparence, les préférences et la bibliothèque de l’animal source, même après un autre choix dans les réglages. Le clone reçoit une nouvelle identité ; ses modifications ne changent pas l’original. Les clones Puppet gardent script, paramètres et expressions actives.

Une concentration terminée admissible déclenche brièvement celebrate puis Repos. Une tenue modifiée déclenche outfit_show. Ces réactions durent deux secondes actives, sans récompense supplémentaire ni sauvegarde ; actions ou modes manuels les interrompent. Les animations absentes utilisent idle. Les graphismes finaux et la correspondance Puppet restent à faire.

Sélectionnez une identité active puis Ramener l’animal pour le placer dans la zone utile de l’écran choisi. Les animaux cachés réapparaissent, interactions inachevées et jouets s’arrêtent, les limites Sprite suivent l’écran. Apparence et valeurs restent intactes. Démarrez les inactifs et réduisez les trop grands.

Les scripts Puppet peuvent utiliser frontengine_actions pour relier les états aux mouvements et expressions existants. Les noms sont validés avant démarrage ; aucune animation n’est devinée. La fin libère les effets de réaction en gardant les choix manuels. Format : docs/formats/puppet-companion-actions.md. Validation visuelle native en attente.

Après le choix de caresser, Puppet attend des allers-retours du pointeur. Sortir, Échap, masquer, changer de mode ou immobiliser annule la caresse inachevée. Le déplacement de la fenêtre est bloqué pendant la caresse. Validation native des gestes en attente.

La garde-robe propose six couleurs rapides pour la zone déclarée sélectionnée. Prévisualisez puis appliquez ; Annuler conserve l’apparence enregistrée. Le choix libre et la couleur par défaut restent disponibles.

Les menus Sprite et Puppet proposent quatre friandises fictives sans déposer de fichier. Fin du repas, satiété et délai restent communs. Nourrir termine la caresse sans récompense si elle est inachevée ; Sprite range son jouet.

Chaque animal peut enregistrer deux friandises différentes, préférée et moins aimée. Seule l’humeur après le repas change ; satiété, affection et délai restent identiques. Les modifications en cours de repas prennent effet au suivant. Les anciens profils sont neutres. food_like et food_dislike sont optionnels ; animations finales en attente.

Les animaux Sprite suivent un repère proche déplaçable avec Viens ici. Le mode sol reste au sol ; les modes libres se déplacent sur deux axes. L’arrivée déclenche une salutation avec son délai habituel. Clic droit ou Fin de l’interaction annule, comme travail/repos, masquage, repas ou nouveau jouet.

La zone des identités propose une liste d’interactions et un bouton pour l’animal actif sélectionné. Le clavier permet salut, courte caresse, toilettage, friandises, jeu/travail/repos ou annulation. La caresse utilise les règles temporisées sans geste du pointeur. Un animal masqué ou inactif n’est pas lancé.

Changer la langue avec la garde-robe ouverte actualise les choix Aucun, Manquant et Valeurs par défaut. Les couleurs, pièces, noms de tenues non appliqués et la position de l’aperçu sont conservés. Les noms fournis par les auteurs restent inchangés.

Pour définir une destination au clavier, choisissez Viens ici dans la gestion des animaux et saisissez les décalages horizontal/vertical en pixels logiques. Les valeurs négatives signifient gauche/haut. La destination reste proche ; le mode sol ignore le décalage vertical. Exécuter lance l’appel, terminer l’interaction l’annule. Les animaux occupés ou non compatibles gardent leur interaction.

Puppet accepte aussi Viens ici depuis son menu ou les décalages clavier du gestionnaire. La fenêtre entière et le repère restent dans la zone de travail. Le centre atteint la cible pendant une demi-seconde avant la salutation commune. Déplacement manuel, soins, modes, masquage, changement de taille ou de zone et commandes du modèle annulent l’appel. Une réaction walk déclarée est utilisée, sinon l’apparence native reste intacte. Le minuteur ne tourne que pendant l’appel. Validation GL/focus native en attente.

Puppet peut poursuivre un point lumineux déplaçable depuis son menu. Le gestionnaire permet à Sprite et Puppet de placer ce point au clavier. Relâché près de l’animal pendant une demi-seconde, il lance le jeu commun de trois secondes ; l’affection arrive seulement à la fin, avec le délai normal. Appel et lumière partagent une cible. Ranger, terminer, soigner, déplacer manuellement, changer de mode ou masquer annule.

Le menu Puppet propose aussi Lancer une balle, et les gestionnaires Sprite et Puppet peuvent la lancer pour l’identité choisie. Physique, relance par glisser, rangement par clic droit, 1 affection et 30 secondes de récupération sont partagés avec Sprite ; la fenêtre Puppet poursuit la balle, la ramasse et la rapporte à son centre d’origine, sans quitter la zone de travail. Chaque relance redémarre le délai. Balle, lumière et Viens ici partagent une cible : en lancer un remplace l’autre. Soins, déplacement manuel, changement de mode ou masquage annulent sans récompense. L’animation de rapport dédiée reste à faire.
