Pagina Testo
------------

.. image:: ../image/text/text.png

* Mostra il testo sullo schermo.
* Opacità - quanto il testo è trasparente.
* Dimensione, carattere, colore - il suo aspetto.
* Contorno - un bordo di colore contrastante, per restare leggibile su
  qualunque fondo.
* Allineamento del testo - verso un angolo o al centro.
* Testo scorrevole - farlo scorrere di lato, con una sua velocità.
* Origine del testo - da dove vengono le parole.

    * Testo fisso - esattamente ciò che sta nel campo.
    * Orologio / Data - un formato strftime.
    * Conto alla rovescia - minuti, HH:MM, o una data completa.
    * Cronometro - conta dal momento in cui parte.
    * Stato del sistema - campi come {cpu} {ram} {disk} {down} {up}.
    * Meteo - campi come {temperature} {description} {humidity} {wind}, per la
      città indicata in «Città per il meteo».

* Tutti gli schermi / Sotto tutte le finestre / Schermo di destinazione - come altrove.

Testo → TXT / JSON / CSV locale visualizza file UTF-8 con campo e intervallo di 1–3600 secondi. JSON: /chiave/indice (es. /build/tasks); CSV: intestazioni uniche, colonna per righe. Campo vuoto: intero file. Lettura in background, un lavoro per sorgente, massimo 1 MiB e 65.536 caratteri. Errori di file/campo, formato, accesso e dimensione sono espliciti; le correzioni ripristinano il risultato. I preset salvano file/campo/intervallo. Le scene portabili copiano il file: condividere il pacchetto condivide quella copia dei dati.
