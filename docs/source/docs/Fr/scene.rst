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
