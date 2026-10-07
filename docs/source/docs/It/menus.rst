Preimpostazioni e impostazioni
------------------------------

Menu Preimpostazioni

* Salva preimpostazione… - le impostazioni di tutte le pagine, sotto un nome.
* Carica preimpostazione… - richiamarla.
* Elimina preimpostazione…
* Esporta… / Importa… - spostarla fra macchine come file json.
* Esporta pacchetto (+contenuti) / Importa pacchetto (+contenuti) - lo stesso, ma
  con le immagini, i video e i suoni che usa, in uno zip.
* Imposta come preimpostazione di avvio… - applicarla all'avvio di FrontEngine.
* Importa contenuti Workshop… - installare preimpostazioni e pacchetti mascotte
  a cui sei iscritto su Steam.

Menu Impostazioni

* Scorciatoie… - combinazioni globali per nascondi tutto, mostra tutto, chiudi
  tutto, disattiva l'audio, opacità su e giù, pagina successiva della dashboard,
  blocco, fermo immagine, elenco scorciatoie e riproduci/pausa, traccia
  successiva e precedente, e lo spostamento della finestra in primo piano sullo
  schermo successivo mantenendone le proporzioni.
* Tema giorno/notte programmato - chiaro di giorno, scuro di notte.
* Avvia con il sistema - aprire FrontEngine all'accesso.
* Ripristina l'ultima sessione - riaprire ciò che c'era sullo schermo.
* Carica plugin (avanzato) - i plugin sono Python e girano con gli stessi
  privilegi di FrontEngine; installa solo quelli di cui ti fidi.
* Pausa intelligente… - mettere via gli overlay mentre un'applicazione è a
  schermo intero, a batteria, o quando certe applicazioni sono in primo piano.
* Mantieni lo schermo attivo - impedisce allo schermo di spegnersi finché c'è
  qualcosa a video. Viene rilasciato quando disattivi l'opzione e alla chiusura di
  FrontEngine, tornando alle normali impostazioni di risparmio energetico.
* Profili applicazione… - applicare una preimpostazione quando una data
  applicazione passa in primo piano.
* Promemoria… - un messaggio ogni tot minuti, o a un'ora precisa.
* Regole… - «quando valgono queste condizioni, fai questo». Giorno della
  settimana, fascia oraria e applicazione in primo piano si combinano; l'azione
  applica un preset, nasconde, mostra o chiude gli overlay, oppure imposta la
  qualità. Una condizione vuota significa «qualsiasi», e una regola parte una
  volta quando le condizioni iniziano a valere, non di continuo.
* Salvaschermo… - dopo tot minuti senza mouse né tastiera, mette a schermo
  l'overlay di una pagina scelta; muovere il mouse lo toglie. Usa quella pagina
  così come l'hai impostata e chiude solo ciò che ha aperto: quello che avevi
  lasciato attivo è ancora lì al ritorno.
* Preimpostazione pianificata… - applicare una preimpostazione a un orario, nei
  giorni scelti. Senza giorni selezionati, tutti i giorni. Scatta al superamento
  dell'ora: avviare più tardi non la recupera.
* Modalità vetrina… - ruotare una lista di preimpostazioni a tempo, per una
  macchina lasciata accesa come display. La finestra principale può intanto
  andare nell'area di notifica - ma solo se ce n'è una da cui richiamarla.
* Controllo dal telefono: Impostazioni → Controllo remoto usa solo HTTPS, un token nuovo a ogni avvio e un elenco fisso di azioni. Il telefono non considera automaticamente attendibile il certificato autofirmato. Esporta il certificato pubblico e confronta l’impronta SHA-256 visualizzata prima di importarlo o approvarlo nelle impostazioni del telefono/browser. La chiave privata resta nella cartella dati dell’utente. Cambi IP, scadenza o rigenerazione possono richiedere una nuova approvazione. Se TLS non parte, non si torna a HTTP.
* Privacy nella condivisione schermo… - nascondere gli overlay da una cattura
  mentre è aperta un'applicazione per riunioni. Il confronto è sui titoli delle
  finestre, così viene individuata anche una riunione in una scheda del browser.
  Solo su Windows.
* Tempo di utilizzo… - quanto tempo passi in ogni applicazione. Resta su questa
  macchina e non viene inviato altrove.
* Cronologia degli appunti… - ciò che hai copiato di recente, con ricerca e
  fissaggio. Tenuta solo in memoria salvo richiesta contraria, perché negli
  appunti finiscono spesso delle password.
* Esporta impostazioni… / Importa impostazioni…

Menu Aiuto

* **Come si usa…** - una guida breve dentro l'applicazione: il primo overlay,
  le impostazioni comuni a tutte le pagine, e come liberare di nuovo lo schermo.
* **Elenco scorciatoie…** - le scorciatoie globali come sono realmente assegnate,
  mostrate sopra lo schermo. Riassegnarle aggiorna anche questo elenco. Premi di
  nuovo la scorciatoia, o Esc, per toglierlo.
* La segnalazione problemi, e il promemoria che F12 chiude subito FrontEngine.

Plugin: abilitare il caricamento non autorizza un plugin. plugin.json o un sidecar per un singolo file dichiara versione, identità, punto d’ingresso e capacità; il consenso viene controllato prima dell’import Python e legato all’impronta del contenuto. Cambi a codice o dichiarazione richiedono nuovo consenso; i plugin vecchi richiedono fiducia completa esplicita. Impostazioni → Revoca autorizzazioni dei plugin elimina le approvazioni salvate; riavvia per scaricare il codice attivo. I plugin Python conservano tutti i privilegi dell’applicazione: dichiarazione e consenso non sono una sandbox del sistema operativo.

Rendering: Impostazioni → Rendering delle sovrapposizioni offre Automatico, GPU o Software e mostra il backend effettivo. Il compositore GPU usa texture OpenGL, shader e framebuffer per ordine, trasformazioni, opacità e ritaglio; errori di inizializzazione passano al software con una motivazione. I contenuti QPainter possono ancora essere rasterizzati sulla CPU prima del caricamento; widget web/video/nativi possono usare finestre separate. Cattura e registrazione possono leggere i fotogrammi GPU sulla CPU. Non è una promessa di cattura senza copie o accelerazione misurata. La composizione GPU delle scene comprende attualmente IMAGE, GIF e TEXT; i puppet usano una propria finestra Imervue.

:doc:`runtime_interoperability`

Impostazioni → Permessi e capacità macOS elenca ogni funzione come disponibile, non disponibile o non supportata, indicando il motivo legato a permessi o installazione.

Apri Comandi dal menu o premi Ctrl+K / Ctrl+Maiusc+P in FrontEngine. Cerca nella lingua attuale, nelle etichette inglesi o nei nomi stabili; frecce per selezionare, Invio per eseguire. Include navigazione, cattura, note, filtro, Workshop e azioni globali. Preset/qualità accettano un valore. Preferiti e ultimi 20 comandi restano dopo il riavvio; parametri e ricerche non vengono salvati.

Preimpostazioni → Versioni delle preimpostazioni conserva fino a 50 istantanee distinte per preimpostazione anche dopo il riavvio. Il salvataggio registra la configurazione precedente e quella nuova senza duplicati. La selezione mostra le differenze dei campi rispetto alle impostazioni attuali delle pagine. L’anteprima applica quella configurazione ai controlli; Annulla, Escape o la chiusura ripristina le impostazioni iniziali. Ripristina applica e salva la versione, annullando le modifiche alle pagine in caso di errore. Le istantanee contengono i percorsi dei media, senza copiarli; l’anteprima non apre sovrapposizioni. Le preimpostazioni JSON/ZIP esistenti rimangono compatibili. La cronologia in presets/.versions resta disponibile dopo l’eliminazione se si riutilizza il nome.

Impostazioni → Regole aggiunge priorità (-1000…1000), attesa (0…86400 secondi interi), anteprima condizioni e cronologia di sessione. Le regole attivate vengono eseguite da priorità bassa ad alta, mantenendo l’ordine della tabella a parità. L’attesa usa un orologio monotono: una transizione bloccata viene consumata e la scadenza non esegue azioni mentre le condizioni restano vere. L’anteprima verifica righe non salvate senza azioni o transizioni consumate. Gli ultimi 200 eventi conservano condizioni, contesto e risultati inviato/eseguito/errore/attesa solo in memoria. Le righe nominate non valide impediscono il salvataggio. Fino a 200 regole hanno identità distinte anche con nomi uguali; le condizioni non mostrate sono preservate. Gli errori riportati dalle azioni vengono registrati senza fermare le regole successive.

Le regole caricano, riproducono o fermano scene e mostrano, nascondono, spostano o cambiano l’opacità di livelli nominati. Seleziona la riga e Scegli scena / livello per sfogliare JSON, .fescene o .puppet e scegliere schermo principale/tutti/indice e un livello dell’editor. Un percorso vuoto riproduce la scena corrente. I file sono letti in background; un candidato fallito mantiene la riproduzione esistente. L’ultima richiesta sostituisce quelle in attesa; le azioni livello successive attendono e falliscono con essa. Livelli bloccati o assenti sono rifiutati. Le modifiche sono annullabili e aggiornano la riproduzione; opacità 0–100, posizione ±100000. Ferma annulla le richieste e chiude la riproduzione; le risorse dell’editor restano fino alla sostituzione o chiusura. La cronologia registra l’esito asincrono effettivo. Tavolozza comandi: percorso o {"path":"scene.fescene","screen":"primary"}, chiave livello per mostra/nascondi, {"layer":"title","opacity":50} o {"layer":"title","x":20,"y":30}.

Impostazioni → Cronologia immagini è separatamente facoltativa e disattivata; aprire non sorveglia né legge appunti. Applica abilita registrazione e SQLite locale opzionale. 10–200 immagini, 8–128 MiB PNG; preferiti protetti ma contati nei limiti, nuove immagini rifiutate se preferiti pieni. Ogni immagine: 16 MP/otto MiB codificata. Un worker comprime, crea miniature e scrive; ultima immagine in attesa e risultati aggregati, intermedie saltate se lento. Preferiti/elimina/cancella, copia originale, fissa e tavola in memoria. Cancella include preferiti/libera pagine; disattivare salvataggio elimina database mantenendo memoria corrente. clipboard-images.sqlite3 accanto impostazioni, database fino a 132 MiB più possibili journal temporanei. Nessun invio/OCR automatico. Uscita scollega e richiede pulizia asincrona.

Impostazioni → Cronologia e ricerca catture richiede attivazione separata; aprire non salva/riconosce. Solo catture esplicite di area da Strumenti, OCR locale nel worker senza appunti/cloud. Ricerca senza distinzione maiuscole; errori OCR mantengono immagine e motivo nel tooltip. Data locale esatta YYYY-MM-DD, campi vuoti per tutto. Copia, fissa, riferimenti, preferiti ed elimina. Opzione capture-history.sqlite3 accanto impostazioni: 10–200 catture / 8–128 MiB PNG, 16 MP/otto MiB ciascuna, database massimo 132 MiB più journal. Eliminare rimuove testo, svuotare anche preferiti, disattivare salvataggio elimina database. Solo ultima cattura in attesa; chiusura scarta attese/risultati senza aspettare OCR attivo.
