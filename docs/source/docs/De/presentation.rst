Präsentieren-Seite
------------------

* Bildschirm-Annotation - über alles zeichnen, was zu sehen ist.

    * Stift, Textmarker, Radierer, mit Farbe und Breite.
    * Rückgängig nimmt den letzten Strich zurück, Löschen alle.
    * Während gezeichnet wird, beansprucht diese Ebene die Maus. Alles andere
      hier lässt Klicks durch.

* Cursor hervorheben - Hervorhebung legt einen Ring um den Zeiger, Klick-Welle
  zeigt, wo geklickt wurde, Spotlight dunkelt alles andere ab.
* Tastenanzeige - zeigt die gedrückten Tasten und die geklickten Maustasten,
  für Aufnahmen und Vorführungen. Position und Schriftgröße sind wählbar,
  Mausklicks lassen sich einzeln abschalten.
* Lupe - folgt dem Cursor, von 1,5x bis 6x.
* Whiteboard - eine endlose Fläche.
* Bild einfrieren - den gewählten Bildschirm mit einer Aufnahme seiner selbst
  überdecken, damit das Projizierte oder Geteilte stehen bleibt, während Sie etwas
  anderes öffnen. Erneut die Schaltfläche oder das Kürzel drücken hebt es auf; jede
  Taste und ein Doppelklick auf das Standbild ebenfalls.

    * Mit der mittleren Maustaste ziehen verschiebt, Scrollen zoomt.
    * Striche liegen in Flächenkoordinaten, Verschieben und Zoomen lässt sie
      also dort, wo sie hingehören.
    * „Whiteboard speichern“ schreibt ein Bild genau des bemalten Bereichs.

Präsentation → Tafel hat unabhängige editierbare Seiten, Zeichen/Auswahlmodus, Shift-Mehrfachauswahl, Strichbewegung/Löschen und insgesamt 20 Undo-Zustände. Mittlere Taste verschiebt, Rad zoomt; Auswahl/Bewegung in Canvas-Koordinaten, eigene Ansicht je Seite. Speichern/Öffnen nutzt versioniertes .fewhiteboard JSON mit Vektorstrichen/Ansichten zum Weiterbearbeiten. Ein Hintergrundworker validiert und liest/schreibt; Fehler erhalten Tafel/Datei. Seiten-PNG zeigt nur die gewählte Seite ohne Bedienelemente/Auswahl/Ansichtstransform, mit vollständigen Stifträndern. Grenzen: 50 Seiten, 2000 Striche/Seite, 100000 Punkte, acht MiB JSON; PNG 8192 Pixel/Seite, 16 Megapixel. Schließen/Escape bricht Schreiben ab und ignoriert späte Lesergebnisse.
