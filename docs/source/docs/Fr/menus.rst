Préréglages et réglages
-----------------------

Menu Préréglages

* Enregistrer un préréglage… - les réglages de toutes les pages, sous un nom.
* Charger un préréglage… - le retrouver.
* Supprimer un préréglage…
* Exporter… / Importer… - déplacer d'une machine à l'autre en json.
* Exporter un paquet (+médias) / Importer un paquet (+médias) - la même chose,
  mais avec les images, vidéos et sons utilisés, en zip.
* Définir comme préréglage de démarrage… - l'appliquer au lancement.
* Importer du contenu Workshop… - installer les préréglages et packs de mascotte
  auxquels vous êtes abonné sur Steam.

Menu Réglages

* Raccourcis clavier… - raccourcis globaux pour tout masquer, tout afficher,
  tout fermer, tout couper, l'opacité, la page suivante du tableau de bord, le
  verrouillage, le gel de l'écran, la liste des raccourcis, ainsi que
  lecture/pause, piste suivante et précédente, et le déplacement de la fenêtre
  active vers l'écran suivant en conservant ses proportions.
* Thème jour/nuit programmé - clair le jour, sombre la nuit.
* Lancer au démarrage du système - ouvrir FrontEngine à l'ouverture de session.
* Restaurer la dernière session - rouvrir ce qui était affiché la dernière fois.
* Charger des extensions (avancé) - les extensions sont du Python et tournent
  avec les mêmes droits que FrontEngine ; n'installez que ce en quoi vous avez
  confiance.
* Pause intelligente… - ranger les calques pendant qu'une application est en
  plein écran, sur batterie, ou quand des applications nommées sont au premier
  plan.
* Garder l'écran allumé - empêche l'écran de s'éteindre tant que quelque chose est
  affiché. Relâché quand vous désactivez l'option et quand FrontEngine se ferme :
  les réglages d'alimentation habituels reprennent.
* Profils d'application… - appliquer un préréglage dès qu'une application donnée
  passe devant.
* Rappels… - un message toutes les tant de minutes, ou à une heure donnée.
* Règles… - « quand ces conditions sont réunies, fais ceci ». Un jour de la
  semaine, une plage horaire et l'application au premier plan se combinent ;
  l'action applique un préréglage, masque, affiche ou ferme les calques, ou
  définit la qualité. Une condition vide signifie « indifférent », et une règle
  s'exécute une fois quand ses conditions deviennent vraies, pas en continu.
* Économiseur d'écran… - après tant de minutes sans souris ni clavier, afficher le
  calque d'une page choisie ; un mouvement de souris le retire. Il utilise la page
  telle que vous l'avez réglée et ne ferme que ce qu'il a ouvert : ce que vous
  aviez laissé tourner est toujours là à votre retour.
* Préréglage programmé… - appliquer un préréglage à une heure, les jours choisis.
  Sans jour coché, tous les jours. Il se déclenche au passage de l'heure : démarrer
  plus tard ne le rattrape pas.
* Mode affichage… - faire défiler une liste de préréglages sur minuterie, pour
  une machine laissée en vitrine. La fenêtre principale peut alors partir dans
  la zone de notification - mais seulement s'il y en a une pour la ramener.
* Commande par téléphone : Paramètres → Commande à distance propose uniquement HTTPS, un jeton renouvelé à chaque démarrage et une liste fixe d’actions. Le téléphone ne fait pas automatiquement confiance au certificat autosigné. Exportez le certificat public et comparez l’empreinte SHA-256 affichée avant l’importation ou l’approbation dans les réglages du téléphone/navigateur. La clé privée reste dans le dossier de données utilisateur. Un changement d’IP, l’expiration ou une régénération peuvent nécessiter une nouvelle approbation. Un échec de TLS ne revient jamais à HTTP.
* Confidentialité du partage d'écran… - masquer les calques d'une capture tant
  qu'une application de réunion est ouverte. La comparaison porte sur les titres
  de fenêtres, ce qui attrape aussi une réunion dans un onglet. Windows
  uniquement.
* Temps d'écran… - le temps passé dans chaque application. Reste sur cette
  machine et n'est envoyé nulle part.
* Historique du presse-papiers… - ce que vous avez copié récemment, avec
  recherche et épinglage. Gardé en mémoire seulement sauf demande contraire, car
  les presse-papiers contiennent souvent des mots de passe.
* Exporter les réglages… / Importer les réglages…

Menu Aide

* **Comment l'utiliser…** - un guide court dans l'application : votre premier
  calque, les réglages communs à toutes les pages, et comment dégager l'écran.
* **Liste des raccourcis…** - les raccourcis globaux tels qu'ils sont réellement
  attribués, affichés par-dessus l'écran. Les réattribuer met aussi cette liste à
  jour. Appuyez de nouveau sur le raccourci, ou sur Échap, pour la retirer.
* Le suivi des problèmes, et le rappel que F12 ferme FrontEngine aussitôt.

Plugins : activer leur chargement ne les autorise pas. plugin.json ou le fichier associé à un plugin unique déclare version, identité, point d’entrée et capacités ; l’accord est vérifié avant l’import Python et lié à l’empreinte du contenu. Code ou déclaration modifiés demandent un nouvel accord ; les anciens plugins exigent une confiance totale explicite. Paramètres → Révoquer les autorisations des plugins efface les accords stockés ; redémarrez pour décharger le code en cours. Les plugins Python gardent tous les privilèges de l’application : déclaration et consentement ne sont pas un bac à sable système.

Rendu : Paramètres → Rendu des superpositions propose Automatique, GPU ou Logiciel et affiche le moteur réellement utilisé. Le compositeur GPU utilise textures OpenGL, shaders et framebuffers pour l’ordre, les transformations, l’opacité et le découpage ; un échec d’initialisation revient au logiciel avec une raison. Le contenu QPainter peut encore être rasterisé sur CPU avant l’envoi ; les widgets web/vidéo/natifs peuvent utiliser des fenêtres séparées. La capture et l’enregistrement peuvent relire les images GPU vers le CPU. Cela ne promet ni capture sans copie ni accélération mesurée. La composition GPU des scènes couvre actuellement IMAGE, GIF et TEXT ; les puppets utilisent leur propre fenêtre Imervue.

:doc:`runtime_interoperability`

Paramètres → Autorisations et capacités macOS indique pour chaque fonction disponible, indisponible ou non prise en charge, avec la raison liée à l’autorisation ou à l’installation.

Ouvrez Commandes dans le menu ou utilisez Ctrl+K / Ctrl+Maj+P dans FrontEngine. Recherchez dans la langue actuelle, les libellés anglais ou les noms stables ; les flèches sélectionnent et Entrée exécute. Navigation, capture, notes, filtre, Workshop et actions globales sont disponibles. Les actions préréglage/qualité acceptent une valeur. Favoris et 20 dernières commandes persistent ; paramètres et recherche ne sont pas enregistrés.
