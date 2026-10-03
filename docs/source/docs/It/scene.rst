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
