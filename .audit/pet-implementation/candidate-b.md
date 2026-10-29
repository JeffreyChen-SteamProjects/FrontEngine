# Candidate B — thin QObject interaction coordinator

## Grounding and decision

`DesktopPetWidget` currently owns `PetMood`, `PetHunger`, `PetGrowth`, `PetMotion`, sprite playback and input events. Its mouse press grants mood and affection before it can tell a click from a drag. `feed()` always grants the food effect, even when full. The chatter timer both decays stats and shows speech, so turning talk off also stops decay. `PetProfileSession` holds the active UUID lease and debounces stats through a reader; `PetProfiles` owns strict version 1 validation and a rollback around `write_user_setting`. Puppet feeding writes the same profile directly. `PetSettingUI` owns the existing focus timer and typing watcher. Those are existing responsibilities to integrate, not parallel services to recreate.

Build a small per-pet `PetInteractionController(QObject)` that decides whether an intent is allowed, changes the *existing* stat objects, and emits a presentation request. Keep motion, rendering, typing observation, focus timing and identity lease where they are. The controller has no second mood/fullness/affection fields and does not serialize a shadow copy. A lightweight `InteractionActivity` holds only `mode`, current short action, and cooldown receipts. This is deliberately narrower than a general state machine: mode changes and short actions are orthogonal, and the controller resolves their presentation priority at one point.

## Caller-first sketch

```python
# DesktopPetWidget and control center call the same intent path.
result = pet.interactions.request(Feed(food_kind=kind, event_id=event_id))
result = pet.interactions.request(Groom(event_id=event_id))
result = pet.interactions.request(Play(toy_id="ball", event_id=event_id))
result = pet.interactions.request(SetMode(mode=PetMode.WORK))
result = pet.interactions.request(SetMode(mode=PetMode.REST))

# A release below QApplication.startDragDistance is a greeting;
# crossing it begins a drag and never emits a greeting for that press.
pet.interactions.pointer_pressed(global_pos)
pet.interactions.pointer_moved(global_pos)
pet.interactions.pointer_released(global_pos)

# The existing focus timer supplies a stable completed-session ID.
pet.interactions.focus_completed(session_id)
```

`request()` returns a bounded `InteractionResult(accepted, reason, presentation)`; refusal reasons include `full`, `cooldown`, `busy`, `unsupported`, `low_energy`, and `asset_missing`. The caller can show the response without inspecting policy. The controller emits `stats_changed`, `activity_changed`, and `presentation_requested` signals. It accepts a monotonic clock for cooldown calculations. GUI callers only invoke it on the Qt thread.

## Ownership and module map

| Module | Owns | Does not own |
| --- | --- | --- |
| `pet_interactions.py` | `PetInteractionController`, intent types, cooldown/event receipts, mode and short-action arbitration, feed/groom/play effects | Numeric stat copies, image assets, disk format, focus timer |
| `desktop_pet.py` | `PetMood`, `PetHunger`, `PetGrowth`, `PetMotion`, existing sprites and Qt event translation | Reward rules or independent cooldowns after migration |
| `pet_profile_session.py` | One active UUID lease, debounced stat snapshot, coordination of durable outfit apply | Outfit validation or duplicated runtime stats |
| `pet_profiles.py` | Versioned profile parsing, migration, bounds, single-record atomic commit, export/import validation | Qt widgets or loaded image objects |
| `pet_wardrobe.py` (later) | Garment compatibility and detached preview draft; validates slot, body, action, layers and missing assets | Persistent identity or stat rewards |
| Sprite/Puppet capability adapter (later) | A small capability query and presentation command translation | Shared policy or fabricated capability |

The controller receives references to the live `PetMood`, `PetHunger`, and `PetGrowth` instances plus an `Energy` object when that field lands. It invokes their existing mutation methods; the widget connects `stats_changed` to `profile_session.schedule()` and existing growth resize. `PetGrowth.THRESHOLDS` remain unchanged. Consider moving these stat classes to a small non-widget module only when adding another controller consumer, then migrate every import in the same change. Puppet can use a profile-backed stat adapter at first; do not give it a second copy that later flushes over another writer.

`PetPresentationPort` is a narrow capability adapter: `supports(action)`, `show(action, on_finished)`, `set_mode(mode)`, `cancel(action)`. Sprite maps known actions to existing six-state fallbacks until new frames exist. Puppet reports only documented native motions/expressions; unsupported wardrobe operations stay unavailable. `show()` is a presentation request, not proof that an asset exists; capability validation precedes reward-affecting actions where animation is required. An action completion callback checks the current action token so a late animation cannot restore an obsolete mode.

## First implementation unit: five UI actions

Wire menu and management-page actions through `request()` for feed, groom, play, work, and rest. Keep the existing right-click menu and focus/typing controls. There is one user-visible action method per intent; drag-drop food calls the same feed path after classification, and timeline feed does too. Remove direct stat changes from the old widget `feed()` rather than retaining an alternate reward route. Existing `change_sprite()` remains the legacy whole-sprite replacement route; new wardrobe preview/apply grants no affection.

| Intent | First-unit policy and result |
| --- | --- |
| Feed | Accept only if fullness is below `FULL` threshold (currently 60), no feed action is active, and the per-pet feed cooldown has expired. Apply `FOOD_EFFECTS` once, clamp via existing stat objects, save schedule once, play eat or fallback. When full, return `full` with a gentle response and zero stat change. The food kind must come from validated snack/drop classification, never file contents. |
| Groom | Optional short, skippable action. Grant at most one small mood/affection reward on accepted completion; no cleanliness meter. Cooldown prevents menu spam. Grooming a robot uses the same intent with a different presentation. |
| Play | Verify energy and capability, then begin one bounded toy action. Spend energy and grant mood/affection once at completion; cancellation before completion grants nothing. Existing tag game is a separate adapter and exits on rest or drag. |
| Work | Set persistent runtime mode `WORK`; settle/limit wandering and chatter via existing motion/typing integration. Re-selecting work is idempotent. Focus timer remains in `PetSettingUI`; its phase signal may select work and grant one completion reward keyed by session ID. |
| Rest | Set runtime mode `REST`, cancel lower-priority play/peer actions, show sleep. Manual wake selects the prior non-rest mode or a defined default. Auto rest is a preference, never mandatory; no offline decay or recovery simulation. |

Proposed initial cooldowns are feed 30 seconds, groom 60 seconds, play 30 seconds, greet 5 seconds, peer greeting 60 seconds per unordered UUID pair. These are prototype constants to tune from observed interaction, not claims of validated timing. Use `monotonic_ns()` for in-process cooldowns and an event receipt for each accepted action. Menu double activation and duplicate focus completion IDs are idempotent. Persistence may store bounded completion IDs for focus rewards if those rewards must survive restart; wall-clock changes never recreate a reward. Do not record mouse coordinates or a running animation in the profile.

Put care decay on a dedicated elapsed-time timer, independent of chatter. Speech, sound, animation amplitude and unsolicited speech each read separate preferences. On launch, start care ticks without applying missed offline ticks. At low energy, idle weights and optional auto rest change; feed/groom remain usable. Priority is close/error, direct input, active short interaction, mode, idle. A drag interrupts a lower-priority action and does not grant a click reward. A click is recognized on release below Qt's drag threshold; explicit petting mode suspends drag until Esc/end. Every interaction returns to the saved mode after its short presentation, unless that mode changed meanwhile.

## Profile evolution and wardrobe transaction

Keep `pet_profiles` as the single storage envelope. Add envelope `version: 2` (or `schemaVersion: 2` consistently, not both), then a strict v2 record validator. Read v1 records without writing; migrate all records to v2 in a detached copy on the first successful mutation. Preserve each UUID, name, mood, fullness and affection exactly. Initialize energy to a neutral default, mode to a runtime default (do not persist an in-flight mode), preferences from explicit defaults, character ID only when an asset binding is known, and an empty equipment map. Preserve the existing one-time shared-legacy-stat migration flag. If validation or save fails, retain the original v1 envelope in memory and on disk. Keep import/export `frontengine.pet-save` version 1 support and add version 2 with bounded IDs and no bundled third-party art.

Suggested v2 record shape: existing five fields plus `energy: int`, `characterId: str | None`, `equipped: {head, neck, body, back}` containing stable garment ID/version refs or null, `savedOutfits: list` capped at 20, and `preferences: {autoRest, sound, bubbles, animationScale, proactiveSpeech}`. A personality/preference variant can be an optional validated ID, not an arbitrary script. Missing asset refs remain in `equipped` and render as base appearance with a visible missing-item state. Legacy single-image/GIF/WebP/six-action packs continue as whole outfits and cannot be mixed into slots. The catalog's six body types and fourteen outfit concepts are asset plans, not entries to mark compatible until actual layers and action coverage exist.

Wardrobe preview is a detached `WardrobeDraft(profile_id, baseline_equipped, candidate_equipped)` with its own renderer/clock lifecycle. `cancel()` discards it. `apply()` validates compatibility, resolves/loads all candidate layers, then calls one `PetProfileSession.apply_outfit(expected_baseline, candidate)` operation. That operation flushes pending stat changes into the same proposed record and asks `PetProfiles.update` for one atomic write; only after persistence succeeds does the live renderer swap at a safe animation boundary. If the visual swap can fail after save, stage the complete composite before committing and retain the old composite for rollback or a compensating commit; do not show a new appearance against an old save. Concurrent wardrobe windows for one UUID use an expected-baseline compare and fail explicitly instead of last-writer-wins. Two different UUIDs update independent records through the same envelope commit. The existing `PetProfiles._commit` rolls back the in-memory envelope on save exception; inspect `JsonRepository.save` semantics before promising crash durability beyond that boundary.

## Sequence and checks

1. Extract controller and route five UI actions plus drop/timeline feed through it. Verify cooldown, full refusal, cancellation and no duplicate stat owner with unit tests against live stat objects; verify speech off still decays care on a fake clock.
2. Split pointer intent on release/drag threshold and add explicit petting mode. Verify one reward per accepted event and no drag reward.
3. Add v2 profile parser/migration, energy and preferences with v1 round-trip and failure rollback cases. Migrate Puppet's direct feed path through the same policy or a clearly scoped capability adapter before claiming consistent behavior.
4. Build MOCHI layered idle/walk/sleep sample and capability checks; then preview/cancel/apply transaction, two-UUID isolation, missing assets and restart restore. Expand only after 64/96/128px and motion/occlusion checks.

## Main risks

- A pass-through controller that leaves old `feed()`, `_on_chatter()`, `mousePressEvent`, Puppet feed and focus reward writers intact creates two rules for the same action. Delete or reroute each legacy writer in the unit that introduces its replacement.
- `PetProfileSession.reader` is an open lambda and `flush()` currently updates only three stat keys. Extending the schema without changing this contract silently drops energy/equipment; keep a typed snapshot contract and one commit path.
- A controller that mirrors motion state or owns a second focus timer will drift from `PetMotion`/`FocusTimer`. Adapt their observed events and commands, then arbitrate only interaction intent.
- Wardrobe atomicity spans disk and visual assets. Preload/validate assets and explicitly handle post-save visual failure; `_commit` alone protects only the settings value during save exceptions.
- Existing art is conceptual. Capability adapters must return unsupported for missing action layers and for Puppet models without native outfit controls.
