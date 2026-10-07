Text-Seite
----------

.. image:: ../image/text/text.png

* Text auf dem Bildschirm anzeigen.
* Deckkraft - wie durchsichtig der Text ist.
* Schriftgröße, Schriftart, Farbe - das Aussehen.
* Kontur - ein Rand in Gegenfarbe, damit der Text über allem lesbar bleibt.
* Textausrichtung - eine Ecke oder die Mitte.
* Lauftext - den Text seitlich laufen lassen, mit eigener Geschwindigkeit.
* Textquelle - woher die Wörter kommen.

    * Fester Text - genau das, was im Feld steht.
    * Uhr / Datum - ein strftime-Format.
    * Countdown - Minuten, HH:MM oder ein vollständiges Datum.
    * Stoppuhr - zählt ab dem Start aufwärts.
    * Systemwerte - Felder wie {cpu} {ram} {disk} {down} {up}.
    * Wetter - Felder wie {temperature} {description} {humidity} {wind}, für
      die unter „Wetter-Stadt“ genannte Stadt.

* Auf allen Bildschirmen / Unter allen Fenstern / Zielbildschirm - wie sonst auch.

Text → Lokale TXT / JSON / CSV zeigt UTF-8-Dateien mit Feldwahl und 1–3600 Sekunden Intervall. JSON: /Schlüssel/Index (etwa /build/tasks); CSV: eindeutige Spaltennamen, Spalte zeilenweise. Leer zeigt die ganze Datei. Hintergrundlesen: ein Auftrag je Quelle, maximal 1 MiB und 65.536 Ausgabezeichen. Fehlende Dateien/Felder, Format-, Zugriffs- und Größenfehler werden angezeigt; Korrekturen stellen die Anzeige wieder her. Presets speichern Datei/Feld/Intervall. Portable Szenen kopieren die Datendatei; das Teilen gibt diesen Datenstand weiter.
