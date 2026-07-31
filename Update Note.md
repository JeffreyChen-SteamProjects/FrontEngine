# Update Notes

## 31 July 2026 — A new interface, seven new pages, and a lot of automation

*Covers everything since the 8 February 2026 release. Current version: 1.0.59.*

FrontEngine started out as a way to put a video, an image or a web page on top of
your screen and leave it there. It still does that, and nothing about the way you
do it has changed. What has changed is how much else it can put on screen, and how
much of it can now happen without you.

This is the largest update the project has had. A rebuilt interface, seven new
pages, a preset system that travels between machines, automation that reacts to
what you are doing, and a full pass over privacy for anyone who shares their
screen for a living.

---

### The interface has been rebuilt

This is the first thing you will notice. FrontEngine had grown to sixteen tabs in
a single row, which sprouted scroll arrows as soon as the window narrowed and gave
no clue which of the sixteen belonged together.

The pages now live in a grouped list down the left-hand side — **On screen**,
**Desktop**, **Work**, **Control** — so finding the right one is a matter of
knowing what you want to do rather than reading sixteen words in a row. It cannot
overflow, and you can always see where you are.

Each page was rebuilt too. Settings are grouped under headings instead of sitting
in one flat list, related controls line up, and sliders no longer stretch to the
full width of the window. The button that actually does the thing — Start, Spawn,
Close all — now sits in its own bar at the bottom of the page and looks different
from everything else, so it is obvious which control is the one you came for.
Nothing was removed and nothing moved to a different page: the same settings are
in the same places, arranged so you can see them.

---

### A pet that lives on your desktop

The **Pet** page is the headline of the new pages. Point it at a single image for something simple,
or at a folder of walk / idle / sleep / climb / fall / drag frames for a pet that
animates properly.

It walks the floor, wanders freely, or chases your cursor. It climbs window edges
and sits on the top edge of your windows. Spawn it more than once and two or more
pets will play tag with each other. Drop a file onto it to feed it; drop an image
or a pet pack onto it to change how it looks.

It talks, too — short remarks as the day goes on, when it is fed, and so on — and
it can read those aloud. It can move in time with your speakers or your
microphone, and it will keep a focus timer for you, with breaks. If you supply
your own Anthropic API key, you can hold a conversation with it.

### Six more pages

**Eye Care** — a warm, amber, rose, yellow, green, blue or grey wash over the
screen with adjustable strength; a reading ruler that follows the cursor; eye
breaks that dim the screen after so many minutes; and colour-vision simulation
(protanopia, deuteranopia, tritanopia, achromatopsia) for checking that a design
still reads.

**Presenting** — draw over whatever is on screen with a pen, highlighter and
eraser, with undo. Ring the pointer, ripple your clicks, or spotlight everything
but the cursor. Show the keys you press for recordings. A magnifier from 1.5x to
6x. And an endless whiteboard you can pan and zoom, which saves an image of the
area you actually drew on.

**Wallpaper** — a rotating wallpaper that sits below every window, per monitor,
from 30 seconds to an hour per image, with shuffle and nested folders. It can
react to what your speakers are playing, and switch to a calmer folder during the
quiet hours you set.

**Focus** — dim every window except the one you are working in, or cover a single
distraction: the taskbar strip, a corner, an edge, or the whole screen.

**Widgets** — an audio spectrum as bars or a ring, a CPU / memory / disk / network
panel, the track your media player is on, and sticky notes that can come back the
next time FrontEngine starts.

**Tools** — measure things and have the answer land on your clipboard: a colour
picker that copies as `#rrggbb`, `rgb()`, `hsl()` or a CSS custom property, a pixel
ruler, and a protractor. Capture a region. Record part of the screen, optionally
with the camera in the corner. Show any video input — including capture cards — as
a circle, rounded rectangle or rectangle. Pin another application's window on top
and change how see-through it is. Save where your windows are and put them back
later. Read the text in a region to copy, translate or ask a question about it.
And send an area of your screen, overlays and all, as a webcam that Zoom, Teams or
Discord can pick as their video source.

---

### Presets that travel

Save everything the pages are set to under a name, and load it back later. Export
one as a json file to move it between machines, or export a package with the
images, videos and sounds it refers to as a zip. Pick one to apply automatically
at startup. Content you subscribe to on Steam can be imported directly.

### It can now run itself

* **Hotkeys** — global shortcuts for hide all, show all, close all, mute all,
  opacity up and down, next dashboard page, and lock.
* **App profiles** — apply a preset automatically when a given application comes
  to the front.
* **Smart pause** — put the overlays away while a fullscreen application is
  running, while on battery, or while named applications have focus.
* **Signage mode** — rotate through a list of presets on a timer, for a machine
  left running as a display.
* **Scheduled day/night theme**, **start with the system**, **restore last
  session**, and **reminders** on an interval or at a time of day.
* **Remote control** — drive FrontEngine from a phone on the same network, and
  bind a MIDI controller.

### A Control Center that reaches everything

One page that reaches every overlay, whichever page opened it: close by kind or
close all, hide and show, mute, lock and unlock, reset positions, and chroma key
for keying in OBS. Unlocked overlays can be dragged into place and remember where
you dropped them. Low power and a High / Balanced / Saver quality setting cut
refresh rate and render resolution when the battery matters.

### Privacy, taken seriously

* **Hide from capture** keeps overlays on your own screen but leaves them out of
  what a screen share records.
* **Screen-sharing privacy** does that automatically while a meeting application
  is open, matched on window titles so a meeting held in a browser tab is caught
  too.
* **Screen time** stays on your machine and is never sent anywhere.
* **Clipboard history** is kept in memory unless you explicitly ask for it to
  persist, because clipboards so often hold passwords.
* Audio-reactive features read a **level** — a single number — and never capture
  what is being said. The audio spectrum does capture audio to compute
  frequencies, in memory only; nothing is recorded or sent, and capture stops when
  you stop the spectrum.
* The features that use Anthropic's API ask for consent first and use your own
  `ANTHROPIC_API_KEY`, which is never stored.
* The phone remote carries a one-time token that changes at every start, and only
  the buttons on the page can be triggered. It is plain HTTP — leave it off on
  networks you do not trust.

### Seven languages, switched live

English, Traditional Chinese, Simplified Chinese, German, Russian, French and
Italian. Changing language no longer needs a restart — the whole interface
re-labels itself in place.

If you installed through Steam, the first launch now follows the language your
Steam client is set to, so it opens in your language rather than in English and
you do not have to go and find the setting. It happens once: after you pick a
language yourself, yours is the one that is used. Steam is read locally — no
account, no network, nothing leaves the machine.

### A guide inside the application

**Help → How to use...** now explains your first overlay, the settings every page
shares, and how to clear the screen again, without sending you to a website.

---

### Notes

* Clicks still pass straight through an overlay, so the window underneath keeps
  working. The two exceptions are the pet and the drawing layer on the Presenting
  page while drawing is switched on.
* Some features depend on Windows APIs and are marked as such in the application:
  audio-reactive overlays, the audio spectrum, pinning another window, hiding
  overlays from capture, and screen-sharing privacy.
* The virtual camera needs the optional `pyvirtualcam` package and a virtual
  camera driver. Without either, the button tells you so.
* **F12 closes FrontEngine at once**, from anywhere.

### Under the hood

Upgraded to PySide6 6.11.1. The static-analysis debt is cleared and the test suite
now runs headless in CI, which builds and installs a package from the checked-out
source so the start-up tests exercise the code in front of them rather than the
one already published.
