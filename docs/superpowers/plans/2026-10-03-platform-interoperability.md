# Platform interoperability implementation plan

> **For agentic workers:** Use superpowers:executing-plans and superpowers:dispatching-parallel-agents for independent file ownership. User approved direct implementation; continue without intermediate approval gates.

**Goal:** Implement the eight approved recording, security, offline recognition, interoperability, platform and rendering changes.
**Architecture:** Keep existing Qt pages and add focused services/adapters. Separate native capabilities and shared puppet runtime from file validation. Each independent domain has exclusive file ownership; root integrates UI and shared documentation.
**Tech Stack:** Python 3.10+, PySide6 6.11.2, NumPy, OpenGL, cryptography, platform OCR bindings, optional Imervue runtime.
**Spec:** `docs/superpowers/specs/2026-10-03-platform-and-interoperability-design.md`

## Global constraints

- Preserve old GIF, pet packs, scenes and presets. Unknown external data is rejected before execution.
- Recording queue: three frames and 64 MiB maximum; stop/finalize without blocking Qt.
- HTTPS only; cloud OCR requires explicit consent; local extraction requires neither consent nor API key.
- Imervue is an optional installed runtime, never imported using developer-specific paths.
- macOS native backends use public APIs; unsupported foreign-window changes remain explicit limitations.
- Plugin declarations describe trusted in-process code, never claim OS sandbox enforcement.
- Software rendering remains available when OpenGL cannot initialize.
- Keep README variants, seven documentation trees, architecture maps and dependency lists aligned.
- Never stage the user's existing SDK or other unrelated changes.

## Review focus

1. Closing during recording must neither block Qt nor replace a valid target with partial output.
2. Empty OCR success must not upload a screenshot; declined consent must prevent every cloud path.
3. Changed plugin code or grants must be checked before import side effects execute.
4. Puppet assets with traversal, symlinks, malformed version or bad references must fail before runtime loading.
5. GPU/context failure and denied macOS permissions must report real capability instead of apparent success.

## Task 1: Incremental recording

Files: `utils/recording/gif_writer.py`, `frame_recorder.py`, `ui/page/tools/tools_setting_ui.py`, `tests/unit_test/test_recording.py` (under `frontengine/` where applicable).
Interfaces: incremental GIF writer; `FrameRecorder.frame_count`, output path, asynchronous finished/error signals. Capture QPixmap on Qt thread; transfer copied RGB to bounded writer queue.
- [x] Add and run failing tests for live writes, decoder round-trip, queue limits, I/O failure and cancellation.
- [x] Implement writer and recorder lifecycle, with target selected before capturing.
- [x] Run recording/tools tests; root runs full suite and checks docs before stage commit.

## Task 2: HTTPS remote

Files: `frontengine/utils/remote/tls_certificate.py`, `remote_server.py`, `frontengine/ui/dialog/remote_control_dialog.py`, remote tests.
Interfaces: certificate provisioning returns certificate/key/fingerprint; server URL uses HTTPS and exposes public certificate export.
- [x] Run failing tests for a real trusted TLS request and rejected token.
- [x] Implement SAN-aware self-signed credentials, TLS-only startup, renewal/export, private key protection.
- [x] Run remote tests and report dependency additions to root.

## Task 3: Local-first OCR

Files: `frontengine/utils/screen_text/local_ocr.py`, `screen_text_service.py`, `frontengine/ui/dialog/screen_text_dialog.py`, screen-text tests; root owns tools-page integration after Task 1.
Interfaces: structured local result distinguishes unavailable, failure and empty success; service exposes extraction capability and selected backend.
- [x] Run failing tests for local success without key/consent and zero network calls on empty results.
- [x] Implement Windows OCR, macOS Vision and optional Tesseract adapters; text-first cloud translation/questions.
- [x] Update result UI and provide root with tools-page integration instructions; run service tests.

## Task 4: Puppet pet and scene interchange

Files: `frontengine/utils/imervue/`, `frontengine/show/pet/puppet_pet.py`, `frontengine/ui/page/pet/pet_setting_ui.py`, `frontengine/utils/scene_format/`, scene IO/manager/factory files, interchange tests.
Interfaces: validated `.puppet` asset, lazy runtime loader, FrontEngine-owned pet lifecycle; `normalize_scene(data, base_dir)` returns legacy-compatible entries including PUPPET.
- [x] Run failing tests for future versions, traversal and valid real sample, old scene compatibility and scene round-trip.
- [x] Implement archive checks and optional Imervue canvas adapter with motion/expressions/script support.
- [x] Add pet UI/drop, PUPPET scene/preset entry, relative asset resolution and versioned export.
- [x] Test with the actual installed reference runtime and `D:/Codes/Imervue/examples/puppet/imeru.puppet` where available; record GL limitations.

## Task 5: macOS native capabilities

Files: `frontengine/utils/macos/`, platform/audio/window/media/MIDI/critical-exit modules as needed, macOS backend tests. Root owns dependencies, CI and docs.
Interfaces: capability/permission status, public-framework window geometry, ScreenCaptureKit frames/audio, native actions; inject external sources for tests.
- [x] Run failing tests for native routing, denied permission and unavailable bindings.
- [x] Implement public API backends and wire existing features; distinguish unsupported Space/opacity/foreign stacking.
- [x] Test on Windows with injected framework boundaries; add real macOS test instructions and CI.

## Task 6: Plugin declarations

Files: `frontengine/utils/plugins/plugin_manifest.py`, `plugin_loader.py`, `frontengine/ui/menu/settings_menu.py`, plugin tests.
Interfaces: immutable validated manifest and content digest; load authorization checked before Python import.
- [x] Run failing tests showing unauthorized plugin import side effects never happen and code changes revoke grants.
- [x] Implement fixed permission vocabulary, manifest/sidecar parsing, digest-bound grants and explicit legacy full-trust approval.
- [x] Wire load-time UI prompts, revocation and stored grants; run workshop/plugin tests.

## Task 7: GPU compositor

Files: `frontengine/show/compositor/`, `frontengine/show/base_widget.py`, compositor tests; root owns scene integration.
Interfaces: layers with image/transform/z/opacity/clip, actual GL shader renderer and raster fallback; shared frame output.
- [x] Run failing tests for composition order, alpha/transform/clip and missing context fallback.
- [x] Implement texture/shader composition, resource lifetime and backend choice; adapt existing painter overlays.
- [x] Integrate scene primitive path without embedding arbitrary native widgets into OpenGL viewport; run real GL smoke when available.

## Task 8: Integration, documentation and validation

Files: dependencies, README plus nine translations, seven Sphinx trees/dictionaries, both architecture maps, `progress.md`, update log/index, macOS CI; Imervue architecture §6 when interface is ready.
- [x] Reconcile tools-page recording/OCR hooks and shared shutdown behavior.
- [x] Document formats, setup/trust/permissions/backend status and platform limitations in all supported languages.
- [x] Run `py -m pytest tests/ -q`, `py -m pyflakes frontengine/ exe/ tests/`, `py -m sphinx -W -b html docs/source <temporary output>` and build/install wheel.
- [ ] Review changes against spec with an independent reviewer, correct failures, commit completed stages, and return changes to the original workspace preserving user edits.


Validation boundaries: Windows real TLS, OCR and desktop OpenGL/puppet checks were exercised; macOS public API routing/lifecycle are covered through injected frameworks and a target-host smoke script. Actual macOS hardware/TCC behavior remains progress.md #9. Final verification counts and commit integration are recorded in docs/updates/2026-10.md.
