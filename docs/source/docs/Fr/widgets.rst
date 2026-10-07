Page Widgets
------------

* Spectre audio - des barres ou un anneau qui suivent ce que jouent les
  haut-parleurs, avec un nombre de bandes réglable. Celui-ci capte réellement
  l'audio, en mémoire seulement, pour en calculer les fréquences ; rien n'est
  enregistré ni envoyé, et la capture s'arrête avec le spectre. Windows et macOS (option macos et autorisation ; macOS natif non vérifié ici).
* Moniteur système - processeur, mémoire, disque, batterie et débit réseau dans
  un petit panneau toujours visible. Cochez les lignes voulues ; une ligne
  masquée continue d'enregistrer et montre à son retour ce qui s'est passé
  entre-temps.
* Afficher la lecture en cours - le morceau où en est votre lecteur.
* Pense-bête - « Nouvelle note » en pose une sur le bureau, « Fermer les notes »
  les retire. « Rouvrir mes notes au démarrage » les ramène la fois suivante.

Widgets → Tâches et calendrier propose coches, échéance locale facultative et import UTF-8 .ics local de VEVENT/VTODO individuels. Aujourd’hui montre tâches inachevées sans date/du jour/en retard et événements chevauchants ; fins de journée entière/minuit exclusives. IANA TZID connue via Qt, UTC affiché localement, flottant local et date inchangée. DST : première occurrence répétée, décalage avant trou ; jours DURATION nominaux locaux. UID+RECURRENCE-ID met à jour, SEQUENCE inférieure ignorée, coches conservées, CANCELLED supprime. Repli/TEXT pris en charge ; liens/alarmes/pièces jointes jamais ouverts. RRULE/RDATE/EXDATE/zones inconnues refusés atomiquement, exporter occurrences seules. tasks.json près paramètres : 500 éléments/quatre MiB, titre 1000/description 2000 caractères, écriture atomique conserve ancien en cas d’erreur. Import quatre MiB/ligne 8192 caractères, sans réseau/sync/alarmes. Worker différé sérialise fichiers, fermer arrête timers/résultats tardifs. Aujourd’hui enregistré dans fermeture/masquage global, ouverture explicite sans restauration automatique ; données durables.

Traces d’annulation comptent dans les 500 et empêchent les anciens imports de ressusciter les événements. Effacer tout confirme puis retire tâches, événements et annulations. Aujourd’hui utilise le dessin logiciel Qt ordinaire pour ne pas couvrir ses commandes.
