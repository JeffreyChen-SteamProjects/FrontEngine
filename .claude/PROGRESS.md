# 進度記錄檔

> 用途：跨 session 記錄「進行中／未完成」的工作。**全部事項做完就清空本檔**（只留下方標題與說明）。
> 更新規則：開始一項工作時寫進「進行中」；完成並合併後移到「已完成（本波）」或直接刪除；全清後恢復空白。

---

## 進行中 / 待辦

（無）

---

## 已知但刻意保留

- **PyPI 上的 v1.0.39 / v1.0.40 是壞的**（缺 `__init__.py` 導致 import 失敗）。
  要不要 yank 由專案擁有者決定，需要 PyPI 憑證，我沒有動。v1.0.41 之後都正常。
- **PyPI 上的 `frontengine_dev` 還停在 1.0.0**，pyproject 已經跟著 stable 走到 1.0.77；
  workflow 裡沒有發佈 dev 套件的步驟。要不要補由專案擁有者決定（需要 PyPI 憑證）。
- **Codacy 對大 PR 會卡住**（PR #216，68 檔案 / +9087 −5290，最後帶著紅的 Codacy 合併）。
  症狀：check 一直是 `action_required`，但它自己回報 0 個 issue、0 個 annotation、
  summary 空白，而且 **PR 的 `files` 端點回傳 `total: 0`**——它認為這個 PR 沒有變更
  檔案，所以算不出 diff。同一個 commit 在 **commit 層級**的 gate 是過的
  （`newIssues: 0`、`isUpToStandards: true`），所以不是程式碼問題。
  試過無效：關掉再重開 PR、推新 commit（三次，每次都真的重新分析）、
  `POST check-runs/{id}/rerequest`（404）、`POST .../reanalyze`（404）。
  要清掉需要帳號層級權限（Codacy 網頁的 Re-analyse 或帳號 api-token）。
  判斷方法：完整的 PR 分析會有 `isUpToStandards` / `newIssues` / `quality` / `coverage`，
  卡住的只有 `analyzable: true`。
- **`pyproject.toml` / `stable.toml` 的 Homepage 指向 `Intergration-Automation-Testing`**，
  但 origin 已經是 `JeffreyChen-SteamProjects`。README 用的是 origin，套件 metadata 沒動
  （會影響 PyPI 頁面，留給擁有者決定）。
- **`dev_requirements.txt` 沒有 pyflakes**，但專案實際用它做靜態檢查。
  README 標成需要另外安裝；也可以改成加進 dev_requirements。
- SonarCloud 上有一筆 `pythonsecurity:S6549`（寵物音效路徑）標成 **WONTFIX** 並附了理由。

---

## 下一步候選（未動工）

1. 本機離線 OCR（Windows.Media.Ocr）需要 WinRT 投影套件，目前沒有。
2. 音訊頻譜、視窗釘選／版面、螢幕錄影只有 Windows 完整支援。
3. 「正在播放」的歌名需要選用套件 `winsdk`。
4. Steam Workshop 的**發布**需要 Steamworks SDK 與 App 憑證。
5. **Steam 商店頁目前只有 2 則評論、討論區 0 個主題**——沒有真實使用者需求訊號。
   功能取捨目前是靠鄰近產品（Lively、Rainmeter、PowerToys、DisplayFusion）推論的。

---

## 刻意移除的（不要再實作回來）

- **直播分頁整個拿掉了**（PR #186）：準心、提詞機、音效板、OBS 控制。
  OBS 那塊什麼都不顯示，只是連去按別的程式的按鈕，卻背了 435 行自己手寫的
  RFC 6455 與 OBS 5.x 協定，而且**從來沒跟真的 OBS 講過話**——測試驗的是我對
  規格的理解，不是 OBS 的行為。OBS 自己就有快速鍵。
  **虛擬攝影機留著**（工具頁在用，它送的是本專案自己的覆蓋層）。
- **臉部追蹤 Live2D**：需要 mediapipe 之類的臉部特徵點模型，這裡沒安裝也跑不起來，
  不想交出沒執行過的程式碼。麥克風對嘴（已完成）涵蓋了「說話時寵物會動」那部分。
- **通知彙整**：`UserNotificationListener` 需要 WinRT projection 套件，不是本專案相依，
  和第 1 項離線 OCR 卡在同一道牆。

---

## 環境備忘

- **分頁不再自己排版**：主視窗是左側 `NavigationSidebar` + `QStackedWidget`（沒有
  分頁列了），各分頁繼承 `ui/page/layout_kit.py` 的 `SettingPage`，用
  `add_section()` / `add_row()` / `add_slider_row()` 描述欄位。不要再回去寫
  `QGridLayout(self)` 加格子座標——那正是滑桿被拉到 1900px 寬的原因。
  樣式在 `ui/style/app_style.py`，顏色一律從 qt-material 色票算出來；
  `apply_stylesheet()` 會整份覆蓋樣式表，所以自訂樣式一定要接在它後面。
- 測試：headless（`QT_QPA_PLATFORM=offscreen`），用 `py` 不用 `python`。
  repo 內：`py -m pytest tests/ -q`（目前 1175 passed）。
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
