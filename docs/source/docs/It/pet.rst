Pagina Mascotte
---------------

Un compagno che vive sulla scrivania.

* Scegli l'immagine della mascotte - una sola immagine.
* Scegli un pacchetto mascotte… - una cartella con le immagini walk / idle /
  sleep / climb / fall / drag, così si anima.
* Scegli un suono (facoltativo) - ciò che riproduce.
* Fai comparire la mascotte - metterla sullo schermo. Premendo di nuovo ne
  compare un'altra.
* Dimensione, velocità.
* Comportamento - camminare sul pavimento, vagare liberamente, o inseguire il
  cursore.
* Arrampicarsi sui muri - lungo i bordi delle finestre.
* Sedersi sulle finestre - posarsi sul bordo superiore delle altre finestre.
* Fumetti - brevi battute secondo l'ora, quando le si dà da mangiare e così via.
* Fermo mentre scrivi - l'animaletto si ferma mentre digiti e riparte un paio di
  secondi dopo, così non attraversa la riga che stai leggendo.
* Leggere ad alta voce - pronunciare quelle battute.
* Giocare a rincorrersi - due o più mascotte si inseguono.
* Reagire all'audio - la mascotte si muove a tempo. Può seguire gli
  **altoparlanti** o il **microfono**; in entrambi i casi legge solo un livello,
  un singolo numero, e non registra mai ciò che viene detto. Windows e macOS (opzione macos e permesso; macOS nativo non verificato qui).
* Chat IA (serve una chiave API) - parlarle. Legge la variabile d'ambiente
  ANTHROPIC_API_KEY; la chiave non viene mai salvata.
* Timer di concentrazione (min) - un timer di lavoro che la mascotte tiene per
  te, con le pause.

Trascina un file sulla mascotte per darle da mangiare, oppure un'immagine o un
pacchetto per cambiarle aspetto.

Animali puppet: installa l’opzione puppet e un runtime Imervue disponibile, poi scegli o trascina un file originale Imervue .puppet v1 sulla pagina Animale. I vecchi pacchetti di immagini e sprite restano disponibili. I puppet usano canvas, movimenti ed espressioni di Imervue, si possono clonare o chiudere e seguono controlli delle sovrapposizioni e preset. Un .petscript.json facoltativo usa il motore di script esistente di Imervue; i pacchetti FrontEngine pet.json non sono file puppet. Versioni sconosciute, percorsi di archivio pericolosi e risorse invalide sono rifiutati prima del caricamento.

:doc:`runtime_interoperability`

Animale → Identità salva UUID, nome, umore, sazietà e affetto indipendenti per ogni sprite o puppet. Prima di crearlo seleziona un’identità salvata per riprendere dopo il riavvio; Nuovo animale ricomincia. Solo la prima identità migra una volta i vecchi valori comuni. La clonazione copia i valori attuali in una nuova identità; nutrire non modifica gli altri animali. Rinomina, aggiorna, esporta o importa singoli salvataggi JSON; l’importazione crea sempre una nuova identità. Ogni identità può essere attiva una sola volta. I salvataggi non includono immagini, script o chat; le preimpostazioni portatili escludono gli ID locali. Fino a 256 identità restano nelle impostazioni; le modifiche sprite vengono salvate dopo un breve ritardo e alla chiusura. Nutrire un puppet modifica solo i valori salvati, non i movimenti o le dimensioni Imervue.
