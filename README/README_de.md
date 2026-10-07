# FrontEngine

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="README_zh-TW.md">繁體中文</a> ·
  <a href="README_zh-CN.md">简体中文</a> ·
  <a href="README_ja.md">日本語</a> ·
  <a href="README_ko.md">한국어</a> ·
  <a href="README_es.md">Español</a> ·
  <a href="README_fr.md">Français</a> ·
  <strong>Deutsch</strong> ·
  <a href="README_pt-BR.md">Português (BR)</a> ·
  <a href="README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**Legen Sie alles über Ihren Bildschirm — oder darunter.**

FrontEngine ist eine Desktop-Overlay-App. Video, Bilder, GIFs, Webseiten, Text,
Partikel, Ton und ein animiertes Haustier können über jedes andere Fenster
gelegt werden (klickdurchlässig, sodass das Darunterliegende weiterhin
funktioniert) oder als lebendiger Hintergrund dahinter. Darum herum gibt es eine
Reihe von Werkzeugen für den Bildschirm selbst: augenschonende Filter,
Präsentationsannotationen, Messen und Erfassen, Fokusmasken und Desktop-Widgets.

[Unterstützen Sie dieses Projekt auf Steam](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [Dokumentation](https://frontengine.readthedocs.io/en/latest/)
 · [Demo ansehen](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](../image/FrontEngine.png)

---

## Installation

Python **3.10+**. Windows 10/11 ist die primäre Zielplattform; macOS und Linux
führen die App aus, mit den unter [Plattformunterstützung](#plattformunterstützung)
aufgeführten Plattformunterschieden.

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

Vorgefertigte Windows-Binärdateien finden Sie auf der
[Releases-Seite](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases),
und der Steam-Build liefert dieselbe Anwendung mit Workshop-Unterstützung aus.

> **Herauskommen.** Overlays können den gesamten Bildschirm bedecken,
> einschließlich FrontEngines eigenem Fenster, daher gibt es zwei Notausgänge,
> die keine Maus benötigen: `Ctrl+Shift+F12` schließt alle Overlays, und
> **F12 beendet die Anwendung sofort** von überall (Windows; macOS benötigt Bedienungshilfen-Berechtigung — siehe
> *Hilfe → Wie man das Schließen erzwingt*).

---

## Was es auf den Bildschirm bringt

Die Seitenleiste gruppiert die Seiten danach, wofür sie da sind. Dieser
Abschnitt folgt ihr.

### Auf dem Bildschirm

Medien-Overlays. Jedes wählt seinen Monitor (oder erstreckt sich über alle),
merkt sich, wohin Sie es gezogen haben, und hat seine eigene Deckkraft.

- **Video** — mit Lautstärke, Wiedergabegeschwindigkeit und Schleife.
- **Bild** — ein einzelnes Bild, ein Ordner als Diashow oder ein
  **Referenzboard**: mehrere Bilder auf einer Leinwand, jedes ziehbar, das ganze
  Board zoom- und verschiebbar.
- **Web** — eine URL oder eine lokale HTML-Datei, optional interaktiv. Der
  **Dashboard-Modus** rotiert durch eine Liste von URLs, sodass ein
  Wandbildschirm Seiten per Hotkey oder Timer durchwechseln kann.
- **GIF / WebP** — Animationen mit einstellbarer Geschwindigkeit.
- **Text** — Schriftart, Farbe, Umriss, Ausrichtung und ein Laufband, das
  entweder einen festen Text oder eine **Live-Quelle** anzeigt: Uhr, Datum,
  Countdown, Stoppuhr, Systemauslastung oder das Wetter. Die Live-Quellen
  verwenden eine `{field}`-Vorlage, und die Seite listet die Felder auf, die
  jede anbietet.
- **Ton** — Musikwiedergabe und WAV-Effekte mit niedriger Latenz.
- **Szene** — kombinieren Sie mehrere der oben genannten zu einer Komposition,
  die durch ein JSON-Dokument beschrieben wird, das Sie speichern und teilen
  können.
- **Partikel** — ein OpenGL-Partikeleffekt.

<details>
<summary>Screenshots (GIFs may take a moment to load)</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](../gifs/play_gif.gif) | ![WEBP](../gifs/webp.gif) |

| Video | Website |
| --- | --- |
| ![Video](../gifs/video.gif) | ![Website](../gifs/website.gif) |

</details>

### Desktop

**Desktop-Haustier** — ein animiertes Sprite, das auf Ihrem Desktop lebt.

- **Sprites** — ein einzelnes GIF/WebP/PNG oder ein *Pet-Pack*-Ordner, dessen
  Dateinamen Zuständen zugeordnet sind: `walk`, `idle`, `sleep`, `climb`,
  `fall`, `drag` (ein fehlender Zustand fällt auf `walk` zurück). Eine optionale
  `pet.json` legt Größe, Geschwindigkeit fest sowie, ob es klettern, sprechen
  oder auf Fenstern sitzen darf.
- **Verhalten** — auf dem Boden mit Schwerkraft laufen (werfen Sie es, und es
  springt), frei umherwandern oder dem Mauszeiger folgen. Boden-Haustiere
  klettern an Bildschirmrändern hoch und stehen auf der oberen Kante anderer
  Fenster.
- **Leben** — Stimmung, Sättigung und ein Zuneigungslevel, die zwischen den
  Durchläufen erhalten bleiben. Es wächst, wenn es aufsteigt, spricht in
  Sprechblasen, macht ein Nickerchen, während Sie weg sind, und warnt Sie vor
  einem niedrigen Akkustand.
- **Interaktion** — ziehen Sie es, klicken Sie mit der rechten Maustaste, um es
  zu klonen / zu füttern / eine Erinnerung zu setzen, und **legen Sie eine Datei
  darauf ab**: ein Bild oder Pet-Pack wird sein neues Aussehen, alles andere
  wird gegessen. Was es isst, ist wichtig — ein Archiv ist ein Festmahl, Musik
  heitert es mehr auf, als es sättigt, ein Dokument ist eine bescheidene
  Mahlzeit, eine Binärdatei ist zu schwer zu kauen.
- **Fangen** — mit zwei oder mehr Haustieren auf dem Bildschirm aktivieren Sie
  *Fangen miteinander spielen*, und eines wird zum "Fänger": Es geht auf seinen
  nächsten Nachbarn zu, während die anderen in die entgegengesetzte Richtung
  laufen, und wer jemanden erwischt, gibt die Fängerrolle weiter.
- **Reagiert auf Ton** — das Haustier pulsiert mit der Ausgabe Ihrer Lautsprecher
  oder mit Ihrem **Mikrofon**, sodass es sich bewegt, während Sie sprechen.
  Beide lesen nur den Ausgabe-*Pegel* — eine Zahl, kein Audio. Spitzen werden
  mit einem RMS-Fenster und einer Hüllkurve mit schnellem Anstieg/langsamem
  Abfall geglättet, sodass der Puls atmet, statt zu flackern. Mit mehreren
  Monitoren folgt jedes Haustier dem Audio-Endpunkt, der zu seinem eigenen
  Bildschirm passt.
- **Fokus-Timer** — ein Pomodoro auf derselben Seite, angekündigt vom Haustier:
  Es sagt Ihnen, wann der Fokus endet und wann die Pause vorbei ist.
- **Chat** — das Haustier kann Ihnen über Claude antworten, wenn
  `ANTHROPIC_API_KEY` gesetzt ist. Aus, sofern Sie es nicht aktivieren; siehe
  [Was die Maschine verlässt](#was-die-maschine-verlässt).

**Hintergrundbild** — spielen Sie einen Ordner mit Bildern und Animationen
*unter* jedem Fenster ab. Jeder Monitor zeigt auf seinen eigenen Ordner mit
seinem eigenen Timer, gemischt oder rekursiv gelesen, und kann mit dem
Lautsprecherpegel pulsieren. Ein zweiter Ordner kann während der Ruhezeiten
übernehmen.

**Widgets** — vier Dinge, die auf dem Desktop sitzen:

- **Audiospektrum** — Balken oder ein Ring, logarithmisch verteilte Bänder,
  geglättet mit einem Folger mit schnellem Anstieg/langsamem Abfall und
  Spitzenmarkierungen, die nach unten driften.
- **Aktuelle Wiedergabe** — der aktuelle Titel aus den Mediensteuerungen von
  Windows, wenn die optionalen `winsdk`-Bindungen installiert sind; andernfalls
  der Name der App, die tatsächlich Ton erzeugt.
- **Systemmonitor** — CPU, Speicher, Datenträger, Akku und Netzwerkdurchsatz als
  kleine Sparklines; haken Sie die Linien an, die Sie möchten. Ein Durchschnitt
  verbirgt ein Stocken; eine Linie nicht. Eine ausgeblendete Linie zeichnet
  weiter auf, sodass ein erneutes Einschalten zeigt, was in der Zwischenzeit
  passiert ist.
- **Haftnotizen** — bearbeitbare Karten über jedem Fenster, die ihren Text, ihre
  Farbe und Position zwischen den Sitzungen behalten.

### Arbeit

**Fokus** — zwei Overlays für den Fall, dass der Bildschirm mit Ihrer Arbeit
konkurriert. *Hintergrundfenster abdunkeln* schattiert alles außer dem Fenster,
in dem Sie arbeiten, in einstellbarer Stärke. *Eine Ablenkung abdecken*
maskiert einen Streifen des Bildschirms: die Taskleiste, eine
Benachrichtigungsecke, einen Rand oder alles davon. Beide lassen Klicks
durch, sodass das Abgedeckte weiterhin funktioniert — es zieht nur nicht mehr
Ihren Blick auf sich.

**Bildschirmschonung** — für lange Sitzungen am Bildschirm:

- **Farbfilter** — sieben Tönungen von warm über Bernstein und Rosé bis Grau,
  in einstellbarer Stärke.
- **Leselineal** — dimmt die Seite und lässt ein helles Band, das dem
  Mauszeiger folgt.
- **Pausenerinnerung** — die 20-20-20-Regel, mit einem Ruhe-Overlay, wenn das
  Intervall abgelaufen ist.
- **Farbsehsimulation** — Protanopie, Deuteranopie, Tritanopie und
  Achromatopsie in einstellbarem Schweregrad, unter Verwendung des Modells von
  Machado et al. (2009). Anders als die anderen Overlays ist dieses
  undurchsichtig, denn zu zeigen, was jemand anderes sieht, bedeutet, den
  Bildschirm neu zu zeichnen, statt ihn zu tönen.

**Präsentieren** — für Demos, Lektionen und Aufnahmen:

- **Annotation** — zeichnen Sie über den Bildschirm mit Stift, Textmarker oder
  Radiergummi, mit Rückgängig und Löschen.
- **Cursoreffekte** — ein Ring um den Zeiger, eine Welle beim Klick und ein
  Scheinwerfer, der alles andere abdunkelt.
- **Tastenanzeige** — zeigt, was Sie gerade gedrückt haben und welche Maustaste
  Sie geklickt haben, sodass Zuschauer folgen können; sie verblasst nach ein
  paar Sekunden. Wählen Sie, wo das Panel sitzt und wie groß der Text ist, und
  schalten Sie Mausklicks für sich allein aus.
- **Lupe** — eine vergrößerte Ansicht des Bereichs um den Mauszeiger.
- **Whiteboard** — eine unendliche Leinwand: ziehen zum Verschieben, scrollen
  zum Zoomen, speichern, was Sie gezeichnet haben. Striche leben in
  Leinwandkoordinaten, sodass Verschieben und Zoomen sie dort belässt, wo sie
  hingehören.
- **Einfrieren** — fixieren Sie das aktuelle Bild eines Monitors, sodass Sie
  hinter einem Standbild weiterarbeiten können. `Ctrl+Shift+F7` gibt es frei,
  was wichtig ist, weil das eingefrorene Bild die Schaltfläche verdeckt, die es
  täte.

**Werkzeuge** — Messen, Erfassen und Fensterhandhabung:

- **Farbwähler / Pixellineal / Winkelmesser** — klicken zum Abtasten oder
  Messen; das Ergebnis landet direkt in der Zwischenablage als `#rrggbb`,
  `rgb(...)`, `hsl(...)` oder einer benutzerdefinierten CSS-Eigenschaft.
- **Bereichserfassung** — ziehen Sie einen Bereich auf; er landet in der
  Zwischenablage, kann in eine Datei gespeichert oder als schwebende, zoombare
  Kopie **angeheftet** werden.
- **Bereich aufnehmen** — Aufzeichnung: Wählen Sie einen Bereich und vor dem Start die GIF- oder AVI-Zieldatei. Abbrechen startet keine Aufnahme. Ein Hintergrundthread schreibt Bilder einzeln; die Warteschlange ist auf drei Bilder und 64 MiB begrenzt. Ein zu großes Einzelbild wird abgewiesen. Bei voller Warteschlange werden Aufnahmen ausgelassen, ihre Zeit bleibt in der Wiedergabe erhalten. Bildrate, Dauer, Bildzahlgrenze und Kamerabild in der Ecke bleiben erhalten. Stoppen schließt die Datei asynchron ab; erst bei Erfolg wird das Ziel atomar ersetzt. Abbruch und Schreibfehler entfernen die temporäre Datei und bewahren ein vorhandenes Ziel.
- **Kamera** — Ihre Webcam in einem Kreis, einem abgerundeten Kasten oder einem
  Rechteck, lokal angezeigt und nie aufgezeichnet. Jeder Videoeingang
  funktioniert, einschließlich Capture-Karten, und die Geräteliste
  aktualisiert sich ohne Neustart, da Karten normalerweise eingesteckt werden,
  während die App bereits läuft.
- **Virtuelle Kamera** — senden Sie einen Bereich, samt Overlays, als Webcam,
  die Zoom, Teams oder Discord als ihre Videoquelle auswählen können. Benötigt
  das optionale Paket `pyvirtualcam` und einen virtuellen Kameratreiber (OBS
  installiert einen); ohne eines von beiden sagt es die Schaltfläche, statt
  still zu versagen.
- **Text lesen** — Bildschirmtext: Werkzeuge → Text lesen versucht zuerst lokale OCR: Windows.Media.Ocr unter Windows, Vision unter macOS oder ein installiertes Tesseract mit Sprachdaten. Lokale Erkennung benötigt weder Cloud-Zustimmung noch ANTHROPIC_API_KEY; ein erfolgreiches leeres Ergebnis lädt keinen Screenshot hoch. Übersetzungen und Fragen dürfen erkannten Text nur mit gesonderter Text-Zustimmung und Ihrem Schlüssel an Anthropic senden. Der Screenshot-Ersatz nach lokalem Fehler benötigt eigene Aufnahme-Zustimmung und den Schlüssel. Das Ergebnis zeigt Dienst und Fehler; dort lässt sich die Zustimmung widerrufen.
- **Ein Fenster anheften** — halten Sie das Fenster eines anderen Programms oben
  oder blenden Sie es aus, während Sie dagegen arbeiten. Nur Stapelung und
  Deckkraft werden berührt, nie der Fensterinhalt.
- **Fensterreplik** — eine kleine, immer im Vordergrund befindliche Live-Kopie
  eines anderen Fensters, sodass Sie einen Render oder einen Chat verfolgen
  können, während er verdeckt ist.
- **Fensterlayouts** — speichern Sie, wo jedes Fenster sitzt, und stellen Sie
  sie später wieder her. Fenster werden anhand des Titels zugeordnet; eines, das
  nicht auf dem Bildschirm ist, wird übersprungen statt geraten.

---

## Alles auf einmal steuern

Die **Steuerzentrale**-Seite erreicht jedes Overlay auf jeder Seite, egal
welche Registerkarte es geöffnet hat: ausblenden, einblenden, schließen,
stummschalten, sperren, Positionen zurücksetzen, die Deckkraft in Schritten
ändern und eine **Qualitätsstufe** (hoch / ausgewogen / sparsam) anwenden, die
die Aktualisierungsrate jedes Overlays begrenzt und seine Renderauflösung
absenkt. Sie trägt außerdem einen Chroma-Key-Hintergrund für OBS, eine
Umschaltung *Aus Erfassung ausblenden*, das Protokollpanel und **An diesen
Desktop anheften** — die Overlays treten beiseite, wenn Sie den virtuellen
Desktop wechseln, und kehren zurück, wenn Sie zurückkommen. Das Lösen bringt
alles zurück, was es weggeräumt hatte.

Standardmäßige globale Hotkeys, alle neu belegbar über **Einstellungen →
Hotkeys**:

| Shortcut | Aktion |
| --- | --- |
| `Ctrl+Shift+F12` | Jedes Overlay schließen |
| `Ctrl+Shift+F11` / `F10` | Jedes Overlay aus- / einblenden |
| `Ctrl+Shift+F9` | Alles stummschalten |
| `Ctrl+Shift+↑` / `↓` | Deckkraft hoch / runter |
| `Ctrl+Shift+L` | Sperren oder entsperren (klickdurchlässig vs. ziehbar) |
| `Ctrl+Shift+→` | Nächste Dashboard-Seite |
| `Ctrl+Shift+F8` | Das Shortcut-Blatt auf dem Bildschirm anzeigen |
| `Ctrl+Shift+F7` | Den Bildschirm einfrieren / freigeben |
| `Ctrl+Shift+F6` / `F5` / `F4` | Medien Wiedergabe/Pause, nächster und vorheriger Titel |
| `Ctrl+Shift+F3` | Das Vordergrundfenster auf den nächsten Monitor verschieben |
| `F12` | Sofort beenden (Windows / macOS*) |

Die Medientransportfunktion sendet die System-Medientasten, sodass sie jeden
Player erreicht, der auf sie hört. Das Verschieben eines Fensters behält seine
Proportionen bei, statt es hinüberzuschnappen, was Windows' eigenes
`Win+Shift+Arrow` tut.

Dieselben Aktionen — und nichts darüber hinaus — treiben die Fernsteuerungen an:

- **Ihr Telefon** (Einstellungen → Fernsteuerung) — FrontEngine liefert eine
  kleine Seite in Ihrem lokalen Netzwerk aus; öffnen Sie den Link auf einem
  Telefon, und die Schaltflächen treiben diese Aktionen an.
- **Ein MIDI-Controller** — Learn drücken, einen Regler oder ein Pad bewegen und zuweisen. Windows verwendet integriertes winmm; macOS verwendet CoreMIDI mit dem macos-Extra. Ein Regler löst oben einmal aus, das Loslassen eines Pads zählt nicht als weiterer Druck.

---

## Presets und Automatisierung

**Presets** erfassen die Einstellungen jeder Seite auf einmal. Speichern, laden,
löschen, exportieren und importieren Sie sie über das Menü **Presets**, wenden
Sie eines beim Start an oder stellen Sie die vorherige Sitzung automatisch
wieder her. Ein Preset kann als **Paket** exportiert werden — eine Zip-Datei,
die die referenzierten Medien mitträgt — sodass es sich auf einer Maschine
öffnet, die diese Dateien nicht hat.

Dinge, die dann selbst entscheiden, alle aus dem Menü **Einstellungen**.
Intelligentes Pausieren ist das einzige, das von Anfang an aktiv ist; alles
andere ist aus, bis Sie es einschalten.

| | |
| --- | --- |
| **Regeln** | *"Wenn diese Bedingungen gelten, tue dies."* Kombinieren Sie einen Wochentag, ein Zeitfenster und welche Anwendung den Fokus hat, und wenden Sie dann ein Preset an, blenden Sie die Overlays aus/ein/schließen Sie sie oder setzen Sie die Qualität. Eine leere Bedingung bedeutet "beliebig", und eine Regel läuft **einmal**, wenn ihre Bedingungen zu gelten beginnen, statt wiederholt, solange sie gelten. Dies ist der eine Ort, an dem Bedingungen sich zusammensetzen; die Zeilen darunter kennen jeweils nur eine einzige Art. |
| **Intelligentes Pausieren** | Stellen Sie die Overlays zurück, während eine Vollbild-App läuft, während die Maschine im Akkubetrieb ist oder während eine benannte App den Fokus hat. *(Standardmäßig an, für die Vollbildregel.)* |
| **App-Profile** | Wenden Sie ein Preset an, wenn Sie zu einer bestimmten App wechseln. |
| **Preset-Zeitplan** | Wenden Sie ein Preset an ausgewählten Wochentagen zu einer festgelegten Zeit an. |
| **Themen-Zeitplan** | Wechseln Sie nach der Uhr zwischen einem Tag- und einem Nachtthema. |
| **Beschilderungsmodus** | Rotieren Sie eine Liste von Presets per Timer mit weggeräumtem Hauptfenster, für eine als Anzeige laufengelassene Maschine. |
| **Bildschirmschoner** | Bringen Sie nach einer Leerlaufschwelle das gewählte Video / Bild / GIF / den Partikel / die Webseite auf und nehmen Sie es herunter, wenn Sie zurückkommen. |
| **Erinnerungen** | Alle N Minuten oder einmal am Tag zu einer festgelegten Zeit, angezeigt als Toast, der sich selbst schließt. |
| **Wachhalten** | Verhindern Sie das Schlafen des Displays, während Overlays aktiv sind. |
| **Mit dem System starten** | Beim Anmelden starten. |
| **Bildschirmzeit** | Welche Apps den Fokus hatten und wie lange, mit einer täglichen Aufschlüsselung und einer Sieben-Tage-Zusammenfassung. Es pausiert, während Sie von der Tastatur weg sind, behält höchstens 60 Tage, und das Löschen entfernt die Datei selbst. |
| **Zwischenablageverlauf** | Durchsuchen Sie, was Sie kopiert haben, und heften Sie die Phrasen an, die Sie wiederverwenden. Zwischenablagen enthalten routinemäßig Passwörter, daher wird dies **nur im Speicher** gehalten, es sei denn, Sie haken separat "zwischen Sitzungen behalten" an. |

---

## Sprachen

Sieben: English, 繁體中文, 简体中文, Deutsch, Русский, Français, Italiano.

Wählen Sie eine aus dem Menü **Sprache**, und die Oberfläche ändert sich
**sofort** — kein Neustart. Was Sie geöffnet hatten, bleibt geöffnet: Overlays
laufen weiter, und die Einstellungen auf jeder Seite bleiben genau so, wie sie
waren. Bei einer Steam-Installation folgt der erste Start der eigenen Sprache
des Steam-Clients.

---

## Datenschutz- und Plattformhinweise

### Was die Maschine verlässt

Alles in FrontEngine ist lokal, es sei denn, es steht auf dieser Liste. Es gibt
vier Ausnahmen, alle opt-in:

| Funktion | Wohin es geht | Schutz |
| --- | --- | --- |
| **Text lesen** (Werkzeuge) | Anthropic API | Bildschirmtext: Werkzeuge → Text lesen versucht zuerst lokale OCR: Windows.Media.Ocr unter Windows, Vision unter macOS oder ein installiertes Tesseract mit Sprachdaten. Lokale Erkennung benötigt weder Cloud-Zustimmung noch ANTHROPIC_API_KEY; ein erfolgreiches leeres Ergebnis lädt keinen Screenshot hoch. Übersetzungen und Fragen dürfen erkannten Text nur mit gesonderter Text-Zustimmung und Ihrem Schlüssel an Anthropic senden. Der Screenshot-Ersatz nach lokalem Fehler benötigt eigene Aufnahme-Zustimmung und den Schlüssel. Das Ergebnis zeigt Dienst und Fehler; dort lässt sich die Zustimmung widerrufen. |
| **Haustier-Chat** | Ihre Nachricht geht an die API von Anthropic | Gleicher Schlüssel, gleiche Regel; standardmäßig aus. |
| **Wetter** (Textquelle) | Koordinaten gehen an Open-Meteo | Kein Schlüssel, kein Konto, keine identifizierenden Daten; nur das, was Sie als Ort eingegeben haben. |
| **Telefon-Fernsteuerung** | HTTPS | Telefonsteuerung: Einstellungen → Fernsteuerung verwendet ausschließlich HTTPS, ein bei jedem Start neues Token und eine feste Aktionsliste. Das Telefon vertraut dem selbstsignierten Zertifikat nicht automatisch. Exportieren Sie das öffentliche Zertifikat und vergleichen Sie den angezeigten SHA-256-Fingerabdruck, bevor Sie es in den Telefon-/Browsereinstellungen importieren oder ihm vertrauen. Der private Schlüssel bleibt im Benutzerdatenordner. IP-Änderung, Ablauf oder Neuerstellung können ein neues Zertifikat erfordern. Ein TLS-Startfehler führt nicht zu HTTP. |

Die Audiofunktionen lesen nur einen Ausgabe-**Pegel** — eine einzelne Zahl —
außer dem Spektrum, das echte Samples benötigt, um Frequenzen zu berechnen, und
daher den Systemausgabestrom erfasst. Diese Samples werden im Speicher
analysiert, nie auf die Festplatte geschrieben oder irgendwohin gesendet, und
die Erfassung stoppt in dem Moment, in dem Sie das Spektrum stoppen.

Plugins: Aktiviertes Laden ist noch keine Freigabe. plugin.json oder eine Begleitdatei für ein einzelnes Plugin deklariert Version, Identität, Einstiegspunkt und Fähigkeiten. Zustimmung wird vor Python-Import geprüft und an die Inhaltsprüfsumme gebunden. Geänderter Code oder geänderte Deklarationen erfordern neue Zustimmung; alte Plugins benötigen ausdrückliches volles Vertrauen. Einstellungen → Plugin-Freigaben widerrufen löscht gespeicherte Freigaben; laufenden Code entlädt erst ein Neustart. Python-Plugins haben weiterhin alle Anwendungsrechte; Deklaration und Zustimmung sind keine Betriebssystem-Sandbox.

### Datenschutz bei der Bildschirmfreigabe

Ihre Overlays sind für Sie, nicht für die Personen, mit denen Sie teilen. Über
**Einstellungen → Datenschutz bei der Bildschirmfreigabe** kann FrontEngine sie
aus der Erfassung herausnehmen, während eine Meeting-App geöffnet ist:

- **Sie bleiben auf Ihrem eigenen Bildschirm.** Nur die erfasste Kopie ist leer
  — dies verwendet Windows' `WDA_EXCLUDEFROMCAPTURE`, ein Flag auf
  Betriebssystemebene, das Konferenz-Apps und Recorder respektieren.
- **Masken sind die Ausnahme.** Eine Ablenkungsmaske existiert, um etwas zu
  verdecken, daher bleibt sie in der Erfassung absichtlich sichtbar.
- **Der Auslöser ist Ihre Liste.** Windows hat keine zuverlässige "werde ich
  gerade erfasst"-API, daher achtet es auf Fenstertitel, die Sie benennen — was
  auch ein in einem Browser-Tab abgehaltenes Meeting erfasst, bei dem die
  ausführbare Datei nur der Browser ist.

Es gibt auch eine manuelle Schaltfläche *Aus Erfassung ausblenden* in der
Steuerzentrale.

> Dies ist Datenschutz, keine Sicherheit: es überlistet den gewöhnlichen
> Erfassungspfad, und es verbirgt niemals etwas vor der Person, die am
> Schreibtisch sitzt.

### Plattformunterstützung

Alles, was hier nicht aufgeführt ist, funktioniert auf allen drei Plattformen.

| Funktion | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Gemeinsame Overlays und Oberfläche | ✅ | ✅ | ✅ |
| Systemaudio, Spektrum und Mikrofon | ✅ | backend* | — |
| Metadaten des laufenden Titels | ✅ | — | — |
| Fenstergeometrie, Anordnung und Monitorwechsel | ✅ | backend* | — |
| Live-Fensterduplikat | ✅ | backend* | — |
| Fremde Fenster: Vordergrund / Deckkraft | ✅ | — | — |
| Overlays von Aufnahme ausschließen | ✅ | — | — |
| MIDI-Steuerung | ✅ | backend* | — |
| Medientasten | ✅ | backend* | — |
| Virtueller Desktop / Space-Auswahl | ✅ | — | — |
| F12-Notausstieg | ✅ | backend* | — |
| Haustier auf anderen Fenstern | ✅ | backend* | wmctrl |

* macOS-Einträge mit „backend“ benötigen das macos-Extra, macOS 13+ und die jeweiligen Berechtigungen. Sie beschreiben implementierte öffentliche Framework-Pfade, keine native Prüfung auf diesem Windows-Rechner; siehe die Laufzeithinweise unten.

Wo eine Funktion nicht funktionieren kann, sagt es die Schaltfläche, statt still
zu versagen.

---

## Laufzeit, Datenschutz und Interoperabilität

Aufzeichnung: Wählen Sie einen Bereich und vor dem Start die GIF- oder AVI-Zieldatei. Abbrechen startet keine Aufnahme. Ein Hintergrundthread schreibt Bilder einzeln; die Warteschlange ist auf drei Bilder und 64 MiB begrenzt. Ein zu großes Einzelbild wird abgewiesen. Bei voller Warteschlange werden Aufnahmen ausgelassen, ihre Zeit bleibt in der Wiedergabe erhalten. Bildrate, Dauer, Bildzahlgrenze und Kamerabild in der Ecke bleiben erhalten. Stoppen schließt die Datei asynchron ab; erst bei Erfolg wird das Ziel atomar ersetzt. Abbruch und Schreibfehler entfernen die temporäre Datei und bewahren ein vorhandenes Ziel.

Telefonsteuerung: Einstellungen → Fernsteuerung verwendet ausschließlich HTTPS, ein bei jedem Start neues Token und eine feste Aktionsliste. Das Telefon vertraut dem selbstsignierten Zertifikat nicht automatisch. Exportieren Sie das öffentliche Zertifikat und vergleichen Sie den angezeigten SHA-256-Fingerabdruck, bevor Sie es in den Telefon-/Browsereinstellungen importieren oder ihm vertrauen. Der private Schlüssel bleibt im Benutzerdatenordner. IP-Änderung, Ablauf oder Neuerstellung können ein neues Zertifikat erfordern. Ein TLS-Startfehler führt nicht zu HTTP.

Bildschirmtext: Werkzeuge → Text lesen versucht zuerst lokale OCR: Windows.Media.Ocr unter Windows, Vision unter macOS oder ein installiertes Tesseract mit Sprachdaten. Lokale Erkennung benötigt weder Cloud-Zustimmung noch ANTHROPIC_API_KEY; ein erfolgreiches leeres Ergebnis lädt keinen Screenshot hoch. Übersetzungen und Fragen dürfen erkannten Text nur mit gesonderter Text-Zustimmung und Ihrem Schlüssel an Anthropic senden. Der Screenshot-Ersatz nach lokalem Fehler benötigt eigene Aufnahme-Zustimmung und den Schlüssel. Das Ergebnis zeigt Dienst und Fehler; dort lässt sich die Zustimmung widerrufen.

Puppet-Haustiere: Installieren Sie das optionale puppet-Extra und eine verfügbare Imervue-Laufzeit; wählen oder ziehen Sie eine originale Imervue-.puppet-v1-Datei auf die Haustierseite. Bild- und Sprite-Pakete bleiben nutzbar. Puppet-Haustiere verwenden Imervues Canvas, Bewegungen und Ausdrücke, können dupliziert oder geschlossen werden und folgen Overlay-Steuerung und Voreinstellungen. Eine optionale .petscript.json verwendet Imervues Skriptengine; FrontEngine-pet.json-Pakete sind keine Puppet-Dateien. Unbekannte Versionen, unsichere Archivpfade und ungültige Medien werden vor dem Laden abgewiesen.

Szenen: Die Szenenseite liest alte JSON-Eintragslisten, versionierte frontengine.scene-Dokumente und portable .fescene-Pakete. PUPPET-Einträge enthalten Position, Größe, Deckkraft, endliche numerische Parameter sowie optionale Bewegung, Ausdruck und Skript. JSON-Pfade beziehen sich auf die Szenendatei. .fescene enthält die referenzierten Medien, die originale .puppet und optionale .petscript.json für andere Rechner. Import prüft Pfade, symbolische Links, Versionen und Entpackgrenzen. Eine FrontEngine-Szene bleibt ein Szenenpaket; .puppet bleibt eine einzelne Imervue-Figur.

macOS: Das optionale macos-Extra zielt auf macOS 13+ und öffentliche PyObjC-Frameworks. Die Backends bieten ScreenCaptureKit für Bildschirm-/Fensteraufnahme und Systemaudio, Mikrofonaufnahme, Quartz-Fenstergeometrie, Accessibility für Fensteranordnung/-bewegung, CoreMIDI, Medientasten und F12 zum Beenden. Bildschirmaufnahme, Bedienungshilfen und Mikrofon haben getrennte Berechtigungen; folgen Sie Systemeinstellungen → Datenschutz & Sicherheit und starten Sie bei Aufforderung neu. Deckkraft/erzwungener Vordergrund fremder Fenster, Space-Auswahl und Aufnahmeausschluss bleiben nicht verfügbar. Native macOS-Berechtigungen, Hardware und Leistung wurden auf diesem Windows-Entwicklungsrechner nicht geprüft. Einstellungen → macOS-Berechtigungen und Fähigkeiten zeigt jede Funktion als verfügbar, nicht verfügbar oder nicht unterstützt, mit Berechtigungs- oder Installationsgrund.

Plugins: Aktiviertes Laden ist noch keine Freigabe. plugin.json oder eine Begleitdatei für ein einzelnes Plugin deklariert Version, Identität, Einstiegspunkt und Fähigkeiten. Zustimmung wird vor Python-Import geprüft und an die Inhaltsprüfsumme gebunden. Geänderter Code oder geänderte Deklarationen erfordern neue Zustimmung; alte Plugins benötigen ausdrückliches volles Vertrauen. Einstellungen → Plugin-Freigaben widerrufen löscht gespeicherte Freigaben; laufenden Code entlädt erst ein Neustart. Python-Plugins haben weiterhin alle Anwendungsrechte; Deklaration und Zustimmung sind keine Betriebssystem-Sandbox.

Darstellung: Einstellungen → Overlay-Darstellung bietet Automatisch, GPU oder Software und zeigt den tatsächlich verwendeten Dienst. Der GPU-Compositor verwendet OpenGL-Texturen, Shader und Framebuffer für Reihenfolge, Transformation, Deckkraft und Ausschnitt; bei Initialisierungsfehler wird mit Begründung auf Software zurückgefallen. QPainter-Inhalte können weiter auf der CPU rasterisiert und hochgeladen werden; Web-/Video-/native Widgets können eigene Fenster verwenden. Aufnahme kann GPU-Bilder zur CPU zurücklesen. Das verspricht weder kopierfreie Aufnahme noch gemessene Leistungsgewinne.

WinRT-Projektionen für Windows-OCR sind in der normalen FrontEngine-Installation unter Windows enthalten; installieren Sie die benötigten Windows-Erkennungssprachen. Tesseract benötigt separat Programm und trainierte Sprachdaten. Das optionale puppet-Extra installiert Imervue>=1.0.90; das macos-Extra installiert öffentliche PyObjC-Frameworks für macOS 13+. Verwenden Sie die Befehle unten. docs/formats/ enthält Beispiele für Puppet, pet.json, Petscript und Szenen.

```bash
pip install "frontengine[puppet]"
pip install "frontengine[macos]"
```

[.puppet / pet.json / .petscript.json / .fescene](../docs/formats/interoperability.md)

---

## Erweitern

- **Steam Workshop** — abonnierte Elemente werden aus Steams eigenem Ordner
  `steamapps/workshop/content` aufgenommen: Presets werden importiert und
  Pet-Packs mit ihren Pfaden aufgelistet, über **Presets → Workshop-Inhalte
  importieren**. Das Veröffentlichen im Workshop benötigt das Steamworks SDK
  und ist nicht eingebaut.
- **Plugins** — ein `plugins/`-Ordner kann eigene Registerkarten hinzufügen,
  entweder über eine `FRONTENGINE_TABS = {"name": WidgetClass}`-Zuordnung oder
  einen `register(registry)`-Hook. Lesen Sie zuerst den Vertrauenshinweis oben.

---

## Entwicklung

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

Die statische Prüfung verwendet pyflakes (in `dev_requirements.txt`), und ein
sauberer Baum gibt überhaupt nichts aus:

```bash
python -m pyflakes frontengine/ exe/ tests/
```

Die Testsuite läuft vollständig außerhalb des Bildschirms und benötigt kein
Display, keine Soundkarte und keine Kamera; alles, was die Außenwelt berührt,
nimmt eine injizierbare Quelle, sodass es mit einer gefälschten getestet werden
kann.

- **Architektur** — [`architecture_explore.md`](../architecture_explore.md)
  kartiert jedes Modul, die Schichtung, den Overlay-Vertrag und die
  Erweiterungspunkte. Lesen Sie es, bevor Sie eine Seite oder ein Overlay
  hinzufügen: mehrere Dinge (die Registry der Steuerzentrale, sieben
  Sprachwörterbücher, sieben Dokumentationsbäume) müssen zusammen aktualisiert
  werden, und die Tests erzwingen das.
- **Mitwirken** — siehe [`CONTRIBUTING.md`](../CONTRIBUTING.md). Eine Funktion
  pro Pull Request, alle CI-Prüfungen grün.
- **Erstellen der ausführbaren Windows-Datei** — `python exe/build_exe.py`
  (Nuitka; fügen Sie `--onefile` für eine einzelne Datei hinzu).
- **Dokumentation** — Sphinx-Quellen in `docs/`, veröffentlicht auf
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) in allen
  sieben Sprachen.

---

## Kontinuierliche Integration und Releases

Die Arbeit fließt `feature → dev → main`, und nur der letzte Schritt
veröffentlicht:

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| Workflow | Auslöser | Zweck |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR nach `main` oder `dev`, manueller Dispatch oder aufgerufen von `Nightly` | Kompilieren, die Unit-Tests ausführen, dann ein Wheel aus *diesem Checkout* bauen, es installieren und die App starten — auf Python 3.10 / 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Täglicher Cron, manueller Dispatch | Ruft `CI` auf. Der Zeitplan liegt absichtlich hier: GitHub deaktiviert Workflows, die einen Cron enthalten, nach etwa 60 Tagen Inaktivität, und das würde sonst die PR-Prüfungen mit hinunterreißen |
| `Release` (`release.yml`) | Ein Pull Request **von `dev`** wird in `main` gemerged, oder manueller Dispatch | Erhöht die Version, committet sie zurück mit `[skip ci]`, tauscht `stable.toml` → `pyproject.toml`, baut sdist + wheel, lädt zu PyPI als `frontengine` hoch, erstellt ein GitHub-Release getaggt `v<version>` und führt `dev` per Fast-Forward nach |

Die Veröffentlichung geschieht **nur, wenn `dev` in `main` gemerged wird**.
Funktionen landen auf `dev`, ohne eine Version zu prägen, und ein Release ist
ein bewusster `dev → main`-Pull-Request. Ein irrtümlich auf `main` gerichteter
Feature-PR wird trotzdem gemerged, veröffentlicht aber nicht — die
Fehlerrichtung ist ein fehlendes Release, nicht ein ungewolltes.

Das Patch-Segment wird automatisch erhöht; für ein Minor- oder Major-Release
führen Sie *Actions → Release → Run workflow* aus und wählen Sie das Segment.
Dieser Weg führt auch eine fehlgeschlagene Veröffentlichung erneut aus, ohne
einen neuen Merge zu benötigen.

Versionen leben in zwei Dateien: `pyproject.toml` ist das Dev-Paket
(`frontengine_dev`) und `stable.toml` ist das veröffentlichte (`frontengine`).

Ein Repository-Secret ist erforderlich: `PYPI_API_TOKEN`, ein PyPI-Token, das
auf das Projekt `frontengine` beschränkt ist. Der Workflow verwendet `__token__`
als Twine-Benutzernamen, sodass nur das Token selbst gespeichert werden muss.

---

## Lizenz

Siehe [`LICENSE`](../LICENSE). Community-Erwartungen finden Sie in
[`Contributor_Covenant_Code_of_Conduct.md`](../Contributor_Covenant_Code_of_Conduct.md).

Workshop-Manifeste sind versioniert und werden vor der Verwendung geprüft. Unbekannte Metadaten-JSON-Dateien gelten nicht als Presets. Preset-Pakete weisen unsichere Archivpfade, überschrittene Ressourcenlimits und kollidierende Mediendateinamen zurück.

Presets → Workshop verwalten öffnet den Steam-Manager; Szene und Tier bieten ebenfalls Zugänge. Windows x64 benötigt einen online angemeldeten Steam-Client für App 2793470 und steam_api64.dll. Gespeicherte .fescene/Szenen-JSON, Preset-ZIP und Sprite-Tierordner lassen sich mit PNG/JPEG-Vorschau unter 1 MB veröffentlichen. Neue Elemente sind standardmäßig privat; Updates prüfen den Eigentümer. Uploads zeigen Fortschritt und Vertragsstatus, speichern IDs für Wiederholungen und laufen bei verborgenem Fenster weiter. Unterbrochene Ergebnisse in Steam prüfen. Abonnements werden validiert und in getrennte Versionsordner kopiert; bei lokalen Änderungen kann die neue oder lokale Version gewählt werden. Laden füllt die Funktionsseite; dort die Wiedergabe starten. Presets benötigen einen neuen Namen. Offline-Ordnerimport bleibt verfügbar. Für Steam-Builds exe/build_exe.py mit --steam-runtime DLL_PFAD verwenden; die DLL liegt neben der EXE, auch mit --onefile. SDK und Entwicklungsdatei steam_appid.txt werden nicht mitgeliefert.

Windows-Installationen enthalten jetzt winrt-Windows.Media.Control für Titel und Interpret im Wiedergabe-Widget über SMTC; älteres winsdk bleibt eine Alternative. Ohne Mediensitzung bleibt das Ergebnis leer; die bisherige Anzeige des Audio-App-Namens bleibt erhalten.

EXE-Builds prüfen benötigte Abhängigkeiten und Versionen vor der Kompilierung; zuerst requirements.txt in der Build-Umgebung installieren.

Szene → Visueller Editor bietet Bild/GIF/Text-Ebenenliste und Vorschau, Gruppenziehen, Eckenskalierung, Position/Größe/Skalierung/Drehung/Reihenfolge/Deckkraft, Leinwandausrichtung, Layoutsperre, Sichtbarkeit, Duplizieren und 100 Undo/Redo-Schritte (Ctrl+Z/Ctrl+Y). Portable .fescene direkt exportieren; im Skript-Tab JSON bearbeiten und anwenden. Wiedergabe übernimmt explizite Größe, Skalierung, Drehung und Sichtbarkeit. Externes JSON beginnt eine neue Undo-Historie; vorhandene Felder bleiben erhalten.

Öffnen Sie Befehle in der Menüleiste oder drücken Sie in FrontEngine Strg+K / Strg+Umschalt+P. Suchen Sie in der aktuellen Sprache, mit englischen Namen oder festen Befehlsnamen; Pfeiltasten wählen, Enter führt aus. Enthalten sind Seitennavigation, Aufnahme, Notizen, Bildschirmfilter, Workshop und bestehende globale Aktionen. Preset/Qualität akzeptieren einen Wert. Favoriten und die letzten 20 Befehle bleiben erhalten; Parameter und Suchtext werden nicht gespeichert.

Text → Lokale TXT / JSON / CSV zeigt UTF-8-Dateien mit Feldwahl und 1–3600 Sekunden Intervall. JSON: /Schlüssel/Index (etwa /build/tasks); CSV: eindeutige Spaltennamen, Spalte zeilenweise. Leer zeigt die ganze Datei. Hintergrundlesen: ein Auftrag je Quelle, maximal 1 MiB und 65.536 Ausgabezeichen. Fehlende Dateien/Felder, Format-, Zugriffs- und Größenfehler werden angezeigt; Korrekturen stellen die Anzeige wieder her. Presets speichern Datei/Feld/Intervall. Portable Szenen kopieren die Datendatei; das Teilen gibt diesen Datenstand weiter.

Werkzeuge → Farbpalette sammelt aufeinanderfolgende Klicks, wenn Farben sammeln aktiv ist. Farben benennen/gruppieren, Hex bearbeiten, suchen, kopieren und entfernen; letzte Proben bleiben nutzbar. Bis zu 512 Farben und 50 verschiedene letzte Proben werden lokal gespeichert. Namen sind je Gruppe ohne Beachtung der Großschreibung eindeutig. CSS/JSON bewahren RGB; CSS-Namenskollisionen erhalten Nummern. Export ersetzt die Datei atomar. Die Befehlspalette öffnet auch die Farbpalette.

Vorlagen → Vorlagenversionen bewahrt je Vorlage bis zu 50 verschiedene Einstellungsschnappschüsse über Neustarts hinweg. Beim Speichern werden alte und neue Konfigurationen erfasst; gleiche Inhalte werden nicht doppelt gespeichert. Die Auswahl zeigt Feldänderungen gegenüber den aktuellen Seiteneinstellungen. Die Vorschau wendet diese Konfiguration auf die Steuerelemente an; Abbrechen, Escape oder Schließen stellt die ursprünglichen Einstellungen wieder her. Wiederherstellen wendet die Version an und speichert sie; bei Anwendungs- oder Speicherfehlern werden die Seiteneinstellungen zurückgesetzt. Schnappschüsse enthalten Medienpfade, keine Mediendateien; die Vorschau öffnet keine Overlays. Bestehende JSON-/ZIP-Vorlagen bleiben kompatibel. Der Verlauf liegt unter presets/.versions und bleibt beim Löschen einer Vorlage für die Wiederverwendung ihres Namens erhalten.

Tier → Tieridentitäten speichert für jedes Sprite- oder Puppet-Tier eine eigene UUID, einen Namen, Stimmung, Sättigung und Zuneigung. Zum Fortsetzen nach Neustart vor dem Erzeugen eine gespeicherte Identität wählen; Neues Tier beginnt neu. Nur die erste Identität übernimmt einmal die alten gemeinsamen Werte. Klonen kopiert aktuelle Werte in eine neue Identität; Füttern verändert andere Tiere nicht. Einzelne JSON-Spielstände lassen sich umbenennen, aktualisieren, exportieren und importieren; Import erzeugt immer eine neue Identität. Eine Identität darf nur einmal aktiv sein. Spielstände enthalten keine Grafiken, Skripte oder Chatverläufe; portable Vorlagen enthalten keine lokalen IDs. Bis zu 256 Identitäten bleiben in den Benutzereinstellungen; Sprite-Änderungen werden gebündelt und beim Schließen gespeichert. Puppet-Füttern ändert nur gespeicherte Werte, keine Imervue-Bewegungen oder Größen.

Bild → Bilder vergleichen zeigt zwei Referenzen in einer gemeinsam zoombaren und verschiebbaren Ansicht: nebeneinander, transparent überlagert, mit verschiebbarer Trennlinie oder als absolute RGB-Differenz. Oben links oder mittig ohne Skalierung ausrichten, oder B proportional in A einpassen. Scrollen zoomt beide; der Regler steuert B-Deckkraft oder Trennlinie. Transparenz und Ränder werden auf Weiß verglichen; Schwarz bedeutet gleiche RGB-Werte. Animationen verwenden nur das erste Bild. Ein Hintergrundauftrag decodiert, richtet aus und berechnet Differenzen; nur die neueste Auswahl wird angewendet. Deckkraft/Trennlinie verwenden vorhandene Pixmaps. Grenzen: 64 MiB je Datei, 8.192 Pixel je Seite und 16.777.216 Pixel je Bild/ausgerichteter Fläche. Fehler erhalten das vorige Paar; Schließen leert Bilder und ignoriert späte Ergebnisse.

Einstellungen → Regeln ergänzt Priorität (-1000…1000), Abklingzeit (0…86400 ganze Sekunden), Bedingungsvorschau und Sitzungsverlauf. Ausgelöste Regeln laufen von niedriger zu höherer Priorität, bei Gleichstand in Tabellenreihenfolge; höhere Werte zuletzt. Eine monotone Uhr steuert die Abklingzeit: blockierte Übergänge werden verbraucht, und Ablauf führt bei weiterhin wahren Bedingungen nichts aus. Vorschau prüft ungespeicherte Zeilen ohne Aktionen oder Zustandsverbrauch. Die letzten 200 Belege enthalten Bedingungen, erfassten Kontext und Versand-/Ausführungs-/Fehler-/Abklingergebnisse nur im Speicher. Ungültige benannte Zeilen verhindern das Speichern. Bis zu 200 Regeln besitzen unabhängige Identitäten, auch bei gleichen Namen; nicht angezeigte Bedingungen bleiben beim Bearbeiten erhalten. Rückgemeldete Aktionsfehler werden protokolliert und stoppen spätere Regeln nicht.

Regeln können Szenen laden, abspielen oder stoppen und benannte Ebenen zeigen, ausblenden, verschieben oder ihre Deckkraft ändern. Zeile auswählen und Szene / Ebene wählen: JSON, .fescene oder .puppet durchsuchen, Hauptbildschirm/alle/Bildschirmindex und Editorebene wählen. Ein leerer Wiedergabepfad nutzt die aktuelle Editorszene. Dateien werden im Hintergrund gelesen; ein fehlgeschlagener Kandidat erhält die laufende Szene. Die letzte Szenenanforderung ersetzt ausstehende Vorgänger; folgende Ebenenaktionen warten darauf und scheitern mit ihr. Gesperrte oder fehlende Ebenen werden abgelehnt. Änderungen sind rückgängig machbar und aktualisieren die Wiedergabe; Deckkraft 0–100, Position ±100000. Stoppen bricht Anforderungen ab und schließt die Wiedergabe; Editorressourcen bleiben bis zum Ersetzen oder Programmende. Der Verlauf erfasst den tatsächlichen asynchronen Abschluss. In der Befehlspalette: Pfad oder {"path":"scene.fescene","screen":"primary"}, Ebenenschlüssel für zeigen/ausblenden, {"layer":"title","opacity":50} oder {"layer":"title","x":20,"y":30}.

Szene → Skript → Szenenvorlagen (auch in der Befehlspalette) bietet Arbeitsdesktop, Unterricht und Fokus mit übersetztem, bearbeitbarem Text. Layout ansehen, Hauptbildschirm oder Bildschirmnummer wählen und Anwenden und abspielen; Proportionen passen in dessen nutzbare logische Größe. Vorlagen enthalten alle Ressourcen. Fehlende Ressourcen werden mit Ebene/Feld/Pfad aufgeführt und verhindern Anwendung. Der Szenentransaktionsablauf ersetzt Editor und Wiedergabe; fehlgeschlagene Vorbereitung erhält die bisherige Szene. Text ändern, Medien ergänzen und als JSON oder portable .fescene exportieren. Schließen der Bibliothek bricht nur ihre ausstehende Anwendung ab. Fokus enthält bearbeitbare Erinnerungstexte; Zeitpläne und Timer bleiben eigene Werkzeuge.

Szene → Visueller Editor ergänzt Video, Web, Puppet und Audio zu Bild/GIF/Text. Live-Vorschau ausdrücklich aktivieren: bis zu acht Quellen, stumm bis zum Anhören, verborgen pausiert, bei Deaktivierung/Schließen freigegeben. Bilder sind auf 1280 Pixel je Seite begrenzt; Fehler werden angezeigt. Benannte Szenen komponieren Videobilder, die eigene Web-Oberfläche und Imervue-Offscreen-Puppet-Bilder mit allen visuellen Ebenen in z-Reihenfolge; Audio ist unsichtbar. Doppelklick bei Wiedergabe oder Interagieren im Editor öffnet dasselbe native Web/Puppet-Eingabefenster. Puppet braucht natives OpenGL und die optionale Laufzeit; Vorschau führt keine Haustierskripte aus, Szenentiere verwenden temporäre Werte. Einzelne Web/Video/Puppet-Fenster bleiben verfügbar. JSON/.fescene erhält alle unterstützten Typen und Medienreferenzen.

Werkzeuge → Bereichsaufzeichnung bietet GIF oder stummes AVI (Motion JPEG), 1–20 fps, Pause/Fortsetzen und Abbrechen. Status zeigt effektive Sekunden, angenommene Bilder und Auslassungen. Pausen zählen weder für Wiedergabe noch Dauergrenze; Stoppen während Pause ist möglich. AVI: bis zu einer Stunde, 72.000 Bilder und 2 GiB; GIF: 120 Sekunden/600 Bilder. Beide nutzen drei Bilder/64 MiB Hintergrundwarteschlange und atomare Ausgabe. AVI hält ein JPEG und schreibt den Index auf Datenträger; ausgelassene Intervalle wiederholen das letzte Bild. Encoder-, Größen- oder Schreibfehler und Abbruch bewahren ein bestehendes Ziel. Kein Audio.

Szene → Visueller Editor → Animationszeitleiste bearbeitet x/y/Deckkraft einer entsperrten Ebene mit Einblend-/Einschubvorlagen. Eindeutige aufsteigende Zeiten: 0–3600 Sekunden, bis 128 Bilder je Ebene; Deckkraft 0–100, Position ±100000, linear oder smooth. Leere Zellen lassen Kanäle unverändert. Anwenden ist rückgängig machbar; JSON/.fescene erhält Spuren. Vorschau scrubben, abspielen, pausieren, fortsetzen und wiederholen ohne temporäre Positionen zu speichern; vor Bearbeitung zurücksetzen. Wiedergabe hat eigene Steuerung und eine gemeinsame monotone Uhr für alle Bildschirme. Verbergen hält die Zeit an; ausdrückliche Pause bleibt bestehen. Medien pausieren mit Animation; Wiederholen steuert Animationsspuren. Szenenaktionen überblenden einen alten Snapshot 0,5 Sekunden, schließen alte Renderer sofort und beginnen die neue Uhr bei null. Alte Szenen bleiben kompatibel.

Szene → Unabhängige Szenenausgabe zeigt die Editorszene in 640×480, 1280×720 oder 1920×1080 Pixeln, unabhängig von Desktopposition, Überdeckung und DPI. Vorschau öffnet keine Kamera; ausdrücklich senden benötigt pyvirtualcam und kompatiblen Treiber. Öffnen/Senden/Schließen erfolgt auf einem Worker mit einem neuesten RGB-Wartebild; langsame Geräte überspringen Zwischenbilder. Ausgabe ohne Audio. IMAGE/GIF/TEXT und natives VIDEO/WEB/PUPPET folgen Ebenenreihenfolge; SOUND unsichtbar. Puppet benötigt optionale Laufzeit und natives OpenGL; Fehler werden angezeigt. Bis 256 Ebenen, acht native Quellen und insgesamt 16 Megapixel Raster. Stoppen, Escape, Dialog-/App-Schließen oder Szenenbearbeitung schließen Renderer und fordern Kameraschluss an; nach Änderungen neu starten. Leser schließen vor Freigabe von Szenenpaketen.

Tier → Sprite-Tierpaket erstellt Zuordnungen für walk/idle/sleep/climb/fall/drag, zeigt Größe und Gehgeschwindigkeit und exportiert einen portablen Ordner mit pet.json. Mindestens eine Aktion; fehlende Aktionen werden gemeldet und nutzen den vorhandenen Loader-Fallback. PNG/JPEG/GIF/WebP: je 64 MiB und 16 Megapixel, insgesamt 256 MiB. Import/Export im Hintergrund, abbrechbar, keine vorhandenen Ordner überschrieben. Ordner können verschoben, auf der Tierseite gewählt und als Workshop-Tierpaket geteilt werden. Import übernimmt nur gewählte Sprites, Namen, Größe und Geschwindigkeit; keine Klänge, Skripte oder Sprache. Imervue .puppet hat ein eigenes Autorenformat. Schließen/Escape gibt Vorschaufilme frei und bricht Dateivorgänge ab.

Werkzeuge → Letzte Aufnahme bearbeiten zeigt eine unabhängige Kopie mit Zuschnitt, Pfeilen, Nummern, Textfeldern und deckend schwarzer Schwärzung. Auf skalierter Vorschau ziehen; Koordinaten und Ausgabe bleiben Bildpixel. Rückgängig, Zurücksetzen und schreibgeschütztes Original sind verfügbar. Kopieren/PNG-Speichern/Anheften nutzt stets denselben abgeflachten Ausschnitt, auch bei Originalansicht. Schwärzungen werden zuletzt gezeichnet; PNG enthält keine Originale/versteckten Ebenen. Rohaufnahme bleibt separat im Speicher. Atomare PNG-Speicherung. Grenzen: 16 Megapixel, 1000 Markierungen, 2000 Zeichen/Text, 20 Undo-Zustände. Schließen/Ersetzen gibt das Dokument frei.

Präsentation → Tafel hat unabhängige editierbare Seiten, Zeichen/Auswahlmodus, Shift-Mehrfachauswahl, Strichbewegung/Löschen und insgesamt 20 Undo-Zustände. Mittlere Taste verschiebt, Rad zoomt; Auswahl/Bewegung in Canvas-Koordinaten, eigene Ansicht je Seite. Speichern/Öffnen nutzt versioniertes .fewhiteboard JSON mit Vektorstrichen/Ansichten zum Weiterbearbeiten. Ein Hintergrundworker validiert und liest/schreibt; Fehler erhalten Tafel/Datei. Seiten-PNG zeigt nur die gewählte Seite ohne Bedienelemente/Auswahl/Ansichtstransform, mit vollständigen Stifträndern. Grenzen: 50 Seiten, 2000 Striche/Seite, 100000 Punkte, acht MiB JSON; PNG 8192 Pixel/Seite, 16 Megapixel. Schließen/Escape bricht Schreiben ab und ignoriert späte Lesergebnisse.

Einstellungen → Bild-Zwischenablageverlauf ist separat optional und standardmäßig aus; Öffnen startet weder Überwachung noch Lesen. Anwenden aktiviert Aufnahme und optionale lokale SQLite-Sitzungsspeicherung. 10–200 Bilder, 8–128 MiB PNG-Nutzdaten; Favoriten schützen vor Verdrängung, zählen aber zu beiden Grenzen. Volle Favoriten melden Ablehnung. Je Bild 16 MP/acht MiB kodiert. Ein Worker komprimiert, erstellt Miniaturen und schreibt; nur neuestes wartendes Bild und zusammengefasste Ergebnisse, langsame Kompression überspringt Zwischenbilder. Favoriten/Löschen/Leeren, Original kopieren, Desktop anheften und Speicher-Referenztafel. Leeren entfernt auch Favoriten und Datenbankseiten; Speichern abschalten löscht Datenbank, aktuelle Speicherhistorie bleibt. clipboard-images.sqlite3 neben Einstellungen, Datenbank bis 132 MiB plus mögliche temporäre Journale. Kein Upload/automatisches OCR. Beenden trennt Überwachung und fordert asynchrone Bereinigung an.

Werkzeuge → Live-OCR zeigt Text neben einem festen Bereich. Anfangs manuell/lokal; explizite Automatik 5–60 Sekunden, Kopie sichtbarer/älterer Texte, zwanzig eindeutige erfolgreiche Speicherergebnisse. Gleich/leer dupliziert nicht. Vier Fenster, je ein Job, 16 MP/acht MiB kodierte Aufnahme, 20000 Zeichen; langsame Jobs überspringen Anfragen. Lokal ruft Cloud auch mit globaler Zustimmung nie auf. Expliziter Cloud-Fallback nutzt ScreenTextService Screenshot-Zustimmung/Zugangsdaten und separate Erlaubnisprüfung; keine automatischen Zustimmungsdialoge/Übersetzung/Textuploads. Jede Fallback-Aktualisierung kann Bereich senden. Überlappung blockiert Rückkopplung. Windows/X11: screen-lokales Qt; Mac: asynchrone native Einzelaufnahme, Stream danach gestoppt. Verbergen stoppt Capture/Timer; Schließen/Escape gibt Quellen/Verlauf frei und ignoriert späte Ergebnisse ohne Warten. Bereits gesendete API-Anfragen können enden. Batch-Cleanup erfasst Fenster; kein automatischer Capture-Neustart.
