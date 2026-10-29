# Software scene composition benchmark

Run from the repository root with runtime requirements installed:

```powershell
git show a090ebe:frontengine/show/compositor/widget.py | Set-Content -Encoding utf8 build/compositor-baseline.py
py -m benchmarks.scene_composition --baseline-file build/compositor-baseline.py --output build/scene-benchmark.json
```

The baseline file executes Python. Use only a trusted export from your own checkout.
Without `--baseline-file`, the command measures the current implementation alone.
This is a developer tool, not a published entry point or CI timing assertion.

The seeded fixture has twelve 320×180 translucent layers on a 1280×720 logical
surface. Each implementation warms up twenty frames and measures seven rounds
of eighty `set_layers` plus `output_frame` calls. Static layers stay unchanged;
changing mode fills the first image with a new color before every frame.
Final raw image SHA-256 hashes must match exactly, including premultiplied alpha.
This measures software composition and layer submission, not complete app FPS,
video decode, GPU rendering/readback, display refresh, or startup time.

Recorded native Windows results: [2026-10-08-scene.json](2026-10-08-scene.json).
The screen was one 125% monitor: 1600×900 physical output. Static baseline work
recomposed the same unchanged frame on every read; the current implementation
retains one software frame and avoids unchanged repaint submissions. Dynamic
work still recomposes; differences within a few tenths of a millisecond are
run-to-run noise. Memory retains one cached frame up to 16 MP; larger surfaces
are rendered without this cache. Caller image mutations use Qt copy-on-write.

Plugin example: copy `examples/plugins/clock` to `plugins/clock`, enable plugin
loading and approve its content digest. Manifest `version: 1` and `api_version: 1`
are supported. Other API versions are rejected before code import. API v1 uses a
no-argument QWidget page constructor and `FRONTENGINE_TABS` or `register(registry)`.
Use unique page names. Optional contracts:

- `overlay_widgets`: dynamic live list; participates in hide/show/mute/lock/quality
  and close-all/app shutdown. Overlays release their media, timers and native
  handles in `closeEvent` before lists or resource leases are cleared.
- `release_overlay_resources()`: reusable batch cleanup, allowing future overlays.
- `shutdown()`: idempotent final page cleanup after overlays have closed.
- `get_state()` / `set_state(dict)`: bounded JSON settings stored under
  `plugin:<page name>` in presets for currently loaded pages. Validate before
  mutating; version preview/restore includes transactional rollback. Presets do
  not discover, import, enable or authorize plugins.

State schema and migrations are the plugin author's responsibility. Manifest API
compatibility does not promise compatibility with arbitrary private app imports.
Python plugins execute with the application's privileges; permissions and digest
grants express trust, not an OS sandbox. Example captions are intentionally
plugin-owned text, independent of the application's language dictionaries.

# Desktop pet benchmark

```powershell
py -m benchmarks.pet_performance --output build/pet-benchmark.json --seconds 30
```

`--output` names the JSON result file; only its file name is used and it is always written under `build/`. It installs the built-in MOCHI into a temporary library and runs four scenarios: one and four pets, each as a plain 128-pixel legacy sprite and as MOCHI wearing three garments. Each scenario shows the pets with their normal timers. After a one-second warm-up, it records:

- process CPU over the measuring window (Windows process time ticks about every 16 ms, so use at least 30 seconds);
- working-set growth;
- the median and p95 of 400 calls to each pet's own `draw_content`: composition, mirroring and painting its content.

`QWidget.render` is deliberately not timed, because it forces a framebuffer readback from the overlay's OpenGL compositor that the screen never pays and that is identical for every kind of sprite.

The enhancement plan named no figures, so the budgets are stated in the script and checked in the output:

- p95 frame work of 4 ms;
- 8% CPU for four layered pets;
- 80 MB more for four layered pets than for four legacy pets.

Recorded native Windows results (one 100% monitor, 30 seconds): [2026-10-29-pets.json](2026-10-29-pets.json).

- **Frame work:** a layered pet takes 0.04 ms per cached frame and about 1.2 ms (p95) when an animation frame recomposes; a legacy sprite takes 0.005 ms.
- **CPU:** under 1% for four layered pets.
- **Memory:** four layered pets use about 33 MB more than four legacy pets. The first scenario's growth also includes one-time Qt and OpenGL setup.

This does not measure display refresh, the GPU compositor or mixed-DPI multi-monitor setups.
