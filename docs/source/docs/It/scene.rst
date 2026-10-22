Pagina Scena
------------

.. image:: ../image/scene/scene.png

Una scena tiene insieme più overlay e si salva in un file.

* Aggiungi pagina web alla scena - indirizzo e opacità.
* Aggiungi video - file, opacità, velocità, volume.
* Aggiungi immagine - file e opacità.
* Aggiungi GIF - file, opacità, velocità.
* Aggiungi suono - file e volume.
* Aggiungi testo - testo, opacità, dimensione, allineamento.
* Avvia la scena - mostrare tutto ciò che è stato aggiunto.
* Esporta il file di scena.
* Carica un file di scena - riprendere una scena salvata.
* Cancella tutti gli script - ricominciare.
* Mostra su tutti gli schermi - una copia per monitor.

Scene: la pagina Scena legge le vecchie mappe JSON, documenti versionati frontengine.scene e pacchetti portabili .fescene. Una voce PUPPET contiene posizione, dimensione, opacità, parametri numerici finiti e movimento, espressione e script facoltativi. I percorsi JSON sono relativi al file della scena. .fescene include media referenziati, .puppet originale e .petscript.json facoltativo per spostarsi tra computer. L’importazione controlla percorsi, collegamenti simbolici, versioni e limiti di estrazione. Una scena FrontEngine resta un pacchetto scena; .puppet resta un singolo personaggio Imervue.

:doc:`runtime_interoperability`

Scena → Editor visuale offre elenco e anteprima di livelli immagine/GIF/testo, trascinamento di gruppo, ridimensionamento dall’angolo, posizione/dimensioni/scala/rotazione/ordine/opacità, allineamento, blocco, visibilità, duplicazione e 100 annulla/ripeti (Ctrl+Z/Ctrl+Y). Esporta direttamente .fescene; la scheda Script consente di modificare e applicare JSON. La riproduzione ripristina dimensioni, scala, rotazione e visibilità esplicite. Il JSON esterno inizia una nuova cronologia; i campi esistenti restano intatti.

Scena → Script → Modelli scena (anche nella tavolozza comandi) offre Desktop di lavoro, Insegnamento e Concentrazione con testo tradotto modificabile. Visualizza, scegli schermo principale o numero e Applica e riproduci; le proporzioni si adattano alla dimensione logica disponibile. I modelli includono le risorse. Quelle mancanti sono elencate con livello/campo/percorso e bloccano l’applicazione. La transazione scena sostituisce editor e riproduzione; una preparazione fallita mantiene la scena precedente. Modifica il testo, aggiungi media ed esporta JSON o .fescene portatile. Chiudere la libreria annulla solo la propria applicazione in attesa. Concentrazione include promemoria modificabili; pianificazione e timer restano strumenti separati.

Scena → Editor visuale aggiunge video, web, Puppet e audio a immagini/GIF/testo. Abilita esplicitamente le anteprime: fino a otto sorgenti, mute prima di Ascolta, in pausa se nascoste, liberate alla disattivazione o chiusura. Immagini limitate a 1280 pixel per lato; errori visibili. Le scene con livelli nominati compongono video, superficie propria del web e immagini Puppet fuori schermo Imervue con tutti i livelli visivi in ordine z; audio invisibile. Doppio clic sul livello web/Puppet in riproduzione o Interagisci nell’editor apre la stessa finestra nativa. Puppet richiede OpenGL nativo e il runtime opzionale; le anteprime non eseguono script e gli animali di scena usano stato temporaneo. Finestre web/video/Puppet indipendenti disponibili. JSON/.fescene conserva tutti i tipi e riferimenti supportati.

Scena → Editor visuale → Cronologia modifica x/y/opacità di un livello sbloccato, con modelli di dissolvenza e scorrimento. Tempi unici crescenti: 0–3600 secondi, 128 fotogrammi per livello; opacità 0–100, posizione ±100000, linear o smooth. Celle vuote: canale invariato. Applicazione annullabile; JSON/.fescene conserva le tracce. Scorri, riproduci, metti in pausa, riprendi o ripeti senza salvare posizioni temporanee; reimposta prima di modificare. Riproduzione: controlli separati e orologio monotono comune agli schermi. Nascondere sospende il tempo; pausa esplicita conservata dopo visualizzazione. Media in pausa con animazione; ripetizione delle tracce. Le azioni scena dissolvono un’immagine precedente per 0,5 secondi, liberano i vecchi renderer e avviano da zero. Scene precedenti compatibili.

Scena → Uscita indipendente mostra la scena dell’editor a 640×480, 1280×720 o 1920×1080 pixel indipendentemente da posizione, occlusione e DPI desktop. Anteprima senza videocamera; invio esplicito con pyvirtualcam e driver compatibile. Apertura/invio/chiusura su un worker con l’ultimo RGB in attesa; dispositivi lenti saltano intermedi. Senza audio. IMAGE/GIF/TEXT e VIDEO/WEB/PUPPET nativi seguono ordine livelli; SOUND invisibile. Puppet richiede runtime opzionale e OpenGL nativo; errori visibili. Fino a 256 livelli, otto sorgenti native e 16 megapixel totali di raster. Stop, Escape, chiusura o modifica liberano renderer e richiedono chiusura videocamera; riavvia dopo modifiche. Lettori chiusi prima del rilascio dei pacchetti.

Le build Windows condividono --preset e --debug con la CLI Python. Per la verifica nativa installare frontengine[puppet] nell’ambiente build; decoder Pillow e dati Imervue installati sono inclusi. Generare input locali: ``py tests/integration/scene_build_fixtures.py FIXTURES --puppet SAMPLE.puppet`` (PyAV per il video). Sul desktop nativo avviare ``FrontEngine.exe --verify-scene-build FIXTURES REPORT`` con nuova cartella rapporto. Il test fisso isola impostazioni temporanee, mantiene anteprime mute e apre solo proprie finestre scena/editor. Verifica sette tipi, JSON vecchio/versionato, esportazione/ricaricamento, GIF animata, interazione web, annulla/ripeti, pausa/ripresa e rilascio; scrive result.json e PNG e termina. Nessuno script Python fornito viene eseguito. Controllare rapporto e codice uscita; runtime/rendering nativo mancante fallisce esplicitamente.
