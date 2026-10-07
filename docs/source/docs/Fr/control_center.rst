Page Centre de contrôle
-----------------------

.. image:: ../image/control_center/control_center.png

Une page qui atteint chaque calque, y compris ceux ouverts par les autres
pages.

Fermeture

* Fermer toutes les vidéos / images / GIF / pages / sons / textes - ce type-là
  seulement.
* Tout fermer - chaque calque à l'écran, quelle que soit la page qui l'a ouvert.
* Effacer le journal - vider la zone de messages à droite.

Tout d'un coup

* Tout masquer / Tout afficher - ranger un instant, puis récupérer.
* Tout couper - faire taire ce qui produit du son.
* Verrouiller / déverrouiller les calques - déverrouillés, ils se déplacent à la
  souris et retiennent où on les a déposés ; verrouillés, ils laissent passer
  les clics.
* Fond vert - peindre le fond d'une couleur unie pour l'incruster dans OBS ou
  équivalent.
* Réinitialiser la position des calques - tout remettre où c'était au départ.
* Mode économie - baisser la cadence et la résolution quand la batterie compte.
* Qualité - Élevée, Équilibrée ou Économie : la même idée, en plus fin.
* Masquer de la capture - les calques restent sur votre écran mais disparaissent
  de ce qu'enregistre un partage d'écran. Windows uniquement. Un cache de la page
  Concentration reste visible, puisque recouvrir est sa seule raison d'être.
* Épingler à ce bureau - les calques restent sur le bureau virtuel où ils ont
  été ouverts. Sur un autre bureau ils s'effacent, et reviennent au retour.
  Détacher ramène tout ce qui avait été rangé. Windows uniquement.

Centre de contrôle → Suivre une fenêtre choisit overlay enregistré de premier niveau et cible Windows visible. Décalage initial proportionnel suit déplacement/taille ; taille logique overlay, position physique sans activation/redimensionnement, bornée au moniteur, vérifiée 250 ms. Minimiser masque ; retour respecte masquage manuel/global ; fermer/masquer/perdre identité détache. Propriété unique réversible + PID/thread bloque réutilisation HWND ; UIPI/cible élevée peut refuser. Détacher avant nouveau décalage. 64 liaisons temporaires sans restauration ; fermer/tout fermer/quitter retire cookies/arrête timer. Adaptateur Windows vérifié uniquement, autre plateforme indique raison. Fenêtres propres sur écran 125% vérifiées ; DPI mixtes multi-écran nécessitent second écran.

Centre de contrôle → Profils de moniteurs sauvegarde/restaure combinaisons matérielles (20 profils/200 fenêtres/512 KiB, monitor-profiles.json local). Positions proportionnelles suivent résolution/principal/DPI, tailles logiques conservées ; combinaison inconnue ramène fenêtres au principal. Automatique opt-in séparé, regroupement 500 ms des overlays/événements Qt, aucun réglage système modifié. Matériel ambigu signalé ; mêmes type/nom exclus mais ramenables. Plein écran/scènes/suivi exclus ; aucun overlay créé ni handle deviné. Coordonnées Qt logiques uniquement. Vérifié nativement sur un écran Windows 125% ; branchement/débranchement, principal et DPI mixtes nécessitent matériel supplémentaire.

Composition logicielle statique garde une image ≤16 MP ; contenu/DPR, transformation, opacité, ordre, clip, taille/DPI invalident. Pas de repaint si inchangé, animation/vidéo restent actives ; GPU readback inchangé. Quitter/Tout fermer partagent sources : fermer une fois avant vider, réinitialiser fonds, cleanup avant assets. Timer non bloquant conserve Qt pendant fin des jobs locaux annulés. Manifest API v1 ; examples/plugins/clock montre QWidget avec overlay_widgets, release_overlay_resources/shutdown facultatifs, get_state/set_state. Préréglages des plugins chargés sous plugin:<nom page>, rollback transactionnel, sans charger code. Copier exemple dans plugins/, activer et approuver digest ; pas de sandbox OS. Benchmark : py -m benchmarks.scene_composition --output build/scene-benchmark.json, --baseline-file fiable optionnel compare pixels ; procédure/données docs/benchmarks/README.md.
