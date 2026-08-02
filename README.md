# FrontEngine

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

Python **3.10+**. Windows 10/11 is the primary target; macOS and Linux run the
app, with the platform differences listed under [Platform support](#platform-support).

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
> outright** from anywhere (Windows only — see *Help → How to force close*).

---

## What it puts on screen

The sidebar groups the pages by what they are for. This section follows it.

### On screen

Media overlays. Each one picks its monitor (or spans all of them), remembers
where you dragged it, and has its own opacity.

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
- **Record area** — record a region to an animated GIF, with the camera
  composited into the corner for the reaction-video look. Capped by both length
  and frame count, because every frame is held in memory.
- **Camera** — your webcam in a circle, rounded box or rectangle, shown locally
  and never recorded. Any video input works, including capture cards, and the
  device list refreshes without a restart since cards are usually plugged in
  while the app is already running.
- **Virtual camera** — send a region, overlays and all, as a webcam that Zoom,
  Teams or Discord can select as their video source. Needs the optional
  `pyvirtualcam` package and a virtual camera driver (OBS installs one); without
  either, the button says so rather than failing quietly.
- **Read text** — drag out an area to copy the text in it, translate it, or ask
  a question about it. This one sends the selection off the machine; see
  [What leaves the machine](#what-leaves-the-machine).
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
| `F12` | Quit immediately (Windows) |

Media transport sends the system media keys, so it reaches any player that
listens for them. Moving a window keeps its proportions rather than snapping it
across, which is what Windows' own `Win+Shift+Arrow` does.

The same actions — and nothing beyond them — are what the remote controls drive:

- **Your phone** (Settings → Remote control) — FrontEngine serves a small page on
  your local network; open the link on a phone and the buttons drive those
  actions.
- **A MIDI controller** — press *Learn*, move a knob or pad, and bind it. It uses
  Windows' built-in winmm, so no extra package is needed. A knob fires once it
  reaches the top rather than repeatedly on the way, and releasing a pad does not
  count as a second press.

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
| **Read text** (Tools) | The selected region is sent to Anthropic's API | Asks once before the first send and remembers the answer; consent can be withdrawn from the result window. Uses your own `ANTHROPIC_API_KEY`, read from the environment and never written to a settings file. Nothing is sent without both. |
| **Pet chat** | Your message goes to Anthropic's API | Same key, same rule; off by default. |
| **Weather** (text source) | Coordinates go to Open-Meteo | No key, no account, no identifying data; only what you typed as a location. |
| **Phone remote** | Serves a page on your local network | Off by default. The link carries a token regenerated on every start, so an old link stops working, and the page can only ask for the fixed action list. It is plain HTTP: someone else on the same network could read the token and press the same buttons — a nuisance rather than a breach given what those buttons do, but leave it off on networks you do not trust. |

The audio features read only an output **meter** — a single number — except the
spectrum, which needs real samples to compute frequencies and so captures the
system output stream. Those samples are analysed in memory, never written to
disk or sent anywhere, and capture stops the moment you stop the spectrum.

**Plugins** are Python and run with the same privileges as FrontEngine — they
cannot be sandboxed. Loading is off by default (Settings → Load plugins), every
load is logged, and one broken plugin is skipped rather than stopping the app.
Install only plugins you trust.

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
| Overlays, pet, wallpaper, presenting, screen care, capture, recording | ✅ | ✅ | ✅ |
| Audio reaction, spectrum, lip-sync (WASAPI) | ✅ | — | — |
| Now playing (media controls) | ✅ | — | — |
| Pin / fade another window, window layouts, live replica | ✅ | — | — |
| Hide overlays from screen capture | ✅ | — | — |
| MIDI control (winmm) | ✅ | — | — |
| Media transport keys | ✅ | — | — |
| Pin overlays to a virtual desktop | ✅ | — | — |
| Move a window to the next monitor | ✅ | — | — |
| `F12` emergency exit | ✅ | — | — |
| Dim background around the *active* window | ✅ | whole screen | whole screen |
| Pet standing on other windows | ✅ | — | with `wmctrl` |

Where a feature cannot work, the button says so rather than failing quietly.

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

Static checking uses pyflakes (`pip install pyflakes`), and a clean tree prints
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
- **Documentation** — Sphinx sources in `docs/`, published to
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) in all seven
  languages.

---

## Continuous integration and releases

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR to `main` or `dev`, or called by `Nightly` | Compile, run the unit tests, then build a wheel from *that checkout*, install it and start the app — on Python 3.10 / 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Daily cron, manual dispatch | Calls `CI`. The schedule lives here on purpose: GitHub disables workflows containing a cron after ~60 days of inactivity, and that would otherwise take the PR checks down with it |
| `Release` (`release.yml`) | A pull request is merged into `main`, or manual dispatch | Bumps the version, commits it back with `[skip ci]`, swaps `stable.toml` → `pyproject.toml`, builds sdist + wheel, uploads to PyPI as `frontengine`, and creates a GitHub release tagged `v<version>` |

Publishing happens **only on merge to `main`** — pushing to `dev` runs CI and
never publishes. The patch segment bumps automatically; for a minor or major
release, run *Actions → Release → Run workflow* and pick the segment. That path
also re-runs a failed publish without needing a new merge.

Versions live in two files: `pyproject.toml` is the dev package
(`frontengine_dev`) and `stable.toml` is the published one (`frontengine`).

One repository secret is required: `PYPI_API_TOKEN`, a PyPI token scoped to the
`frontengine` project. The workflow uses `__token__` as the twine username, so
only the token itself needs storing.

---

## License

See [`LICENSE`](LICENSE). Community expectations are in
[`Contributor_Covenant_Code_of_Conduct.md`](Contributor_Covenant_Code_of_Conduct.md).
