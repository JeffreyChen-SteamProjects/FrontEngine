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
