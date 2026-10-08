Pagina Widget
-------------

* Spettro audio - barre o un anello che si muovono con ciò che riproducono gli
  altoparlanti, con numero di bande regolabile. Questo cattura davvero l'audio,
  ma solo in memoria per calcolarne le frequenze; nulla viene registrato o
  inviato, e la cattura finisce insieme allo spettro. Windows e macOS (opzione macos e permesso; macOS nativo non verificato qui).
* Monitor di sistema - processore, memoria, disco, batteria e traffico di rete
  in un piccolo pannello sempre visibile. Spunta le linee che vuoi; una linea
  nascosta continua a registrare e al ritorno mostra cosa è successo nel
  frattempo.
* Mostra in riproduzione - il brano a cui è arrivato il tuo lettore.
* Foglietto adesivo - «Nuova nota» ne appiccica uno sulla scrivania, «Chiudi le
  note» li toglie. «Riapri le mie note all'avvio» li riporta la volta dopo.

Widget → Attività e calendario offre spunte, scadenza locale facoltativa e importazione locale UTF-8 .ics di VEVENT/VTODO singoli. Oggi mostra attività incomplete senza data/scadute/odierne ed eventi sovrapposti; fine intera giornata/mezzanotte esclusiva. TZID IANA note con Qt, UTC visualizzato locale, floating locale, date invariate. DST: prima occorrenza duplicata, offset prima del salto; giorni DURATION nominali locali. UID+RECURRENCE-ID aggiorna, SEQUENCE minore ignorata, spunte conservate, CANCELLED rimuove. Folding/escape TEXT; mai aprire link/sveglie/allegati. RRULE/RDATE/EXDATE/zone ignote rifiutate atomicamente, esportare singole occorrenze. tasks.json vicino impostazioni: 500 elementi/quattro MiB, titolo 1000/descrizione 2000 caratteri, scrittura atomica conserva vecchi dati su errore. Import quattro MiB/riga 8192, niente rete/sync/sveglie. Worker avviato su richiesta serializza file, chiusura ferma timer/risultati tardivi. Oggi partecipa a chiusura/nascondi collettivi, apertura esplicita senza ripristino automatico; dati persistenti.

Registrazioni di annullamento contano nei 500 e impediscono che vecchi import ripristinino eventi. Cancella tutto chiede conferma ed elimina attività, eventi e annullamenti. Oggi usa disegno software Qt normale per non coprire i controlli.
