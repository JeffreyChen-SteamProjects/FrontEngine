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
