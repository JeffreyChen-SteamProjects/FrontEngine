Widgets-Seite
-------------

* Audio-Spektrum - Balken oder ein Ring, die sich zum Ton der Lautsprecher
  bewegen, mit einstellbarer Bänderzahl. Dies nimmt tatsächlich Ton auf, nur im
  Arbeitsspeicher, um Frequenzen zu berechnen; nichts wird aufgezeichnet oder
  gesendet, und die Aufnahme endet mit dem Spektrum. Windows und macOS (macos-Extra und Berechtigung; native macOS-Prüfung steht aus).
* Systemmonitor - CPU, Speicher, Festplatte, Akku und Netzwerkdurchsatz als
  kleine, stets sichtbare Anzeige. Die gewünschten Linien sind ankreuzbar; eine
  ausgeblendete Linie zeichnet weiter auf und zeigt beim Einblenden, was
  inzwischen geschah.
* Aktuelle Wiedergabe anzeigen - der Titel, bei dem Ihr Player gerade ist.
* Notizzettel - „Neue Notiz“ legt eine auf den Desktop, „Notizen schließen“
  räumt sie weg. „Meine Notizen beim Start wieder öffnen“ holt sie beim
  nächsten Mal zurück.

Widgets → Aufgaben und Kalender bietet Häkchen, optionale lokale Fälligkeit und lokalen UTF-8-.ics-Import einzelner VEVENT/VTODO. Heute zeigt unvollständige undatierte/fällige/überfällige Aufgaben und überlappende Ereignisse; ganztägige/Mitternacht-Enden exklusiv. Bekannte IANA-TZID über Qt, UTC lokal angezeigt, flottierende Zeiten lokal, Datum bleibt Datum. DST: erste Wiederholung, Offset vor Lücke; DURATION-Tage bleiben nominal lokal. UID+RECURRENCE-ID aktualisiert, niedrigere SEQUENCE überschreibt nicht, Häkchen bleiben, CANCELLED entfernt. Faltung/TEXT-Escapes; keine Links/Alarme/Anhänge geöffnet. RRULE/RDATE/EXDATE/eigene unbekannte Zonen atomar abgelehnt, einzelne Vorkommen exportieren. tasks.json neben Einstellungen: 500 Einträge/vier MiB, Titel 1000/Beschreibung 2000 Zeichen, atomar mit Erhalt bei Fehlern. Import vier MiB/Zeile 8192 Zeichen, kein Netz/Sync/Alarm. Lazy Worker serialisiert Datei-I/O, Schluss stoppt Timer/späte Ergebnisse. Heute ist in Batch-Schließen/Verbergen registriert und startet nur explizit; Daten bleiben, Widget wird nicht automatisch wiederhergestellt.

Abbruchdatensätze zählen zur 500er-Grenze und verhindern Wiederherstellung durch alte Importe. Alles leeren fragt nach und entfernt Aufgaben, Termine und Abbruchdaten. Heute nutzt normale Qt-Softwarezeichnung, damit der Compositor die Bedienung nicht verdeckt.
