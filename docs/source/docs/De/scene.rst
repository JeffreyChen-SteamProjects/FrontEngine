Szenen-Seite
------------

.. image:: ../image/scene/scene.png

Eine Szene fasst mehrere Overlays zusammen und lässt sich als Datei sichern.

* Webseite zur Szene hinzufügen - Adresse und Deckkraft.
* Video hinzufügen - Datei, Deckkraft, Geschwindigkeit, Lautstärke.
* Bild hinzufügen - Datei und Deckkraft.
* GIF hinzufügen - Datei, Deckkraft, Geschwindigkeit.
* Ton hinzufügen - Datei und Lautstärke.
* Text hinzufügen - Text, Deckkraft, Schriftgröße, Ausrichtung.
* Szene starten - alles Hinzugefügte anzeigen.
* Szenendatei ausgeben - das Gebaute sichern.
* Szenendatei laden - eine gesicherte Szene zurückholen.
* Alle Skripte löschen - von vorn anfangen.
* Auf allen Bildschirmen zeigen - eine Kopie je Monitor.

Szenen: Die Szenenseite liest alte JSON-Eintragslisten, versionierte frontengine.scene-Dokumente und portable .fescene-Pakete. PUPPET-Einträge enthalten Position, Größe, Deckkraft, endliche numerische Parameter sowie optionale Bewegung, Ausdruck und Skript. JSON-Pfade beziehen sich auf die Szenendatei. .fescene enthält die referenzierten Medien, die originale .puppet und optionale .petscript.json für andere Rechner. Import prüft Pfade, symbolische Links, Versionen und Entpackgrenzen. Eine FrontEngine-Szene bleibt ein Szenenpaket; .puppet bleibt eine einzelne Imervue-Figur.

:doc:`runtime_interoperability`

Szene → Visueller Editor bietet Bild/GIF/Text-Ebenenliste und Vorschau, Gruppenziehen, Eckenskalierung, Position/Größe/Skalierung/Drehung/Reihenfolge/Deckkraft, Leinwandausrichtung, Layoutsperre, Sichtbarkeit, Duplizieren und 100 Undo/Redo-Schritte (Ctrl+Z/Ctrl+Y). Andere Typen bleiben als Platzhalter erhalten. Portable .fescene direkt exportieren; im Skript-Tab JSON bearbeiten und anwenden. Wiedergabe übernimmt explizite Größe, Skalierung, Drehung und Sichtbarkeit. Externes JSON beginnt eine neue Undo-Historie; vorhandene Felder bleiben erhalten.
