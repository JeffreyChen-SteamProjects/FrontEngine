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
| U-20261106-12 | 2026-11-06 | Verify service reuse during built-in page and command navigation | #testing #ui | [2026-11](2026-11.md) |
| U-20261106-11 | 2026-11-06 | Record native MainUI onboarding and cold reload with failed video gate | #testing #acceptance | [2026-11](2026-11.md) |
| U-20261106-10 | 2026-11-06 | Verify integrated accessibility and search regression; integrate plugin fixes | #testing #integration | [2026-11](2026-11.md) |
| U-20261106-09 | 2026-11-06 | Verify work reservations across storage and restart | #pets #economy #acceptance | [2026-11](2026-11.md) |
| U-20261106-08 | 2026-11-06 | Verify preset menu round trips and plugin batch cleanup | #ui #presets #acceptance | [2026-11](2026-11.md) |
| U-20261106-07 | 2026-11-06 | Separate plugin navigation IDs from built-in pages | #ui #plugins #testing | [2026-11](2026-11.md) |
| U-20261106-06 | 2026-11-06 | Include loaded plugin pages in command search | #ui #plugins #testing | [2026-11](2026-11.md) |
| U-20261106-05 | 2026-11-06 | Verify full focus regression and integrate accessibility and search fixes | #testing #integration | [2026-11](2026-11.md) |
| U-20261106-04 | 2026-11-06 | Verify Features menu routes across seven languages | #ui #acceptance | [2026-11](2026-11.md) |
| U-20261106-03 | 2026-11-06 | Select the named command before unrelated history matches | #ui #search #testing | [2026-11](2026-11.md) |
| U-20261106-02 | 2026-11-06 | Give the Work list a translated accessible name | #ui #accessibility #testing | [2026-11](2026-11.md) |
| U-20261106-01 | 2026-11-06 | Restore visible keyboard focus to content lists | #ui #accessibility #testing | [2026-11](2026-11.md) |
| U-20261105-69 | 2026-11-05 | 家園主視窗鍵盤操作流程驗收 | #testing #ui #accessibility | [2026-11](2026-11.md) |
| U-20261105-68 | 2026-11-05 | 完整回歸通過並結束窄視窗整合驗收 | #testing #ui #done | [2026-11](2026-11.md) |
| U-20261105-67 | 2026-11-05 | 六居民自動生活三日與確定性重播 | #testing #pet #economy | [2026-11](2026-11.md) |
| U-20261105-66 | 2026-11-05 | 中斷重啟後的寵物身分與搬入搬出驗收 | #testing #storage #pet | [2026-11](2026-11.md) |
| U-20261105-65 | 2026-11-05 | 家園與角色分段存檔中斷恢復 | #testing #storage | [2026-11](2026-11.md) |
| U-20261105-64 | 2026-11-05 | 家園存檔程序中斷驗收 | #testing #storage | [2026-11](2026-11.md) |
| U-20261105-63 | 2026-11-05 | Integrate message and font fixes and verify the installed wheel | #integration #packaging #testing | [2026-11](2026-11.md) |
| U-20261105-62 | 2026-11-05 | Select and verify Arial in narrow layout regression tests | #testing #ui | [2026-11](2026-11.md) |
| U-20261105-61 | 2026-11-05 | Keep home operation feedback translatable across language changes | #ui #testing | [2026-11](2026-11.md) |
| U-20261105-60 | 2026-11-05 | Verify native home layouts inside the complete main window | #ui #acceptance | [2026-11](2026-11.md) |
| U-20261105-59 | 2026-11-05 | Wrap home headings and collection totals at native narrow widths | #ui #testing #acceptance | [2026-11](2026-11.md) |
| U-20261105-58 | 2026-11-05 | Inspect native home wrapping and preserve narrower layout failures | #ui #acceptance | [2026-11](2026-11.md) |
| U-20261105-57 | 2026-11-05 | Wrap selected furniture text without widening hidden home tabs | #ui #testing | [2026-11](2026-11.md) |
| U-20261105-56 | 2026-11-05 | Reproduce narrow Russian home overflow with explicit Arial | #testing #ui | [2026-11](2026-11.md) |
| U-20261105-55 | 2026-11-05 | 驗證放大鏡的混合 DPI 顯示與定時更新 | #testing #dpi | [2026-11](2026-11.md) |
| U-20261105-54 | 2026-11-05 | 驗證合成器修正版的已安裝套件 | #packaging #testing | [2026-11](2026-11.md) |
| U-20261105-53 | 2026-11-05 | 延後合成器提交以修復跨螢幕切換崩潰 | #fix #rendering #done | [2026-11](2026-11.md) |
| U-20261105-52 | 2026-11-05 | 縮小 OpenGL 清理崩潰的調查範圍 | #testing #diagnosis | [2026-11](2026-11.md) |
| U-20261105-51 | 2026-11-05 | 保存完整回歸失敗與合成器清理對照 | #testing #diagnosis | [2026-11](2026-11.md) |
| U-20261105-50 | 2026-11-05 | 縮減 GPU 後端替換崩潰並保留回歸失敗 | #investigation #ui #test | [2026-11](2026-11.md) |
| U-20261105-49 | 2026-11-05 | 記錄多覆蓋層連續跨螢幕的原生崩潰 | #investigation #ui | [2026-11](2026-11.md) |
| U-20261105-48 | 2026-11-05 | 驗證便條與白板修正進入安裝套件 | #test #packaging #ui | [2026-11](2026-11.md) |
| U-20261105-47 | 2026-11-05 | 修正白板工具列被半透明畫布蓋暗 | #fix #ui #verification | [2026-11](2026-11.md) |
| U-20261105-46 | 2026-11-05 | 修正便條文字被繪圖合成器遮住 | #fix #ui #verification | [2026-11](2026-11.md) |
| U-20261105-45 | 2026-11-05 | 驗證粒子四方向跨混合 DPI 螢幕 | #verification #ui | [2026-11](2026-11.md) |
| U-20261105-44 | 2026-11-05 | 驗證影片原生畫面跨混合 DPI 螢幕 | #verification #ui | [2026-11](2026-11.md) |
| U-20261105-43 | 2026-11-05 | 驗證 Web 覆蓋層跨混合 DPI 螢幕 | #verification #ui | [2026-11](2026-11.md) |
| U-20261105-42 | 2026-11-05 | 驗證最新 wheel 內容與隔離安裝流程 | #test #packaging #ui | [2026-11](2026-11.md) |
| U-20261105-41 | 2026-11-05 | 完成教學後移除無效的跳過操作 | #fix #ui #pet | [2026-11](2026-11.md) |
| U-20261105-40 | 2026-11-05 | 說明空白工作清單並依選取啟用取消 | #fix #ui #pet | [2026-11](2026-11.md) |
| U-20261105-39 | 2026-11-05 | 驗證家園新玩家完整教學與存檔重開 | #test #pet #events | [2026-11](2026-11.md) |
| U-20261105-38 | 2026-11-05 | 驗證 GIF 與文字覆蓋層跨螢幕 | #test #ui | [2026-11](2026-11.md) |
| U-20261105-37 | 2026-11-05 | 記錄最新版主視窗回歸與 SMTC 診斷 | #test #ui | [2026-11](2026-11.md) |
| U-20261105-36 | 2026-11-05 | 圖片覆蓋層混合 DPI 複驗 | #test #ui | [2026-11](2026-11.md) |
| U-20261105-35 | 2026-11-05 | Synchronize inbox reminders while the home is paused | fix, ui, pet, events | [2026-11](2026-11.md) |
| U-20261105-34 | 2026-11-05 | Retranslate inbox history without changing past events | fix, ui, pet, events | [2026-11](2026-11.md) |
| U-20261105-33 | 2026-11-05 | Refresh daily commissions when the game day changes | fix, pet, events | [2026-11](2026-11.md) |
| U-20261105-32 | 2026-11-05 | Fit populated homes into narrow windows | fix, ui, pet | [2026-11](2026-11.md) |
| U-20261105-31 | 2026-11-05 | Run current native GUI acceptance and expose populated-home overflow | validation, ui, native | [2026-11](2026-11.md) |
| U-20261105-30 | 2026-11-05 | Keep resident wardrobes with the home asset directory | fix, pet, storage | [2026-11](2026-11.md) |
| U-20261105-29 | 2026-11-05 | Guard home panel actions during shutdown | fix, lifecycle, pet | [2026-11](2026-11.md) |
| U-20261105-28 | 2026-11-05 | Show saved photos in the album immediately | fix, ui, pet | [2026-11](2026-11.md) |
| U-20261105-27 | 2026-11-05 | Keep home photos and content folders with their owner | fix, home, storage | [2026-11](2026-11.md) |
| U-20261105-26 | 2026-11-05 | Keep pet assets in the owned data directory | fix, pet, storage | [2026-11](2026-11.md) |
| U-20261105-25 | 2026-11-05 | 保存設定與作業所有權的受測整合階段 | #storage #runtime #validation | [2026-11](2026-11.md) |
| U-20261105-24 | 2026-11-05 | 修正驗收關閉判定、GIF 檔案釋放與窄視窗家園 | #done #ui #lifecycle #testing | [2026-11](2026-11.md) |
| U-20261105-23 | 2026-11-05 | 將獨立角色資料與寵物生命週期綁定儲存所有權 | #storage #pet #testing | [2026-11](2026-11.md) |
| U-20261105-22 | 2026-11-05 | 重現關閉後仍處理寵物素材完成訊號 | #review #pet #lifecycle | [2026-11](2026-11.md) |
| U-20261105-21 | 2026-11-05 | 完成相容執行環境兩小時原生家園驗收 | #done #testing #pet-home | [2026-11](2026-11.md) |
| U-20261105-20 | 2026-11-05 | Retain usable pets and home until final shutdown saves succeed | #done #pets #saving #ui | [2026-11](2026-11.md) |
| U-20261105-19 | 2026-11-05 | Add owned storage sessions before integrating application lifetimes | #snapshot #saving #architecture #tests | [2026-11](2026-11.md) |
| U-20261105-18 | 2026-11-05 | Retain the desktop home when closing cannot save | #done #pets #saving #ui | [2026-11](2026-11.md) |
| U-20261105-17 | 2026-11-05 | Verify the installed save fix and reproduce shared-directory writer conflicts | #snapshot #tests #saving | [2026-11](2026-11.md) |
| U-20261105-16 | 2026-11-05 | Report complete saves and clear recovered save errors | #done #pets #saving #ui | [2026-11](2026-11.md) |
| U-20261105-15 | 2026-11-05 | Keep shop prices visible when tile names are long or fonts grow | #done #ui #pets | [2026-11](2026-11.md) |
| U-20261105-14 | 2026-11-05 | Organize native screenshots and a sampled workflow clip for inspection | #done #ui #acceptance | [2026-11](2026-11.md) |
| U-20261105-13 | 2026-11-05 | Complete the fresh-home first fifteen minutes with timed UI and cold-reload evidence | #done #pets #native #acceptance | [2026-11](2026-11.md) |
| U-20261105-12 | 2026-11-05 | Preserve shared menu references across Features rebuilds and language changes | #done #ui #menus | [2026-11](2026-11.md) |
| U-20261105-11 | 2026-11-05 | Verify native entry routing, installed runtime and interrupted save recovery | #snapshot #tests #native #saving | [2026-11](2026-11.md) |
| U-20261105-10 | 2026-11-05 | Exclude early Python 3.14 runtimes after isolated Qt garbage-collection crash | #decision #deps #native | [2026-11](2026-11.md) |
| U-20261105-09 | 2026-11-05 | Native soak preparation exposed an intermittent access violation | #incident #pets #native | [2026-11](2026-11.md) |
| U-20261105-08 | 2026-11-05 | Full regression and installed-wheel home checks pass; mixed DPI unavailable | #snapshot #tests #native #packaging | [2026-11](2026-11.md) |
| U-20261105-07 | 2026-11-05 | Persist life-event frequency and keep blocked layout restoration retryable | #done #pets #events #saving | [2026-11](2026-11.md) |
| U-20261105-06 | 2026-11-05 | Refresh item visuals and preserve photos, notifications and paid upgrades | #done #ui #pets | [2026-11](2026-11.md) |
| U-20261102-29 | 2026-11-02 | Ten more pieces of furniture | #done #pets #game #art | [2026-11](2026-11.md) |
| U-20261102-28 | 2026-11-02 | Five more outfits, and a wardrobe that fetches new clothes by itself | #done #pets #art #ui | [2026-11](2026-11.md) |
| U-20261102-27 | 2026-11-02 | The desktop pet page starts with one click | #done #pets #ui | [2026-11](2026-11.md) |
| U-20261102-26 | 2026-11-02 | Fewer steps across the pages: no monitor prompt, no not-ready dialogs, choose or drop to show | #done #ui | [2026-11](2026-11.md) |
| U-20261102-25 | 2026-11-02 | Size the desktop home, keep the pet in view, and pat with a double-click | #done #pets #game #ui | [2026-11](2026-11.md) |
| U-20261105-01 | 2026-11-05 | Native strip checks repaired and image overlay mixed DPI verified | #snapshot #tests #native | [2026-11](2026-11.md) |
| U-20261105-02 | 2026-11-05 | Interrupted home-strip drags release the resident | #done #pets #events | [2026-11](2026-11.md) |
| U-20261105-03 | 2026-11-05 | Cancelling layout edits prevents late moves and area painting | #done #ui #pets #events | [2026-11](2026-11.md) |
| U-20261105-04 | 2026-11-05 | Blocking saves retain background write completion ownership | #done #pets #saving | [2026-11](2026-11.md) |
| U-20261105-05 | 2026-11-05 | Room-scoped arranging and persistent meeting-mode exit | #done #ui #pets | [2026-11](2026-11.md) |
| U-20261102-30 | 2026-11-02 | Rain and snow on the desktop strip, in a layer that never takes input | #done #pets #game #native | [2026-11](2026-11.md) |
| U-20261102-24 | 2026-11-02 | Require Python 3.11; stop supporting 3.10 | #migration #deps #ci | [2026-11](2026-11.md) |
| U-20261102-23 | 2026-11-02 | Old entry points tested after the move, and a background smoke run of the pet home | #done #tests #pets | [2026-11](2026-11.md) |
| U-20261102-22 | 2026-11-02 | Furniture packs, themes and blueprints on the Workshop, with missing packs named | #done #pets #game #workshop #security | [2026-11](2026-11.md) |
| U-20261102-21 | 2026-11-02 | Picture and Puppet pets appear in the home as themselves | #done #pets #game #animation #security | [2026-11](2026-11.md) |
| U-20261102-20 | 2026-11-02 | Ambient sound with its own volume, and evening on the desktop strip | #done #pets #game #audio | [2026-11](2026-11.md) |
| U-20261102-19 | 2026-11-02 | Cleanliness: pets tidy themselves up, a bath tub is quicker | #done #pets #game #art #migration | [2026-11](2026-11.md) |
| U-20261102-18 | 2026-11-02 | Tests delete the windows they close | #done #tests #fix | [2026-11](2026-11.md) |
| U-20261102-17 | 2026-11-02 | Real-device acceptance may only sit at the top of progress.md, checked by a test | #done #process | [2026-11](2026-11.md) |
| U-20261102-16 | 2026-11-02 | Furniture content packs, checked at the boundary | #done #pets #game #security | [2026-11](2026-11.md) |
| U-20261102-15 | 2026-11-02 | Share a home as a blueprint and visit one read-only | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-14 | 2026-11-02 | Seasons in the home's year, seasonal goals and advanced trades | #done #pets #game #art | [2026-11](2026-11.md) |
| U-20261102-13 | 2026-11-02 | Event cooldowns, goal windows and furniture art as data, and choosing who moves in | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-12 | 2026-11-02 | Tests free the widgets they give up | #done #tests #fix | [2026-11](2026-11.md) |
| U-20261102-11 | 2026-11-02 | Grooming, toys, calling a pet over, tag and pet photos in the home | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-10 | 2026-11-02 | Pets keep you company during focus sessions, and a dropped file is only a treat | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-09 | 2026-11-02 | Pause the home while the computer is locked, and badges on furniture | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-08 | 2026-11-02 | Workstation upgrades, pets helping at work, and a stock limit for automatic jobs | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-07 | 2026-11-02 | A collapsible toolbar on the desktop strip, and care and info in its right-click menus | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-06 | 2026-11-02 | Raised furniture with pet stairs, unreachable preview, crossing points between zones | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-05 | 2026-11-02 | Stop home character loading from crashing after the page closes | #done #pets #fix | [2026-11](2026-11.md) |
| U-20261102-04 | 2026-11-02 | Zones on several screens, floor areas, transfers and unplugged screens | #done #pets #game | [2026-11](2026-11.md) |
| U-20261102-03 | 2026-11-02 | Layout editor: undo and redo, drag and nudge, layout codes, ready-made layouts | #done #pets #game #ui | [2026-11](2026-11.md) |
| U-20261102-02 | 2026-11-02 | Thirty-one pieces of furniture, level unlocks and a Collection tab | #done #pets #game #art | [2026-11](2026-11.md) |
| U-20261102-01 | 2026-11-02 | Free arranging: a separate home with every piece and no costs | #done #pets #game | [2026-11](2026-11.md) |
| U-20261101-24 | 2026-11-01 | Pet home shortcuts, a waiting list, zoom and a way out of arranging on the strip | #done #pets #game #ui | [2026-11](2026-11.md) |
| U-20261101-23 | 2026-11-01 | Real-device acceptance first in progress.md; finished and decided plan items closed | #done #process | [2026-11](2026-11.md) |
| U-20261101-22 | 2026-11-01 | Dialogs join the redesign: natural-width buttons, roomy margins, an accented default | #done #ui #design | [2026-11](2026-11.md) |
| U-20261101-21 | 2026-11-01 | Patch setuptools and certifi in the publish lock | #bugfix #deps #security #ci | [2026-11](2026-11.md) |
| U-20261101-20 | 2026-11-01 | The home runs itself, with fewer settings and a picture for everything | #done #pets #game #ui #art | [2026-11](2026-11.md) |
| U-20261101-19 | 2026-11-01 | Page-by-page review of the redesign and new documentation screenshots | #done #ui #design #docs | [2026-11](2026-11.md) |
| U-20261101-18 | 2026-11-01 | The pet home page becomes a game screen | #done #ui #design #pets #game | [2026-11](2026-11.md) |
| U-20261101-17 | 2026-11-01 | Setting pages in one centred column; calm headings, even controls | #done #ui #design | [2026-11](2026-11.md) |
| U-20261101-16 | 2026-11-01 | Redesigned window frame: sidebar icons, brand mark, search entry | #done #ui #design | [2026-11](2026-11.md) |
| U-20261101-15 | 2026-11-01 | Own design system replaces qt-material | #done #ui #design | [2026-11](2026-11.md) |
| U-20261101-14 | 2026-11-01 | Built-in characters get drawn home poses | #done #pets #game #art #animation | [2026-11](2026-11.md) |
| U-20261101-13 | 2026-11-01 | Furniture drawn as Blender-rendered pictures per theme | #done #pets #game #art | [2026-11](2026-11.md) |
| U-20261101-12 | 2026-11-01 | Residents appear as their own characters | #done #pets #game #animation | [2026-11](2026-11.md) |
| U-20261101-11 | 2026-11-01 | Home modes, a quiet inbox and the performance measurements | #done #pets #game #performance | [2026-11](2026-11.md) |
| U-20261101-10 | 2026-11-01 | Days, nights, weather, themes and twelve life moments | #done #pets #game #accessibility | [2026-11](2026-11.md) |
| U-20261101-09 | 2026-11-01 | Goals, commissions, wishes, life moments and the home celebration | #done #pets #game #migration | [2026-11](2026-11.md) |
| U-20261101-08 | 2026-11-01 | Pets live together: comfort, company, friendships and personality | #done #pets #game #migration | [2026-11](2026-11.md) |
| U-20261101-07 | 2026-11-01 | Three professions with materials, goods and a backpack | #done #pets #game #economy | [2026-11](2026-11.md) |
| U-20261101-06 | 2026-11-01 | Features menu: every tool one click from the pet home, with a measured inventory | #done #ui #game | [2026-11](2026-11.md) |
| U-20261101-05 | 2026-11-01 | The pet home on the desktop: click-through strip, layer choice, smooth drawing | #done #pets #game #native | [2026-11](2026-11.md) |
| U-20261101-04 | 2026-11-01 | Pet home on a real desktop: acceptance run and readable cells | #snapshot #pets #game #native | [2026-11](2026-11.md) |
| U-20261101-03 | 2026-11-01 | Pet home page: play the first loop from the main window | #done #pets #game #ui | [2026-11](2026-11.md) |
| U-20261101-02 | 2026-11-01 | Pet home service: one clock, identity leases, background saves | #done #pets #game | [2026-11](2026-11.md) |
| U-20261101-01 | 2026-11-01 | Pet home domain layer: world, simulation, economy and saves | #done #pets #game | [2026-11](2026-11.md) |
| U-20261029-47 | 2026-10-29 | Make the built-in walk and climb read as real steps at pet size | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-48 | 2026-10-29 | Show animated pets moving on the GPU path and walk MOCHI with generated step frames | #done #pets #animation #compositor | [2026-10](2026-10.md) |
| U-20261029-49 | 2026-10-29 | Paint desktop pets through Qt so their frames change while they move | #done #pets #animation #compositor | [2026-10](2026-10.md) |
| U-20261029-50 | 2026-10-29 | Stop pets jittering left and right on narrow window ledges | #done #pets #motion | [2026-10](2026-10.md) |
| U-20261029-51 | 2026-10-29 | Generated walk and climb frames for the other five built-in characters | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-52 | 2026-10-29 | Clean stray specks and off-palette pink from the generated pet frames | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-53 | 2026-10-29 | Fix the PR #227 macOS install failure and SonarCloud findings | #done #pets #ci #quality | [2026-10](2026-10.md) |
| U-20261030-01 | 2026-10-30 | Clean up listeners and widgets before the test process exits | #done #ci #tests | [2026-10](2026-10.md) |
| U-20261030-02 | 2026-10-30 | Clear the release PR's SonarCloud gate | #done #ci #quality #macos | [2026-10](2026-10.md) |
| U-20261030-03 | 2026-10-30 | Build the executable on every CPU core by default | #done #packaging #build | [2026-10](2026-10.md) |
| U-20261030-04 | 2026-10-30 | Puppet pets stroll on their own | #done #pets #puppet #motion | [2026-10](2026-10.md) |
| U-20261030-05 | 2026-10-30 | Start built-in characters from the Pet page as sprite pets | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261030-06 | 2026-10-30 | Pick each autonomous pet action at random from the whole action set | #done #pets #puppet #motion | [2026-10](2026-10.md) |
| U-20261030-07 | 2026-10-30 | Name the random-actions mode in the menu and start summoned pets moving at once | #done #pets #ui #motion | [2026-10](2026-10.md) |
| U-20261030-08 | 2026-10-30 | Accept the whole GUI on an isolated desktop | #done #ui #tests #native | [2026-10](2026-10.md) |
| U-20261029-46 | 2026-10-29 | Keep pets aligned and sized across monitors with different scaling | #done #pets #monitors #native | [2026-10](2026-10.md) |
| U-20261029-45 | 2026-10-29 | Accept pet toys, calls, strokes and Puppet reactions on the real screen, isolated | #done #pets #puppet #native | [2026-10](2026-10.md) |
| U-20261029-44 | 2026-10-29 | End grooming with a stretch and limit repeated peer greetings | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-43 | 2026-10-29 | Verify pet manager keyboard navigation through native Windows input on an isolated desktop | #done #pets #accessibility #native | [2026-10](2026-10.md) |
| U-20261029-42 | 2026-10-29 | Export the built-in characters as rigged Puppet models and verify them natively | #done #puppet #art #native | [2026-10](2026-10.md) |
| U-20261029-41 | 2026-10-29 | Localize built-in part and garment labels | #done #pets #i18n | [2026-10](2026-10.md) |
| U-20261029-40 | 2026-10-29 | Measure one and four pets, layered against legacy, within stated budgets | #done #pets #performance | [2026-10](2026-10.md) |
| U-20261029-39 | 2026-10-29 | Offer every pet menu command from the keyboard in the pet manager | #done #pets #accessibility | [2026-10](2026-10.md) |
| U-20261029-38 | 2026-10-29 | Set chatter frequency and animation size separately per pet | #done #pets #settings | [2026-10](2026-10.md) |
| U-20261029-37 | 2026-10-29 | Replace conflicting garments, label fit, compare looks and switch outfits safely | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261029-36 | 2026-10-29 | Add relationship stages, welcome and goodbye greetings, Puppet click intent | #done #pets #puppet #interaction | [2026-10](2026-10.md) |
| U-20261029-35 | 2026-10-29 | Play sit, transitions, landing, catch and peer waves on desktop pets | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-34 | 2026-10-29 | Ship six drawn INKSIDE characters and fourteen outfits as layered assets | #done #pets #art #wardrobe | [2026-10](2026-10.md) |
| U-20261029-33 | 2026-10-29 | Add the Puppet ball toy | #done #puppet #toys | [2026-10](2026-10.md) |
| U-20261029-32 | 2026-10-29 | Add the Puppet light-spot toy | #done #puppet #toys | [2026-10](2026-10.md) |
| U-20261029-31 | 2026-10-29 | Verify Puppet call movement on native GL | #done #puppet #native | [2026-10](2026-10.md) |
| U-20261029-30 | 2026-10-29 | Move Puppet pets on Come here | #done #puppet #interaction | [2026-10](2026-10.md) |
| U-20261029-29 | 2026-10-29 | Choose call destinations by keyboard | #done #pets #accessibility | [2026-10](2026-10.md) |
| U-20261029-28 | 2026-10-29 | Switch wardrobe language live | #done #pets #i18n | [2026-10](2026-10.md) |
| U-20261029-27 | 2026-10-29 | Start interactions from the pet manager | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261029-26 | 2026-10-29 | Add the Come here command | #done #pets #interaction | [2026-10](2026-10.md) |
| U-20261029-25 | 2026-10-29 | Store per-pet treat preferences | #done #pets #care | [2026-10](2026-10.md) |
| U-20261029-24 | 2026-10-29 | Add the pet treat menu | #done #pets #care | [2026-10](2026-10.md) |
| U-20261029-23 | 2026-10-29 | Add wardrobe style swatches | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261029-22 | 2026-10-29 | Accept the wardrobe background-install lifecycle | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261029-21 | 2026-10-29 | Run the pet regression set and native Puppet reactions | #done #pets #native | [2026-10](2026-10.md) |
| U-20261029-20 | 2026-10-29 | Add Puppet petting gestures | #done #puppet #interaction | [2026-10](2026-10.md) |
| U-20261029-19 | 2026-10-29 | Clean up mixed Puppet test processes | #done #puppet #tests | [2026-10](2026-10.md) |
| U-20261029-18 | 2026-10-29 | Accept Puppet transparent photos natively | #done #puppet #native | [2026-10](2026-10.md) |
| U-20261029-17 | 2026-10-29 | Map shared interactions to Puppet native reactions | #done #puppet #animation | [2026-10](2026-10.md) |
| U-20261029-16 | 2026-10-29 | Recover a selected pet | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261029-15 | 2026-10-29 | Show celebration and outfit presentations | #done #pets #animation | [2026-10](2026-10.md) |
| U-20261029-14 | 2026-10-29 | Keep the source appearance when cloning a pet | #done #pets #storage | [2026-10](2026-10.md) |
| U-20261029-13 | 2026-10-29 | Pilot switchable MOCHI faces | #done #pets #art | [2026-10](2026-10.md) |
| U-20261029-12 | 2026-10-29 | Add the light-spot toy | #done #pets #toys | [2026-10](2026-10.md) |
| U-20261029-11 | 2026-10-29 | Take Puppet photos | #done #puppet #photo | [2026-10](2026-10.md) |
| U-20261029-10 | 2026-10-29 | Integrate ball play with window perching | #done #pets #toys | [2026-10](2026-10.md) |
| U-20261029-09 | 2026-10-29 | Throw a ball the pet fetches | #done #pets #toys | [2026-10](2026-10.md) |
| U-20261029-08 | 2026-10-29 | Recognize direct petting gestures | #done #pets #interaction | [2026-10](2026-10.md) |
| U-20261029-07 | 2026-10-29 | Save transparent pet photos | #done #pets #photo | [2026-10](2026-10.md) |
| U-20261029-06 | 2026-10-29 | Choose character parts and restore them from outfits | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261029-05 | 2026-10-29 | Place pets safely during focus and specify per-character customization | #done #pets #focus | [2026-10](2026-10.md) |
| U-20261029-04 | 2026-10-29 | Drive companion modes from the focus timer | #done #pets #focus | [2026-10](2026-10.md) |
| U-20261029-03 | 2026-10-29 | Let social play follow each pet state | #done #pets #interaction | [2026-10](2026-10.md) |
| U-20261029-02 | 2026-10-29 | Keep pets when saving during close fails | #done #pets #storage | [2026-10](2026-10.md) |
| U-20261029-01 | 2026-10-29 | Pilot MOCHI animation assets | #done #pets #art | [2026-10](2026-10.md) |
| U-20261028-08 | 2026-10-28 | Recolor wardrobe regions per pet | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261028-07 | 2026-10-28 | Add the wardrobe interface | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261028-06 | 2026-10-28 | Install layered assets and restore them on restart | #done #pets #assets | [2026-10](2026-10.md) |
| U-20261028-05 | 2026-10-28 | Play layered outfits live on the desktop | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261028-04 | 2026-10-28 | Make wardrobe drafts transactional | #done #pets #wardrobe | [2026-10](2026-10.md) |
| U-20261028-03 | 2026-10-28 | Lay the layered pet rendering foundation | #done #pets #rendering | [2026-10](2026-10.md) |
| U-20261028-02 | 2026-10-28 | Add per-pet customization | #done #pets #ui | [2026-10](2026-10.md) |
| U-20261028-01 | 2026-10-28 | Design pet interactions, wardrobe and high-contrast chibi style | #decision #pets #design | [2026-10](2026-10.md) |
| U-20261022-02 | 2026-10-22 | Keep packaging checks and Qt test cleanup aligned | #bugfix #deps #ci | [2026-10](2026-10.md) |
| U-20261018-01 | 2026-10-18 | Reorganize the workspace around common actions and compact inspectors | #done #ui #ux | [2026-10](2026-10.md) |
| U-20261008-24 | 2026-10-08 | Complete delivery checks and verify the final compiled source | #done #ci #packaging | [2026-10](2026-10.md) |
| U-20261008-23 | 2026-10-08 | Check the native Mac fixture before exiting its Qt event loop | #done #macos #ci | [2026-10](2026-10.md) |
| U-20261008-22 | 2026-10-08 | Resolve owned Mac windows without depending on Quartz titles | #done #macos #ci | [2026-10](2026-10.md) |
| U-20261008-21 | 2026-10-08 | Make native acceptance failures explicit and clarify media lifecycle | #done #quality #packaging | [2026-10](2026-10.md) |
| U-20261008-20 | 2026-10-08 | Keep Python 3.10 builds compatible and isolate Mac unit frameworks | #done #ci #platform | [2026-10](2026-10.md) |
| U-20261008-19 | 2026-10-08 | Fix scene extraction aliases and platform-specific CI tests | #done #ci #scene | [2026-10](2026-10.md) |
| U-20261008-18 | 2026-10-08 | Verify all scene types in the current standalone Windows build | #done #packaging #scene | [2026-10](2026-10.md) |
| U-20261008-17 | 2026-10-08 | Verify composited Linux opacity pixels and restoration | #done #linux #native | [2026-10](2026-10.md) |
| U-20261008-16 | 2026-10-08 | Verify native Steam initialization failure without stopping client | #done #steam #native | [2026-10](2026-10.md) |
| U-20261008-15 | 2026-10-08 | Inject desktop prerequisites in monitor profile regression tests | #done #linux #tests | [2026-10](2026-10.md) |
| U-20261008-14 | 2026-10-08 | Add opt-in Linux audio and explicit X11 Wayland capabilities | #done #linux #platform | [2026-10](2026-10.md) |
| U-20261008-13 | 2026-10-08 | Cache static composition and share overlay plugin cleanup | #done #performance #plugins | [2026-10](2026-10.md) |
| U-20261008-12 | 2026-10-08 | Save bounded monitor profiles and adapt registered Qt overlays | #done #monitors #overlays | [2026-10](2026-10.md) |
| U-20261008-11 | 2026-10-08 | Follow selected Windows targets with temporary identity bindings | #done #windows #overlays | [2026-10](2026-10.md) |
| U-20261008-10 | 2026-10-08 | Organize static assets and review reference repair | #done #assets #scene | [2026-10](2026-10.md) |
| U-20261008-09 | 2026-10-08 | Persist local tasks and import calendar into Today widget | #done #widgets #calendar | [2026-10](2026-10.md) |
| U-20261008-08 | 2026-10-08 | Search opt-in capture history with local OCR | #done #capture #ocr | [2026-10](2026-10.md) |
| U-20261008-07 | 2026-10-08 | Pin live OCR with explicit local/cloud refresh | #done #ocr #capture | [2026-10](2026-10.md) |
| U-20261008-06 | 2026-10-08 | Reuse bounded opt-in image clipboard history | #done #clipboard #images | [2026-10](2026-10.md) |
| U-20261008-05 | 2026-10-08 | Persist select and edit multi-page whiteboards | #done #whiteboard #editor | [2026-10](2026-10.md) |
| U-20261008-04 | 2026-10-08 | Crop annotate and flatten captured images | #done #capture #editor | [2026-10](2026-10.md) |
| U-20261008-03 | 2026-10-08 | Create and preview portable sprite pet packs | #done #pets #editor | [2026-10](2026-10.md) |
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
| U-20261022-01 | 2026-10-22 | Keep dependency metadata aligned | #bugfix #deps #ci | [2026-10](2026-10.md) |
| U-20261012-03 | 2026-10-12 | Verify native macOS capture with an owned window identifier | #done #ci #tests | [2026-10](2026-10.md) |
| U-20261012-02 | 2026-10-12 | Isolate native unit-test frameworks and canonicalize Windows ACLs | #done #ci #tests | [2026-10](2026-10.md) |
| U-20261012-01 | 2026-10-12 | Fix macOS CI platform assumptions and scene extraction roots | #done #ci #tests | [2026-10](2026-10.md) |
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
| [2026-11.md](2026-11.md) | 2026-11 | 135 |
| [2026-10.md](2026-10.md) | 2026-10 | 129 |
| [2026-09.md](2026-09.md) | 2026-09 | 11 |
