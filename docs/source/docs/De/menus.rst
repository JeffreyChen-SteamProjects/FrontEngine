Voreinstellungen und Einstellungen
----------------------------------

Menü „Voreinstellungen“

* Voreinstellung speichern… - alle Seiteneinstellungen unter einem Namen.
* Voreinstellung laden… - zurückholen.
* Voreinstellung löschen…
* Exportieren… / Importieren… - als json-Datei zwischen Rechnern bewegen.
* Paket exportieren (+Medien) / importieren (+Medien) - dasselbe, aber mit den
  Bildern, Videos und Tönen darin, als zip.
* Als Start-Voreinstellung festlegen… - beim Start von FrontEngine anwenden.
* Workshop-Inhalte importieren… - auf Steam abonnierte Voreinstellungen und
  Haustier-Pakete installieren.

Menü „Einstellungen“

* Tastenkürzel… - global für alle ausblenden, anzeigen, schließen,
  stummschalten, Deckkraft hoch und runter, nächste Dashboard-Seite, sperren,
  Bildschirm einfrieren, die Kürzelliste sowie Medien abspielen/pausieren,
  nächster und vorheriger Titel sowie das Verschieben des Vordergrundfensters
  auf den nächsten Bildschirm unter Beibehaltung seiner Proportionen.
* Tag-/Nacht-Design nach Zeitplan - tagsüber hell, nachts dunkel.
* Mit dem System starten - FrontEngine bei der Anmeldung starten.
* Letzte Sitzung wiederherstellen - wieder öffnen, was zuletzt zu sehen war.
* Plugins laden (fortgeschritten) - Plugins sind Python und laufen mit
  denselben Rechten wie FrontEngine; installieren Sie nur, was Sie kennen.
* Intelligente Pause… - Overlays wegräumen, solange eine Vollbild-Anwendung
  läuft, im Akkubetrieb, oder wenn genannte Anwendungen im Vordergrund sind.
* Bildschirm wach halten - verhindert, dass der Bildschirm schlafen geht, solange
  etwas zu sehen ist. Wird beim Ausschalten und beim Beenden freigegeben, sodass
  wieder die eigenen Energieeinstellungen gelten.
* App-Profile… - eine Voreinstellung anwenden, sobald eine bestimmte Anwendung
  nach vorn kommt.
* Erinnerungen… - eine Meldung alle so viele Minuten oder zu einer Uhrzeit.
* Regeln… - „wenn diese Bedingungen gelten, tu das“. Wochentag, Zeitfenster und
  das Programm im Vordergrund lassen sich kombinieren; als Aktion eine
  Voreinstellung anwenden, die Overlays aus- oder einblenden, schließen oder die
  Qualität setzen. Eine leere Bedingung heißt „beliebig“, und eine Regel läuft
  einmal, wenn ihre Bedingungen zu gelten beginnen, nicht laufend.
* Bildschirmschoner… - nach so vielen Minuten ohne Maus und Tastatur das Overlay
  einer gewählten Seite anzeigen; eine Mausbewegung nimmt es wieder weg. Es nutzt
  die Seite so, wie sie eingerichtet ist, und schließt nur, was es selbst geöffnet
  hat - was Sie laufen ließen, ist bei Ihrer Rückkehr noch da.
* Geplante Voreinstellung… - eine Voreinstellung zu einer Uhrzeit an den gewählten
  Tagen anwenden. Ohne angehakten Tag täglich. Sie löst beim Überschreiten der
  Uhrzeit aus; ein späterer Start holt sie nicht nach.
* Anzeigetafel-Modus… - eine Liste von Voreinstellungen auf Zeit durchwechseln,
  für einen Rechner, der als Anzeige läuft. Das Hauptfenster kann dabei in die
  Taskleiste - aber nur, wenn es eine gibt, die es zurückholen kann.
* Telefonsteuerung: Einstellungen → Fernsteuerung verwendet ausschließlich HTTPS, ein bei jedem Start neues Token und eine feste Aktionsliste. Das Telefon vertraut dem selbstsignierten Zertifikat nicht automatisch. Exportieren Sie das öffentliche Zertifikat und vergleichen Sie den angezeigten SHA-256-Fingerabdruck, bevor Sie es in den Telefon-/Browsereinstellungen importieren oder ihm vertrauen. Der private Schlüssel bleibt im Benutzerdatenordner. IP-Änderung, Ablauf oder Neuerstellung können ein neues Zertifikat erfordern. Ein TLS-Startfehler führt nicht zu HTTP.
* Privatsphäre beim Bildschirmteilen… - Overlays vor einer Bildschirmaufnahme
  verbergen, solange eine Meeting-Anwendung offen ist. Verglichen wird mit
  Fenstertiteln, damit auch ein Meeting im Browser-Tab erkannt wird. Nur unter
  Windows.
* Bildschirmzeit… - wie lange Sie in welcher Anwendung sind. Bleibt auf diesem
  Rechner und wird nirgendwohin gesendet.
* Verlauf der Zwischenablage… - was zuletzt kopiert wurde, durchsuchbar, mit
  Anheften. Bleibt nur im Arbeitsspeicher, sofern Sie nichts anderes verlangen,
  denn in Zwischenablagen stehen oft Passwörter.
* Einstellungen exportieren… / importieren…

Menü „Hilfe“

* **Bedienung …** - eine kurze Anleitung in der Anwendung: Ihr erstes Overlay,
  die Einstellungen, die jede Seite teilt, und wie der Bildschirm wieder frei wird.
* **Tastenkürzel-Liste…** - die globalen Tastenkürzel so, wie sie tatsächlich
  belegt sind, über dem Bildschirm. Neu belegen ändert auch diese Liste. Erneut
  das Kürzel drücken oder Escape blendet sie aus.
* Fehler-Tracker, und der Hinweis, dass F12 FrontEngine sofort beendet.

Plugins: Aktiviertes Laden ist noch keine Freigabe. plugin.json oder eine Begleitdatei für ein einzelnes Plugin deklariert Version, Identität, Einstiegspunkt und Fähigkeiten. Zustimmung wird vor Python-Import geprüft und an die Inhaltsprüfsumme gebunden. Geänderter Code oder geänderte Deklarationen erfordern neue Zustimmung; alte Plugins benötigen ausdrückliches volles Vertrauen. Einstellungen → Plugin-Freigaben widerrufen löscht gespeicherte Freigaben; laufenden Code entlädt erst ein Neustart. Python-Plugins haben weiterhin alle Anwendungsrechte; Deklaration und Zustimmung sind keine Betriebssystem-Sandbox.

Darstellung: Einstellungen → Overlay-Darstellung bietet Automatisch, GPU oder Software und zeigt den tatsächlich verwendeten Dienst. Der GPU-Compositor verwendet OpenGL-Texturen, Shader und Framebuffer für Reihenfolge, Transformation, Deckkraft und Ausschnitt; bei Initialisierungsfehler wird mit Begründung auf Software zurückgefallen. QPainter-Inhalte können weiter auf der CPU rasterisiert und hochgeladen werden; Web-/Video-/native Widgets können eigene Fenster verwenden. Aufnahme kann GPU-Bilder zur CPU zurücklesen. Das verspricht weder kopierfreie Aufnahme noch gemessene Leistungsgewinne. GPU-Szenenkomposition umfasst derzeit IMAGE, GIF und TEXT; Puppet-Darstellung verwendet ein eigenes Imervue-Fenster.

:doc:`runtime_interoperability`

Einstellungen → macOS-Berechtigungen und Fähigkeiten zeigt jede Funktion als verfügbar, nicht verfügbar oder nicht unterstützt, mit Berechtigungs- oder Installationsgrund.

Öffnen Sie Befehle in der Menüleiste oder drücken Sie in FrontEngine Strg+K / Strg+Umschalt+P. Suchen Sie in der aktuellen Sprache, mit englischen Namen oder festen Befehlsnamen; Pfeiltasten wählen, Enter führt aus. Enthalten sind Seitennavigation, Aufnahme, Notizen, Bildschirmfilter, Workshop und bestehende globale Aktionen. Preset/Qualität akzeptieren einen Wert. Favoriten und die letzten 20 Befehle bleiben erhalten; Parameter und Suchtext werden nicht gespeichert.

Vorlagen → Vorlagenversionen bewahrt je Vorlage bis zu 50 verschiedene Einstellungsschnappschüsse über Neustarts hinweg. Beim Speichern werden alte und neue Konfigurationen erfasst; gleiche Inhalte werden nicht doppelt gespeichert. Die Auswahl zeigt Feldänderungen gegenüber den aktuellen Seiteneinstellungen. Die Vorschau wendet diese Konfiguration auf die Steuerelemente an; Abbrechen, Escape oder Schließen stellt die ursprünglichen Einstellungen wieder her. Wiederherstellen wendet die Version an und speichert sie; bei Anwendungs- oder Speicherfehlern werden die Seiteneinstellungen zurückgesetzt. Schnappschüsse enthalten Medienpfade, keine Mediendateien; die Vorschau öffnet keine Overlays. Bestehende JSON-/ZIP-Vorlagen bleiben kompatibel. Der Verlauf liegt unter presets/.versions und bleibt beim Löschen einer Vorlage für die Wiederverwendung ihres Namens erhalten.

Einstellungen → Regeln ergänzt Priorität (-1000…1000), Abklingzeit (0…86400 ganze Sekunden), Bedingungsvorschau und Sitzungsverlauf. Ausgelöste Regeln laufen von niedriger zu höherer Priorität, bei Gleichstand in Tabellenreihenfolge; höhere Werte zuletzt. Eine monotone Uhr steuert die Abklingzeit: blockierte Übergänge werden verbraucht, und Ablauf führt bei weiterhin wahren Bedingungen nichts aus. Vorschau prüft ungespeicherte Zeilen ohne Aktionen oder Zustandsverbrauch. Die letzten 200 Belege enthalten Bedingungen, erfassten Kontext und Versand-/Ausführungs-/Fehler-/Abklingergebnisse nur im Speicher. Ungültige benannte Zeilen verhindern das Speichern. Bis zu 200 Regeln besitzen unabhängige Identitäten, auch bei gleichen Namen; nicht angezeigte Bedingungen bleiben beim Bearbeiten erhalten. Rückgemeldete Aktionsfehler werden protokolliert und stoppen spätere Regeln nicht.

Regeln können Szenen laden, abspielen oder stoppen und benannte Ebenen zeigen, ausblenden, verschieben oder ihre Deckkraft ändern. Zeile auswählen und Szene / Ebene wählen: JSON, .fescene oder .puppet durchsuchen, Hauptbildschirm/alle/Bildschirmindex und Editorebene wählen. Ein leerer Wiedergabepfad nutzt die aktuelle Editorszene. Dateien werden im Hintergrund gelesen; ein fehlgeschlagener Kandidat erhält die laufende Szene. Die letzte Szenenanforderung ersetzt ausstehende Vorgänger; folgende Ebenenaktionen warten darauf und scheitern mit ihr. Gesperrte oder fehlende Ebenen werden abgelehnt. Änderungen sind rückgängig machbar und aktualisieren die Wiedergabe; Deckkraft 0–100, Position ±100000. Stoppen bricht Anforderungen ab und schließt die Wiedergabe; Editorressourcen bleiben bis zum Ersetzen oder Programmende. Der Verlauf erfasst den tatsächlichen asynchronen Abschluss. In der Befehlspalette: Pfad oder {"path":"scene.fescene","screen":"primary"}, Ebenenschlüssel für zeigen/ausblenden, {"layer":"title","opacity":50} oder {"layer":"title","x":20,"y":30}.

Einstellungen → Bild-Zwischenablageverlauf ist separat optional und standardmäßig aus; Öffnen startet weder Überwachung noch Lesen. Anwenden aktiviert Aufnahme und optionale lokale SQLite-Sitzungsspeicherung. 10–200 Bilder, 8–128 MiB PNG-Nutzdaten; Favoriten schützen vor Verdrängung, zählen aber zu beiden Grenzen. Volle Favoriten melden Ablehnung. Je Bild 16 MP/acht MiB kodiert. Ein Worker komprimiert, erstellt Miniaturen und schreibt; nur neuestes wartendes Bild und zusammengefasste Ergebnisse, langsame Kompression überspringt Zwischenbilder. Favoriten/Löschen/Leeren, Original kopieren, Desktop anheften und Speicher-Referenztafel. Leeren entfernt auch Favoriten und Datenbankseiten; Speichern abschalten löscht Datenbank, aktuelle Speicherhistorie bleibt. clipboard-images.sqlite3 neben Einstellungen, Datenbank bis 132 MiB plus mögliche temporäre Journale. Kein Upload/automatisches OCR. Beenden trennt Überwachung und fordert asynchrone Bereinigung an.

Einstellungen → Aufnahmeverlauf und Suche ist separat einzuschalten; Öffnen speichert/erkennt nichts. Nur explizite Bereichsaufnahmen aus Werkzeuge werden lokal im Worker erkannt, ohne Zwischenablage oder Cloud. Suche ohne Groß-/Kleinschreibung; OCR-Fehler behalten das Bild mit Grund im Tooltip. Datum genau YYYY-MM-DD in lokaler Zeitzone, leere Felder zeigen alles. Kopieren, Anheften, Referenztafel, Favoriten und Löschen. Optional capture-history.sqlite3 neben Einstellungen: 10–200 Bilder / 8–128 MiB PNG, 16 MP/acht MiB pro Bild, Datenbank bis 132 MiB plus Journale. Löschen entfernt Text, Leeren auch Favoriten, Speicherung abschalten entfernt Datei. Nur neueste wartende Aufnahme; Schließen verwirft Wartendes/Ergebnisse ohne auf aktive OCR zu warten.

Einstellungen → Materialbibliothek: Bilder/GIF, Sprite-Pet-Ordner, .puppet-Texturen und JSON/.fescene mit statischen Vorschauen, Tags, Suche ohne Groß-/Kleinschreibung und Favoriten. Kein Kopieren/Löschen/Ausführen, Vergessen nur Katalog. asset-library.json neben Einstellungen: 200 Einträge/ein MiB, 32 Tags à 40 Zeichen; Bilder 64 MiB/16 MP, Archive 256 MiB, Szenen 256 Ebenen. Szene statisch mit Medien-Platzhaltern, Puppet erste Textur. Verweise: aktuelle Szene, aktive lokale Presets, registrierte Szene-JSON (200 Presets/16 MiB); fehlende Pfade bleiben. Neu zuordnen prüft gleichen Typ und bestätigt genaue Verweise, aktuelle Szene rückgängig editierbar, lokale schreibbare Workspace-Szenen/Presets/Katalog repariert. Literaltext, unveränderliche Historie, Pakete, externe Szenen/Workshop schreibgeschützt; lokale Importkopien möglich. Geänderte Dateien brechen ab. 50 Dateien/16 MiB mit atomarem .asset-relink.json-Rollbackjournal; Wiederherstellung vor nächstem Job, Konflikte behalten Journal. OS-Sperre .asset-library.lock schützt parallele Instanzen. Lazy Worker dekodiert/scannt/schreibt, Schluss storniert ausstehende Reparatur und stellt unveränderten Szenenedit wieder her, späte Ergebnisse verworfen. Wiedergabe nach Pfadänderung neu starten.
