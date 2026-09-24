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
> **F12 beendet die Anwendung sofort** von überall (nur Windows — siehe
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
- **Bereich aufnehmen** — nehmen Sie einen Bereich als animiertes GIF auf, mit
  der in die Ecke eingeblendeten Kamera für den Reaktionsvideo-Look. Begrenzt
  sowohl durch Länge als auch durch die Bildanzahl, weil jedes Bild im Speicher
  gehalten wird.
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
- **Text lesen** — ziehen Sie einen Bereich auf, um den Text darin zu kopieren,
  ihn zu übersetzen oder eine Frage dazu zu stellen. Dieses hier sendet die
  Auswahl von der Maschine weg; siehe
  [Was die Maschine verlässt](#was-die-maschine-verlässt).
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
| `F12` | Sofort beenden (Windows) |

Die Medientransportfunktion sendet die System-Medientasten, sodass sie jeden
Player erreicht, der auf sie hört. Das Verschieben eines Fensters behält seine
Proportionen bei, statt es hinüberzuschnappen, was Windows' eigenes
`Win+Shift+Arrow` tut.

Dieselben Aktionen — und nichts darüber hinaus — treiben die Fernsteuerungen an:

- **Ihr Telefon** (Einstellungen → Fernsteuerung) — FrontEngine liefert eine
  kleine Seite in Ihrem lokalen Netzwerk aus; öffnen Sie den Link auf einem
  Telefon, und die Schaltflächen treiben diese Aktionen an.
- **Ein MIDI-Controller** — drücken Sie *Lernen*, bewegen Sie einen Regler oder
  ein Pad und belegen Sie ihn. Er verwendet Windows' eingebautes winmm, sodass
  kein zusätzliches Paket benötigt wird. Ein Regler löst aus, sobald er das obere
  Ende erreicht, statt wiederholt auf dem Weg dorthin, und das Loslassen eines
  Pads zählt nicht als zweiter Druck.

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
| **Text lesen** (Werkzeuge) | Der ausgewählte Bereich wird an die API von Anthropic gesendet | Fragt einmal vor dem ersten Senden und merkt sich die Antwort; die Zustimmung kann aus dem Ergebnisfenster widerrufen werden. Verwendet Ihren eigenen `ANTHROPIC_API_KEY`, aus der Umgebung gelesen und nie in eine Einstellungsdatei geschrieben. Ohne beides wird nichts gesendet. |
| **Haustier-Chat** | Ihre Nachricht geht an die API von Anthropic | Gleicher Schlüssel, gleiche Regel; standardmäßig aus. |
| **Wetter** (Textquelle) | Koordinaten gehen an Open-Meteo | Kein Schlüssel, kein Konto, keine identifizierenden Daten; nur das, was Sie als Ort eingegeben haben. |
| **Telefon-Fernsteuerung** | Liefert eine Seite in Ihrem lokalen Netzwerk aus | Standardmäßig aus. Der Link trägt ein Token, das bei jedem Start neu erzeugt wird, sodass ein alter Link aufhört zu funktionieren, und die Seite kann nur nach der festen Aktionsliste fragen. Es ist einfaches HTTP: jemand anderes im selben Netzwerk könnte das Token lesen und dieselben Schaltflächen drücken — ein Ärgernis statt eines Sicherheitsbruchs angesichts dessen, was diese Schaltflächen tun, aber lassen Sie es in Netzwerken aus, denen Sie nicht vertrauen. |

Die Audiofunktionen lesen nur einen Ausgabe-**Pegel** — eine einzelne Zahl —
außer dem Spektrum, das echte Samples benötigt, um Frequenzen zu berechnen, und
daher den Systemausgabestrom erfasst. Diese Samples werden im Speicher
analysiert, nie auf die Festplatte geschrieben oder irgendwohin gesendet, und
die Erfassung stoppt in dem Moment, in dem Sie das Spektrum stoppen.

**Plugins** sind Python und laufen mit denselben Rechten wie FrontEngine — sie
können nicht in einer Sandbox isoliert werden. Das Laden ist standardmäßig aus
(Einstellungen → Plugins laden), jedes Laden wird protokolliert, und ein
defektes Plugin wird übersprungen, statt die App zu stoppen. Installieren Sie
nur Plugins, denen Sie vertrauen.

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
| Overlays, Haustier, Hintergrundbild, Präsentieren, Bildschirmschonung, Erfassung, Aufnahme | ✅ | ✅ | ✅ |
| Audioreaktion, Spektrum, Lippensynchronisation (WASAPI) | ✅ | — | — |
| Aktuelle Wiedergabe (Mediensteuerung) | ✅ | — | — |
| Ein anderes Fenster anheften / ausblenden, Fensterlayouts, Live-Replik | ✅ | — | — |
| Overlays aus der Bildschirmerfassung ausblenden | ✅ | — | — |
| MIDI-Steuerung (winmm) | ✅ | — | — |
| Medientransporttasten | ✅ | — | — |
| Overlays an einen virtuellen Desktop anheften | ✅ | — | — |
| Ein Fenster auf den nächsten Monitor verschieben | ✅ | — | — |
| `F12`-Notausstieg | ✅ | — | — |
| Hintergrund um das *aktive* Fenster abdunkeln | ✅ | ganzer Bildschirm | ganzer Bildschirm |
| Haustier steht auf anderen Fenstern | ✅ | — | mit `wmctrl` |

Wo eine Funktion nicht funktionieren kann, sagt es die Schaltfläche, statt still
zu versagen.

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
