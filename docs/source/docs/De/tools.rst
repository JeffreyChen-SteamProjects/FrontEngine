Werkzeuge-Seite
---------------

* Messen - klicken zum Messen, Rechtsklick löscht. Das Gemessene landet direkt
  in der Zwischenablage.

    * Farbwähler - die Farbe unter dem Cursor, kopiert als #rrggbb, rgb(...),
      hsl(...) oder als CSS-Custom-Property.
    * Pixel-Lineal - der Abstand zwischen zwei Punkten.
    * Winkelmesser - der Winkel zwischen dreien.

* Bereichsaufnahme - einen Bereich aufziehen; er landet in der Zwischenablage,
  und „Letzte kopieren“ legt ihn erneut dorthin.

  Letzten anheften legt die Aufnahme als kleines Fenster über alles: ziehbar, per
  Mausrad skalierbar, mit Doppelklick oder Escape zu schließen - eine Spezifikation,
  eine Farbreferenz oder eine Fehlermeldung neben der eigenen Arbeit.
* Bildschirmtext: Werkzeuge → Text lesen versucht zuerst lokale OCR: Windows.Media.Ocr unter Windows, Vision unter macOS oder ein installiertes Tesseract mit Sprachdaten. Lokale Erkennung benötigt weder Cloud-Zustimmung noch ANTHROPIC_API_KEY; ein erfolgreiches leeres Ergebnis lädt keinen Screenshot hoch. Übersetzungen und Fragen dürfen erkannten Text nur mit gesonderter Text-Zustimmung und Ihrem Schlüssel an Anthropic senden. Der Screenshot-Ersatz nach lokalem Fehler benötigt eigene Aufnahme-Zustimmung und den Schlüssel. Das Ergebnis zeigt Dienst und Fehler; dort lässt sich die Zustimmung widerrufen.
* Aufzeichnung: Wählen Sie einen Bereich und vor dem Start die GIF- oder AVI-Zieldatei. Abbrechen startet keine Aufnahme. Ein Hintergrundthread schreibt Bilder einzeln; die Warteschlange ist auf drei Bilder und 64 MiB begrenzt. Ein zu großes Einzelbild wird abgewiesen. Bei voller Warteschlange werden Aufnahmen ausgelassen, ihre Zeit bleibt in der Wiedergabe erhalten. Bildrate, Dauer, Bildzahlgrenze und Kamerabild in der Ecke bleiben erhalten. Stoppen schließt die Datei asynchron ab; erst bei Erfolg wird das Ziel atomar ersetzt. Abbruch und Schreibfehler entfernen die temporäre Datei und bewahren ein vorhandenes Ziel.
* Virtuelle Kamera - einen Bereich samt Overlays als Webcam senden, die Zoom,
  Teams oder Discord als Videoquelle wählen können. Benötigt das optionale
  Paket pyvirtualcam und einen Treiber für virtuelle Kameras; fehlt eines von
  beidem, sagt die Schaltfläche das.
* Kamera - jede Videoquelle anzeigen, auch Capture-Karten, als Kreis,
  abgerundetes Rechteck oder Rechteck, mit Rahmen und Spiegelung. Sie wird nur
  lokal gezeigt, nichts wird aufgezeichnet.
* Fenster anheften… - das Fenster einer anderen Anwendung im Vordergrund halten
  und seine Durchsichtigkeit ändern. Nur unter Windows.
* Fenster duplizieren… - ein zweites, kleines Fenster zeigt ein gewähltes Fenster
  live, während das Original bleibt, wo es ist. Praktisch, um ein Video oder einen
  Build im Auge zu behalten. Ziehen zum Verschieben, Doppelklick zum Schließen.
  Windows und macOS (macos-Extra und Berechtigung; native macOS-Prüfung steht aus).

  Ein Duplikat kann auch nur einen Teil zeigen - obere oder untere Hälfte, eine
  Seite oder die Mitte - sodass eine Chatspalte oder ein Fortschrittsbalken für
  sich stehen kann. Der Ausschnitt ist ein Anteil, bleibt also beim Ändern der
  Fenstergröße derselbe Teil.
* Fensteranordnung - merken, wo die Fenster stehen, und sie später
  zurücksetzen.

:doc:`runtime_interoperability`

Werkzeuge → Farbpalette sammelt aufeinanderfolgende Klicks, wenn Farben sammeln aktiv ist. Farben benennen/gruppieren, Hex bearbeiten, suchen, kopieren und entfernen; letzte Proben bleiben nutzbar. Bis zu 512 Farben und 50 verschiedene letzte Proben werden lokal gespeichert. Namen sind je Gruppe ohne Beachtung der Großschreibung eindeutig. CSS/JSON bewahren RGB; CSS-Namenskollisionen erhalten Nummern. Export ersetzt die Datei atomar. Die Befehlspalette öffnet auch die Farbpalette.

Werkzeuge → Bereichsaufzeichnung bietet GIF oder stummes AVI (Motion JPEG), 1–20 fps, Pause/Fortsetzen und Abbrechen. Status zeigt effektive Sekunden, angenommene Bilder und Auslassungen. Pausen zählen weder für Wiedergabe noch Dauergrenze; Stoppen während Pause ist möglich. AVI: bis zu einer Stunde, 72.000 Bilder und 2 GiB; GIF: 120 Sekunden/600 Bilder. Beide nutzen drei Bilder/64 MiB Hintergrundwarteschlange und atomare Ausgabe. AVI hält ein JPEG und schreibt den Index auf Datenträger; ausgelassene Intervalle wiederholen das letzte Bild. Encoder-, Größen- oder Schreibfehler und Abbruch bewahren ein bestehendes Ziel. Kein Audio.
