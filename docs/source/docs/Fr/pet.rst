Page Mascotte
-------------

Un compagnon qui vit sur le bureau.

La page s’ouvre sur *Votre mascotte* : cliquez sur un des personnages intégrés et une mascotte habillée comme lui apparaît aussitôt sur le bureau. En dessous, les mascottes du bureau sont listées avec *Garde-robe*, *Ramener l’animal* et *Ranger* (un double-clic en ramène une) ; tous les autres réglages restent repliés jusqu’à ce que vous ouvriez leur section. Au premier démarrage, sans animal ni maison, FrontEngine s'ouvre sur cette page.

* Chaque mascotte de bureau est un personnage en calques : un personnage INKSIDE
  intégré ou un personnage installé dans la garde-robe. Les images, les GIF et les
  dossiers de packs de sprites ne sont pas utilisés ; une mascotte lancée ainsi
  auparavant revient sous le personnage intégré que la maison montre déjà pour elle.
* Choisir un modèle Puppet… - lancer plutôt une mascotte Puppet (.puppet).
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
* Faire revenir les animaux au démarrage de FrontEngine - activé par défaut : les
  animaux présents sur le bureau à la fermeture reviennent tels quels au démarrage
  suivant ; un animal rangé reste rangé.
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

Déposez un fichier sur la mascotte pour la nourrir, ou un lien pour qu'elle
aille le chercher.

Animaux puppet : installez un moteur Rigora disponible, puis choisissez ou déposez un fichier original Rigora .puppet v1 sur la page Animal. Les puppets utilisent le canevas, les animations et les expressions de Rigora, peuvent être clonés ou fermés et suivent les contrôles de superposition et préréglages. Un .petscript.json facultatif utilise le moteur de script existant de Rigora. Versions inconnues, chemins dangereux et ressources invalides sont refusés avant le chargement du moteur.

Les animaux Puppet se promènent aussi d'eux-mêmes : après quelques secondes de repos, ils marchent un peu vers la gauche ou la droite à leur hauteur actuelle avec le mouvement de marche, restent dans la zone de travail de l'écran, puis se reposent de nouveau. Le glisser, les caresses, Viens ici et les jouets, le calme pendant la frappe et les modes qui n'autorisent pas à agir seul passent avant la promenade.

Le choix par défaut du menu Comportement, Enchaîner toutes les actions (au hasard), fait choisir au hasard à un animal libre sa prochaine action parmi toutes ses actions ; Marcher au sol se limite à marcher et attendre. Un animal en calques choisit entre marcher, attendre, s'asseoir, jouer, faire sa toilette, grimper au mur le plus proche, saluer, dormir, fêter et montrer sa tenue ; un animal Puppet choisit entre une promenade et s'asseoir, jouer, faire sa toilette, saluer ou fêter sur place. Un animal invoqué se met aussitôt à marcher. Les poses sont tenues sur place, et un animal sans animation pour une pose affiche son animation d'attente.

:doc:`runtime_interoperability`

Compagnon → Identités enregistre une UUID, un nom, l’humeur, la satiété et l’affection propres à chaque animal en calques ou Puppet. Choisissez une identité enregistrée avant de le créer pour reprendre après redémarrage ; Nouveau compagnon recommence. Seule la première identité migre une fois les anciennes valeurs communes. Cloner copie les valeurs actuelles vers une nouvelle identité ; nourrir ne change pas les autres compagnons. Renommez, actualisez, exportez ou importez des sauvegardes JSON individuelles ; l’import crée toujours une nouvelle identité. Une identité ne peut être active qu’une fois. Les sauvegardes ne contiennent ni fichiers de ressources, scripts, ni historique de discussion ; les préréglages portables excluent les IDs locaux. Jusqu’à 256 identités sont conservées dans les réglages ; les changements de l’animal de bureau sont enregistrés après un bref délai et à la fermeture. Nourrir un puppet ne modifie que les valeurs sauvegardées, pas les mouvements ni la taille Rigora.

Exportez les sauvegardes des compagnons sous un autre nom de fichier. L’export refuse les noms réservés aux réglages, au foyer, aux sauvegardes, aux fichiers temporaires et de verrouillage, ainsi que les fichiers de destination liés.

Interactions et état enregistré
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Les profils de version 2 conservent l’UUID et les statistiques de la version 1 et ajoutent l’énergie, le mode choisi, les préférences et des références d’apparence validées. 

Le menu de l'animal en calques permet de dire bonjour, caresser doucement et brosser, ainsi que de choisir les modes persistants Jouer ensemble, Travailler ensemble et Se reposer. Terminer l’interaction annule l’action en cours. Les actions minutées ne donnent leurs bénéfices qu’à leur terme ; une annulation ne donne aucune récompense. Un animal rassasié refuse la nourriture et une pause est nécessaire avant de répéter une action. Déplacer l’animal ou changer son apparence ne donne aucune récompense. Cette version ne propose pas d’interface de jouets.

Les soins suivent le temps actif, indépendamment des bulles de dialogue. Le temps passé masqué ou hors ligne ne cumule aucun soin ni récompense à rattraper. Les animaux en calques utilisent la session d’interaction commune pour les actions du menu et les modes. Les animaux Puppet partagent cette session et les règles d’alimentation ; leurs réactions visuelles natives dépendent des capacités du moteur et du modèle.

Sélectionnez une identité sur la page Animal et ouvrez « Personnaliser l’animal », également accessible depuis son menu. Chaque identité conserve sa taille (16–512), sa vitesse (1–20), son comportement au sol/en promenade/en poursuite, l’escalade des murs, la position sur les fenêtres, les bulles, le volume (0–100), le calme pendant la saisie, le repos automatique, les lancers et les interactions sociales. « Utiliser les réglages de la page » hérite des réglages de présentation de la page ; le clonage et l’importation conservent les réglages individuels. « Appliquer » enregistre atomiquement avant de mettre à jour l’animal actif. « Annuler » ne change rien ; le rétablissement des réglages attend « Appliquer ». Un échec ou conflit conserve le brouillon. Puppet désactive les commandes non prises en charge et n’applique que la taille, les bulles et le calme pendant la saisie parmi les réglages de présentation. La garde-robe native et les illustrations en couches restent à réaliser.

Identités des animaux → Garde-robe ouvre un aperçu animé distinct des personnages installés. Installer un dossier vérifie layered-pet.json et copie les ressources dans pet-assets près des paramètres locaux. Choisissez les éléments de tête, cou, corps et dos, les actions et la direction, puis enregistrez jusqu’à 20 tenues par identité. Équiper un élément remplace ce qui occupe les mêmes emplacements et le nomme ; Annuler le rétablit. Seules les pièces adaptées à la morphologie actuelle sont proposées ; celles sans toutes les animations apparaissent désactivées. Essayer une pièce joue une courte présentation, et Épingler pour comparer garde l’apparence actuelle à côté du brouillon. Un animal déplacé ou en pleine interaction change de tenue une fois terminé. Un animal qui n’a pas encore de personnage est invité à en choisir un d’abord. Appliquer enregistre et actualise l’animal sur le bureau ; Annuler abandonne les modifications depuis la dernière application. Les ressources manquantes restent référencées ; réparez-les puis actualisez. Puppet ne prend pas en charge ces vêtements en calques. Ajouter le personnage intégré dessine l’un des six personnages INKSIDE (MOCHI, MOSS, PIP, BOLT, INK ou GILL) avec trente pièces de garde-robe issues de quatorze tenues, ajustées à sa morphologie, puis les installe en arrière-plan avec la même validation ; fermer la garde-robe annule. Chaque personnage propose des variantes d’yeux, de bouche et de trois parties du corps ainsi que des zones recolorables, et chaque pièce suit toutes ses animations. Les noms des parties et des vêtements suivent la langue de l’interface. La garde-robe intégrée compte dix-neuf tenues en 43 pièces, dont Balade d’hiver, Cuisine, Fête, Jour d’école et Jour de plage ; chaque pièce va à tous les corps intégrés. Ouvrir la garde-robe d’une mascotte portant un personnage intégré ajoute de lui-même les vêtements d’un FrontEngine plus récent.

Les personnages intégrés marchent, grimpent et prennent chaque pose à partir de leurs calques, si bien que vêtements, pièces modifiées et couleurs restent toujours ajustés.

Les animaux de bureau passent toujours par le dessin Qt ordinaire, quel que soit le rendu des superpositions : un animal déplace sa fenêtre à chaque pas, et sur le chemin GPU ses images d’animation cessaient de changer pendant le déplacement.

Les animaux prennent des poses adaptées : le mode Travail les fait s’asseoir, passer en Repos joue un court endormissement et en sortir un réveil. Jouer, la balle, le rapport et le chat coûtent un peu d’énergie ; sous 20, un animal inactif s’assoit même sans repos automatique et obéit toujours à chaque commande. L’atterrissage après un dépôt ou un lancer, la saisie d’une balle lancée et la rencontre d’un autre animal affichent de brèves réactions d’atterrissage, d’attrape et de salut sans interrompre le déplacement, les jouets ni vos commandes. Les personnages tiers sans ces clips utilisent leur animation d’attente ou de sommeil. La toilette se termine par un étirement, et des animaux qui se croisent sans cesse se saluent au plus une fois par minute.

La relation grandit avec l’affection en quatre étapes : Nouvelle rencontre, Familier (20), Proche (100) et En harmonie (250). L’étape apparaît dans l’état. Chaque étape a sa salutation, les animaux proches font signe et ceux en harmonie sautent de joie ; atteindre une étape la fête une seule fois, et rien n’est verrouillé ni perdu. Un animal enregistré rappelé dit bon retour, et Fermer depuis son propre menu fait un signe d’adieu avant de fermer la fenêtre. Les Puppet distinguent maintenant clic et glisser comme les animaux en calques : un clic salue au relâchement et seul un déplacement au-delà de la distance système déplace la fenêtre, sans récompense.

Personnaliser l’animal règle aussi le Bavardage (Désactivé, Rarement, Normal, Souvent) pour les phrases que l’animal lance seul et l’Amplitude des animations (Calme, Normal, Vif) pour la pulsation audio et les courtes réactions d’atterrissage et d’attrape, indépendamment des bulles et du volume. Les réponses à vos actions restent affichées sans bavardage. Les Puppet appliquent le Bavardage aux répliques programmées du script. Les présentations enregistrées avant restent valides et utilisent Normal pour les deux.

La liste d’interactions du gestionnaire propose aussi les commandes de menu de l’animal actif choisi : photo, état, rappel, discussion si un service est connecté, cloner et fermer, ainsi que chaque mouvement et expression d’un modèle Puppet. Tout le menu contextuel est donc accessible au clavier.

Utiliser le personnage intégré, sur la page Animal, installe en arrière-plan le personnage INKSIDE choisi avec sa garde-robe et le sélectionne comme source. Démarrer crée alors un animal portant ce personnage : il peut être habillé dans la garde-robe et garde sa tenue s'il porte déjà ce personnage. Utiliser le modèle Puppet intégré, juste à côté, produit toujours la version Rigora Puppet. Le personnage lui-même est installé en premier : un animal lancé depuis une carte apparaît en une ou deux secondes ; ses vêtements finissent de s'installer en arrière-plan, et la garde-robe ajoute à l'ouverture ceux qui manquent encore.

Utiliser le modèle Puppet intégré, sur la page Animal, dessine en arrière-plan le personnage INKSIDE choisi comme modèle Rigora .puppet : tête, bras, queue et corps riggés, dix mouvements, trois expressions et un script qui y associe les actions du compagnon. Il est enregistré dans pet-assets/puppets et choisi comme source avec son script ; Démarrer le lance comme animal Puppet.

Avec plusieurs écrans à des échelles différentes, un animal déplacé ou ramené sur un autre écran garde sa taille, reste dans la zone de travail de cet écran et s’y promène. Les bords de fenêtre des écrans mis à l’échelle sont mesurés dans les mêmes coordonnées que l’animal, qui se pose donc exactement sur les fenêtres.

La garde-robe propose les zones de couleur déclarées par le personnage ou le vêtement. Choisissez une zone et une couleur, ou rétablissez la couleur originale. Seuls les calques de masque désignés sont colorés ; les contours et autres détails sont conservés. Les couleurs sont prévisualisées avant application et sauvegardées par identité et tenue, y compris à l’export/import. Sans zones déclarées, ces commandes restent désactivées.

Si l’enregistrement échoue à la fermeture, l’animal reste ouvert avec son état et le minuteur de nouvelle tentative. Tout fermer conserve les animaux non fermés ; quitter attend la réussite de leurs enregistrements avant de libérer les ressources. L’affection est plafonnée à la limite du format pour que les récompenses suivantes ne rendent pas le profil impossible à enregistrer.

Salutations et poursuites exigent deux animaux visibles en mode jeu, sans interaction en cours, avec les échanges autorisés, sans transport ni pause de saisie. Les animaux indisponibles quittent les cibles et rôles. Le jeu se suspend sous deux participants admissibles et reprend à leur retour. Désactiver les bulles masque le texte, sans supprimer les récompenses sociales.

Le minuteur de concentration place les animaux visibles sans interaction en mode Travail, puis Repos pendant les pauses. Arrêter rétablit les modes précédents sauf modification manuelle. Chaque tour terminé donne une seule fois 3 points d’affection et 5 d’humeur aux compagnons visibles admissibles ; arrêt anticipé ou masquage ne donne aucune récompense. Travail/Repos supprime les bavardages spontanés. Le minuteur utilise un temps écoulé monotone, indépendant de l’horloge système.

Au début de la concentration, les compagnons sont placés en bas à droite de leur écran si la place suffit. L’arrêt restaure leur position précédente seulement sans déplacement ni changement de mode manuel.

Les personnages en calques peuvent proposer des variantes de visage et de corps. La garde-robe les prévisualise par animal ; Appliquer les enregistre, et les tenues conservent personnage et éléments. Chaque variante doit couvrir toutes les images d’animation. Les graphismes définitifs des six personnages restent à produire.

Le menu des animaux en calques propose une photo : figer l’apparence actuelle ou choisir une pose en calques, puis enregistrer un PNG transparent. Aucun pixel du bureau ni bulle de dialogue n’est inclus. Les photos Puppet utilisent un moteur Rigora compatible et initialisé pour une image transparente figée, sans capture du bureau. La validation GL native reste à faire.

Pour les animaux en calques, choisissez Caresser puis déplacez le pointeur en aller-retour. Trois mouvements nets déclenchent une réaction ; les petits tremblements ne comptent pas. Déplacement et jeu social sont suspendus. Quitter, masquer, changer de mode ou terminer annule la caresse inachevée. Les récompenses exigent achèvement et délai de récupération.

Les animaux en calques peuvent lancer et ranger une balle. Glissez puis relâchez pour relancer, clic droit pour ranger. L’animal la rapporte près du départ ; le retour donne 1 affection avec 30 secondes actives de récupération. Travail/repos, autres interactions, masquage, calme pendant la saisie ou délai dépassé annulent sans récompense. Les Puppet rapportent aussi la balle (voir plus bas).

Les animaux au sol quittent les rebords pour chercher la balle. Les perchoirs de fenêtre sont suspendus pendant le jeu puis réactivés ; le retour se fait au sol près de la position horizontale initiale.

Le point lumineux est une petite cible déplaçable à portée limitée. Les animaux au sol suivent au sol. Relâchez la cible et laissez l’animal l’atteindre pour lancer une courte réaction de jeu, récompensée après achèvement selon le délai existant. Clic droit ou Ranger termine. Une seule balle ou lumière par animal.

Le clonage utilise le personnage/modèle, l’apparence, les préférences et la bibliothèque de l’animal source, même après un autre choix dans les réglages. Le clone reçoit une nouvelle identité ; ses modifications ne changent pas l’original. Les clones Puppet gardent script, paramètres et expressions actives.

Une concentration terminée admissible déclenche brièvement celebrate puis Repos. Une tenue modifiée déclenche outfit_show. Ces réactions durent deux secondes actives, sans récompense supplémentaire ni sauvegarde ; actions ou modes manuels les interrompent. Les animations absentes utilisent idle. Les graphismes finaux et la correspondance Puppet restent à faire.

Sélectionnez une identité active puis Ramener l’animal pour le placer dans la zone utile de l’écran choisi. Les animaux cachés réapparaissent, interactions inachevées et jouets s’arrêtent, les limites physiques des animaux en calques suivent l’écran. Apparence et valeurs restent intactes. Démarrez les inactifs et réduisez les trop grands.

Les scripts Puppet peuvent utiliser frontengine_actions pour relier les états aux mouvements et expressions existants. Les noms sont validés avant démarrage ; aucune animation n’est devinée. La fin libère les effets de réaction en gardant les choix manuels. Format : docs/formats/puppet-companion-actions.md. Validation visuelle native en attente.

Après le choix de caresser, Puppet attend des allers-retours du pointeur. Sortir, Échap, masquer, changer de mode ou immobiliser annule la caresse inachevée. Le déplacement de la fenêtre est bloqué pendant la caresse. Validation native des gestes en attente.

La garde-robe propose six couleurs rapides pour la zone déclarée sélectionnée. Prévisualisez puis appliquez ; Annuler conserve l’apparence enregistrée. Le choix libre et la couleur par défaut restent disponibles.

Les menus des animaux en calques et Puppet proposent quatre friandises fictives sans déposer de fichier. Fin du repas, satiété et délai restent communs. Nourrir termine la caresse sans récompense si elle est inachevée ; l’animal en calques range son jouet.

Chaque animal peut enregistrer deux friandises différentes, préférée et moins aimée. Seule l’humeur après le repas change ; satiété, affection et délai restent identiques. Les modifications en cours de repas prennent effet au suivant. Les anciens profils sont neutres. food_like et food_dislike sont optionnels ; animations finales en attente.

Les animaux en calques suivent un repère proche déplaçable avec Viens ici. Le mode sol reste au sol ; les modes libres se déplacent sur deux axes. L’arrivée déclenche une salutation avec son délai habituel. Clic droit ou Fin de l’interaction annule, comme travail/repos, masquage, repas ou nouveau jouet.

La zone des identités propose une liste d’interactions et un bouton pour l’animal actif sélectionné. Le clavier permet salut, courte caresse, toilettage, friandises, jeu/travail/repos ou annulation. La caresse utilise les règles temporisées sans geste du pointeur. Un animal masqué ou inactif n’est pas lancé.

Changer la langue avec la garde-robe ouverte actualise les choix Aucun, Manquant et Valeurs par défaut. Les couleurs, pièces, noms de tenues non appliqués et la position de l’aperçu sont conservés. Les noms fournis par les auteurs restent inchangés.

Pour définir une destination au clavier, choisissez Viens ici dans la gestion des animaux et saisissez les décalages horizontal/vertical en pixels logiques. Les valeurs négatives signifient gauche/haut. La destination reste proche ; le mode sol ignore le décalage vertical. Exécuter lance l’appel, terminer l’interaction l’annule. Les animaux occupés ou non compatibles gardent leur interaction.

Puppet accepte aussi Viens ici depuis son menu ou les décalages clavier du gestionnaire. La fenêtre entière et le repère restent dans la zone de travail. Le centre atteint la cible pendant une demi-seconde avant la salutation commune. Déplacement manuel, soins, modes, masquage, changement de taille ou de zone et commandes du modèle annulent l’appel. Une réaction walk déclarée est utilisée, sinon l’apparence native reste intacte. Le minuteur ne tourne que pendant l’appel. Validation GL/focus native en attente.

Puppet peut poursuivre un point lumineux déplaçable depuis son menu. Le gestionnaire permet aux animaux en calques et Puppet de placer ce point au clavier. Relâché près de l’animal pendant une demi-seconde, il lance le jeu commun de trois secondes ; l’affection arrive seulement à la fin, avec le délai normal. Appel et lumière partagent une cible. Ranger, terminer, soigner, déplacer manuellement, changer de mode ou masquer annule.

Le menu Puppet propose aussi Lancer une balle, et les gestionnaires des animaux en calques et Puppet peuvent la lancer pour l’identité choisie. Physique, relance par glisser, rangement par clic droit, 1 affection et 30 secondes de récupération sont partagés avec les animaux en calques ; la fenêtre Puppet poursuit la balle, la ramasse et la rapporte à son centre d’origine, sans quitter la zone de travail. Chaque relance redémarre le délai. Balle, lumière et Viens ici partagent une cible : en lancer un remplace l’autre. Soins, déplacement manuel, changement de mode ou masquage annulent sans récompense. L’animation de rapport dédiée reste à faire.

L’ajout d’un personnage intégré affiche la progression de la création et de l’installation validée du personnage et de ses vêtements. Le pourcentage indique les étapes terminées, pas le temps restant. La barre disparaît après réussite ou échec. Fermer la garde-robe annule le travail restant.

Les messages d’interaction apparaissent au-dessus du bouton d’exécution, près du focus clavier. Dans les fenêtres étroites, les titres de section et les boutons de détails passent à la ligne. Les champs d’identité et d’interaction gardent une largeur minimale lisible et passent sous leur libellé si nécessaire. La sélection, les valeurs et les commandes sont conservées.

Les champs de personnalisation exposent leurs libellés visibles via l’accessibilité Qt. Les noms des friandises préférées ou détestées, de la taille, de la vitesse, du volume, du comportement, du bavardage et de l’amplitude des animations suivent la langue de l’interface.

Les champs de garde-robe et de photo exposent leurs libellés visibles via l’accessibilité Qt, notamment les emplacements de vêtements, les tenues enregistrées, la pose et son instant. Ces noms suivent la langue de l’interface sans modifier le brouillon ni la photo.

L’option « Pose capturée » suit la langue de l’interface sans changer la pose sélectionnée, son instant ni la photo.

Si la fenêtre photo se ferme pendant le choix de l’emplacement, le chemin retourné est ignoré. Aucune nouvelle photo n’est écrite et les fichiers existants restent inchangés. Une fenêtre photo fermée refuse aussi les demandes ultérieures d’enregistrement.

Fermer la garde-robe pendant le choix d’un dossier ou d’une couleur annule le résultat retourné. Aucune installation ne démarre et aucune couleur ne change. Les demandes ultérieures de sélection de cette garde-robe fermée sont aussi ignorées.

Le dîner entre amis se déclenche lorsque trois habitants au moins mangent dans la même zone. Des repas dans des zones séparées ne constituent pas une même réunion. Cet événement est enregistré au plus une fois par jour du foyer, même après sauvegarde et réouverture.
