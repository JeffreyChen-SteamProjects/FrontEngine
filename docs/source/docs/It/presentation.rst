Pagina Presentazione
--------------------

* Annotazioni sullo schermo - disegnare sopra a ciò che è visibile.

    * Penna, evidenziatore, gomma, con colore e spessore.
    * «Annulla» toglie l'ultimo tratto, «Cancella» li toglie tutti.
    * Mentre il disegno è attivo questo livello prende il mouse. Tutto il resto
      qui lascia passare i clic.

* Evidenziazione del cursore - l'alone disegna un anello attorno al puntatore,
  l'onda al clic mostra dove hai premuto, il riflettore oscura il resto.
* Visualizzazione dei tasti - mostra i tasti premuti e i pulsanti del mouse
  cliccati, utile per registrazioni e dimostrazioni. Posizione del pannello e
  dimensione del testo sono a scelta; i clic del mouse si disattivano a parte.
* Lente - segue il cursore, da 1,5x a 6x.
* Lavagna - una tela senza fine.
* Congela lo schermo - coprire lo schermo scelto con una sua fotografia, così ciò
  che è proiettato o condiviso resta fermo mentre apri altro. Premere di nuovo il
  pulsante o la scorciatoia lo libera; anche un tasto qualsiasi o un doppio clic
  sull'immagine ferma.

    * Trascina col tasto centrale per spostarti, la rotella per ingrandire.
    * I tratti sono tenuti in coordinate della tela, quindi spostarsi e
      ingrandire li lascia dove devono stare.
    * «Salva la lavagna» scrive un'immagine della sola area disegnata.

Presentazione → Lavagna ha pagine modificabili indipendenti, modalità disegno/selezione, selezione multipla Maiusc, spostamento/eliminazione tratti e 20 stati annullabili complessivi. Tasto centrale sposta, rotella ingrandisce; selezione/movimento in coordinate della tela, vista per pagina. Salva/apri .fewhiteboard JSON con versione conserva tratti vettoriali/viste per continuare. Un worker valida e legge/scrive; errori conservano lavagna/file. PNG pagina esclude controlli/selezione/trasformazione con margini completi. Limiti: 50 pagine, 2000 tratti/pagina, 100000 punti, otto MiB JSON; PNG 8192 pixel/lato e 16 megapixel. Chiusura/Escape annulla scritture e ignora letture tardive.
