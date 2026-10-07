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

Scène → Éditeur visuel propose liste et aperçu des calques image/GIF/texte, déplacement groupé, redimensionnement par le coin, position/taille/échelle/rotation/ordre/opacité, alignement, verrouillage, visibilité, duplication et 100 annulations/rétablissements (Ctrl+Z/Ctrl+Y). Exportez directement .fescene ; l’onglet Script permet aussi de modifier et appliquer le JSON. La lecture restitue taille, échelle, rotation et visibilité explicites. Le JSON externe ouvre un nouvel historique ; les champs existants restent intacts.

Scène → Script → Modèles de scène (aussi dans la palette de commandes) propose Bureau de travail, Enseignement et Concentration avec texte traduit et modifiable. Prévisualisez, choisissez l’écran principal ou son numéro puis Appliquer et lire ; les proportions s’adaptent à la taille logique disponible. Les modèles incluent leurs ressources. Les ressources absentes sont indiquées par calque/champ/chemin et bloquent l’application. La transaction de scène remplace éditeur et lecture ; une préparation échouée préserve la scène précédente. Modifiez le texte, ajoutez des médias et exportez en JSON ou .fescene portable. Fermer la bibliothèque annule seulement sa propre application en attente. Concentration propose des rappels modifiables ; planification et minuteries restent des outils distincts.

Scène → Éditeur visuel ajoute vidéo, web, Puppet et audio aux images/GIF/textes. Activez explicitement les aperçus : huit sources maximum, muettes avant Écouter, suspendues si masquées, libérées en désactivant ou fermant. Images limitées à 1280 pixels par côté ; les erreurs sont affichées. La lecture des scènes nommées compose vidéos, surface propre du moteur web et images Puppet hors écran Imervue avec tous les calques visuels dans l’ordre z ; l’audio reste invisible. Double-cliquez un calque web/Puppet en lecture ou choisissez Interagir dans l’éditeur pour ouvrir la même fenêtre native. Puppet exige OpenGL natif et le moteur optionnel ; les aperçus n’exécutent pas de scripts et les animaux de scène utilisent un état temporaire. Les fenêtres web/vidéo/Puppet indépendantes restent disponibles. JSON/.fescene conserve tous les types et références pris en charge.

Scène → Éditeur visuel → Chronologie édite x/y/opacité d’un calque déverrouillé, avec modèles de fondu et glissement. Temps uniques croissants : 0–3600 secondes, 128 images clés par calque ; opacité 0–100, position ±100000, linear ou smooth. Cellules vides : canal inchangé. Application annulable ; JSON/.fescene conserve les pistes. Parcourez, lisez, suspendez, reprenez ou relisez l’aperçu sans enregistrer les positions temporaires ; réinitialisez avant modification. Lecture : commandes propres et horloge monotone commune aux écrans. Masquage suspend le temps ; pause explicite conservée après affichage. Les médias suivent la pause ; relire concerne les pistes. Les actions de scène dissolvent un ancien instantané pendant 0,5 seconde, libèrent les moteurs et démarrent à zéro. Anciennes scènes compatibles.
