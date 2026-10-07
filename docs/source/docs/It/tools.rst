Pagina Strumenti
----------------

* Misura - clicca per misurare, il tasto destro cancella. Ciò che misuri va
  dritto negli appunti.

    * Selettore di colore - il colore sotto il cursore, copiato come #rrggbb,
      rgb(...), hsl(...) o come proprietà CSS personalizzata.
    * Righello in pixel - la distanza fra due punti.
    * Goniometro - l'angolo fra tre.

* Cattura di un'area - traccia un'area; finisce negli appunti, e «Copia
  l'ultima» ce la rimette.

  Fissa l'ultima mette la cattura sopra tutto in una finestrella: trascinabile,
  ridimensionabile con la rotellina, si chiude con doppio clic o Esc - una specifica,
  un riferimento di colore o un messaggio di errore accanto al lavoro.
* Testo sullo schermo: Strumenti → Leggi il testo usa prima l’OCR locale: Windows.Media.Ocr su Windows, Vision su macOS oppure Tesseract installato con dati linguistici. L’estrazione locale non richiede consenso cloud né ANTHROPIC_API_KEY; un risultato vuoto riuscito non carica screenshot. Traduzioni e domande possono inviare il testo riconosciuto ad Anthropic solo con consenso separato al testo e la tua chiave. L’invio di screenshot dopo un errore locale richiede un consenso distinto alle catture e la chiave. Il risultato mostra motore ed errori e permette di revocare il consenso.
* Registrazione: seleziona un’area e scegli il GIF o AVI di destinazione prima della cattura. Annullare non avvia la registrazione. Un thread in background scrive i fotogrammi progressivamente; la coda è limitata a tre fotogrammi e 64 MiB. Un fotogramma troppo grande viene rifiutato. Se la coda è piena, le catture vengono saltate mantenendo il tempo trascorso nella riproduzione. Restano frequenza, limiti di durata e numero di fotogrammi e inserto della fotocamera. L’arresto finalizza in modo asincrono; il file sostituisce atomicamente la destinazione solo al successo. Annullamento ed errori eliminano il temporaneo e preservano il file esistente.
* Fotocamera virtuale - inviare un'area, overlay compresi, come webcam che Zoom,
  Teams o Discord possono scegliere come sorgente video. Serve il pacchetto
  facoltativo pyvirtualcam e un driver per fotocamere virtuali; se manca uno dei
  due, il pulsante lo dice.
* Fotocamera - mostrare qualsiasi ingresso video, comprese le schede di
  acquisizione, come cerchio, rettangolo arrotondato o rettangolo, con bordo e
  specchiatura. È mostrata solo in locale e non viene registrato nulla.
* Fissa una finestra… - tenere in primo piano la finestra di un altro programma
  e regolarne la trasparenza. Solo su Windows.
* Duplica una finestra… - una seconda finestra piccola mostra dal vivo quella
  scelta, mentre l'originale resta dov'è. Comodo per tenere d'occhio un video o
  una compilazione mentre lavori. Trascina per spostarla, doppio clic per
  chiuderla. Windows e macOS (opzione macos e permesso; macOS nativo non verificato qui).

  Un duplicato può mostrare solo una parte della finestra - metà superiore o
  inferiore, un lato o il centro - così una colonna di chat o una barra di
  avanzamento sta per conto suo. La zona è una proporzione, quindi ridimensionare
  l'originale mostra sempre la stessa parte.
* Disposizione delle finestre - ricordare dove sono le finestre e rimetterle lì.

:doc:`runtime_interoperability`

Strumenti → Tavolozza colori raccoglie clic consecutivi quando attivata. Assegna nomi/gruppi, modifica hex esatti, cerca, copia e rimuovi; riutilizza i campioni recenti. Fino a 512 colori e 50 campioni distinti vengono salvati localmente. Nomi unici per gruppo senza distinzione tra maiuscole/minuscole; duplicati rifiutati. CSS/JSON mantengono RGB; collisioni CSS ricevono numeri. Esportazione atomica. Anche Comandi apre la tavolozza.

Strumenti → Registrazione area offre GIF o AVI senza audio (Motion JPEG), 1–20 fps, Pausa/Riprendi e Annulla. Stato: secondi effettivi, fotogrammi accettati e saltati. Le pause non contano nella riproduzione né nei limiti; si può fermare in pausa. AVI: fino a un’ora, 72.000 fotogrammi e 2 GiB; GIF: 120 secondi/600 fotogrammi. Coda di tre fotogrammi/64 MiB e uscita atomica per entrambi. AVI mantiene un JPEG e scrive l’indice su disco; intervalli saltati ripetono l’ultima immagine. Errori di codifica, dimensione o disco e annullamento preservano la destinazione esistente. Nessun audio.
