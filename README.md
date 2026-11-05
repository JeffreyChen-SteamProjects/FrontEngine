# FrontEngine

<p align="center">
  <strong>English</strong> ·
  <a href="README/README_zh-TW.md">繁體中文</a> ·
  <a href="README/README_zh-CN.md">简体中文</a> ·
  <a href="README/README_ja.md">日本語</a> ·
  <a href="README/README_ko.md">한국어</a> ·
  <a href="README/README_es.md">Español</a> ·
  <a href="README/README_fr.md">Français</a> ·
  <a href="README/README_de.md">Deutsch</a> ·
  <a href="README/README_pt-BR.md">Português (BR)</a> ·
  <a href="README/README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**Put anything on top of your screen — or underneath it.**

FrontEngine is a desktop overlay app. Video, images, GIFs, web pages, text,
particles, sound and an animated pet can be placed over every other window
(click-through, so what is underneath still works), or behind them as a live
wallpaper. Around that sits a set of tools for the screen itself: eye-comfort
filters, presentation annotation, measuring and capture, focus masks and
desktop widgets.

[Support this project on Steam](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [Documentation](https://frontengine.readthedocs.io/en/latest/)
 · [Watch a demo](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](image/FrontEngine.png)

---

## Install

Python 3.11+ is supported, except 3.14.0 through 3.14.4. For Python 3.14, use 3.14.5 or later. Windows 10/11 is the primary target; macOS and Linux run the
app, with the platform differences listed under [Platform support](#platform-support).

A native Qt crash was reproduced on Windows with Python 3.14.4; earlier 3.14 patches are excluded as a precaution. Recreate existing virtual environments with a compatible interpreter, and use that interpreter for source runs. EXEs that embed an excluded version need a rebuild with a compatible interpreter. Updating the FrontEngine package does not upgrade Python.

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

Pre-built Windows binaries are on the
[Releases page](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases),
and the Steam build ships the same application with Workshop support.

> **Getting out.** Overlays can cover the whole screen, including FrontEngine's
> own window, so there are two escape hatches that do not need the mouse:
> `Ctrl+Shift+F12` closes every overlay, and **F12 quits the application
> outright** from anywhere (Windows; macOS needs Accessibility permission — see *Help → How to force close*).

---

## What it puts on screen

The sidebar groups the pages by what they are for. This section follows it.

Every page has an icon in the sidebar, and the search box at its top (Ctrl+K) opens Commands. The menu bar's Help and Docs menus are named just that. On a wide window the setting pages keep their cards in one centred column; the pet home and the scene editor use the full width.

### Home

**Pet home** — the first page. Your saved pets move into a small home, live there on their own and work for home coins.

- *Create a home* gives a bed, a dining table, a writing desk and 10 coins. Nothing is created or started until you press it, and every other tool works without a home. Before the home is created, every saved pet is listed under *Pets moving in with you*, all ticked; untick the ones that should stay where they are. The ticked pets move in as themselves - same identity, name, closeness, mood, fullness, energy, look and wardrobe - nothing is copied or reset, and a pet left out can move in later from the Residents tab without the starter kit being handed out again. The home's year has four seasons of seven game days - spring, summer, autumn, winter - shown in the status line and as petals, falling leaves or snow in the overview's sky (still with *Reduce motion*); in winter rain falls as snow. Each season offers one goal of its own (grow flowers, play, harvest herbs, relax) that pays once; a season missed simply comes round again next year. With no saved pets, *Create a home* also brings a first pet and selects it.
- *Move in* a saved pet or make a *New pet*. A pet lives either in the home or on the desktop, never both at once; its energy, fullness, mood and affection carry over and go back to its profile when it moves out.
- *Arrange* puts furniture from storage on the floor. A red preview says why a spot does not work (outside the home, something already there, blocks the entrance); Esc stops arranging. *Put away* returns a piece to storage, and work at it pauses with its progress kept. While arranging, drag a piece to move it, or select it and press ← / → for one cell at a time; *Undo* and *Redo* (Ctrl+Z / Ctrl+Y) cover every layout change. *Copy layout* puts a layout code on the clipboard (only furniture and positions - no pets, coins or anything personal) and *Paste layout* reads one back; four ready-made layouts (*Starter home*, *Cozy corner*, *Workshop*, *Garden studio*) show what they still need and its price before *Apply layout* buys it and sets everything out, and the previous layout stays one *Undo* away. *Paint areas on the floor* labels stretches of floor as *Living*, *Work*, *Leisure* or *Dining* (or clears a label); pets prefer furniture in an area meant for what they are doing and are never forbidden anything else. With a second monitor, *Add a zone on that screen* gives the home a zone there with its own desktop strip and *Move this zone there* moves one; a pet changes zone only through *Move to that zone*. When a monitor is unplugged, the pets of its zone wait and its furniture stays where it was - nothing is copied - and they carry on when the screen is back. The *Cat tree* and *Climbing wall* are raised: a playful pet jumps up by itself, anyone else needs *Pet stairs* beside them, and a red preview reads *Nobody could get up there* when neither is true - work stations always stay on the ground. *Entrance leads to* joins two zones' entrances into a crossing point: pets sometimes wander over in their free time and walk back to their own bed at bedtime, never into a screen that is not connected. *Share blueprint…* saves the whole home's rooms and furniture as a JSON file - no pets, names, coins, goals, screen names or anything personal - and *Visit a blueprint…* opens such a file read-only: you look around its rooms, nothing runs, is bought or is saved, and nothing goes online. A file that is not a blueprint is refused; pieces this FrontEngine does not have are listed instead of shown.
- *Work* needs no setting up: during their working hours pets take up whatever their workstations allow, their own trade first, using only materials already in the backpack, and the tab lists what each is doing with a picture of what it makes; any job can be called off. Each finished unit pays exactly once, and a cancelled one pays nothing. The starter furniture is set out by itself, *Place* puts a stored piece in the first free spot (or *Arrange* and click the floor), furniture bought in the *Shop* goes straight into the home, and finished *Getting started* rewards and the commissions you have the goods for settle themselves. The shop, backpack and storage show every piece and item as a picture. Tile names and prices stay on separate lines, tile sizes follow the font, and long names remain available in tooltips. The *Settings* tab keeps only showing the home on the desktop and reducing motion. Workstations can be upgraded twice from their right-click menu or the Furniture tab (*Upgrade*, priced from the piece and its level, free while arranging freely); every station of that kind shares the level, so putting one away or rearranging never loses it, and each level works a quarter faster. A pet with free time may walk over and lend a hand to one at work - up to two helpers, each adding a quarter to the speed - and learns a little of that trade. Automatic jobs no longer make goods once storage holds twenty of them. Furniture shows what is happening at it: a dot while it is in use, the trade's tool (✎ ❀ ⚒) while a pet works there, and a ✓ for a few seconds after a job is finished. With *Pets work alongside my focus sessions* on, starting the pet page's focus timer queues a work request for every free pet - nothing it is doing is cut short, the work earns the usual rewards, and nothing reads what you type or minds a pause - and a break or stopping the timer takes back only the requests the home itself queued. Each trade has an advanced job for a pet at skill level 4 in a home at level 4: *Write a novel* (120 coins), *Arrange a bouquet* (three flowers into a bouquet worth 30) and *Build a music box* (three wood and a toy into a music box worth 80).
- *Shop* sells extra furniture; selling returns at most half the price, and the basic bed, table and desk are never sold. The home has 45 pieces of furniture, each with a use or a look of its own (beds from a pet cushion to a bunk bed, tables, two workstations per trade, a sofa, a bean bag, a ball pit, a piano, a rug, an aquarium and more); some open at a higher home level, shown in the shop, and so do short stories, flowers and stools. The *Collection* tab is the furniture guide (every piece and how to get it), what the pets made and the photo album. The *Getting started* goal *Choose a routine* became *Place a decoration*, since routines are automatic; an old save keeps its state. Furniture packs add pieces to the shop and the collection: each is a folder in `pet-home-packs` (*Open the packs folder* in the Settings tab) with a `pack.json` - format `frontengine.home-pack` version 1, a stable id equal to the folder name, a name, the source and the licence, and up to 64 pieces with id, name, category, width, solid, interaction points, what they are for, the poses they want, price and comfort - plus a `furniture/warm_home/<art>.png` picture for each piece (other themes optional) and a `thumbnail.png`. A pack is refused whole, with the reason shown in the Settings tab, for unknown fields, a path or link leading outside it, a picture that is not a PNG or is over 2 MB, a duplicate id or any file that could run; nothing in a pack is ever executed. Pieces become `<pack>__<id>`, and a removed pack's pieces wait in the save until it is back. The second collection adds a floor lamp, hanging plants, a wardrobe, a futon, a kotatsu, a TV set, a fireplace, a rocking horse, a telescope and a shower.
- A pack can also bring themes - a name, the built-in theme whose furniture pictures it uses, and floor, day-sky and night-sky colours - which join the Furniture tab's theme list; a pack with only themes is fine. A home using a theme whose pack has gone keeps it and looks like the warm home until the pack returns. Furniture packs, themes and blueprints are also on the Steam Workshop as their own kinds: subscribed packs and themes are in the home the next time FrontEngine starts, and a subscribed blueprint opens as a read-only visit. A blueprint names the content packs it needs, and both the Workshop list and the visit say which of them are not installed.
- The page is laid out like a game screen: the home on top with its day, time, weather, coins and *Start* / *Pause* on one line, and *Residents*, *Work*, *Furniture*, *Shop*, *Backpack*, *Goals*, *Inbox*, *Collection* and *Settings* as tabs underneath, so the home stays in view while you use them. Before there is a home, the top shows the bed, table and desk a new home starts with beside *Create a home*. Under the overview sit *Back to the desktop*, *Backpack*, *Goals* and the zoom (− / + or Ctrl+wheel), and a *Waiting for you* list of what the home cannot settle by itself (a pet to move in, unread notes, furniture left in storage, jobs waiting for materials, a ready celebration, a wish); clicking a line opens its tab. While arranging, the desktop strip shows *Done arranging*, since it never takes the keyboard. A save from a newer FrontEngine offers *Get the latest FrontEngine*. *Free arranging* switches to a separate home (``pet-home-sandbox.json``) with every piece of furniture, no costs and no coins; nothing done there reaches the managed home, its coins and goals, or the pets' own values, and switching back or forth cancels what the pets were doing without rewards and saves first.
- Time passes only while the home is running (*Start* / *Pause*); time while FrontEngine was closed or the computer slept is never simulated. The home is saved to `pet-home.json` beside your settings, with the previous good copy kept as `pet-home.json.bak`. A save that cannot be read, or one from a newer version, is never overwritten: the page offers the backup, or keeps the old file and starts a new home. After a failed save succeeds on retry, its live error message clears; the Inbox keeps the error history. If shutdown cannot save settings, pet or home state, notes, the last session or usage history, FrontEngine stays open so you can correct the problem and retry. Earlier successful writes and canceled activities are not rolled back.

Each process has one FrontEngine control window. Its settings folder stays reserved until its background work and windows have finished closing; another process cannot open the same folder. JEditor and PyBreeze reuse the embedded window and keep the host open if saving fails or closure is still pending.

On narrow windows, home status text sits above action buttons that wrap onto another line. After a GIF overlay finishes closing, its source file can be moved or deleted.

Pet generation, previews, default wardrobes and home artwork use the settings page’s owned data directory, even if the host changes its working directory. An explicitly supplied pet asset library is preserved. Home photos, the album and the local content-pack folder use the same owned data directory. New photos appear in the album as soon as saving succeeds, including while the home is paused.

Home panel actions are rejected while closing is prepared or in progress; blueprint file-dialog results are checked again before use. Cancelling close permits new actions without replaying rejected ones.

Hosts embedding individual settings pages must pass an explicit DefaultSettingsLifetime through lifetime=. Save and stop the page before closing that lifetime, and observe its finished signal before exiting the host. [Runtime lifetime API](docs/formats/runtime-lifetime.md)
- Pets dressed as a layered character (a built-in INKSIDE character or one from the wardrobe) appear in the home as themselves: walking while on the way, sitting at the desk or in the armchair, sleeping in bed, eating at the table, playing at the toy box, greeting each other, facing the way they walk. *Wardrobe…* on a resident opens the usual wardrobe, and a new outfit shows up in the home at once. Characters are loaded in the background; until then a coloured marker stands in. Picture pets (a GIF, a picture or a sprite pack) and Puppet pets that have been on the desktop appear in the home as themselves: a sprite pack's own walking, idle and sleeping animations, a GIF's own frames, and for a Puppet a still taken from its own canvas; a pet with a single still picture bounces while walking, hops while playing and settles down to sleep. Pets with no usable look of their own (new pets, or a picture that has since been moved) appear as one of the built-in characters, the same one every time; their own look and their desktop pet are not changed. An undressed built-in character with its default parts and colours has its own drawn poses: it lies on the bed to sleep, sits in the armchair, eats, plays, writes at the desk, waters the planter and hammers at the workbench (sitting, sleeping, eating and playing also on the desktop). Dressed or recoloured, it keeps the layered animation and sits at its station. A pet still wearing an older version of a built-in character is moved to the current one automatically, keeping its outfit and colours.
- Four home *modes*: *Normal*; *Focus*, which keeps the desktop strip quiet (no bubbles or cards); *Meeting*, which hides the home and pauses it and says so; and *Power saver*, which draws the strip at 15 frames per second without slowing the pets' lives. Sharing your screen switches to Meeting for as long as it lasts. The *Inbox* collects finished work, needs, life moments and problems, folds repeats into one line and never pops up or takes focus; pets eating and napping on their own are never listed.
- The home has days, nights and weather: the overview's sky follows the game clock from dawn to night, and clear, cloudy or rainy spells change every six game hours, chosen from the home itself so they are the same each time. Weather is atmosphere only; it never damages anything or makes you wait. Three themes (*Warm home*, *Green studio*, *Night studio*) change colours, never the layout. Furniture is drawn as outlined cartoon pictures modelled in Blender, coloured to match each theme; a piece's name shows while it is selected or while arranging. Rain, starry nights, a first close friend, getting good at a job, a green home, a full house, a first short story and a good harvest join the life moments, twelve in all. *Reduce motion* stops pets gliding between steps and keeps the rain still; every event is also written in the card and the moments list, and the home makes no sound.
- Ambient sound is off until you turn it on in the *Settings* tab, with a volume of its own: birdsong by day, crickets at night, rain or a soft winter wind in that weather. It is silent while the home is paused, in a meeting or the computer is locked. On the desktop strip, evening and night gently dim the furniture and pets; the empty parts of the strip stay clear, so clicks still go through to the windows behind. When it rains or snows, drops or flakes also fall over the strip, in a layer of its own that never takes the mouse or focus; they pause in focus and meeting mode and stand still under *Reduce motion*.
- *Goals* grow with the home: a home level that rises with milestones you reach by living (all three jobs, more residents, more furniture, close friendships), ten *Getting started* goals with small rewards collected by themselves (skip them any time; they stay reviewable), three *commissions* a day that buy goods for coins with no streaks or missed-day penalties, a small wish per pet that says how to fulfil it and never counts down, life moments such as birthdays, a first handmade creation or dinner with friends, and a one-time home celebration once two or more pets live together and all three jobs have been done. *Take a photo* saves the drawing of the home to `pet-album` beside your settings; nothing from your desktop is captured. The backpack shows how much of the furniture collection you own.
- Pets need comfort and company too. Beds, armchairs and decorations make a home comfortable; low comfort wears on mood. Pets say hello to each other, enjoy meals and games together and grow closer, and now and then squabble over the last free seat. Each pet has a lasting personality (diligent, playful, quiet, sociable, or a liking for gardening, writing or crafting) that shapes what it chooses and makes liked work a little faster; no personality makes a pet unfit for anything. The card shows personality, closest friends and how many minutes the current activity has left, and on the desktop short bubbles say what a pet just started, who it greeted and what it earned. Older home saves gain the new needs on load; a home saved by this version is protected from older FrontEngine versions.
- Pets like to stay clean as well: cleanliness wears down slowly (faster while playing), and a grubby pet tidies itself up where it stands or bathes in a bath tub, which is quicker; grooming helps too, and when a grubby pet lives in a home without a tub, the list under the home suggests one.
- Three jobs: writing at the desk, gardening at a *Planter* (herbs that make meals happier, flowers to sell) and crafting at a *Workbench* with wood from the shop (toys to sell, stools that go straight into storage). Work runs in visible phases (sow, water, harvest…) and waits rather than starting when materials are missing. The *Backpack* lists everything the home owns, what is set aside for work, and sells goods. Buying always costs more than selling returns, and no chain of jobs can turn something back into itself.
- The home also lives on the desktop: a transparent strip along the bottom of the screen, standing on the taskbar edge. Only pets, furniture and the small ⌂ button take the mouse; every other pixel clicks through to the windows behind, and the strip never takes focus. Click a pet for its card, right-click it for commands, drag it to move it; right-click furniture to put it away. *Show the home on the desktop* turns it off, *Desktop layer* puts it above or below other windows (above by default), Hide all pauses the home until it is shown again, and the Control Center's quality setting picks 60, 30 or 15 frames per second without changing how fast the home lives. The arrow beside ⌂ opens a toolbar with *Arrange*, *Residents* and *Work* plus the coins, the pet you last clicked and the open jobs; the ⌂ menu moves it to the other end of the strip, and whether it is open and where it sits are remembered. A pet's right-click menu starts with *Feed*, *Pat* and *Talk* - a small lift to fullness, mood or company, at most once every half minute per kind and never for a pet that is resting elsewhere - then *Ask to* (the commands), *Wardrobe…*, *Work for this pet…* and *Follow in the overview*, which keeps it in view while the overview is zoomed in. A piece's right-click menu says what it is for and who is using it, and offers *Move* (arranging right on the desktop) and *Put away*. Locking the computer pauses the home the same way, and the status line says so until it is unlocked. Dropping a file on a pet in the home counts as feeding it (with the same half-minute cooldown); the file is never opened, changed or deleted and never turns into materials or coins. The pet menu also has *Groom* and *Play with a toy* (not while it works, eats or sleeps), *Come here* (it walks to where you right-clicked and waits there a little), *Play tag* (with the nearest free pet; a busy pet is never pulled in, and both enjoy it) and *Take a photo* (that pet from the overview, saved to the album).
- The strip can be made smaller or larger (75–200 %, furniture, pets and height together) with Ctrl + mouse wheel over a pet or piece, from ⌂ → *Size*, or in the Settings tab; the choice is remembered. A home wider than its screen at that size stays on the screen and glides along to keep the pet you last clicked (or the pets) in view. Double-click a pet on the strip to pat it.
- **Features**, the first menu, holds every tool grouped by purpose (media, scenes and wallpaper, widgets, focus and eye care, presenting, capture, pets, automation, content and Workshop, overlay control, settings and help), plus *Search features* (Ctrl+K), *Pinned* and *Recent*. Entries open the same pages and run the same commands as before, so hotkeys, presets, rules, the phone remote and MIDI keep working; the Presets, Settings, Language and Help menus appear inside it as they are. Sidebar groups fold with a click on their heading and stay folded. The tray menu gains *Open Pet home*.

### On screen

Media overlays. Each one picks its monitor (or spans all of them), remembers
where you dragged it, and has its own opacity.

By default an overlay opens on the screen FrontEngine is on, without asking. Choosing a file shows it at once, so does dropping one onto the page, and *Start* without a file opens the chooser; an empty text or address field is pointed at instead of a warning dialog, and Enter in it starts.

- **Video** — with volume, playback rate and looping.
- **Image** — a single picture, a folder as a slideshow, or a **reference
  board**: several images on one canvas, each draggable, the whole board
  zoomable and pannable.
- **Web** — a URL or a local HTML file, optionally interactive. **Dashboard
  mode** rotates through a list of URLs, so a wall display can cycle pages on a
  hotkey or a timer.
- **GIF / WebP** — animations at an adjustable speed.
- **Text** — font, colour, outline, alignment and a marquee, showing either a
  fixed string or a **live source**: clock, date, countdown, stopwatch, system
  load, or the weather. The live sources take a `{field}` template, and the page
  lists the fields each one offers.
- **Sound** — music playback and low-latency WAV effects.
- **Scene** — combine several of the above into one composition described by a
  JSON document you can save and share.
- **Particle** — an OpenGL particle effect.

<details>
<summary>Screenshots (GIFs may take a moment to load)</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](gifs/play_gif.gif) | ![WEBP](gifs/webp.gif) |

| Video | Website |
| --- | --- |
| ![Video](gifs/video.gif) | ![Website](gifs/website.gif) |

</details>

### Desktop

**Desktop pet** — an animated sprite that lives on your desktop.

The page opens with *Your pet*: click one of the built-in characters and a pet dressed as it appears on the desktop at once, or pick *Your own picture…*. Below, the pets on the desktop are listed with *Wardrobe*, *Bring pet back* and *Put away* (a double-click brings one back); every other setting is folded away until you open its section.

- Companion care saves energy and play/work/rest modes for each identity, preserving version 1 UUIDs and stats. The sprite menu adds greeting, petting and grooming. Timed actions reward completion only; full pets refuse food and repeats need a cooldown. Care follows active time, with no hidden/offline catch-up. Puppet pets share session and feeding rules; native responses depend on runtime/model capabilities. 

- **Sprites** — a single GIF/WebP/PNG, or a *pet pack* folder whose file names
  map to states: `walk`, `idle`, `sleep`, `climb`, `fall`, `drag` (a missing
  state falls back to `walk`). An optional `pet.json` sets size, speed and
  whether it may climb, talk or sit on windows.
- **Behaviour** — walk on the floor with gravity (throw it and it bounces),
  wander freely, or chase the cursor. Floor pets climb screen edges and stand on
  the top edge of other windows.
- **Life** — mood, fullness and an affection level that persist between runs.
  It grows as it levels up, talks in speech bubbles, naps while you are away and
  warns you about a low battery.
- **Interaction** — drag it, right-click to clone / feed / set a reminder, and
  **drop a file onto it**: an image or pet pack becomes its new look, anything
  else is eaten. What it eats matters — an archive is a feast, music cheers it
  up more than it fills, a document is a modest meal, a binary is too hard to
  chew.
- **Tag** — with two or more pets on screen, tick *Play tag with each other* and
  one becomes "it": it walks toward its nearest neighbour while the others run
  the other way, and catching someone passes the tag on.
- **Reacts to sound** — the pet pulses with your speakers' output, or with your
  **microphone** so it moves while you talk. Both read only the output *meter* —
  a number, not audio. Peaks are smoothed with an RMS window and a
  fast-attack/slow-decay envelope so the pulse breathes instead of flickering.
  With several monitors, each pet follows the audio endpoint matching its own
  screen.
- **Focus timer** — a pomodoro on the same page, announced by the pet: it tells
  you when focus ends and when the break is over.
- **Chat** — the pet can answer you through Claude when `ANTHROPIC_API_KEY` is
  set. Off unless you enable it; see [What leaves the machine](#what-leaves-the-machine).

**Wallpaper** — play a folder of images and animations *beneath* every window.
Each monitor points at its own folder with its own timer, shuffled or read
recursively, and can pulse with the speaker level. A second folder can take over
during quiet hours.

**Widgets** — four things that sit on the desktop:

- **Audio spectrum** — bars or a ring, log-spaced bands, smoothed with a
  fast-attack/slow-decay follower and peak markers that drift down.
- **Now playing** — the current track from Windows' media controls when the
  optional `winsdk` bindings are installed; otherwise the name of the app that
  is actually making sound.
- **System monitor** — CPU, memory, disk, battery and network throughput as
  small sparklines; tick the lines you want. An average hides a stall; a line
  does not. A hidden line keeps recording, so turning it back on shows what
  happened meanwhile.
- **Sticky notes** — editable cards above every window, keeping their text,
  colour and position between sessions.

### Work

**Focus** — two overlays for when the screen competes with your work. *Dim
background windows* shades everything except the window you are working in, at
an adjustable strength. *Cover a distraction* masks a strip of the screen: the
taskbar, a notification corner, an edge, or all of it. Both pass clicks
through, so what they cover still works — it just stops pulling your eye.

**Screen care** — for long sessions at the screen:

- **Colour filter** — seven tints from warm through amber and rose to grey, at
  an adjustable strength.
- **Reading ruler** — dims the page and leaves a bright band that follows the
  cursor.
- **Break reminder** — the 20-20-20 rule, with a rest overlay when the interval
  is up.
- **Colour-vision simulation** — protanopia, deuteranopia, tritanopia and
  achromatopsia at an adjustable severity, using the Machado et al. (2009)
  model. Unlike the other overlays this one is opaque, because showing what
  someone else sees means repainting the screen rather than tinting it.

**Presenting** — for demos, lessons and recordings:

- **Annotation** — draw over the screen with a pen, highlighter or eraser, with
  undo and clear.
- **Cursor effects** — a ring around the pointer, a ripple on click, and a
  spotlight that dims everything else.
- **Keystroke display** — shows what you just pressed, and which mouse button
  you clicked, so viewers can follow along; it fades after a couple of seconds.
  Pick where the panel sits and how big the text is, and turn mouse clicks off
  on their own.
- **Magnifier** — a zoomed view of the area around the cursor.
- **Whiteboard** — an infinite canvas: drag to pan, scroll to zoom, save what
  you drew. Strokes live in canvas coordinates, so panning and zooming leaves
  them where they belong.
- **Freeze** — pin the current frame of a monitor so you can keep working
  behind a still image. `Ctrl+Shift+F7` releases it, which matters because the
  frozen image covers the button that would.

**Tools** — measuring, capture and window handling:

- **Colour picker / pixel ruler / protractor** — click to sample or measure; the
  result goes straight to the clipboard as `#rrggbb`, `rgb(...)`, `hsl(...)` or
  a CSS custom property.
- **Region capture** — drag out an area; it lands on the clipboard, can be saved
  to a file, or **pinned** on top as a floating, zoomable copy.
- **Record area** — Recording: select an area and choose the output GIF or AVI before capture starts. Cancelling does not start recording. Frames are written incrementally on a background thread with a queue limited to three frames and 64 MiB; a single oversized frame is rejected. A full queue drops captures and preserves elapsed playback timing. Frame-rate, duration and frame-count limits and the optional camera inset remain. Stop finalizes asynchronously; the final file replaces the destination atomically only after success. Cancellation and write errors clean up the temporary file and preserve an existing destination.
- **Camera** — your webcam in a circle, rounded box or rectangle, shown locally
  and never recorded. Any video input works, including capture cards, and the
  device list refreshes without a restart since cards are usually plugged in
  while the app is already running.
- **Virtual camera** — send a region, overlays and all, as a webcam that Zoom,
  Teams or Discord can select as their video source. Needs the optional
  `pyvirtualcam` package and a virtual camera driver (OBS installs one); without
  either, the button says so rather than failing quietly.
- **Read text** — Screen text: Tools → Read text first uses local OCR: Windows.Media.Ocr on Windows, Vision on macOS, or an installed Tesseract executable with language data. Local extraction needs neither cloud consent nor ANTHROPIC_API_KEY; an empty successful result does not upload a screenshot. Translation and questions can send recognized text to Anthropic only with separate text consent and your key. Screenshot fallback after local failure needs its own capture consent and the key. The result shows the backend and errors; consent can be withdrawn there.
- **Pin a window** — keep another program's window on top, or fade it, while you
  work against it. Only stacking and opacity are touched, never window content.
- **Window replica** — a small always-on-top live copy of another window, so you
  can watch a render or a chat while it is buried.
- **Window layouts** — save where every window sits and put them back later.
  Windows are matched by title; one that is not on screen is skipped rather than
  guessed at.

---

## Controlling everything at once

The **Control center** page reaches every overlay on every page, whichever tab
opened it: hide, show, close, mute, lock, reset positions, step the opacity, and
apply a **quality tier** (high / balanced / saver) that caps each overlay's
refresh rate and drops its render resolution. It also carries a chroma-key
background for OBS, a *Hide from capture* toggle, the log panel, and **Pin to
this desktop** — the overlays step aside when you switch virtual desktop and
return when you come back. Unpinning brings back whatever it put away.

Default global hotkeys, all rebindable from **Settings → Hotkeys**:

| Shortcut | Action |
| --- | --- |
| `Ctrl+Shift+F12` | Close every overlay |
| `Ctrl+Shift+F11` / `F10` | Hide / show every overlay |
| `Ctrl+Shift+F9` | Mute everything |
| `Ctrl+Shift+↑` / `↓` | Opacity up / down |
| `Ctrl+Shift+L` | Lock or unlock (click-through vs draggable) |
| `Ctrl+Shift+→` | Next dashboard page |
| `Ctrl+Shift+F8` | Show the shortcut sheet on screen |
| `Ctrl+Shift+F7` | Freeze / unfreeze the screen |
| `Ctrl+Shift+F6` / `F5` / `F4` | Media play/pause, next and previous track |
| `Ctrl+Shift+F3` | Move the foreground window to the next monitor |
| `F12` | Quit immediately (Windows / macOS*) |

Media transport sends the system media keys, so it reaches any player that
listens for them. Moving a window keeps its proportions rather than snapping it
across, which is what Windows' own `Win+Shift+Arrow` does.

The same actions — and nothing beyond them — are what the remote controls drive:

- **Your phone** (Settings → Remote control) — FrontEngine serves a small page on
  your local network; open the link on a phone and the buttons drive those
  actions.
- **A MIDI controller** — Press Learn, move a knob or pad, and bind it. Windows uses built-in winmm; macOS uses CoreMIDI with the macos extra. A knob fires once at the top, and releasing a pad does not count as another press.

---

## Presets and automation

**Presets** capture the settings of every page at once. Save, load, delete,
export and import them from the **Presets** menu, apply one on launch, or
restore the previous session automatically. A preset can be exported as a
**package** — a zip carrying the media it references — so it opens on a machine
that does not have those files.

Things that then decide for themselves, all from the **Settings** menu. Smart
pause is the only one that starts out on; everything else is off until you
switch it on.

| | |
| --- | --- |
| **Rules** | *"When these conditions hold, do this."* Combine a weekday, a time window and which application has focus, then apply a preset, hide/show/close the overlays, or set the quality. A blank condition means "any", and a rule runs **once** when its conditions start holding rather than repeatedly while they do. This is the one place conditions compose; the rows below each know a single kind. |
| **Smart pause** | Stand the overlays down while a fullscreen app runs, while the machine is on battery, or while a named app has focus. *(On by default, for the fullscreen rule.)* |
| **App profiles** | Apply a preset when you switch to a given app. |
| **Preset schedule** | Apply a preset on chosen weekdays at a set time. |
| **Theme** | Follow the system, or always light or dark (*Settings → Theme*). The window uses FrontEngine's own design in the ink, paper and orange of the built-in characters; settings from earlier versions keep the light or dark look they had. |
| **Theme schedule** | Switch between a day and a night theme by the clock. |
| **Signage mode** | Rotate a list of presets on a timer with the main window put away, for a machine left running as a display. |
| **Screensaver** | After an idle threshold, bring up the video / image / GIF / particle / web page you chose, and take it down when you come back. |
| **Reminders** | Every N minutes, or once a day at a set time, shown as a toast that closes itself. |
| **Keep awake** | Stop the display sleeping while overlays are up. |
| **Start with the system** | Launch at login. |
| **Screen time** | Which apps had focus and for how long, with a daily breakdown and a seven-day summary. It pauses while you are away from the keyboard, keeps 60 days at most, and clearing deletes the file itself. |
| **Clipboard history** | Search what you copied and pin the phrases you reuse. Clipboards routinely hold passwords, so this is kept **in memory only** unless you separately tick "keep between sessions". |

---

## Languages

Seven: English, 繁體中文, 简体中文, Deutsch, Русский, Français, Italiano.

Pick one from the **Language** menu and the interface changes **immediately** —
no restart. Whatever you had open stays open: overlays keep running, and the
settings on every page are left exactly as they were. On a Steam install the
first launch follows the Steam client's own language.

---

## Privacy and platform notes

### What leaves the machine

Everything in FrontEngine is local unless it is on this list. There are four
exceptions, all opt-in:

| Feature | Where it goes | Guard |
| --- | --- | --- |
| **Read text** (Tools) | Anthropic API | Screen text: Tools → Read text first uses local OCR: Windows.Media.Ocr on Windows, Vision on macOS, or an installed Tesseract executable with language data. Local extraction needs neither cloud consent nor ANTHROPIC_API_KEY; an empty successful result does not upload a screenshot. Translation and questions can send recognized text to Anthropic only with separate text consent and your key. Screenshot fallback after local failure needs its own capture consent and the key. The result shows the backend and errors; consent can be withdrawn there. |
| **Pet chat** | Your message goes to Anthropic's API | Same key, same rule; off by default. |
| **Weather** (text source) | Coordinates go to Open-Meteo | No key, no account, no identifying data; only what you typed as a location. |
| **Phone remote** | HTTPS | Phone control: Settings → Remote control serves HTTPS only, with a token that changes on every start and a fixed action list. The local self-signed certificate is not automatically trusted by a phone. Export the public certificate and compare the displayed SHA-256 fingerprint before importing or trusting it through your phone/browser settings. The private key stays in the user data directory. Changed IP addresses, expiry or regeneration may require trusting a new certificate. TLS startup failure does not fall back to HTTP. |

The audio features read only an output **meter** — a single number — except the
spectrum, which needs real samples to compute frequencies and so captures the
system output stream. Those samples are analysed in memory, never written to
disk or sent anywhere, and capture stops the moment you stop the spectrum.

Plugins: enabling loading does not authorize a plugin. A plugin.json or single-file sidecar declares version, identity, entrypoint and capabilities; approval is checked before Python import and tied to the content digest. Changed code or declarations require approval again; legacy plugins require explicit full trust. Settings → Revoke plugin grants removes stored approvals; restart to unload already running code. Python plugins still run with full application privileges: declarations and consent are not an OS sandbox.

### Screen-sharing privacy

Your overlays are for you, not for the people you are sharing with. From
**Settings → Screen-sharing privacy**, FrontEngine can take them out of the
capture while a meeting app is open:

- **They stay on your own screen.** Only the captured copy is blank — this uses
  Windows' `WDA_EXCLUDEFROMCAPTURE`, an OS-level flag conferencing apps and
  recorders honour.
- **Masks are the exception.** A distraction mask exists to cover something, so
  it deliberately stays visible in the capture.
- **The trigger is your list.** Windows has no dependable "am I being captured"
  API, so it watches for window titles you name — which also catches a meeting
  held in a browser tab, where the executable is just the browser.

There is a manual *Hide from capture* button in the control center too.

> This is privacy, not security: it defeats the ordinary capture path, and it
> never hides anything from the person sitting at the desk.

### Platform support

Everything not listed here works on all three platforms.

| Feature | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Common overlays and UI | ✅ | ✅ | Qt / X11 |
| System audio, spectrum and microphone | ✅ | backend* | Pulse† |
| Now-playing metadata | ✅ | — | — |
| Window geometry, layouts and monitor move | ✅ | backend* | X11† |
| Live window replica | ✅ | backend* | — |
| Foreign-window topmost / opacity | ✅ | — | X11† |
| Exclude overlays from capture | ✅ | — | — |
| MIDI control | ✅ | backend* | — |
| Media transport keys | ✅ | backend* | — |
| Virtual desktop / Space selection | ✅ | — | — |
| F12 emergency exit | ✅ | backend* | — |
| Pet standing on other windows | ✅ | backend* | wmctrl |

* macOS entries marked “backend” require the macos extra, macOS 13+ and the indicated permissions. They describe implemented public-framework paths, not native validation on this Windows host; see the runtime notes below.

Where a feature cannot work, the button says so rather than failing quietly.

---

## Runtime, privacy and interoperability

Recording: select an area and choose the output GIF or AVI before capture starts. Cancelling does not start recording. Frames are written incrementally on a background thread with a queue limited to three frames and 64 MiB; a single oversized frame is rejected. A full queue drops captures and preserves elapsed playback timing. Frame-rate, duration and frame-count limits and the optional camera inset remain. Stop finalizes asynchronously; the final file replaces the destination atomically only after success. Cancellation and write errors clean up the temporary file and preserve an existing destination.

Phone control: Settings → Remote control serves HTTPS only, with a token that changes on every start and a fixed action list. The local self-signed certificate is not automatically trusted by a phone. Export the public certificate and compare the displayed SHA-256 fingerprint before importing or trusting it through your phone/browser settings. The private key stays in the user data directory. Changed IP addresses, expiry or regeneration may require trusting a new certificate. TLS startup failure does not fall back to HTTP.

Screen text: Tools → Read text first uses local OCR: Windows.Media.Ocr on Windows, Vision on macOS, or an installed Tesseract executable with language data. Local extraction needs neither cloud consent nor ANTHROPIC_API_KEY; an empty successful result does not upload a screenshot. Translation and questions can send recognized text to Anthropic only with separate text consent and your key. Screenshot fallback after local failure needs its own capture consent and the key. The result shows the backend and errors; consent can be withdrawn there.

Puppet pets: install the optional puppet extra and an available Imervue runtime, then choose an original Imervue .puppet v1 file on the Pet page or drop it there. Existing image/sprite pet packs still work. Puppet pets use Imervue's canvas, motions and expressions, can be cloned or closed, and participate in FrontEngine's overlay controls and presets. Choose an optional .petscript.json for Imervue's existing script engine; do not treat FrontEngine pet.json packs as puppet files. Unknown versions, unsafe archive paths and invalid assets are rejected before runtime loading.

Puppet pets also stroll on their own: after a few seconds' rest they walk a short way left or right along their current height with the walk motion, stay inside the screen's work area, then rest again. A stroll gives way to dragging, petting, Come here and toys, settling while typing, and modes that do not allow acting alone.

The Behaviour menu's default, Cycle all actions (random), has a free pet pick what to do next at random from its whole set of actions; Walk on floor keeps only walking and idling. A sprite pet chooses among walking, idling, sitting, playing, grooming, climbing the nearer wall, waving, sleeping, celebrating and showing off its outfit; a Puppet pet chooses between a stroll and sitting, playing, grooming, waving or celebrating in place. A summoned pet sets off walking at once. Poses are held in place, and a pet without an image for a pose shows its idle image.

Scenes: the Scene page accepts old entry-mapping JSON, a versioned frontengine.scene envelope, and portable .fescene packages. Add a PUPPET entry with position, size, opacity, finite numeric parameters, optional motion, expression and script. Paths in JSON resolve relative to the scene file. A .fescene includes the referenced media, original .puppet and optional .petscript.json so it can move between machines. Import checks paths, symlinks, versions and extraction limits. A FrontEngine scene remains a scene package; .puppet remains one Imervue character.

macOS: the optional macos extra targets macOS 13+ with public PyObjC frameworks. Backends provide ScreenCaptureKit screen/window capture and system audio, microphone capture, Quartz window geometry, Accessibility window layout/movement, CoreMIDI, media keys and the F12 exit path. Screen Recording, Accessibility and Microphone permissions are checked separately; follow System Settings → Privacy & Security and restart when requested. Foreign-window opacity/topmost changes, Space selection and excluding overlays from other apps' captures remain unavailable. Native macOS permissions, hardware and performance have not been verified on this Windows development host. Settings → macOS permissions and capabilities lists each feature as available, unavailable or unsupported and shows the permission or installation reason.

Plugins: enabling loading does not authorize a plugin. A plugin.json or single-file sidecar declares version, identity, entrypoint and capabilities; approval is checked before Python import and tied to the content digest. Changed code or declarations require approval again; legacy plugins require explicit full trust. Settings → Revoke plugin grants removes stored approvals; restart to unload already running code. Python plugins still run with full application privileges: declarations and consent are not an OS sandbox.

Rendering: Settings → Overlay rendering selects Auto, GPU or Software and shows the backend actually used. The GPU compositor uses OpenGL textures, shaders and framebuffers for layer order, transforms, opacity and clipping; initialization failure falls back to software with a reason. Existing QPainter content can still be rasterized on the CPU before texture upload; web/video/native widgets may use separate windows. Capture or recording may read a GPU frame back to the CPU. These paths are not a promise of zero-copy capture or measured speed gains.

Windows OCR WinRT projections are included in a normal FrontEngine installation on Windows; install the Windows recognition languages you need. Tesseract requires its executable and trained language data installed separately. The optional puppet extra installs Imervue>=1.0.90; the macos extra installs the public PyObjC frameworks for macOS 13+. Use the commands below. See docs/formats/ for puppet, pet.json, petscript and scene examples.

```bash
pip install "frontengine[puppet]"
pip install "frontengine[macos]"
```

[.puppet / pet.json / .petscript.json / .fescene](docs/formats/interoperability.md)

---

## Extending

- **Steam Workshop** — subscribed items are picked up from Steam's own
  `steamapps/workshop/content` folder: presets are imported and pet packs are
  listed with their paths, from **Presets → Import Workshop content**.
  Publishing to the Workshop needs the Steamworks SDK and is not built in.
- **Plugins** — a `plugins/` folder can add its own tabs, either through a
  `FRONTENGINE_TABS = {"name": WidgetClass}` mapping or a `register(registry)`
  hook. Read the trust note above first.

---

## Development

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

Static checking uses pyflakes (in `dev_requirements.txt`), and a clean tree prints
nothing at all:

```bash
python -m pyflakes frontengine/ exe/ tests/
```

The test suite runs entirely offscreen and needs no display, sound card or
camera; anything that touches the outside world takes an injectable source so
it can be tested with a fake one.

- **Architecture** — [`architecture_explore.md`](architecture_explore.md) maps
  every module, the layering, the overlay contract and the extension points.
  Read it before adding a page or an overlay: several things (the control
  center registry, seven language dictionaries, seven documentation trees) have
  to be updated together, and the tests enforce that.
- **Contributing** — see [`CONTRIBUTING.md`](CONTRIBUTING.md). One feature per
  pull request, all CI checks green.
- **Building the Windows executable** — `python exe/build_exe.py`
  (Nuitka; add `--onefile` for a single file).
  It compiles on every CPU core by default; `--jobs N` caps the parallel jobs (less memory), `--jobs -N` leaves N cores free.
- **Documentation** — Sphinx sources in `docs/`, published to
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) in all seven
  languages.

---

## Continuous integration and releases

Work flows `feature → dev → main`, and only the last step publishes:

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR to `main` or `dev`, manual dispatch, or called by `Nightly` | Compile, run the unit tests, then build a wheel from *that checkout*, install it and start the app — on Python 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Daily cron, manual dispatch | Calls `CI`. The schedule lives here on purpose: GitHub disables workflows containing a cron after ~60 days of inactivity, and that would otherwise take the PR checks down with it |
| `Release` (`release.yml`) | A pull request **from `dev`** is merged into `main`, or manual dispatch | Bumps the version, commits it back with `[skip ci]`, swaps `stable.toml` → `pyproject.toml`, builds sdist + wheel, uploads to PyPI as `frontengine`, creates a GitHub release tagged `v<version>`, and fast-forwards `dev` |

Publishing happens **only when `dev` merges into `main`**. Features land on `dev`
without minting a version, and a release is a deliberate `dev → main` pull
request. A feature PR aimed at `main` by mistake still merges but does not
publish — the failure direction is a missing release, not an unwanted one.

The patch segment bumps automatically; for a minor or major release, run
*Actions → Release → Run workflow* and pick the segment. That path also re-runs
a failed publish without needing a new merge.

Versions live in two files: `pyproject.toml` is the dev package
(`frontengine_dev`) and `stable.toml` is the published one (`frontengine`).

One repository secret is required: `PYPI_API_TOKEN`, a PyPI token scoped to the
`frontengine` project. The workflow uses `__token__` as the twine username, so
only the token itself needs storing.

---

## Security

Report vulnerabilities privately. The policy, supported versions, and operator notes are in [SECURITY.md](SECURITY.md).

## License

See [`LICENSE`](LICENSE). Community expectations are in
[`Contributor_Covenant_Code_of_Conduct.md`](Contributor_Covenant_Code_of_Conduct.md).

Workshop content manifests are versioned and validated before use. Unknown metadata JSON is not treated as a preset. Preset packages reject unsafe archive paths, resource-limit violations and colliding media filenames.

Presets → Manage Workshop opens the Steam manager; Scene and Pet also provide shortcuts. On Windows x64, connect an online Steam client for App 2793470 and provide steam_api64.dll. Publish saved .fescene/scene JSON, preset ZIP packages or sprite pet folders with a PNG/JPEG preview under 1 MB. New items default to private; updates verify ownership. Uploads show progress and agreement status, preserve item IDs for retries and continue when the manager is hidden. Interrupted outcomes require verification in Steam. Subscriptions are validated and copied to separate version folders; local-change conflicts offer the downloaded or local version. Loading fills the relevant page; use that page to start playback. Preset imports require a new name. Offline folder import remains available. For a Steam build, add --steam-runtime PATH_TO_steam_api64.dll to exe/build_exe.py; the selected DLL ships beside the executable (also for --onefile). The SDK and development steam_appid.txt are not included. Pet home furniture packs and themes are published from their pack folder (only `pack.json`, the thumbnail and furniture pictures are copied) and a blueprint from its file, rewritten from its checked parts so no pets, names, coins, chat or settings can ride along; the content packs a blueprint uses are listed in its manifest.

Windows installations now include winrt-Windows.Media.Control for the Now playing widget (song title and artist through SMTC); older winsdk remains a fallback. No active media session yields an empty result, with the existing audio-application fallback retained.

Executable builds check all required dependencies and versions before compilation; install requirements.txt in the build environment first.

Scene → Visual editor provides an image/GIF/text layer list and preview, group dragging, corner resizing, position/size/scale/rotation/order/opacity controls, canvas alignment, layout locking, visibility, duplication and 100-step undo/redo (Ctrl+Z/Ctrl+Y). Export portable .fescene packages directly; the Script tab also supports editing and applying JSON. Explicit dimensions, scale, rotation and visibility are restored during scene playback. Loading/applying external JSON starts a new undo history; existing scene fields remain intact.

Open Commands from the menu bar or press Ctrl+K / Ctrl+Shift+P inside FrontEngine. Search the current interface language, English labels or stable command names; Up/Down selects and Enter runs. Commands include page navigation, capture, notes, the screen filter, Workshop and existing global actions. Preset/quality actions accept a value. Favorites and the last 20 commands survive restart; arguments and search text are not saved.

Settings use grouped cards: common actions stay visible, and secondary commands move into More actions menus. Advanced tools and messages expand with Show details. The scene editor places the canvas beside Properties, Preview and Animation tabs. Fields and inline controls wrap in narrow windows; the bottom action remains visible. Commands show favorite state and keyboard hints. A failed command keeps its input for retry; selecting a different command clears the previous argument.

Text → Local TXT / JSON / CSV displays a UTF-8 file with a selectable field and 1–3600 second refresh. JSON fields use /key/index paths (for example /build/tasks); CSV uses unique headers and displays the selected column as lines. An empty field displays the whole file. Reads run in a worker with one pending read per feed, a 1 MiB input limit and 65,536 output characters. Missing files/fields, invalid format, permissions and size limits have explicit states; corrected files recover automatically. Presets save the file/field/interval. Portable scenes copy the selected data file, so sharing a package shares that snapshot.

Tools → Color palette collects consecutive picker clicks when Collect colors is enabled. Name and group swatches, edit exact hex values, search, copy and remove colors; recent samples remain reusable. Up to 512 swatches and 50 distinct recent colors are saved locally and survive restart. Names are unique within each group (case insensitive); duplicate names are rejected. CSS and JSON export preserve RGB values; CSS variable name collisions get numeric suffixes. Export writes atomically. The Commands palette can also open Color palette.

Palette exports reject reserved settings, home, backup, temporary and lock filenames, and linked destination files.

Presets → Preset versions keeps up to 50 distinct settings snapshots per preset across restarts. Saving records the previous and new configurations; identical settings are deduplicated. Select a version to compare field changes with the current page settings. Preview applies that exact configuration to page controls; Cancel preview, Escape or closing restores the original settings. Restore version applies and saves it, rolling page settings back if application or saving fails. Snapshots contain media paths, not copies of media files; preview does not open overlays. Existing JSON/ZIP presets remain compatible. History lives under presets/.versions; deleting a preset leaves its history available if the name is reused.

Pet → Pet identities saves an independent UUID, name, mood, fullness and affection for every sprite or puppet pet. Choose a saved identity before spawning to resume it after restart; New pet creates fresh state. The first identity migrates the old shared values once. Cloning copies current stats to a new identity; feeding never changes another pet. Rename, refresh, export or import individual JSON saves; import always creates a new identity. One saved identity can be active only once. Saves contain no sprites, scripts or chat history, and local identity IDs are excluded from portable presets. Up to 256 identities are stored in user settings; sprite changes are saved after a short debounce and on close. Puppet feeding updates only saved stats and does not alter Imervue motions or geometry.

Export pet saves under a separate filename. Exports reject reserved settings, home, backup, temporary and lock filenames, and linked destination files.

Image → Compare images opens two references in one zoomable/pannable view. Switch between side by side, transparent overlay, a sliding wipe divider and absolute RGB difference. Align top-left or centers without scaling, or proportionally fit B inside A. Scroll zooms both images together; the slider controls B opacity or divider position. Transparent pixels and padding are compared on white; black difference pixels mean identical RGB. Only the first animated frame is used. Decoding/alignment/difference runs in a worker, with one pending request and only the latest selection applied; opacity/wipe redraws reuse pixmaps. Inputs are limited to 64 MiB per file, 8,192 pixels per dimension and 16,777,216 pixels per image/aligned canvas. Failed selection preserves the previous pair; closing clears images and ignores late results.

Settings → Rules adds priority (-1000…1000), cooldown (0…86400 whole seconds), condition preview and session execution history. Triggered rules execute from lower to higher priority, keeping table order for ties; higher priorities run last. Cooldown uses a monotonic clock: a blocked rising edge is consumed, and expiry does not execute while conditions remain true. Preview inspects unsaved rows without running actions or consuming edges. The last 200 receipts retain rule conditions, sampled context and dispatched/executed/failed/cooldown outcomes; history stays in memory. Invalid named rows prevent saving. Up to 200 rules are supported, with stable independent identities even for duplicate labels. Existing non-table conditions survive edits. An action callback reporting failure is recorded as failed, and one failure does not stop later rules.

Rules can load, play or stop a scene and show, hide, move or change the opacity of a named layer. Select the row and use Choose scene / layer target to browse JSON, .fescene or .puppet files, choose the primary/all/indexed screen, or select an editor layer. Playing with an empty path uses the current editor scene. File reads run in the background; a failed candidate leaves existing playback intact. The latest scene request replaces earlier pending requests; subsequent layer actions wait for it and fail if it fails. Locked or missing layers are rejected. Layer edits support undo and update playback; opacity is 0–100 and positions are limited to ±100000. Stop cancels pending requests and closes playback, keeping editor assets until replacement or application shutdown. Execution history records actual asynchronous completion. Scene actions also appear in the command palette: use a path or {"path":"scene.fescene","screen":"primary"}, a layer key for show/hide, {"layer":"title","opacity":50}, or {"layer":"title","x":20,"y":30}.

Scene → Script → Scene templates (also in the command palette) provides Work desktop, Teaching and Focus starter layouts with localized editable text. Preview the layout and choose the primary or a numbered screen before Apply and play; proportions fit its available logical size. Templates include all required resources. Missing resources are listed with layer/field/path and block application. Applying replaces the editor and playback through the same scene candidate transaction; failed preparation preserves the old scene. Edit the resulting text, add media and use Scene output to save JSON or a portable .fescene. Closing the library cancels only its pending application. Focus includes editable reminder text; scheduling and timers remain separate tools.

Scene → Visual editor can add video, web, Puppet and audio alongside image/GIF/text. Enable live previews explicitly: at most eight sources, muted until Listen to selected media, paused when hidden, closed on disable or shutdown. Frames are bounded to 1280 pixels per side; unavailable sources show an error. Named scene playback composes video frames, the web renderer’s own surface and Imervue offscreen Puppet frames with all visual layers in z order; audio has no visible playback layer. Double-click a web/Puppet layer in playback or choose Interact with selected media in the editor to open its own native input window. Puppet preview needs native OpenGL and the optional runtime; preview does not execute pet scripts, and scene pets use temporary stats. Standalone web/video/Puppet windows remain available. JSON/.fescene export preserves every supported type and media reference.

Tools → Record area offers GIF or silent AVI (Motion JPEG), 1–20 fps, Pause/Resume and Cancel. Status shows effective seconds, accepted frames and drops. Paused time is excluded from playback and duration limits, including stopping while paused. AVI supports up to one hour and 72,000 frames, with a 2 GiB output limit; GIF retains the 120-second/600-frame limits. Both use the three-frame/64 MiB background queue and atomic output. AVI retains one JPEG and writes its index to disk; dropped intervals repeat the last image to preserve timing. Encoding, size-limit or disk failures and cancellation preserve an existing target. No audio is recorded.

Scene → Visual editor → Animation timeline edits x/y/opacity keyframes for one unlocked layer, with fade-in and slide-in starters. Times are unique and increasing, 0–3600 seconds, up to 128 frames per layer; opacity is 0–100, positions ±100000, easing linear or smooth. Empty cells leave that channel unchanged. Apply creates one undoable edit; JSON and portable .fescene retain animation tracks. Scrub, play, pause, resume or replay preview without saving temporary positions; Reset restores saved geometry before editing. Scene playback has separate animation controls and one shared monotonic clock across screens. Hidden views suspend it; explicit pause persists after showing. Media suspends during animation pause; replay controls animation tracks. Scene-action replacement dissolves an outgoing composed snapshot into the new scene over 0.5 seconds, releases old renderers immediately and starts the new timeline at zero. Legacy scenes without tracks remain compatible.

Scene → Independent scene output previews the current editor scene at fixed 640×480, 1280×720 or 1920×1080 pixels, independent of desktop position, occlusion and DPI. Start preview does not open a camera; Send to virtual camera explicitly uses optional pyvirtualcam and an installed compatible driver. Device startup/send/close runs on one worker with only the latest pending RGB frame; slow devices drop intermediate frames. Output is muted and carries no audio. IMAGE/GIF/TEXT and native VIDEO/WEB/PUPPET are composed in layer order; SOUND is invisible. Puppet requires its optional runtime and native OpenGL; unavailable media/device errors are displayed. Up to 256 layers, eight native media sources and 16 megapixels of total layer raster are supported. Stop, Escape, dialog/application close and editor changes dispose renderers and request camera closure; restart after scene edits. Closing old asset readers precedes scene-package lease release.

Pet → Sprite pet pack editor maps walk/idle/sleep/climb/fall/drag images, previews size and walking speed, and exports a portable folder with pet.json. At least one action is required; missing actions are listed and use the existing loader fallback. PNG/JPEG/GIF/WebP sprites are limited to 64 MiB and 16 megapixels each, 256 MiB total. Import/export runs off the GUI thread, can be cancelled and never overwrites an existing export folder. Exported folders can be relocated, selected on the Pet page and shared as Workshop pet packs. Import retains selected sprites, name, size and speed only; sounds, scripts and speech are not copied. Imervue .puppet uses its separate authoring format. Closing or Escape releases preview movies and cancels pending file work.

Tools → Edit last capture opens a detached original with crop, arrow, numbered badges, text boxes and opaque black redaction. Drag on the scaled preview; coordinates and export remain in physical image pixels. Undo/reset and a read-only original view are available. Copy edited, Save edited PNG and Pin edited all use the same flattened crop/marks, even when viewing the original. Redactions are painted last, and saved PNGs contain no original or hidden layers; the last raw capture remains separate in memory. PNG saves are atomic. Limits are 16 megapixels, 1000 marks, 2000 characters per text box and 20 undo states. Closing/replacing the panel releases its document.

Presentation → Whiteboard now has independent editable pages, drawing/selection modes, Shift multi-selection, stroke movement and deletion, and twenty undo states across pages. Middle drag pans and wheel zooms; hit testing and movement stay in canvas coordinates. Each page retains its own view. Save/Open editable file uses versioned .fewhiteboard JSON with all vector strokes and views, allowing edits after reopening; save/read validation runs on one background worker and failures preserve the current board or existing file. Export this page PNG flattens only that page, excluding controls, selection and view transforms, with full pen margins. Bounds: 50 pages, 2000 strokes/page, 100000 total points, eight MiB JSON; PNG up to 8192 pixels/side and 16 megapixels. Closing/Escape cancels pending writes and ignores late read results.

Settings → Image clipboard history is separately opt-in and off by default; opening it neither enables monitoring nor reads the clipboard. Apply settings enables recording and optional between-session local SQLite persistence. Choose 10–200 images and 8–128 MiB of PNG payloads; favorites protect from eviction while counting toward both limits, and a full favorite set rejects new images explicitly. Images are limited to 16 megapixels/eight MiB encoded each. One worker owns compression, thumbnails and database writes, with one latest pending clipboard image and coalesced result mailboxes; slow compression drops intermediate images. Thumbnails support favorite/delete/clear, copying the original image, desktop pinning and an in-memory reference board. Clear includes favorites and frees stored payload pages; turning persistence off deletes the local database while retaining current memory history. The database is clipboard-images.sqlite3 beside settings (132 MiB database bound, transient SQLite journals may add disk usage); no uploads or automatic OCR. Shutdown disconnects monitoring and requests asynchronous worker cleanup.

Tools → Live OCR window pins recognized text next to a fixed selected region. Manual/local-only initially, with explicit auto refresh every 5–60 seconds, copy of displayed current/history text and twenty unique successful memory results. Unchanged or empty text does not duplicate history. At most four windows, one OCR job per window, 16 MP/eight MiB encoded capture and 20000 text characters; slow recognition skips repeated requests. Local-only never calls cloud even if global consent exists. Explicit cloud fallback uses existing ScreenTextService screenshot consent and credentials, with a separate Review cloud permission action; no automatic consent dialogs, translation or cloud text upload. Each enabled fallback refresh can upload the region. Window overlap is rejected to avoid feedback. Windows/X11 use screen-local Qt capture; Mac uses asynchronous native one-frame capture and stops its stream after a frame. Hide stops capture/timers; close/Escape releases sources/history and ignores late worker results without waiting. An already submitted external API request may still finish. These temporary windows are included in batch overlay cleanup and do not automatically reopen with capture enabled.

Settings → Capture history and search is separately opt-in. Opening does not save or recognize anything. Only explicit Tools region captures enter its local OCR worker, never clipboard monitoring or cloud fallback. Successful OCR becomes a case-insensitive text index; failures still save the image and show a reason tooltip. Date search uses exact YYYY-MM-DD in the user’s local timezone; leave fields empty for all entries. Copy, pin, reference board, favorites and deletion reuse image history controls. Optional capture-history.sqlite3 beside settings persists 10–200 captures / 8–128 MiB PNG data (16 MP/eight MiB per image; main database at most 132 MiB plus temporary journals). Delete removes OCR text together; clear includes favorites; persistence opt-out deletes the database. One latest pending capture skips intermediate inputs when slow; closing drops pending work/results without waiting for an active local recognizer.

Widgets → Tasks and calendar manages checked tasks with optional local due time and imports local UTF-8 .ics individual VEVENT/VTODO records. A separate Today widget shows incomplete undated/due/overdue tasks and events overlapping today; all-day and midnight end times are exclusive. Known IANA TZID uses platform Qt rules, UTC instants display locally, floating times remain local, all-day dates never shift. DST repeated times choose the first occurrence and missing times use the pre-transition offset; DURATION nominal days preserve local wall time. UID plus RECURRENCE-ID identifies updates; lower SEQUENCE cannot overwrite newer imports, checkmarks survive reimport, CANCELLED removes matching records. Folded lines and TEXT escapes supported; links, alarms and attachments are never opened. Recurrence rules/RDATE/EXDATE and unknown custom zones are explicitly rejected atomically; export individual occurrences. tasks.json beside settings holds at most 500 items/four MiB (title 1000, description 2000 characters); atomic writes preserve old data on failure. Import size four MiB, property 8192 characters, no network/sync/alarm. Lazy serialized worker keeps file I/O off the GUI; close stops timers and drops late results. Today widget joins batch close/hide controls; opening is explicit, task data persists without automatically restoring a widget.

Cancellation tombstones count toward the 500-record limit and prevent stale imports from resurrecting cancelled events. Clear all asks for confirmation and removes tasks, events and cancellation metadata. Interactive Today controls use ordinary Qt software painting so the compositor cannot cover them.

Settings → Asset library registers selected images/GIFs, sprite pet folders, .puppet textures and JSON/.fescene scenes, with static thumbnails, comma-separated tags, case-insensitive name/path/tag search and favorites. It does not copy, delete or execute media; forgetting only removes catalog metadata. asset-library.json beside settings holds 200 entries/one MiB, 32 tags of 40 characters each; images at most 64 MiB/16 MP, archives 256 MiB and scenes 256 layers. Scene thumbnails combine image/text and labelled media placeholders; Puppet thumbnail is its first texture. Show references scans the current scene, active local presets and registered scene JSON (200 presets/16 MiB total); missing paths remain discoverable. Relocate validates the same resource type, shows exact references for confirmation, updates the current scene as an undoable edit and repairs writable workspace scene JSON/presets plus catalog. Literal text, immutable preset history, portable archives, external scene files and managed Workshop sources remain unchanged/read-only; imported local copies can be registered. Concurrent changes abort rather than overwrite. Up to 50 files/16 MiB are protected by an atomic rollback journal (.asset-relink.json); interruption recovers before the next job, unexpected edits retain the journal with an explicit conflict. An OS-owned .asset-library.lock prevents another app instance from recovering an active repair. Lazy serialized workers decode/scan/write off the GUI; shutdown cancels pending repair writes and restores an unchanged in-flight scene edit, discarding late results. Restart playback after changing a media path.

Control Center → Follow a window selects an existing registered top-level overlay and a visible Windows target. Bind preserves the current proportional offset as the target moves/resizes; follower size remains logical and native movement uses physical coordinates with no activation/resize request. It clamps to the target monitor work area and rechecks on each 250 ms poll. Target minimize hides, restore respects user hide/hide-all, and close/hidden target or lost identity detaches. A unique reversible window property plus PID/thread checks prevents HWND reuse from inheriting a binding; elevated/UIPI targets can explicitly deny registration. Detach before manually dragging to a new offset. At most 64 temporary bindings, none restored across sessions; overlay close/close-all/app shutdown remove cookies and stop idle timer. This is the verified Windows adapter only; unsupported platforms show a reason. Native acceptance used own windows on one 125% display; cross-monitor mixed-DPI acceptance still requires another display.

Control Center → Monitor profiles explicitly saves/restores positions for each hardware monitor combination (20 profiles, 200 windows, 512 KiB local monitor-profiles.json). Proportional work-area positions adapt to resolution/primary/DPI changes while preserving logical window sizes; unavailable profiles clamp existing windows onto the primary work area. Automatic adaptation is separately opt-in, debounced 500 ms, and observes new overlays and Qt screen changes without modifying OS display settings. Hardware identity ambiguity is reported; same-kind/title duplicates are excluded from saved restoration but can be brought back into view. Fullscreen/scene windows and active target-follow bindings are excluded. It never creates overlays or guesses native handles. Movement stays entirely in Qt logical coordinates. Native save/restore/off-screen recovery passed on one Windows 125% display; real monitor plug/unplug, primary changes and mixed DPI still require additional hardware.

Static software composition now reuses one cached frame (up to 16 MP); image content/DPR, transforms, opacity, stacking, clip, output size and output DPI invalidate it. Unchanged layer submissions skip repaint; animated/video frames still refresh. GPU readback is unchanged. App exit and Close all share the registered overlay sources, close each object once before clearing, reset wallpaper playlists and run cleanup before releasing scene assets. Qt stays alive while canceled local file/raster workers finish, using a nonblocking timer. Plugin API v1 remains the supported manifest version; examples/plugins/clock provides a trusted QWidget page with overlay_widgets, optional release_overlay_resources/shutdown and get_state/set_state. Loaded plugin state is namespaced as plugin:<page name> in presets, including transactional rollback; presets never load code. Copy the selected example folder into plugins/, then explicitly enable and approve its content digest. Declarations/grants do not create an OS sandbox. Developer software benchmark: py -m benchmarks.scene_composition --output build/scene-benchmark.json; an optional trusted --baseline-file compares exact output pixels. Measurements and baseline procedure are in docs/benchmarks/README.md.

Help → Platform capabilities shows read-only adapter prerequisites and precise latest failures without starting capture/listeners. Linux audio uses distro pulseaudio-utils (parec) with PulseAudio or PipeWire Pulse compatibility: default output monitor for spectrum/reactivity, default microphone for lip sync. Unlike the Windows peak-only meter, Linux meter/reactivity reads actual audio samples; lazy first enabled sample starts one owned worker/child, keeps only 2048 sanitized float samples in memory, drops stale data and never writes/sends audio. Stop/close/app shutdown reaps only owned capture children without GUI joins. Device/server/permission failures are explicit. Linux foreign-window geometry/layout/topmost/monitor movement uses python-xlib (installed on Linux), EWMH and physical XRandR work areas; opacity requires a compositing manager. X11 pynput supports desktop input with DISPLAY/server access. Native Wayland arbitrary-window positioning and desktop-wide pynput input are unavailable, even with Xwayland; the UI gives this reason and monitor restoration refuses unsupported movement. Other native Wayland applications are never described as globally monitored. Linux protocol acceptance uses an isolated X11/Wayland server and virtual Pulse devices; physical Linux audio/multi-monitor and macOS hardware acceptance remain pending.

A meter stops its owned capture within 1.25 seconds after reactive sampling ends; a new enabled sample can restart it.

Windows builds share --preset and --debug with the Python CLI. For packaged native acceptance, install the optional frontengine[puppet] runtime in the build environment (Pillow decoder plugins and installed Imervue package data are included). Generate local synthetic fixtures with `py tests/integration/scene_build_fixtures.py FIXTURES --puppet SAMPLE.puppet` (fixture generation also needs PyAV). Run `FrontEngine.exe --verify-scene-build FIXTURES REPORT`, choosing a new report directory and a native desktop. This fixed test isolates settings in a temporary directory, keeps previews muted, opens only its own scene/editor windows, verifies all seven types, legacy/versioned JSON, export/reload, GIF animation, web interaction, undo/redo, pause/resume and cleanup, then writes result.json and preview PNGs and exits. It executes no supplied Python test scripts. Inspect the report and exit code; unavailable runtime/native rendering fails explicitly.

Choose an identity on the Pet page and open Customize pet, or open it from that pet's menu. Each identity can keep its own size (16–512), speed (1–20), floor/wander/chase behaviour, wall climbing, window sitting, speech bubbles, volume (0–100), settling while typing, automatic rest, throwing and social preferences. Use page defaults inherits the page's presentation settings; cloning and importing retain individual settings. Apply saves atomically before updating the active pet. Cancel changes nothing; Reset defaults only stages changes until Apply. A failed save or conflicting edit retains your draft. Puppet disables unsupported controls and applies only size, speech bubbles and settling while typing among presentation settings. Native wardrobe controls and layered artwork remain unfinished.

Pet identities → Wardrobe opens a separate animated preview for an installed layered character. Install asset folder copies validated layered-pet.json resources into pet-assets beside the local settings. Choose head, neck, body and back items, preview actions and facing, and save up to 20 outfits per identity. Equipping an item replaces whatever shares its slots and names what was replaced; Cancel restores it. Only pieces for the current body type are listed, and pieces missing animations are shown disabled. Trying an item on plays a short outfit show, and Pin for comparison keeps the current look beside the draft. A pet that is being dragged or is mid-interaction switches clothes once it finishes. Pets showing whole-image sprites are told to choose a layered character first. Apply saves and updates the active sprite; Cancel discards edits since the last Apply. Missing resources remain referenced and can be repaired, then rescanned with Refresh. Puppet models do not accept layered Sprite clothing. Add built-in character draws one of six INKSIDE characters (MOCHI, MOSS, PIP, BOLT, INK or GILL) with thirty wardrobe pieces from fourteen outfits fitted to its body, then installs them through the same validation in the background; closing the wardrobe cancels it. Each character offers eye, mouth and three body-part choices plus recolorable regions, and every piece follows all of its animations. Part and garment names follow the interface language. The built-in wardrobe has nineteen outfits in 43 pieces, among them Winter walk, Kitchen, Party, School day and Beach day; every piece fits every built-in body. Opening the wardrobe for a pet wearing a built-in character adds the clothes a newer FrontEngine brought, by itself.

An undressed built-in character with its default parts and colors walks and climbs with hand-drawn whole-body step frames; with clothing or changed parts it uses the layered animation so every piece stays fitted.

Desktop pets always paint through ordinary Qt painting, whatever Overlay rendering is set to: a pet moves its window every tick, and on the GPU path its animation frames stopped changing while it moved.

Pets now settle into poses: Work mode sits, entering Rest plays a short falling-asleep clip and leaving it plays a wake-up clip. Playing, ball and fetch games and tag cost a little energy; below 20 energy an idle pet sits even with automatic rest off, and it still obeys every command. Landing after a drop or throw, grabbing a thrown ball and meeting another pet show brief land, catch and wave reactions without interrupting movement, toys or your commands. Sprite packs without these clips fall back to their idle or sleep images. Grooming ends with a stretch, and pets that keep meeting wave to each other at most once a minute.

Relationships grow with affection through four stages: Just met, Familiar (20), Close (100) and In sync (250). The stage appears in Status. Each stage has its own greeting line, Close pets wave and In sync pets jump for joy, and reaching a new stage plays a one-time celebration; nothing is locked or lost. A saved pet summoned again says welcome back, and Close from the pet’s own menu waves goodbye before the window closes. Puppet pets now separate a click from a drag the same way as Sprite pets: a click greets on release, and only movement beyond the system drag distance moves the window, without rewards.

Customize pet also sets Chatter (Off, Rarely, Normal, Often) for lines the pet starts on its own and Animation size (Calm, Normal, Lively) for the audio pulse and quick land and catch reactions, separately from speech bubbles and volume. Replies to what you do still appear with chatter off. Puppet pets apply Chatter to scheduled script lines. Presentations saved earlier keep working and use Normal for both.

The pet manager's interaction list also offers the selected live pet's own menu commands: photo, status, reminder, chat when a chat service is attached, clone and close, plus every motion and expression of a Puppet model. Everything in a pet's right-click menu can therefore be done with the keyboard.

Use built-in character on the Pet page installs the chosen INKSIDE character and its wardrobe in the background and selects it as the source. Start then spawns an ordinary sprite pet wearing that character: it walks and climbs with the hand-drawn step frames, can be dressed in the wardrobe, and keeps its outfit when it already wears the character. Use built-in Puppet model beside it still makes the Imervue Puppet version.

Use built-in Puppet model on the Pet page draws the chosen INKSIDE character as an Imervue .puppet model in the background: rigged head, arms, tail and body, ten motions, three expressions and a pet script that maps companion actions to them. It is saved under pet-assets/puppets and selected as the source with its script, so Start spawns it as a Puppet pet.

On setups with several monitors at different scaling, a pet dragged or brought back to another monitor keeps its size, stays inside that monitor’s work area and walks there. Window ledges on scaled monitors are measured in the same coordinates as the pet, so it perches exactly on top of windows.

Wardrobe color controls appear for regions declared by the selected character or clothing asset. Choose a region and color, or restore its authored color. Only designated mask layers are tinted; outlines and unmarked details remain unchanged. Colors are previewed before Apply and saved per identity and outfit, including profile export/import. Assets without declared regions have no color controls enabled.

If a pet save fails during close, the pet remains open with its current state and retry timer. Close all retains pets that could not close, and application exit waits for successful pet saves before teardown. Affection stops at the supported save limit so further rewards cannot make the profile unsaveable.

Peer greetings and tag require both pets to be visible, in Play mode, idle, socially enabled and not being carried or settled for typing. Unavailable pets are removed from targets and tag roles. Tag pauses below two eligible pets and resumes when they become available. Disabling speech bubbles only silences greeting text; it does not remove social rewards.

Starting the pet focus timer puts currently visible, idle pets into Work mode; breaks use Rest mode. Stop restores previous modes unless you changed a mode yourself. Each completed focus round awards eligible visible companions 3 affection and 5 mood once; stopping early or hiding a pet gives no completion reward. Work/Rest suppress proactive chatter. The default timer uses monotonic elapsed time, not wall-clock changes.

Focus mode arranges companions in the lower-right work area of their screen when space permits. Stopping restores their previous positions only if you have not moved them or changed their mode.

Layered characters can declare selectable face/body parts. Wardrobe previews part choices per pet; Apply persists them and saved outfits retain the character and parts. Every declared choice must cover every animation frame. Production artwork for the six characters remains unfinished.

The sprite pet menu offers Pet photo: freeze its current appearance or select an authored layered pose, then save a transparent PNG. Captures contain only the pet, without desktop pixels or speech bubbles. Puppet pets also offer a frozen transparent photo through a compatible initialized Imervue renderer; no desktop pixels are captured. Native GL photo acceptance remains pending.

For sprite pets, choose Pet gently, then move the pointer back and forth over the pet. Three deliberate stroke segments start one petting reaction; jitter does not count. Dragging and social play pause during this mode. Leaving, hiding, changing mode or End interaction cancels unfinished petting. Rewards remain subject to completion and cooldown.

Sprite pets offer Throw a ball and Put ball away. Drag and release the ball to throw it again, or right-click it to dismiss. The pet chases the bounded ball and carries it back near its starting point; a completed return grants one affection with a 30-second active-time cooldown. Work/rest, other interactions, hiding, typing-settle or timeout cancel without a reward. Puppet pets can fetch the ball too (see below).

Floor pets leave window ledges to fetch a ball. Window perching pauses during the game and resumes afterward; the return point is on the floor near the original horizontal position.

Play with a light spot adds a small draggable target near the pet. Its range is bounded; floor pets chase along the floor. Release the target and let the pet reach it to start a short play reaction, rewarded only on completion under the existing play cooldown. Right-click the spot or choose Put toy away to stop. Only one ball or light toy can be active per pet.

Cloning uses the selected pet’s own sprite/model, appearance, preferences and asset library, even if the settings page now selects another asset. The clone receives a new identity; later outfit or part edits do not change the original. Puppet clones also retain their source script, parameter values and active expressions.

Eligible focus completion briefly requests the celebrate animation, then returns to Rest. Applying a changed wardrobe briefly requests outfit_show. These two-second active-time reactions add no rewards and are not saved; manual actions or mode changes interrupt them. Assets without those animations use the existing idle fallback. Finished reaction artwork and native Puppet animation mapping remain pending.

Select an active identity and choose Bring pet back to move it into the selected monitor’s work area. Hidden pets become visible, unfinished interactions and toys stop, and sprite physics bounds follow the new screen. Appearance and care values remain unchanged. Inactive pets require Start; oversized pets require a smaller size first.

Puppet scripts may declare frontengine_actions to map companion states to existing model motions and expressions. Names are validated before startup; missing bindings do not guess animations. Completion releases reaction-owned effects while preserving manual choices. See docs/formats/puppet-companion-actions.md. Native visual acceptance remains pending.

Puppet petting now waits for back-and-forth pointer strokes after choosing Pet gently. Leaving, Escape, hiding, changing mode or settling cancels unfinished petting. Dragging is suppressed while petting. Native gesture acceptance remains pending.

Wardrobe style colors offer six quick swatches for the selected declared color region. Preview first, then Apply; Cancel preserves the saved appearance. Free color selection and restoring the region default remain available.

Sprite and Puppet menus now offer four fictional treats without requiring a file drop. They share feeding completion, fullness limits and cooldowns. Feeding ends petting first; unfinished petting gives no reward, and Sprite toys are put away.

Each pet can save a favorite and a different disliked treat in Customize pet. These affect mood only after feeding completes; fullness, affection and cooldown are unchanged. Mid-meal edits affect the next meal. Old profiles remain neutral. Optional food_like and food_dislike artwork or Puppet bindings provide short reactions; production artwork is pending.

Sprite pets offer Come here with a draggable nearby marker. Floor pets approach along the floor; wander/chase pets follow in two dimensions. Arrival triggers a short greeting with the normal greeting cooldown. Right-click the marker or End interaction to cancel. Work/rest, hiding, feeding or a new toy also cancel.

Pet identities now provides an Interaction picker and Perform interaction button for the selected live pet. Keyboard users can greet, pet briefly, groom, choose treats, change play/work/rest mode or cancel. Manager petting uses the same timed care rules without pointer strokes. Hidden or inactive pets show feedback instead of spawning.

Changing the interface language while the wardrobe is open updates its None, Missing and Reset defaults choices without discarding pending colors, parts, outfit names or the preview position. Asset-provided names stay as authored.

For keyboard destination selection, choose Come here in the pet manager and enter horizontal/vertical offsets in logical pixels. Negative values mean left/up. The target is constrained to the nearby work area, and floor mode ignores vertical offsets. Perform interaction starts the call; End interaction cancels it. Busy or unsupported pets keep their current interaction.

Puppet also supports Come here from its menu or the manager’s keyboard offsets. Its window moves toward the marker with the entire pet and marker constrained to the work area. Arrival is measured at the pet center and triggers the shared greeting after half a second. Dragging the pet, care, mode changes, hiding, resizing, screen-area changes or manual model commands cancel the call. A declared walk reaction is used while moving; models without one retain their native appearance. The movement timer runs only during a call. Native GL/focus acceptance remains pending.

Puppet can chase a draggable light spot from its menu. Both Sprite and Puppet managers offer light play with keyboard offsets. Releasing the light near the pet for half a second starts the shared three-second play action; affection is awarded only on completion and follows the normal cooldown. Calls and light play share one target. Put toy away, End interaction, care, manual dragging, mode changes or hiding cancel it.

Puppet pets also offer Throw a ball from their menu, and both Sprite and Puppet managers can throw one for the selected identity. The ball physics, drag-to-rethrow, right-click dismissal, one-affection reward and 30-second cooldown are shared with Sprite; the Puppet window chases, picks up and carries the ball back to its original centre, staying inside the work area. Each rethrow starts a fresh timeout. Ball, light and Come here share one target, so starting one replaces the other. Care, manual dragging, mode changes or hiding cancel without a reward. Authored fetch animation remains pending.

Home settings keeps the mode selector available while manually selected Meeting mode hides the desktop strip. Undo and redo belong to each room; if furniture is unavailable or no longer fits, the current layout and history stay intact for retry. Esc cancels arranging and area painting. Consecutive photos receive separate files. Lifetime events remain recorded after they leave the recent-history list, and paid workstation upgrades survive temporarily missing furniture packs. Older saves can recover only event records they still contain.
