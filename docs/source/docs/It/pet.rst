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

Animale → Crea pacchetto associa walk/idle/sleep/climb/fall/drag, mostra dimensione e velocità di camminata ed esporta una cartella portatile con pet.json. Almeno un’azione; azioni assenti segnalate e gestite dal ripiego del caricatore. PNG/JPEG/GIF/WebP: 64 MiB e 16 megapixel per file, totale 256 MiB. Importazione/esportazione in background, annullabile, senza sovrascrivere cartelle esistenti. Cartelle trasferibili, selezionabili in Animale e condivisibili come pacchetti Workshop. Importa solo sprite selezionati, nome, dimensione e velocità, senza suoni, script o dialoghi. Imervue .puppet usa un formato di creazione separato. Chiusura/Escape libera animazioni e annulla operazioni.

Interazioni e stato salvato
~~~~~~~~~~~~~~~~~~~~~~~~~~~

I profili della versione 2 conservano UUID e statistiche della versione 1 e aggiungono energia, modalità scelta, preferenze e riferimenti di aspetto convalidati. 

Il menu dello sprite permette di salutare, accarezzare delicatamente e spazzolare, oltre a scegliere le modalità persistenti Giocare insieme, Lavorare insieme e Riposare. Termina l’interazione annulla l’azione in corso. Le azioni a tempo danno benefici solo al completamento; annullarle non dà ricompense. Un animale sazio rifiuta il cibo e occorre una pausa prima di ripetere un’azione. Trascinare l’animale o cambiarne l’aspetto non dà ricompense. Non è ancora presente un’interfaccia per i giocattoli.

La cura segue il tempo attivo, indipendentemente dai fumetti. Il tempo trascorso nascosto o offline non accumula cure o ricompense da recuperare. Gli sprite usano la sessione di interazione condivisa per le azioni del menu e le modalità. Gli animali Puppet condividono la sessione e le regole di alimentazione; le loro risposte visive native dipendono dalle capacità del runtime e del modello.

Scegli un’identità nella pagina Animale e apri «Personalizza l’animale», disponibile anche nel menu dell’animale. Ogni identità conserva dimensione (16–512), velocità (1–20), comportamento a terra/girovagare/inseguire, arrampicata, sosta sulle finestre, fumetti, volume (0–100), calma durante la digitazione, riposo automatico, lanci e interazioni sociali. «Usa le impostazioni della pagina» eredita le impostazioni di presentazione della pagina; clonazione e importazione mantengono quelle individuali. «Applica» salva atomicamente prima di aggiornare l’animale attivo. «Annulla» non modifica nulla; il ripristino richiede «Applica». Errori di salvataggio o conflitti mantengono la bozza. Puppet disabilita i controlli non supportati e applica solo dimensione, fumetti e calma durante la digitazione tra le impostazioni di presentazione. Il guardaroba nativo e la grafica a livelli restano da completare.

Identità animali → Guardaroba apre un’anteprima animata separata dei personaggi installati. Installa cartella risorse verifica layered-pet.json e copia le risorse in pet-assets accanto alle impostazioni locali. Scegli testa, collo, corpo e schiena, azioni e direzione; salva fino a 20 completi per identità. Rimuovi prima gli elementi in conflitto. Applica salva e aggiorna lo Sprite attivo; Annulla scarta le modifiche dopo l’ultima applicazione. I riferimenti mancanti restano salvati: ripara le risorse e aggiorna. Puppet non supporta questi abiti Sprite. Aggiungi personaggio integrato disegna uno dei sei personaggi INKSIDE (MOCHI, MOSS, PIP, BOLT, INK o GILL) con trenta capi da quattordici completi adattati al suo corpo e li installa in background con la stessa convalida; chiudere il guardaroba annulla. Ogni personaggio offre varianti di occhi, bocca e tre parti del corpo, oltre a zone ricolorabili, e ogni capo segue tutte le animazioni.

Il guardaroba mostra le zone colore dichiarate dal personaggio o dall’abito. Scegli zona e colore oppure ripristina l’originale. Si colorano solo i livelli maschera designati; contorni e altri dettagli restano invariati. I colori si vedono prima di Applica e vengono salvati per identità e completo, anche nell’esportazione/importazione. Senza zone dichiarate i controlli sono disattivati.

Se il salvataggio fallisce durante la chiusura, l’animale resta aperto con lo stato attuale e il timer di ripetizione. Chiudi tutto conserva gli animali non chiusi; l’uscita attende il salvataggio prima di liberare le risorse. L’affetto si ferma al limite supportato, evitando profili non salvabili dopo ulteriori premi.

Saluti e inseguimenti richiedono entrambi gli animali visibili in modalità gioco, senza interazioni in corso, con socialità abilitata e senza trascinamento o pausa di digitazione. Gli animali non disponibili escono da bersagli e ruoli. Il gioco si ferma con meno di due partecipanti idonei e riprende al ritorno. Disattivare i fumetti nasconde solo il testo, non i premi sociali.

Il timer di concentrazione porta gli animali visibili senza interazioni in modalità Lavoro, poi Riposo nelle pause. Stop ripristina i modi precedenti salvo modifiche manuali. Ogni ciclo completo dà una sola volta 3 affetto e 5 umore ai compagni visibili idonei; interruzione anticipata o animali nascosti non ricevono il premio. Lavoro/Riposo blocca le chiacchiere spontanee. Il timer usa tempo trascorso monotono, indipendente dall’orologio di sistema.

All’avvio della concentrazione i compagni si dispongono in basso a destra nel proprio schermo se c’è spazio. Lo stop ripristina la posizione precedente solo senza spostamenti o cambi di modalità manuali.

I personaggi a livelli possono offrire varianti del viso e del corpo. Il guardaroba le mostra per animale; Applica le salva e gli abiti conservano personaggio e parti. Ogni variante deve coprire tutti i fotogrammi. La grafica definitiva dei sei personaggi resta da realizzare.

Il menu Sprite offre una foto: congela l’aspetto attuale o scegli una posa a livelli e salva un PNG trasparente. Desktop e fumetti sono esclusi. Le foto Puppet usano un renderer Imervue compatibile e inizializzato per un’immagine trasparente fissa, senza catturare il desktop. La verifica GL nativa resta da eseguire.

Per gli Sprite scegli Accarezza e muovi il puntatore avanti e indietro. Tre movimenti netti avviano una reazione; piccoli tremori non contano. Trascinamento e gioco sociale si fermano. Uscire, nascondere, cambiare modalità o terminare annulla la carezza incompleta. I premi richiedono completamento e attesa.

Gli Sprite possono lanciare e riporre una palla. Trascina e rilascia per rilanciarla, clic destro per rimuoverla. L’animale la riporta vicino alla partenza; il ritorno dà 1 affetto con 30 secondi attivi di attesa. Lavoro/riposo, altre interazioni, nascondere, pausa durante la digitazione o timeout annullano senza premio. Anche Puppet riporta la palla (vedi sotto).

Gli animali a terra lasciano i bordi delle finestre per recuperare la palla. Le soste sulle finestre si sospendono durante il gioco e riprendono dopo; il ritorno avviene a terra vicino alla posizione orizzontale iniziale.

Il punto luminoso è un piccolo bersaglio trascinabile a distanza limitata. Gli animali a terra lo seguono sul pavimento. Rilascia il bersaglio e lascia che venga raggiunto per avviare una breve reazione, premiata al completamento con l’attesa esistente. Clic destro o Riponi termina. Un solo giocattolo per animale.

La clonazione usa immagine/modello, aspetto, preferenze e libreria dell’animale originale, anche dopo una diversa scelta nelle impostazioni. Il clone ha una nuova identità; modifiche a vestiti o parti non alterano l’originale. I cloni Puppet mantengono script, parametri ed espressioni attive.

Il completamento valido della concentrazione richiede celebrate e poi Riposo. Un cambio di guardaroba richiede outfit_show. Le reazioni durano due secondi attivi, senza premi aggiuntivi né salvataggio; azioni o modalità manuali le interrompono. Animazioni mancanti usano idle. Grafica finale e associazioni Puppet restano da fare.

Seleziona un’identità attiva e Riporta l’animale per spostarla nell’area utile dello schermo scelto. Gli animali nascosti riappaiono, interazioni incomplete e giocattoli si fermano, i limiti Sprite seguono lo schermo. Aspetto e valori restano invariati. Avvia gli inattivi e riduci quelli troppo grandi.

Gli script Puppet possono usare frontengine_actions per associare stati a movimenti ed espressioni esistenti. I nomi sono verificati prima dell’avvio; nessuna animazione viene indovinata. Il completamento rilascia gli effetti della reazione e conserva le scelte manuali. Formato: docs/formats/puppet-companion-actions.md. Verifica visiva nativa in sospeso.

Dopo la scelta di accarezzare, Puppet attende movimenti avanti e indietro del puntatore. Uscita, Esc, nascondimento, cambio modalità o quiete annullano la carezza incompleta. Il trascinamento è disabilitato durante la carezza. Verifica nativa dei gesti in sospeso.

Il guardaroba offre sei colori rapidi per la zona dichiarata selezionata. Anteprima e poi Applica; Annulla conserva l’aspetto salvato. Restano disponibili scelta libera e ripristino del colore.

I menu Sprite e Puppet offrono quattro spuntini immaginari senza trascinare file. Completamento, sazietà e attesa restano condivisi. Nutrire interrompe la carezza incompleta senza premio; Sprite ripone il giocattolo.

Ogni animale può salvare uno spuntino preferito e uno diverso sgradito. Cambia solo l’umore a pasto concluso; sazietà, affetto e attesa restano invariati. Modifiche durante il pasto valgono dal successivo. I vecchi profili sono neutrali. food_like e food_dislike sono opzionali; animazioni finali in sospeso.

Gli animali Sprite seguono un segnaposto vicino trascinabile con Vieni qui. Il modo pavimento resta a terra; i modi liberi si muovono su due assi. L’arrivo avvia un saluto con l’attesa normale. Clic destro o Fine interazione annulla, così come lavoro/riposo, nascondimento, cibo o un nuovo gioco.

La sezione identità offre scelta ed esecuzione delle interazioni per l’animale attivo selezionato. Da tastiera sono disponibili saluto, breve carezza, cura, spuntini, gioco/lavoro/riposo e annullamento. La carezza usa le regole temporizzate senza gesti del puntatore. Animali nascosti o inattivi non vengono avviati.

Cambiare lingua con il guardaroba aperto aggiorna le opzioni Nessuno, Mancante e Ripristina predefiniti. Colori, parti, nomi degli abiti non applicati e posizione dell’anteprima restano invariati. I nomi delle risorse rimangono quelli originali.

Per scegliere la destinazione da tastiera, seleziona Vieni qui nella gestione animali e inserisci gli scostamenti orizzontale/verticale in pixel logici. I valori negativi indicano sinistra/alto. La meta resta vicina; la modalità pavimento ignora lo scostamento verticale. Esegui avvia il richiamo, termina interazione lo annulla. Gli animali occupati o non supportati mantengono l’interazione attuale.

Puppet supporta Vieni qui dal menu o dagli scostamenti da tastiera del gestore. Finestra e segnaposto restano nell’area di lavoro. Il centro raggiunge la meta per mezzo secondo prima del saluto comune. Trascinamento, cura, modalità, nascondimento, modifiche a dimensioni o area e comandi manuali annullano il richiamo. Viene usata la reazione walk dichiarata, altrimenti resta l’aspetto nativo. Il timer funziona solo durante il richiamo. Verifica GL/focus nativa in sospeso.

Puppet può inseguire un punto luminoso trascinabile dal menu. Il gestore permette a Sprite e Puppet di posizionarlo da tastiera. Rilasciato vicino all’animale per mezzo secondo avvia il gioco comune di tre secondi; l’affetto arriva solo al termine, con l’attesa normale. Richiamo e luce condividono una meta. Riporre, terminare, curare, trascinare, cambiare modalità o nascondere annulla.

Anche il menu Puppet offre Lancia una palla, e i gestori Sprite e Puppet possono lanciarla per l’identità scelta. Fisica, rilancio trascinando, rimozione con clic destro, 1 affetto e 30 secondi di attesa sono condivisi con Sprite; la finestra Puppet insegue la palla, la raccoglie e la riporta al centro originale, restando nell’area di lavoro. Ogni rilancio riavvia il timeout. Palla, luce e Vieni qui condividono una meta: avviarne una sostituisce l’altra. Cura, trascinamento, cambio modalità o nascondere annullano senza premio. L’animazione di riporto dedicata è in sospeso.
