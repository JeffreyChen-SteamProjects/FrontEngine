# CLAUDE.md - FrontEngine

PySide6 desktop overlay app (Python 3.10+, qt-material, PyOpenGL, numpy).
Published on PyPI as `frontengine` (stable, `stable.toml`) and `frontengine_dev`
(dev, `pyproject.toml`). What it does and how to run it: `README.md`.

## Session progress log (check first)

`progress.md` (repository root) lists outstanding work only. Read it before
planning so you resume where the last session stopped.

- While working, record pending items there; delete each one the moment it is
  done and record it in `docs/updates/` (see the stage-commit section below).
- It is tracked, so keep it free of anything that should not be public. Only
  `.claude/settings.local.json` stays ignored.
- Rules and standing knowledge live in this file ("Deliberately removed" and
  "Environment notes" below), never in `progress.md`.

## Architecture

`architecture_explore.md` (repository root) is the authoritative map: every
module, the layering and dependency direction, the overlay contract, the
cross-cutting conventions and the extension points. **Read it before planning
structural work** — it lists what has to change together (the control-center
registry, seven language dictionaries, seven documentation trees).

**Keep it current.** Any structural change updates it **in the same commit as
the code**:

- adding, removing, renaming or moving a module, package, page or overlay
- changing what a module is responsible for, or the dependency direction
- changing a cross-cutting convention (`BaseWidget` contract, control-center
  registration, threading rules, settings persistence)
- adding or removing an extension point

Behaviour changes inside a module that keep its stated responsibility need no
edit. When unsure, open the file and check whether it is still true — a stale
map gets trusted before anyone notices it drifted. Line counts there are
indicative; refresh them when you touch the surrounding entry, don't chase them.

## Conventions

**Security** — the boundaries that actually exist in this code:

- User-supplied paths (media, pet packs, capture targets) go through
  `pathlib.Path` and must stay inside their intended directory. Preset packages
  take only the final path segment when extracting (zip-slip).
- External data — scene JSON, `user_setting.json`, Workshop items, plugin
  manifests — is validated at the boundary; malformed entries are skipped or
  rejected explicitly, never trusted through.
- Subprocess calls use list form with `shell=False` and a fixed allow-list of
  absolute paths (see `utils/platform_info`). Never interpolate user input.
- API keys come from the environment only and are never written to a settings
  file. No secrets in the repository.

**Qt / performance**:

- `QTimer` over `time.sleep()`; never block the GUI thread. Cross-thread
  signals need an explicit `QueuedConnection`.
- Overlays set `WA_TranslucentBackground` + `WA_DeleteOnClose`, default to
  opacity 0.2, and take their refresh interval from `utils/power_mode` so the
  quality tier reaches them.
- Release media, timers and native handles in `closeEvent` — closing is what
  runs it, dropping a Python reference is not.

**Style** — type hints on public signatures; bilingual (Chinese/English)
comments where they already exist, English-only for new code; functions under
50 lines.

**Testing** — `python -m pytest tests/ -q`, headless (`QT_QPA_PLATFORM=offscreen`,
set by `conftest.py`). Everything must pass before a PR. Anything touching the
outside world takes an injectable source so it can be tested with a fake.

## Deliberately removed (do not re-add)

- **直播分頁整個拿掉了**（PR #186）：準心、提詞機、音效板、OBS 控制。
  OBS 那塊什麼都不顯示，只是連去按別的程式的按鈕，卻背了 435 行自己手寫的
  RFC 6455 與 OBS 5.x 協定，而且**從來沒跟真的 OBS 講過話**——測試驗的是我對
  規格的理解，不是 OBS 的行為。OBS 自己就有快速鍵。
  **虛擬攝影機留著**（工具頁在用，它送的是本專案自己的覆蓋層）。
- **臉部追蹤 Live2D**：需要 mediapipe 之類的臉部特徵點模型，這裡沒安裝也跑不起來，
  不想交出沒執行過的程式碼。麥克風對嘴（已完成）涵蓋了「說話時寵物會動」那部分。
- **通知彙整**：`UserNotificationListener` 需要 WinRT projection 套件，不是本專案相依，
  和離線 OCR 卡在同一道牆。

## Environment notes

- **分頁不再自己排版**：主視窗是左側 `NavigationSidebar` + `QStackedWidget`（沒有
  分頁列了），各分頁繼承 `ui/page/layout_kit.py` 的 `SettingPage`，用
  `add_section()` / `add_row()` / `add_slider_row()` 描述欄位。不要再回去寫
  `QGridLayout(self)` 加格子座標——那正是滑桿被拉到 1900px 寬的原因。
  樣式在 `ui/style/app_style.py`，顏色一律從 qt-material 色票算出來；
  `apply_stylesheet()` 會整份覆蓋樣式表，所以自訂樣式一定要接在它後面。
- 測試：headless（`QT_QPA_PLATFORM=offscreen`），用 `py` 不用 `python`。
  repo 內：`py -m pytest tests/ -q`。
- **改 UI 後要一併更新 docs/**。Sphinx 文件樹有七種語言（Eng / Zh / ZhCn / De /
  Ru / Fr / It），`test_documentation.py` 會檢查七棵樹頁面一致、圖片存在、
  沒有提到已移除的功能。加分頁時七種語言都要加，只加英文會被測試擋下來。
  建置驗證：`py -m sphinx -b html docs/source <暫存目錄>`，應該 0 警告。
- **改語言字典後跑 `test_translations.py`**。七種語言的鍵集合必須**完全一致**
  （不是「其他語言會 fallback」——測試會擋）。
  **語言檔是 LF 行尾**，其餘檔案是 CRLF；用腳本改時兩邊都要用 `newline=""` 開檔。
- **測語言要寫真的設定檔**：`read_user_setting()` 在 `reset_language()` 之前跑，
  直接改 `user_setting_dict` 會被蓋掉，七種語言會全部顯示英文（假通過）。
- **整批操作要用哨兵驗證**：往每個分頁的清單塞一個標記物件，再看
  `_all_overlay_widget_lists()` 撈不撈得到。
- **`QTimer.singleShot(0, callback)` 從背景執行緒呼叫永遠不會觸發**（計時器建在沒有
  事件迴圈的那條執行緒上）。一定要用三參數版 `singleShot(0, context_qobject, callback)`。
- **執行期會換字的按鈕要用 `retranslator.set_text`，不要用 `setText`**。
- **關閉覆蓋層要先 `close()` 再清清單**：只丟 Python 參考不會跑 `closeEvent`。
- **`QWidget::close()` 在 Qt 不是虛擬函式**：收尾邏輯要放在 `_shutdown()`。
- **用絕對路徑跑暫存目錄裡的腳本時要設 `PYTHONPATH`**：`sys.path[0]` 是腳本所在目錄。
- 靜態檢查：`py -m pyflakes frontengine/ exe/ tests/` **應該完全沒有輸出**。
- **測試不能有真實副作用**：`send_media_key()` 不帶 sender 在 Windows 上會**真的**
  按下播放鍵，把開發者正在聽的音樂暫停掉。測試一律注入假的 sender。
- **重構行為邏輯時的驗證方式**：用 `git show HEAD:<file>` 把舊版寫到暫存目錄、
  載成另一個模組，然後用相同的亂數種子逐步比對兩邊的狀態。
- **每個放 .py 的資料夾都要有 `__init__.py`**（`find = { namespaces = false }`）。
- **`requirements.txt` 要和 `pyproject.toml` 的 dependencies 一致**，也不能列 `frontengine` 自己。
- **CI 的啟動測試會先用 checkout 打包出 wheel 再安裝**，測的是眼前的程式碼。
- **offscreen 測不到**：原生視窗 handle（Win32 `SetWindowPos`）、音效卡、攝影機、
  虛擬桌面切換。
- **混合 DPI 的座標空間，純邏輯測試永遠看不出來**。Qt 的 `QScreen` 給的是**邏輯**
  像素，`GetWindowRect` / `SetWindowPos` 用的是**實體**像素；單一縮放比例下兩者
  完全相同，所以測試都會過。實機（100% + 125% 雙螢幕）上 Qt 說第二台是 1536x816、
  Win32 說是 1920x1020，差 25%。凡是要把 Qt 的螢幕座標餵給 Win32 呼叫的地方，
  都要改用 `EnumDisplayMonitors` + `GetMonitorInfoW` 的 rcWork（見 `monitor_move.py`）。
  另外跨 DPI 邊界時 Windows 會在 `SetWindowPos` **之後**自己依比例放大視窗，
  所以位置算完還要再夾一次。
- **驗證平台限定功能時，用自己建的視窗／虛擬桌面**，不要動使用者既有的東西；
  會有副作用的（媒體鍵、關閉虛擬桌面）用 `try/finally` 還原，並先確認狀態真的變了
  才送「恢復」那一步（沒生效就送第二次，反而會把還在播的東西暫停掉）。
- **`QPixmap`／`QMovie` 沒有 QApplication 會讓行程直接中止**；conftest 已建好。
- **Sonar 的抑制註解要標在它指出的那一行**，標在上一行完全沒作用。
  安全類規則（`pythonsecurity:*`）不吃 `# NOSONAR`，只能走 API 或網頁標記。
- **numpy 的 `reshape` 要傳 tuple**；色差平方要用 `int32`（`int16` 會溢位）。
- **行尾**：`.gitattributes` 是 `* text=auto`、`core.autocrlf=true`。
- **GitHub 掃整個 commit 訊息找 `[skip ci]`，包含內文**。在訊息裡「解釋」這個
  指令會把那個 commit 自己的 CI 也跳掉——實際發生過：那個為了 `[skip ci]` 而
  加上 `workflow_dispatch` 的 commit，就是這樣被自己跳過的。commit 訊息裡改用
  文字描述（「skip-CI 指令」），檔案內文則不受影響，可以照寫。
- **GitHub 上會留著已刪除 workflow 的清單項目**。`gh api .../actions/workflows`
  現在還列著 `Release Dev`（`release-dev.yml`，2026-04-21 建立、在 dev 跑過一次
  失敗、後來被 `b01858b` 刪掉），狀態顯示 `active` 但檔案不在任何分支上，
  所以不會再觸發。看到不認得的 workflow 先用 `git log --all -- <path>` 查它
  是不是遺留項目，不要以為有東西會偷跑。
- Codacy PR issues（**不要加 `-H "project-token: $CODACY_PROJECT_TOKEN"`**）：
  `curl -s "https://app.codacy.com/api/v3/analysis/organizations/gh/JeffreyChen-SteamProjects/repositories/FrontEngine/pull-requests/<PR>/issues?limit=100"`
  環境變數裡那個 `CODACY_PROJECT_TOKEN` **綁的是別的 repo**：帶著它查 FrontEngine，
  Codacy 會照 token 而不是照網址解析，回傳 `automation_file` 專案的 issue
  （`automation_file/`、`test_webdav_client.py` 之類這裡根本不存在的檔案）。
  公開 repo 不帶 token 就查得到，回的才是 FrontEngine 自己的。
- SonarCloud（PR 用 `&pullRequest=<PR>`，main 省略該參數）：
  `curl -s -u "$SonarCloudToken:" "https://sonarcloud.io/api/issues/search?componentKeys=JeffreyChen-SteamProjects_FrontEngine&resolved=false&ps=100"`
- **Codacy 可能卡在很大的 PR 上**（check 一直 `action_required`、PR 的 `files` 端點回 `total: 0`）。症狀、試過無效的做法與判斷方法見 `docs/updates/2026-09.md` U-20260922-02。

## Stage commits, `progress.md`, `docs/updates/` and `architecture.md`

Workspace rule shared by every repository under `D:\Codes` (full text: `D:\Codes\CLAUDE.md`).

- **Commit at every stage.** A stage is the smallest piece of work that leaves the repository consistent and passes this project's checks (definition of done, tests, lint): one finished `progress.md` item, or one self-contained step of a larger one. Commit it before starting the next stage, before switching to another repository, and before the session ends. Do not leave work uncommitted across sessions; if a stage cannot be finished, commit the consistent part and record the rest in `progress.md`.
  - Stage only the files that stage touched (`git add <path>`, never `git add -A`), follow this file's commit-message rules, and never add AI attribution.
  - Committing is not pushing: push or open a PR only as this project's branch flow says or when asked.
- **`progress.md`** (repository root, tracked) holds outstanding work only: no finished items, no history, no rules.
- **`docs/updates/`** records finished work: one batch file per month (`YYYY-MM.md`), one entry per piece of work headed `## U-YYYYMMDD-NN · date · title · #tags`, and an index with query commands in `docs/updates/README.md`. When a `progress.md` item is done, delete it and add a `#done` entry plus its index row in the same commit.
- **`architecture.md`** (repository root) is the short architecture overview: layers, entry points, main flows, extension points, cross-project boundaries. Update it in the same commit whenever a change alters any of those. `architecture_explore.md` stays the detailed per-module map under its own rule in this file.
- **Cross-project contracts** are listed in `architecture.md` §6: what other repositories rely on here (CLI flags, import paths, constructor arguments, file layouts) and what this repository relies on elsewhere. No test here protects them, so never rename or remove one without changing its consumers in the same round, and update §6 whenever a contract is added or changes.
- `Update Note.txt` stays the Steam announcement draft (format rules under "Release announcements"); it is not the update log.

## Git workflow

**Work flows `feature → dev → main`, and only the last step publishes.**

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release:
                               version bump, PyPI,
                               GitHub release, tag
```

- Branch features off `dev` and open the PR against `dev`. Merging there runs CI
  and publishes nothing, so features can accumulate.
- Release by opening a PR from `dev` to `main`. Merging it is what mints a
  version — that is the only thing that does.
- `release.yml` enforces this: it publishes only when the merged PR's head
  branch is `dev`. A feature PR aimed at `main` by mistake still merges, it just
  does not release, and a later `dev → main` picks it up. The failure direction
  is a missing release rather than an unwanted one.
- After a release the workflow fast-forwards `dev` to the released commit. If it
  reports that it could not (someone pushed to `dev` mid-release), run
  `git push origin main:dev` once the two are reconciled.
- Anything genuinely main-only — a hotfix, a released-version correction — can
  still go straight to `main`; it will not publish on its own. Use *Actions →
  Release → Run workflow* to publish deliberately.

Other rules:

- **Commits**: concise, imperative, say *what* and *why*.
  Good: `Fix particle widget memory leak on resize`. Bad: `update stuff`.
- **Authorship**: do NOT mention any AI tool or assistant in commit messages or
  `Co-Authored-By` lines. Commits are authored by the developer.
- **PRs**: one feature per PR, all CI green, and a structural change carries its
  `architecture_explore.md` update.
- **Versions**: `pyproject.toml` = dev, `stable.toml` = stable. Both are bumped
  by the release workflow — do not edit them by hand.
- **`[skip ci]` leaves no CI record.** The version bump and progress-log commits
  carry it, so a branch can end up on a HEAD that CI never ran against. Use
  *Actions → CI → Run workflow* to verify a branch on demand.
- **GitHub scans the whole commit message for the skip directive, body included.**
  Writing *about* it — explaining why a commit carries one — skips that commit's
  CI too. Describe it in prose ("the skip-CI directive") in commit messages;
  files may spell it out freely.

## Release announcements

`Update Note.txt` is the Steam announcement. It is **BBCode, not Markdown** —
`**bold**` and `### heading` would appear literally.

- Tags: `[h2]`, `[b]`, `[list]`/`[*]`, `[hr][/hr]`. There is no inline code —
  write formats and variable names as prose, or leave them out.
- **One paragraph per line, however long.** Steam turns a single newline into a
  hard line break, so 80-column wrapping arrives broken mid-sentence.
- `.txt` on purpose: BBCode in a `.md` renders as noise on GitHub.
- No title inside the file (Steam has its own field) and no `[img]` tags —
  screenshots are uploaded to Steam first and referenced by the URL it returns.
- **No version number.** Every merge to `main` bumps the version, so whatever is
  written is wrong the moment it lands. State the window the announcement
  covers instead.

Announce what a user can see. Workflow fixes, lint debt and tracked files do
not belong in it.
