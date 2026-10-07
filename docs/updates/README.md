# docs/updates: update log index

`progress.md` holds only work that is **not done yet**. Everything that *was* done (what changed, measured numbers, decisions, snapshots) is recorded here: **one batch file per month**, one entry per piece of work, each entry with a fixed-format ID and tags, and one row per entry in the index below.

> No TODOs here. If an entry mentions something still open, it only points to it (e.g. "open item: `progress.md` #3"); the item itself lives in `progress.md`.

## How to query

Run from the repository root:

| To find | Command |
|---|---|
| every entry, one line each | `rg -n "^## U-2" docs/updates` |
| entries of one type | `rg -n "^## U-2.*#done" docs/updates` |
| entries with a topic tag | `rg -n "^## U-2.*#<tag>" docs/updates` |
| one day or one month | `rg -n "^## U-202609" docs/updates` |
| the full text of one entry | `rg -n -A 60 "^## U-20260922-01" docs/updates` |
| any keyword | `rg -n "keyword" docs/updates` |

Without `rg`: `git grep -n "^## U-2" -- docs/updates`, or in PowerShell `Select-String -Path docs/updates/*.md -Pattern '^## U-2'`.

## Entry format

```markdown
## U-YYYYMMDD-NN · YYYY-MM-DD · one-line title · #type #topic

- **What**: ...
- **Result / numbers**: ...
- **Files**: `path` ...
- **Evidence**: commit, file:line, link ...
- **Open items**: none / see `progress.md` ...
```

- **ID**: `U-` + date + two-digit sequence for that day. IDs are never renumbered or reused, so code comments and other documents can cite them.
- **Type tag** (exactly one): `#done` finished `progress.md` item, `#snapshot` measurement or inventory, `#decision`, `#incident`, `#migration`, `#docs`, `#release`.
- Topic tags are free-form (`#mcp`, `#wayland`, ...).
- Keep conclusions, numbers, files and evidence; drop the reasoning trail and dead ends.

## Batch rules

1. One file per month: `docs/updates/YYYY-MM.md`. Append new entries at the end.
2. Over about 800 lines, continue in `YYYY-MM-b.md` (then `-c`) and list it in the batch table below.
3. **Claim the ID under a lock.** Several sessions may write this log at the same time (for example parallel autonomous runs), and without a lock two of them pick the same number:
   1. `mkdir docs/updates/.id-lock`. Creating a directory is atomic, so only one writer succeeds. If it already exists, someone else is claiming: wait a few seconds and retry. A lock older than 10 minutes is stale and may be removed.
   2. Find the day's last number with `rg -n "^## U-YYYYMMDD" docs/updates` and write the heading line and the index row.
   3. `rmdir docs/updates/.id-lock`, then fill in the body. Git never tracks the empty lock directory.
   4. Before committing, `rg -c "^## U-<your ID>" docs/updates` must report one match in total. If not, renumber your entry under the lock and fix its index row. Whoever merges a branch renumbers entries that reuse an ID.
4. **One line per index row**: title only (about 60 characters), no summary.
5. Never rewrite a recorded entry. Correct it with a new `#decision` or `#incident` entry and add "→ corrected in U-..." to the old one.

## When a `progress.md` item is done

In the same commit: delete the item from `progress.md`, add a `#done` entry here that names it, and add its index row.

---

## Index (newest first)

| ID | Date | Title | Tags | Batch |
|---|---|---|---|---|
| U-20261008-02 | 2026-10-08 | Send independent fixed-size scenes to a virtual camera | #done #scene #camera | [2026-10](2026-10.md) |
| U-20261008-01 | 2026-10-08 | Edit replay and crossfade scene animation timelines | #done #scene #animation | [2026-10](2026-10.md) |
| U-20261007-24 | 2026-10-07 | Record silent AVI with pause resume and bounded streaming | #done #recording #video | [2026-10](2026-10.md) |
| U-20261007-23 | 2026-10-07 | Compose and interact with bounded live scene media previews | #done #scene #media | [2026-10](2026-10.md) |
| U-20261007-22 | 2026-10-07 | Preview and apply editable work teaching and focus scene templates | #done #templates #scene | [2026-10](2026-10.md) |
| U-20261007-21 | 2026-10-07 | Automate scene playback and named layer edits with deferred receipts | #done #rules #scene | [2026-10](2026-10.md) |
| U-20261007-20 | 2026-10-07 | Prioritize cooldown and diagnose edge-triggered automation rules | #done #rules #diagnostics | [2026-10](2026-10.md) |
| U-20261007-19 | 2026-10-07 | Preserve saved rule time windows during repeated normalization | #done #rules #fix | [2026-10](2026-10.md) |
| U-20261007-18 | 2026-10-07 | Compare aligned reference images with shared zoom wipe and RGB differences | #done #images #compare | [2026-10](2026-10.md) |
| U-20261007-17 | 2026-10-07 | Resume clone and manage independent sprite and puppet pet saves | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261007-16 | 2026-10-07 | Store independent validated pet identities and portable saves | #done #pets #storage | [2026-10](2026-10.md) |
| U-20261007-15 | 2026-10-07 | Preview and restore bounded preset configuration versions | #done #presets #versions | [2026-10](2026-10.md) |
| U-20261007-14 | 2026-10-07 | Collect and manage exact RGB color palettes | #done #palette #tools | [2026-10](2026-10.md) |
| U-20261007-13 | 2026-10-07 | Resolve roadmap decision and retain only outstanding work | #decision #roadmap | [2026-10](2026-10.md) |
| U-20261007-12 | 2026-10-07 | Add asynchronous local file text feeds and field selection | #done #text #data | [2026-10](2026-10.md) |
| U-20261007-11 | 2026-10-07 | Add localized keyboard command search with favorites | #done #commands #ui | [2026-10](2026-10.md) |
| U-20261007-10 | 2026-10-07 | Share action definitions across existing input routes | #done #actions #refactor | [2026-10](2026-10.md) |
| U-20261007-09 | 2026-10-07 | Verify packaged Windows startup and Workshop runtime | #done #packaging #workshop | [2026-10](2026-10.md) |
| U-20261007-08 | 2026-10-07 | Add undoable visual scene editing and playback transforms | #done #scene #ui | [2026-10](2026-10.md) |
| U-20261007-07 | 2026-10-07 | Reject incomplete executable build environments before compiling | #done #packaging | [2026-10](2026-10.md) |
| U-20261007-06 | 2026-10-07 | Include and verify Windows Now playing projections | #done #windows #dependencies | [2026-10](2026-10.md) |
| U-20261007-05 | 2026-10-07 | Integrate Workshop management and validate private Steam sharing | #done #workshop #ui | [2026-10](2026-10.md) |
| U-20261007-04 | 2026-10-07 | Validate and retain isolated Workshop subscription versions | #done #workshop | [2026-10](2026-10.md) |
| U-20261007-03 | 2026-10-07 | Persist Workshop publication IDs and recover interrupted uploads | #done #workshop | [2026-10](2026-10.md) |
| U-20261007-02 | 2026-10-07 | Add native Steam runtime and validate SDK callback ABI | #done #steam #workshop | [2026-10](2026-10.md) |
| U-20261007-01 | 2026-10-07 | Validate Workshop publication snapshots and preset archives | #done #workshop #security | [2026-10](2026-10.md) |
| U-20261003-02 | 2026-10-03 | Track selected Steam SDK examples and application configuration | #steam #configuration | [2026-10](2026-10.md) |
| U-20261003-01 | 2026-10-03 | Add streaming capture and platform interoperability | #done #interop | [2026-10](2026-10.md) |
| U-20261001-04 | 2026-10-01 | Release job builds with the locked setuptools | #done #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-03 | 2026-10-01 | Release job installs hash-locked build tooling | #done #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-02 | 2026-10-01 | The sdist carries no tests; discovery limited to frontengine | #done #packaging #X-13 | [2026-10](2026-10.md) |
| U-20261001-01 | 2026-10-01 | Every workflow job has a timeout | #ci #tests | [2026-10](2026-10.md) |
| U-20260925-02 | 2026-09-25 | CI and classifiers cover Python 3.13 and 3.14 | #ci #packaging #tests | [2026-09](2026-09.md) |
| U-20260925-01 | 2026-09-25 | Dependabot waits 7 days before proposing a new release | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260924-02 | 2026-09-24 | Keep checkout credentials only in the job that pushes | #ci #security | [2026-09](2026-09.md) |
| U-20260924-01 | 2026-09-24 | Move CI to Node 24 actions pinned by commit | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260923-03 | 2026-09-23 | pyflakes in dev_requirements; stable.toml header; system_tray location | #done #docs | [2026-09](2026-09.md) |
| U-20260923-02 | 2026-09-23 | PySide6 6.11.2; Dependabot targets dev | #done #deps #ci | [2026-09](2026-09.md) |
| U-20260923-01 | 2026-09-23 | FrontEngine.log moves out of the working directory | #done #logging | [2026-09](2026-09.md) |
| U-20260922-04 | 2026-09-22 | Point project URLs at JeffreyChen-SteamProjects/FrontEngine | #done #metadata | [2026-09](2026-09.md) |
| U-20260922-03 | 2026-09-22 | SonarCloud S6549 on pet sound paths marked WONTFIX | #decision #sonarcloud | [2026-09](2026-09.md) |
| U-20260922-02 | 2026-09-22 | Codacy stalls on very large PRs (PR #216) | #incident #ci | [2026-09](2026-09.md) |
| U-20260922-01 | 2026-09-22 | Adopt progress/architecture/docs-updates rules | #docs #migration | [2026-09](2026-09.md) |


## Batches

| File | Period | Entries |
|---|---|---:|
| [2026-10.md](2026-10.md) | 2026-10 | 32 |
| [2026-09.md](2026-09.md) | 2026-09 | 11 |
