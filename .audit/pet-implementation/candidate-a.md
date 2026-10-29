# Candidate A: one pure interaction reducer, owned by the identity session

Design only. Ground and sketch complete; synthesis belongs to the parent architect. Implementation and further delegation intentionally excluded from this task.

## Grounding and constraints

`DesktopPetWidget` currently owns three mutable stat objects (`_mood`, `_hunger`, `_growth`). `PetProfileSession.reader` reads those objects; `flush()` persists only mood/fullness/affection. `PetProfiles` already owns strict record validation, detached reads, identity creation, import/export, atomic settings rollback and the legacy shared-stat migration. Its store and export envelope are version 1. `PetProfileSession` provides the one-live-widget lease keyed by settings object and UUID.

The existing split exists to keep widget activity responsive while debouncing persistence. Preserve those properties, but move authoritative runtime identity state into the session so new energy and outfit fields do not create another competing owner. Persistence remains a snapshot, not an independently ticking simulation.

`PetMotion` owns position, velocity, surfaces and locomotion. It must retain that responsibility. Interaction intent should gate its autonomous choices rather than duplicate its physics. Today chatter decrements stats; idle detection, tag roles, peers, focus and mouse press can wake or guide motion independently. These are the concrete integration risks: adding menu actions alone leaves old writers overriding the new modes. `change_sprite()` and mouse press currently award affection; both must route through the reducer or stop rewarding.

The current accepted art scope is six characters and fourteen outfit concepts. No layered animation assets exist merely because concept sheets exist. First interaction functionality must work with legacy sprite fallbacks and label fallback animation honestly.

## Caller-first usage

```python
# Widget owns event adaptation, not statistics or interaction policy.
view = self.profile_session.dispatch(Feed(kind=classify_food(path)), now=monotonic())
self._apply_interaction_view(view)

# Existing animation timer advances active elapsed time, regardless of speech.
view = self.profile_session.advance(now=monotonic())
self.motion.step(..., allow_autonomy=view.allow_autonomy)
self._render(view.action or self._physical_visual_state())

# Both management page and desktop menu use exactly these same commands.
self.profile_session.dispatch(SetMode(Mode.REST), now=monotonic())
```

The session binds UUID and creates command IDs. Callers cannot select another identity or supply arbitrary stat deltas. Existing `state()` returns a detached serializable snapshot for exports and management controls. A read-only `view` exposes stats, mode, interaction, progress, requested visual, motion permissions and semantic feedback. Feedback carries a sequence ID so applying a view repeatedly cannot replay sound or level-up effects.

## Modules and narrow API

`frontengine/show/pet/pet_interaction.py` is Qt-free domain logic:

```python
class Mode(Enum):
    PLAY = "play"
    WORK = "work"
    REST = "rest"

@dataclass(frozen=True)
class InteractionState:
    identity: PetIdentity       # sole runtime stat/profile value
    transient: Action | None  # kind, generation, elapsed, duration, reward-applied
    active_seconds: float
    reward_cooldowns: ...     # monotonic active-time deadlines, session-only

def transition(state: InteractionState, event: Event) -> Transition:
    raise NotImplementedError

def present(state: InteractionState) -> InteractionView:
    raise NotImplementedError
```

Events are a closed union: `Feed`, `Groom`, `SetMode`, `Greet`, `BeginDrag`, `EndDrag`, `Cancel`, `Advance`, eventually `BeginPetting`, `PetStroke`, `FocusCompleted`, `ApplyOutfit`. There is no public `AddAffection` or `SetStat` bypass. `Advance` supplies validated nonnegative active elapsed time, never wall-clock dates. Pure transition returns new state plus semantic effects; it performs no storage, GUI, random selection or file reads.

`PetProfileSession` owns the current `InteractionState`, monotonic clock adaptation, deduplication of upstream stable event IDs, debounced saves and transactional structural changes. Public additions are `dispatch(command, now)`, `advance(now)` and read-only `view`. `schedule`, `flush`, `close`, `active`, `identifier` retain their current purposes. Remove `reader` when migrating the widget; do not retain writable `_mood/_hunger/_growth` alongside reducer stats. Legacy stat helper classes may remain as pure conversions or isolated test helpers, but no widget mutates them.

`pet_profiles.py` owns wire-format parsing/migration and bounded asset-reference validation. The renderer only reads an action and eventual outfit composition; it never changes identity or awards rewards. Future wardrobe compatibility belongs to a separate asset-domain module, not the reducer or session.

## State and priority contract

Persistent mode and transient interaction are orthogonal. No stack of previous modes: completion always reveals the *current* mode. Selecting WORK during an eat cancels eat and enters WORK; selecting REST while grooming cancels grooming. Repeating an already active command does not restart its timer or reward it again. Drag interrupts a short action, exits tag pairing and suppresses mode locomotion until release/landing. Shutdown and material asset failure outrank all commands.

Priority: close/asset fault > direct input > active short interaction > mode behavior > autonomous idle. Only the session's projected motion policy can enable idle wake, peer following or tag. Chatter becomes presentation-only. Existing focus timer emits domain commands; no replacement focus clock.

Prototype timing is explicit, configurable policy, not an art claim: feed 2 seconds; groom 3 seconds; greeting 0.75 seconds. Rewards apply once on successful completion. Cancelled actions grant none. Feed at fullness 100 yields a short refusal and no stat delta or reward. Repeated feed during feed is a busy/no-op result. Cooldown spans both normal completion and repeated requests, so distinct event IDs cannot bypass limits. Groom is skippable/cancellable; no mandatory cleanliness statistic. PLAY/WORK/REST are indefinite modes, with visible entry feedback and REST wake action. PLAY enables existing bounded roaming/tag eligibility; it does not claim an unimplemented ball toy.

Energy recovery/consumption is computed from active elapsed time, with a remainder accumulator to avoid frame-rate dependence. REST recovers; active play consumes; WORK preserves or slowly recovers according to a single policy table. Low energy can request rest only when the preference permits it. User interaction remains available. A resumed app starts a new monotonic baseline; no persisted last-seen penalty. Clamp an unusually long tick and reset on suspend so system sleep does not simulate hours of care or decay. Mood/fullness decay moves out of chatter into this same active-time mechanism. First implementation records the chosen cadence; old randomized 15–35 second chatter is not a reliable gameplay clock.

For mouse input, press records a pending gesture only. Exceeding `QApplication.startDragDistance()` emits BeginDrag once. Release without threshold crossing emits Greet once. Petting is an explicit later mode that disables drag. No reward on press/move or ordinary outfit changes.

## Persistent v2 shape

Keep the store's existing `version` field as its schema discriminator rather than introduce a second conflicting `schemaVersion`:

```json
{
  "version": 2,
  "migrated": true,
  "records": {
    "<uuid hex>": {
      "id": "<uuid hex>", "name": "Mochi",
      "mood": 60, "fullness": 70, "affection": 0, "energy": 70,
      "mode": "play",
      "appearance": {
        "character": null,
        "equipped": {"head": null, "neck": null, "body": null, "back": null},
        "saved_outfits": []
      },
      "preferences": {
        "auto_rest": true, "allow_throw": true, "allow_social": true,
        "snack_preferences": {}
      },
      "progress": {"completed_focus_ids": []}
    }
  }
}
```

Asset refs are `{ "id": "...", "version": "..." }`; they never contain developer paths. Nullable `character` means legacy externally configured whole-sprite appearance, not an invented MOCHI asset. Each equipped slot contains a garment ref or null; compatibility validation enforces occupancy across slots before commit. Multi-slot items can have the same canonical ref in each occupied slot; the wardrobe owner supplies canonicalization and the renderer deduplicates canonical items. Saved outfits are bounded to 20 named complete selections with stable local IDs. Basic defaults do not unlock unavailable artwork. Missing assets preserve refs and render a base fallback; they are not normalized to null.

Preferences are per identity, while existing global sound/bubble controls remain their current scope until intentionally migrated. Do not silently make global user settings per-pet. Stable focus completion IDs must come from the existing timer's durable run identity. A bounded list alone cannot guarantee lifetime duplicate prevention; use a timer-owned monotonic completion sequence/high-water mark if available. Until that integration exists, do not claim clock-resistant cross-restart focus rewards.

v1 migration preserves id/name/all three existing stats exactly, adds energy/mode/default appearance/preferences and retains `migrated`. Validate all records first, then atomically commit the entire migrated container; on error retain original bytes/settings. An unversioned legacy store remains the existing one-time shared-stat path. Import accepts v1 and v2, validates strictly, and creates a fresh UUID while retaining intended appearance refs. Export uses envelope version 2. No unknown fields are silently discarded and no v1 downgrade is written.

## Commit semantics

Every stat mutation replaces the session's immutable state then schedules the existing debounce. Failed stat flush leaves dirty runtime state for retry, consistent with current behavior; UI must not say it is saved. A structural change (outfit, saved outfit, preferences if user expects an Apply transaction) first validates and preloads resources, persists a candidate record, then installs the runtime candidate. Failure leaves both original runtime and saved outfit. No timer or callback writes stale entire records: merge only the session-owned dirty fields into the latest repository record, preserving a management-page rename. Active rename/export should use the session or repository's explicit supported path.

Wardrobe preview owns a detached appearance draft and renderer; it is never another profile session. Apply targets the original UUID and candidate revision, with preloaded assets and one safe presentation boundary. The maximum boundary wait remains to be measured. No outfit action changes stats.

## Smallest complete first unit

1. Implement v2 read/migration/import/export and the interaction reducer; move all widget stat mutations into session commands in the same unit.
2. Expose Feed, Groom, Work, Play, Rest and Wake in the existing context menu and profile-management equivalent controls. Timed actions give observable fallback animation/status feedback; mode selection remains visible after action completion.
3. Gate old idle/peer/tag/focus wake paths through the interaction policy. Move decay off chatter. Remove costume reward and press reward; distinguish release-click from drag threshold.
4. Verify with fake-clock domain tests plus offscreen widget actions: feed completion once, interruption no reward, saturation no farming, chatter on/off identical stats, rest survives feeding, work survives idle/tag ticks, duplicate identity refusal, reopen v2, migration failure rollback, renamed profile not overwritten, and two pets independent. No host GUI input or visible window is needed for this unit.

## Red-flag screen and tradeoffs

The reducer hides priority, timed completion, rewards and energy behind one transition. Session owns live state; repository owns serialized validation; motion owns physics. This avoids split stat ownership and parallel command paths. The cost is migrating *all* current stat writers, including tag and peer events, together; leaving wrappers that still mutate old objects invalidates this design.

Pure reducer effects must not become a generic application event bus. Keep the closed event union limited to pet behavior and explicit presentation effects. The widget must not reimplement timing or cooldown rules. Flat legacy stats remain in v2 to minimize migration churn; structured appearance/preferences are added because they are genuine domains. Unknown asset references are valid recoverable intent, while malformed references remain invalid input.

Largest unresolved risks are old autonomous motion overriding persistent modes, durable focus identity unavailable, close-time save failure currently dropping retry opportunity, whole-store size budget once 256 pets each have 20 outfits, and missing art coverage. The design does not solve those by claiming layered costumes or native-desktop validation already exist.
