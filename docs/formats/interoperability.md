# FrontEngine / Imervue interchange

FrontEngine reads the version 1 `.puppet` container produced by
[Imervue](https://github.com/JeffreyChen-s-Utils/Imervue).
Install `pip install "frontengine[puppet]"` for its actual Canvas, motion,
expression, idle/input and pet script runtime. FrontEngine owns its windows,
settings and lifecycle; opening a puppet does not instantiate Imervue's PetWindow
or modify Imervue preferences. Sprite images and existing sprite manifests remain supported.

## Puppet container

`.puppet` is a ZIP with `puppet.json`; optional `mimetype` must equal
`application/vnd.imervue.puppet+zip`. The manifest contains integer `version: 1`,
`size: [width, height]`, and lists `drawables`, `deformers`, `parameters`.
Drawable textures reside under `textures/`; named `motions` and `expressions`
reference their JSON members, and optional `physics` references a physics member.
These documents use the upstream Imervue reader/writer unchanged. FrontEngine
passes selected motion/expression names and finite numeric parameter overrides
to that runtime. Select an optional `.petscript.json` via the pet or scene editor
for Imervue's speech, hit-area and scheduled pet interactions.

Containers are validated before optional runtime creation: at most 4096 entries,
256 MiB uncompressed total and 8 MiB per JSON member. Absolute, traversal,
Windows drive, duplicate and symlink members are rejected. Unknown container
versions and missing referenced resources fail explicitly.

## Pet scripts and sprite packs

An optional Imervue `.petscript.json` is a data document loaded by the upstream
`Imervue.desktop_pet.pet_script` engine:

```json
{
  "version": 1,
  "name": "Imeru",
  "greetings": ["Hello!"],
  "time_of_day_greetings": {"morning": ["Good morning!"]},
  "hit_responses": {"head": ["Hi!"]},
  "motion_lines": {"wave": ["Hello!"]},
  "scheduled": [{"every_seconds": 600, "messages": ["Time for a break?"]}]
}
```

Speech lists use the runtime's round-robin selection. Hit-area IDs/motion names
refer to the puppet document. Scheduled entries run while the pet is visible.
Invalid/missing selected script files report a load error before window allocation.
No Python code is stored in these data files.

Existing FrontEngine sprite packs are folders with optional `pet.json` and
state images. Recognized state filename stems are `walk/run/move`, `idle/sit/stand`,
`sleep/zzz/rest`, `climb/grab/wall`, `fall/jump`, `drag/pinch/grabbed/held`, using
GIF, WEBP, PNG or JPEG. Missing states fall back to available idle/walk images.

```json
{
  "name": "Mochi", "size": 96, "speed": 5,
  "climb": true, "talk": true, "sit_on_windows": false,
  "sound": "meow.wav", "lines": {"any": ["Hello!"], "morning": ["Morning!"]}
}
```

Sprite manifest fields are optional; unknown or malformed fields are ignored.
This sprite manifest and the Imervue puppet/script documents remain distinct
formats. FrontEngine's pet UI accepts both, and stores the selected puppet script
in its own preset `puppet_script` field.

## Scene version 1

A `.json` scene accepts the existing object mapping entry names to settings, or
this envelope (the writer emits the envelope). The machine-readable contract is
[`scene-v1.schema.json`](scene-v1.schema.json); runtime checks also enforce finite numbers
and archive path/resource constraints:

```json
{
  "format": "frontengine.scene",
  "version": 1,
  "entries": {
    "pet": {
      "type": "PUPPET",
      "file_path": "assets/imeru.puppet",
      "script_path": "assets/imeru.petscript.json",
      "x": 80, "y": 120, "z": 0,
      "size": [240, 360], "opacity": 100,
      "motion": "idle", "expression": "happy",
      "parameters": {"ParamAngleX": 0}
    }
  }
}
```

`file_path` is required for PUPPET. `script_path`, motion and expression are optional;
parameter overrides default to `{}`. Size contains two integers from 16 to 4096;
opacity is a percentage from 0 to 100; positions/depth/parameters are finite numbers.
`x`/`y` are logical coordinates relative to the selected monitor. A puppet receives
its own native window rather than a QGraphicsProxyWidget. Other scene types remain
supported. IMAGE, GIF and TEXT scenes use the compositor; scenes with web/video/audio
continue using the graphics view. Puppet windows remain separate from the painter layers.

Relative asset paths resolve against the scene's directory and cannot escape it.
Legacy absolute JSON file references remain usable. JSON exports reference existing
assets; distribute a `.fescene` when recipients need a self-contained copy.

`.fescene` is a ZIP containing `scene.json` with the same envelope and copied
`file_path`/`script_path` assets under `assets/<number>/<filename>`.
The writer deduplicates shared sources and atomically replaces the output only
when all resources have been written and validated. Import enforces the puppet
archive resource/path limits, rejects references outside the package, and keeps
extracted resources alive until application shutdown. A `.puppet` can also be
opened directly as a single-entry scene. FrontEngine scenes can reference Imervue
puppets; Imervue does not read FrontEngine's entire scene envelope.

## Plugin permissions version 1

For `plugins/example/plugin.py`, place `plugin.json` beside the entrypoint.
For `plugins/example.py`, use `plugins/example.json`:

```json
{
  "version": 1,
  "api_version": 1,
  "id": "example",
  "entrypoint": "plugin.py",
  "permissions": ["ui", "filesystem"]
}
```

Available declarations: `filesystem`, `network`, `screen_capture`, `microphone`,
`native_code`, `clipboard`, `input`, `ui`. The entrypoint must match the actual
filename and contain no directory components. Existing `FRONTENGINE_TABS` and
`register(registry)` entrypoints remain supported. Loading is disabled by default.
Before import, FrontEngine requests a grant bound to the plugin ID, absolute
location and SHA-256 package contents; changed code requires a new grant.
Manifest-free legacy plugins require an explicit `full_trust` grant.
Settings import/export cannot transfer authorization. Revocation prevents future
loads; restart to unload already running plugin code.

These declarations and consent gates are not an operating-system sandbox.
An approved Python plugin executes with FrontEngine's application privileges;
declared capabilities are review information rather than per-call restrictions.

## Runtime boundaries

Region GIF recording encodes and flushes frames on a worker using a bounded
queue and memory budget; slow writes drop frames and retain timing. Stop finalizes
asynchronously; successful completion atomically replaces the selected target.
Cancel/error removes the temporary file and preserves an existing target.

Remote control uses HTTPS with a persistent self-signed certificate and a token.
Export/trust the certificate and compare its SHA-256 fingerprint on the phone;
renewal changes the fingerprint. HTTP has no fallback. Local OCR tries Windows
Media OCR, macOS Vision, then installed Tesseract. Recognized text and screenshot
cloud fallbacks require separate consent; an empty local result is still success.

Overlay rendering offers auto/GPU/software and reports the actual backend and
fallback reason. GPU composition uses textures with transforms, alpha, clipping
and depth. Painter content rasterizes on CPU; this is not a zero-copy capture path.
`BaseWidget.output_frame()` and `SceneCompositorView.output_frame()` return QImages
for integrations. Static raster content and texture uploads are cached.

macOS 13+ uses ScreenCaptureKit, public Accessibility, AVFoundation, CoreMIDI and
Quartz APIs through the `macos` extra. Screen Recording, Accessibility, Input
Monitoring and Microphone authorization are reported in Settings. Cross-display
capture regions and foreign-window alpha/topmost, Spaces control and capture
exclusion are explicitly unsupported. Windows verification does not establish
real Mac hardware or TCC behavior; use `tests/integration/macos_native_smoke.py`
on the target Mac to verify the actual host.
