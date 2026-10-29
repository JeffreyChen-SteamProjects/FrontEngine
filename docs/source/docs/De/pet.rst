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

Interaktionen und gespeicherter Zustand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tierprofile der Version 2 behalten UUID und Werte aus Version 1 und ergänzen Energie, den gewählten Modus, Vorlieben und geprüfte Verweise auf das Aussehen. 

Das Sprite-Menü bietet Hallo sagen, Sanft streicheln und Fell pflegen sowie die dauerhaften Modi Zusammen spielen, Zusammen arbeiten und Ausruhen. Interaktion beenden bricht die aktuelle Aktion ab. Zeitlich begrenzte Aktionen bringen erst nach Abschluss Vorteile; Abbrechen gibt keine Belohnung. Satte Tiere lehnen Futter ab, wiederholte Aktionen benötigen eine Pause. Ziehen oder Ändern des Aussehens bringt keine Belohnung. Eine Spielzeugoberfläche ist noch nicht enthalten.

Pflege läuft nach aktiver Zeit und unabhängig von Sprechblasen. Versteckte Tiere und Offline-Zeit erzeugen keine nachträglich berechnete Pflege oder Belohnungen. Sprite-Tiere nutzen die gemeinsame Interaktionssitzung für Menüaktionen und Modi. Puppet-Tiere teilen diese Sitzung und die Fütterungsregeln; ihre native Darstellung hängt von den Fähigkeiten der Laufzeit und des Modells ab.

Wähle eine Identität auf der Haustierseite und öffne „Haustier anpassen“ oder nutze das Menü des Haustiers. Jede Identität speichert Größe (16–512), Tempo (1–20), Boden-/Wander-/Verfolgungsverhalten, Wandklettern, Sitzen auf Fenstern, Sprechblasen, Lautstärke (0–100), Ruhe beim Tippen, automatisches Ausruhen sowie Wurf- und Sozialverhalten separat. „Seitenvorgaben verwenden“ übernimmt die Darstellungs- und Verhaltenseinstellungen der Seite; Klonen und Import behalten individuelle Einstellungen. „Anwenden“ speichert atomar vor der Aktualisierung des aktiven Haustiers. „Abbrechen“ ändert nichts; wiederhergestellte Vorgaben gelten erst nach „Anwenden“. Bei Speicherfehlern oder Bearbeitungskonflikten bleibt der Entwurf erhalten. Puppet deaktiviert nicht unterstützte Steuerelemente und übernimmt bei Darstellung und Verhalten nur Größe, Sprechblasen und Ruhe beim Tippen. Native Garderobensteuerung und geschichtete Grafiken sind noch nicht fertig.

Tieridentitäten → Garderobe öffnet eine eigene animierte Vorschau installierter Figuren. Asset-Ordner installieren prüft layered-pet.json und kopiert Ressourcen nach pet-assets neben den lokalen Einstellungen. Kopf, Hals, Körper und Rücken, Aktionen und Blickrichtung sind wählbar; jede Identität speichert bis zu 20 Outfits. Ein angelegtes Teil ersetzt, was dieselben Plätze belegt, und nennt es; Abbrechen stellt es wieder her. Nur Teile für den aktuellen Körperbau werden angeboten, Teile ohne alle Animationen erscheinen deaktiviert. Anprobieren zeigt eine kurze Präsentation, und „Zum Vergleich anheften“ zeigt den aktuellen Look neben dem Entwurf. Ein Tier, das gezogen wird oder gerade interagiert, wechselt die Kleidung erst danach. Tiere mit ganzen Sprite-Bildern werden gebeten, zuerst eine mehrschichtige Figur zu wählen. Anwenden speichert und aktualisiert das aktive Sprite; Abbrechen verwirft Änderungen seit dem letzten Anwenden. Fehlende Ressourcen bleiben referenziert und können nach Reparatur neu eingelesen werden. Puppet unterstützt diese Sprite-Kleidung nicht. Integrierte Figur hinzufügen zeichnet eine von sechs INKSIDE-Figuren (MOCHI, MOSS, PIP, BOLT, INK oder GILL) samt dreißig passenden Kleidungsstücken aus vierzehn Outfits und installiert sie im Hintergrund mit derselben Prüfung; Schließen der Garderobe bricht ab. Jede Figur bietet Augen-, Mund- und drei Körperteil-Varianten sowie umfärbbare Bereiche, und jedes Teil folgt allen Animationen. Teil- und Kleidungsnamen folgen der Oberflächensprache.

Eine unbekleidete integrierte Figur mit Standardteilen und -farben läuft und klettert mit handgezeichneten Ganzkörper-Schrittbildern; mit Kleidung oder geänderten Teilen nutzt sie die geschichtete Animation, damit jedes Stück passt.

Desktop-Tiere zeichnen unabhängig von der Overlay-Darstellung immer über das normale Qt-Zeichnen: Ein Tier bewegt sein Fenster bei jedem Takt, und auf dem GPU-Pfad wechselten seine Animationsbilder während der Bewegung nicht mehr.

Tiere nehmen passende Haltungen ein: Im Arbeitsmodus sitzen sie, beim Wechsel in Ruhe läuft ein kurzer Einschlafclip, beim Verlassen ein Aufwachclip. Spielen, Ball, Apportieren und Fangen kosten etwas Energie; unter 20 Energie setzt sich ein untätiges Tier auch ohne automatische Ruhe, gehorcht aber weiter jedem Befehl. Landung nach Ablegen oder Werfen, das Fangen eines geworfenen Balls und Begegnungen mit anderen Tieren zeigen kurze Lande-, Fang- und Winkreaktionen, ohne Bewegung, Spielzeug oder Befehle zu unterbrechen. Sprite-Pakete ohne diese Clips nutzen ihre Ruhe- oder Schlafbilder. Nach der Fellpflege streckt sich das Tier, und Tiere, die sich ständig begegnen, winken einander höchstens einmal pro Minute.

Beziehungen wachsen mit der Zuneigung in vier Stufen: Gerade kennengelernt, Vertraut (20), Eng verbunden (100) und Im Einklang (250). Die Stufe erscheint im Status. Jede Stufe hat eine eigene Begrüßung, eng verbundene Tiere winken, Tiere im Einklang springen vor Freude, und eine neue Stufe wird einmal gefeiert; nichts wird gesperrt oder geht verloren. Ein gespeichertes Tier begrüßt dich beim erneuten Aufrufen, und Schließen über sein eigenes Menü winkt zum Abschied, bevor das Fenster schließt. Puppet-Tiere unterscheiden Klick und Ziehen jetzt wie Sprite-Tiere: Ein Klick grüßt beim Loslassen, erst Bewegung über die Systemziehdistanz verschiebt das Fenster, ohne Belohnung.

Tier anpassen stellt außerdem Plaudern (Aus, Selten, Normal, Oft) für Sätze, die das Tier von selbst beginnt, und die Animationsstärke (Ruhig, Normal, Lebhaft) für Audiopuls und kurze Lande- und Fangreaktionen ein, getrennt von Sprechblasen und Lautstärke. Antworten auf deine Aktionen erscheinen auch bei ausgeschaltetem Plaudern. Puppet-Tiere wenden Plaudern auf geplante Skriptsätze an. Früher gespeicherte Darstellungen bleiben gültig und nutzen für beides Normal.

Die Interaktionsliste der Tierverwaltung bietet außerdem die Menübefehle des gewählten aktiven Tiers an: Foto, Status, Erinnerung, Chat bei angebundenem Chatdienst, Klonen und Schließen sowie jede Bewegung und jeden Ausdruck eines Puppet-Modells. Alles aus dem Rechtsklickmenü ist damit auch per Tastatur erreichbar.

Integriertes Puppet-Modell verwenden auf der Tierseite zeichnet die gewählte INKSIDE-Figur im Hintergrund als Imervue-.puppet-Modell: geriggter Kopf, Arme, Schwanz und Körper, zehn Bewegungen, drei Ausdrücke und ein Tierskript, das Begleitaktionen darauf abbildet. Es wird unter pet-assets/puppets gespeichert und mit seinem Skript als Quelle gewählt, sodass Start es als Puppet-Tier erzeugt.

Bei mehreren Monitoren mit unterschiedlicher Skalierung behält ein Tier, das auf einen anderen Monitor gezogen oder dorthin zurückgeholt wird, seine Größe, bleibt in dessen Arbeitsbereich und läuft dort weiter. Fensterkanten auf skalierten Monitoren werden in denselben Koordinaten wie das Tier gemessen, sodass es genau auf Fenstern sitzt.

Die Garderobe zeigt Farbbereiche an, die Figur oder Kleidung deklarieren. Wähle einen Bereich und eine Farbe oder stelle die Originalfarbe wieder her. Nur markierte Maskenebenen werden eingefärbt; Konturen und andere Details bleiben erhalten. Farben werden vor dem Anwenden angezeigt und je Identität und Outfit gespeichert, auch beim Export/Import. Ohne deklarierte Bereiche bleiben Farbregler deaktiviert.

Scheitert das Speichern beim Schließen, bleiben Tier, aktueller Zustand und Wiederholungs-Timer erhalten. Alle schließen behält Tiere, die nicht geschlossen werden konnten; vor dem Beenden müssen ihre Daten gespeichert sein. Zuneigung steigt nicht über die unterstützte Speichergrenze, damit weitere Belohnungen das Profil nicht ungültig machen.

Begrüßungen und Fangspiel erfordern zwei sichtbare Tiere im Spielmodus, ohne laufende Interaktion, mit erlaubtem Sozialverhalten und ohne Tragen oder Tipppause. Nicht verfügbare Tiere werden aus Zielen und Rollen entfernt. Unter zwei geeigneten Tieren pausiert das Spiel und wird später fortgesetzt. Deaktivierte Sprechblasen unterdrücken nur den Text, nicht die sozialen Belohnungen.

Beim Start des Fokus-Timers wechseln sichtbare Tiere ohne laufende Interaktion in Arbeit, in Pausen in Ruhe. Stop stellt frühere Modi wieder her, sofern sie nicht manuell geändert wurden. Jede abgeschlossene Runde gibt geeigneten sichtbaren Begleitern einmal 3 Zuneigung und 5 Stimmung; vorzeitiger Stop oder Verbergen gibt keine Abschlussbelohnung. Arbeit/Ruhe unterdrückt spontane Gespräche. Der Timer nutzt monotone verstrichene Zeit statt Änderungen der Systemuhr.

Beim Fokusstart werden Tiere bei ausreichend Platz unten rechts im Arbeitsbereich ihres Bildschirms angeordnet. Beim Stop wird die alte Position nur ohne manuelle Bewegung oder Modusänderung wiederhergestellt.

Mehrschichtige Charaktere können Gesichts- und Körpervarianten anbieten. Die Garderobe zeigt eine Vorschau pro Tier; Anwenden speichert sie, Outfits behalten Charakter und Teile. Jede Variante muss alle Animationsbilder abdecken. Die fertigen Grafiken der sechs Charaktere fehlen noch.

Das Sprite-Tiermenü bietet Tierfoto: aktuelle Ansicht einfrieren oder eine vorhandene Ebenenpose wählen und als transparentes PNG speichern. Desktop und Sprechblasen werden nicht aufgenommen. Puppet-Fotos nutzen einen kompatiblen initialisierten Imervue-Renderer für transparente Standbilder ohne Desktop-Aufnahme. Die native GL-Abnahme steht noch aus.

Bei Sprite-Tieren Sanft streicheln wählen und den Zeiger hin und her bewegen. Drei deutliche Streichelbewegungen starten eine Reaktion; Zittern zählt nicht. Ziehen und Sozialspiel pausieren. Wegbewegen, Verbergen, Moduswechsel oder Interaktion beenden bricht unfertiges Streicheln ab. Belohnungen erfordern Abschluss und Abklingzeit.

Sprite-Tiere können einen Ball werfen und wegräumen. Ziehen und loslassen wirft erneut, Rechtsklick entfernt ihn. Das Tier holt den begrenzten Ball zum Start zurück; Abschluss gibt 1 Zuneigung mit 30 Sekunden aktiver Abklingzeit. Arbeit/Ruhe, andere Interaktionen, Verbergen, Tippruhe oder Zeitlimit brechen ohne Belohnung ab. Puppet-Tiere holen den Ball ebenfalls (siehe unten).

Bodentiere verlassen Fensterkanten zum Ballholen. Fensterplätze pausieren während des Spiels und werden danach wieder genutzt; die Rückkehr erfolgt am Boden nahe der ursprünglichen horizontalen Position.

Der Lichtpunkt ist ein kleiner ziehbarer Zielpunkt in begrenzter Nähe des Tiers. Bodentiere folgen am Boden. Nach Loslassen und Erreichen beginnt eine kurze Spielreaktion, belohnt erst nach Abschluss mit der bestehenden Abklingzeit. Rechtsklick oder Spielzeug weglegen beendet sie. Pro Tier ist nur ein Ball oder Lichtpunkt aktiv.

Klonen nutzt Bild/Modell, Aussehen, Einstellungen und Asset-Bibliothek des ursprünglichen Tiers, auch nach anderer Auswahl auf der Einstellungsseite. Der Klon erhält eine neue Identität; spätere Kleidungs- oder Teileänderungen betreffen das Original nicht. Puppet-Klone behalten Skript, Parameterwerte und aktive Ausdrücke.

Ein geeigneter Fokusabschluss fordert kurz celebrate an, danach folgt Ruhe. Geänderte Garderoben fordern outfit_show an. Die Reaktionen dauern zwei aktive Sekunden, geben keine Zusatzbelohnung und werden nicht gespeichert; manuelle Aktionen oder Modi unterbrechen sie. Fehlende Animationen nutzen idle. Fertige Grafiken und Puppet-Zuordnung stehen aus.

Aktive Identität wählen und Tier zurückholen bringt sie in den Arbeitsbereich des Zielbildschirms. Verborgene Tiere werden sichtbar, offene Interaktionen und Spielzeuge enden, Sprite-Grenzen folgen dem Bildschirm. Aussehen und Pflegewerte bleiben erhalten. Inaktive Tiere zuerst starten, zu große zuerst verkleinern.

Puppet-Skripte können mit frontengine_actions Zustände auf vorhandene Bewegungen und Ausdrücke abbilden. Namen werden vor dem Start geprüft; fehlende Bindungen raten keine Animation. Abschluss gibt reaktionseigene Effekte frei und erhält manuelle Auswahl. Format: docs/formats/puppet-companion-actions.md. Native Sichtprüfung steht aus.

Nach der Wahl von Streicheln startet Puppet die Interaktion erst bei Hin-und-her-Bewegungen des Zeigers. Verlassen, Esc, Ausblenden, Moduswechsel oder Ruhe brechen sie ab. Ziehen ist dabei gesperrt. Die native Gestenprüfung steht aus.

Die Garderobe bietet sechs Stilfarben für den gewählten Farbbereich des Assets. Erst Vorschau, dann Anwenden; Abbrechen erhält das gespeicherte Aussehen. Freie Farbwahl und Zurücksetzen bleiben verfügbar.

Sprite- und Puppet-Menüs bieten vier fiktive Leckerbissen ohne Dateiablage. Abschluss, Sättigungsgrenze und Wartezeit bleiben gemeinsam. Füttern beendet Streicheln ohne Belohnung für unvollständige Gesten; Sprite räumt Spielzeug weg.

Jedes Tier kann einen beliebten und einen anderen unbeliebten Leckerbissen speichern. Nur die Stimmung nach dem Fressen ändert sich; Sättigung, Zuneigung und Wartezeit bleiben gleich. Änderungen gelten ab der nächsten Mahlzeit. Alte Profile sind neutral. food_like und food_dislike sind optionale Reaktionen; fertige Animationen stehen aus.

Sprite-Tiere können mit Komm her einer nahen verschiebbaren Markierung folgen. Bodenmodus bleibt am Boden; freie Modi bewegen sich zweidimensional. Ankunft startet einen kurzen Gruß mit normaler Wartezeit. Rechtsklick oder Interaktion beenden bricht ab, ebenso Arbeit/Ruhe, Ausblenden, Füttern oder ein neues Spielzeug.

Der Identitätsbereich bietet eine Interaktionsauswahl und Ausführen für das gewählte aktive Tier. Per Tastatur sind Gruß, kurzes Streicheln, Pflege, Leckerbissen, Spiel/Arbeit/Ruhe und Abbruch möglich. Streicheln nutzt die gemeinsame Zeitregel ohne Zeigergesten. Verborgene oder inaktive Tiere werden nicht gestartet.

Beim Sprachwechsel in der geöffneten Garderobe werden die Optionen für keine Auswahl, fehlende Ressourcen und Standardwerte aktualisiert. Entwürfe für Farben, Teile und Outfitnamen sowie die Vorschauposition bleiben erhalten. Ressourcennamen bleiben im Original.

Für ein Tastaturziel wählen Sie Komm her in der Tierverwaltung und geben horizontale/vertikale Verschiebungen in logischen Pixeln ein. Negative Werte bedeuten links/oben. Das Ziel bleibt im nahen Arbeitsbereich; der Bodenmodus ignoriert vertikale Werte. Ausführen startet, Interaktion beenden bricht ab. Beschäftigte oder nicht unterstützte Tiere behalten ihre aktuelle Interaktion.

Puppet unterstützt Komm her über Menü oder Tastaturversatz im Manager. Das gesamte Tierfenster und die Markierung bleiben im Arbeitsbereich. Erreicht die Fenstermitte das Ziel für eine halbe Sekunde, startet der gemeinsame Gruß. Ziehen, Pflege, Moduswechsel, Ausblenden, Größen- oder Arbeitsbereichsänderungen und manuelle Modellbefehle brechen ab. Eine deklarierte walk-Reaktion wird verwendet; sonst bleibt die native Darstellung erhalten. Der Bewegungstimer läuft nur während des Rufs. Native GL-/Fokusprüfung steht aus.

Puppet kann über sein Menü einem ziehbaren Lichtpunkt folgen. Im Manager bieten Sprite und Puppet Lichtspiel mit Tastaturversatz. Nach einer halben Sekunde losgelassen in der Nähe beginnt das gemeinsame dreisekündige Spiel; Zuneigung gibt es erst nach Abschluss mit normaler Wartezeit. Ruf und Licht teilen ein Ziel. Spielzeug weglegen, Interaktion beenden, Pflege, Ziehen, Moduswechsel oder Ausblenden brechen ab.

Puppet-Tiere bieten Ball werfen ebenfalls im Menü an, und die Manager für Sprite und Puppet können für die gewählte Identität werfen. Ballphysik, erneutes Werfen per Ziehen, Entfernen per Rechtsklick, 1 Zuneigung und 30 Sekunden Abklingzeit sind mit Sprite gemeinsam; das Puppet-Fenster jagt den Ball, hebt ihn auf und trägt ihn zur ursprünglichen Mitte zurück, stets im Arbeitsbereich. Jeder neue Wurf startet ein neues Zeitlimit. Ball, Licht und Komm her teilen ein Ziel; ein neues ersetzt das alte. Pflege, Ziehen, Moduswechsel oder Ausblenden brechen ohne Belohnung ab. Eigene Apportier-Animation steht aus.
