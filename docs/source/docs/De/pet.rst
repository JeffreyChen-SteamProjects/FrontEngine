Haustier-Seite
--------------

Ein Begleiter, der auf dem Desktop lebt.

* Haustier-Bild wählen - ein einzelnes Bild.
* Haustier-Paket wählen… - ein Ordner mit Bildern für walk / idle / sleep /
  climb / fall / drag, damit es sich bewegt.
* Ton wählen (optional) - was es abspielt.
* Haustier erzeugen - auf den Bildschirm setzen. Nochmals gedrückt kommt ein
  weiteres dazu.
* Größe, Geschwindigkeit.
* Verhalten - auf dem Boden laufen, frei umherstreifen oder dem Cursor folgen.
* An Wänden klettern - an Fensterkanten hochlaufen.
* Auf Fenstern sitzen - auf der Oberkante anderer Fenster rasten.
* Sprechblasen - kurze Bemerkungen je nach Tageszeit, beim Füttern und so fort.
* Beim Tippen still halten - das Tier bleibt stehen, solange Sie tippen, und geht
  ein paar Sekunden danach weiter, damit es nicht über die Zeile läuft, die Sie
  gerade lesen.
* Laut vorlesen - diese Bemerkungen ausgesprochen.
* Fangen spielen - zwei oder mehr Haustiere jagen einander.
* Auf Audio reagieren - das Haustier bewegt sich zum Ton. Es folgt wahlweise
  den **Lautsprechern** oder dem **Mikrofon**; beides liest nur einen Pegel,
  eine einzelne Zahl, und nimmt nie auf, was gesagt wird. Windows und macOS (macos-Extra und Berechtigung; native macOS-Prüfung steht aus).
* KI-Chat (API-Schlüssel nötig) - mit ihm sprechen. Liest die Umgebungsvariable
  ANTHROPIC_API_KEY; der Schlüssel wird nie gespeichert.
* Fokus-Timer (Min.) - eine Arbeitsuhr, die das Haustier für Sie führt, mit
  Pausen.

Ziehen Sie eine Datei auf das Haustier, um es zu füttern, oder ein Bild bzw.
ein Haustier-Paket, um sein Aussehen zu ändern.

Puppet-Haustiere: Installieren Sie das optionale puppet-Extra und eine verfügbare Imervue-Laufzeit; wählen oder ziehen Sie eine originale Imervue-.puppet-v1-Datei auf die Haustierseite. Bild- und Sprite-Pakete bleiben nutzbar. Puppet-Haustiere verwenden Imervues Canvas, Bewegungen und Ausdrücke, können dupliziert oder geschlossen werden und folgen Overlay-Steuerung und Voreinstellungen. Eine optionale .petscript.json verwendet Imervues Skriptengine; FrontEngine-pet.json-Pakete sind keine Puppet-Dateien. Unbekannte Versionen, unsichere Archivpfade und ungültige Medien werden vor dem Laden abgewiesen.

:doc:`runtime_interoperability`

Tier → Tieridentitäten speichert für jedes Sprite- oder Puppet-Tier eine eigene UUID, einen Namen, Stimmung, Sättigung und Zuneigung. Zum Fortsetzen nach Neustart vor dem Erzeugen eine gespeicherte Identität wählen; Neues Tier beginnt neu. Nur die erste Identität übernimmt einmal die alten gemeinsamen Werte. Klonen kopiert aktuelle Werte in eine neue Identität; Füttern verändert andere Tiere nicht. Einzelne JSON-Spielstände lassen sich umbenennen, aktualisieren, exportieren und importieren; Import erzeugt immer eine neue Identität. Eine Identität darf nur einmal aktiv sein. Spielstände enthalten keine Grafiken, Skripte oder Chatverläufe; portable Vorlagen enthalten keine lokalen IDs. Bis zu 256 Identitäten bleiben in den Benutzereinstellungen; Sprite-Änderungen werden gebündelt und beim Schließen gespeichert. Puppet-Füttern ändert nur gespeicherte Werte, keine Imervue-Bewegungen oder Größen.

Tier → Sprite-Tierpaket erstellt Zuordnungen für walk/idle/sleep/climb/fall/drag, zeigt Größe und Gehgeschwindigkeit und exportiert einen portablen Ordner mit pet.json. Mindestens eine Aktion; fehlende Aktionen werden gemeldet und nutzen den vorhandenen Loader-Fallback. PNG/JPEG/GIF/WebP: je 64 MiB und 16 Megapixel, insgesamt 256 MiB. Import/Export im Hintergrund, abbrechbar, keine vorhandenen Ordner überschrieben. Ordner können verschoben, auf der Tierseite gewählt und als Workshop-Tierpaket geteilt werden. Import übernimmt nur gewählte Sprites, Namen, Größe und Geschwindigkeit; keine Klänge, Skripte oder Sprache. Imervue .puppet hat ein eigenes Autorenformat. Schließen/Escape gibt Vorschaufilme frei und bricht Dateivorgänge ab.
