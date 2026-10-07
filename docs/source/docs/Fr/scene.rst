Page Scène
----------

.. image:: ../image/scene/scene.png

Une scène réunit plusieurs calques et s'enregistre dans un fichier.

* Ajouter une page web - adresse et opacité.
* Ajouter une vidéo - fichier, opacité, vitesse, volume.
* Ajouter une image - fichier et opacité.
* Ajouter un GIF - fichier, opacité, vitesse.
* Ajouter un son - fichier et volume.
* Ajouter du texte - texte, opacité, taille, alignement.
* Démarrer la scène - afficher tout ce qui a été ajouté.
* Exporter le fichier de scène.
* Charger un fichier de scène - retrouver une scène enregistrée.
* Effacer tous les scripts - repartir de zéro.
* Afficher sur tous les écrans - une copie par moniteur.

Scènes : la page Scène accepte l’ancien JSON de correspondance des entrées, un document versionné frontengine.scene et les paquets portables .fescene. Une entrée PUPPET contient position, taille, opacité, paramètres numériques finis et animation, expression ou script facultatifs. Les chemins JSON sont relatifs au fichier de scène. .fescene inclut les médias référencés, le .puppet original et le .petscript.json facultatif pour changer d’ordinateur. L’importation vérifie chemins, liens symboliques, versions et limites d’extraction. Une scène FrontEngine reste un paquet de scène ; .puppet reste un personnage Imervue.

:doc:`runtime_interoperability`

Scène → Éditeur visuel propose liste et aperçu des calques image/GIF/texte, déplacement groupé, redimensionnement par le coin, position/taille/échelle/rotation/ordre/opacité, alignement, verrouillage, visibilité, duplication et 100 annulations/rétablissements (Ctrl+Z/Ctrl+Y). Les autres types sont conservés comme cadres. Exportez directement .fescene ; l’onglet Script permet aussi de modifier et appliquer le JSON. La lecture restitue taille, échelle, rotation et visibilité explicites. Le JSON externe ouvre un nouvel historique ; les champs existants restent intacts.

Scène → Script → Modèles de scène (aussi dans la palette de commandes) propose Bureau de travail, Enseignement et Concentration avec texte traduit et modifiable. Prévisualisez, choisissez l’écran principal ou son numéro puis Appliquer et lire ; les proportions s’adaptent à la taille logique disponible. Les modèles incluent leurs ressources. Les ressources absentes sont indiquées par calque/champ/chemin et bloquent l’application. La transaction de scène remplace éditeur et lecture ; une préparation échouée préserve la scène précédente. Modifiez le texte, ajoutez des médias et exportez en JSON ou .fescene portable. Fermer la bibliothèque annule seulement sa propre application en attente. Concentration propose des rappels modifiables ; planification et minuteries restent des outils distincts.
