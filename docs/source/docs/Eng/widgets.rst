Widgets Page
------------

* Audio spectrum - bars or a ring that move with what your speakers play, with
  an adjustable number of bands. This one does capture audio, in memory only,
  to compute frequencies; nothing is recorded or sent, and capture stops when
  you stop the spectrum. Windows and macOS (optional macos extra and permission; native macOS unverified here).
* System monitor - CPU, memory, disk, battery and network throughput as a
  small always-visible panel. Tick the lines you want; a line you hide keeps
  recording, so turning it back on shows what happened meanwhile.
* Show now playing - the track your media player is on.
* Sticky note - New note puts a note on the desktop; Close notes clears them.
  Reopen my notes when FrontEngine starts brings them back next time.

Widgets → Tasks and calendar manages checked tasks with optional local due time and imports local UTF-8 .ics individual VEVENT/VTODO records. A separate Today widget shows incomplete undated/due/overdue tasks and events overlapping today; all-day and midnight end times are exclusive. Known IANA TZID uses platform Qt rules, UTC instants display locally, floating times remain local, all-day dates never shift. DST repeated times choose the first occurrence and missing times use the pre-transition offset; DURATION nominal days preserve local wall time. UID plus RECURRENCE-ID identifies updates; lower SEQUENCE cannot overwrite newer imports, checkmarks survive reimport, CANCELLED removes matching records. Folded lines and TEXT escapes supported; links, alarms and attachments are never opened. Recurrence rules/RDATE/EXDATE and unknown custom zones are explicitly rejected atomically; export individual occurrences. tasks.json beside settings holds at most 500 items/four MiB (title 1000, description 2000 characters); atomic writes preserve old data on failure. Import size four MiB, property 8192 characters, no network/sync/alarm. Lazy serialized worker keeps file I/O off the GUI; close stops timers and drops late results. Today widget joins batch close/hide controls; opening is explicit, task data persists without automatically restoring a widget.

Cancellation tombstones count toward the 500-record limit and prevent stale imports from resurrecting cancelled events. Clear all asks for confirmation and removes tasks, events and cancellation metadata. Interactive Today controls use ordinary Qt software painting so the compositor cannot cover them.
