# 進度記錄檔

> 用途：跨 session 記錄「進行中／未完成」的工作。**全部事項做完就清空本檔**（只留下方標題與說明）。
> 更新規則：開始一項工作時寫進「進行中」；完成並合併後移到「已完成（本波）」或直接刪除；全清後恢復空白。

---

## 進行中 / 待辦

**六項新功能已全部實作並驗證，但尚未 commit**（使用者沒有要求提交）。
`py -m pytest tests/ -q` = 1170 passed，pyflakes 無輸出，offscreen 啟動測試 exit 0。

1. **系統監控加電池與網路** — `system_stats.sample()` 新增 `battery` /
   `battery_state` / `down_bytes` / `up_bytes`（電池讀數借自 `platform_info`
   並快取 30 秒，因為 macOS 要 fork `pmset` 而監控是每秒取樣）。
   `monitor_widget` 的折線改成百分比／速率兩種，使用者勾選要顯示哪幾條。
2. **`{欄位}` 提示** — `SAMPLE_FIELDS` / `FORECAST_FIELDS` 宣告可用欄位，
   文字分頁直接列出來。原本欄位清單寫死在翻譯字串裡而且**已經漂掉**
   （system 列 7 個、實際 9 個；weather 列 5 個、實際 6 個），現在由測試釘住。
3. **媒體播放控制** — `utils/media_keys/`，ctypes `keybd_event` 送 VK_MEDIA_*，
   不需要 WinRT。接上快速鍵／手機遙控／MIDI。
4. **按鍵顯示補滑鼠與樣式** — `InputWatchService` 新增 `mouse_pressed(str)` 訊號
   （座標與按鍵拆兩個訊號，漣漪與按鍵顯示各取所需）；位置／字級／是否顯示滑鼠可調。
5. **虛擬桌面感知** — `utils/virtual_desktop/`，只用有文件的
   `IVirtualDesktopManager::IsWindowOnCurrentVirtualDesktop`。控制中心多一顆
   「綁在這個虛擬桌面」。
6. **視窗搬到下一個螢幕** — `utils/window_pin/monitor_move.py`，保留相對位置與大小。
7. **條件式規則引擎** — `utils/rules/rule_engine.py` + `ui/dialog/rules_dialog.py`，
   設定選單多一項「條件式規則…」。既有四套排程都留著，這裡補的是它們之間的組合。

### 真機驗證結果（2026-08-03，Windows 11，雙螢幕 100% + 125%）

三項全部實測通過。驗證腳本用的是**自己建的視窗與自己建的虛擬桌面**，
沒有動到使用者既有的視窗。

- **虛擬桌面**：自己桌面 True → 建新桌面切過去 False → 服務確實把視窗藏起來 →
  切回來 True → 服務確實還原。整條路成立。
- **媒體鍵**：對正在播放的 Edge 送一次播放/暫停，WASAPI 出聲工作階段消失，
  再送一次回來。鍵真的到得了播放器。
- **搬視窗**：位置相對比例精準對應，落地後完整在目標螢幕內，循環回第一台。

**真機抓到、offscreen 抓不到的兩件事（都已修）**：

1. **DPI 座標空間錯誤**（真 bug）。`screen_rects()` 原本回傳 Qt 的**邏輯**像素，
   但 `GetWindowRect` / `SetWindowPos` 用的是**實體**像素。單一縮放比例下兩者
   剛好相同，所以純邏輯測試永遠看不出來；在 100% + 125% 的雙螢幕上，Qt 說第二台
   是 1536x816、Win32 說是 1920x1020，差 25%，視窗會照著一個小四分之一的螢幕擺放。
   已改成 `EnumDisplayMonitors` + `GetMonitorInfoW` 的 rcWork。
2. **跨 DPI 時 Windows 會在我們之後再放大視窗**（`WM_DPICHANGED`，實測 x1.25）。
   那是對的（維持視覺大小），但發生在我們算完位置之後，貼齊右緣的視窗會被推出
   畫面。已加 `_settle_inside_screen()`：落地後讀回實際位置再夾一次。
   兩件事都補了單元測試（`test_monitor_move.py`）。

另外修正一個測試的錯誤假設：`IsWindowOnCurrentVirtualDesktop` 對不認識的 handle
回傳 **S_OK + True**（不是 False 也不是錯誤）。程式本來就是安全的（關掉的覆蓋層
不會被誤藏），是我原本的預期寫錯了。`GetWindowDesktopId` 相對嚴謹，同樣的 handle
會回 `TYPE_E_ELEMENTNOTFOUND`——拿它交叉驗證確認了 vtable 索引是對的。

---

## 已知但刻意保留

- **PyPI 上的 v1.0.39 / v1.0.40 是壞的**（缺 `__init__.py` 導致 import 失敗）。
  要不要 yank 由專案擁有者決定，需要 PyPI 憑證，我沒有動。v1.0.41 之後都正常。
- **PyPI 上的 `frontengine_dev` 還停在 1.0.0**，pyproject 已經是 1.0.76；
  workflow 裡沒有發佈 dev 套件的步驟。要不要補由專案擁有者決定（需要 PyPI 憑證）。
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
  repo 內：`py -m pytest tests/ -q`（目前 1170 passed）。
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
- **`QPixmap`／`QMovie` 沒有 QApplication 會讓行程直接中止**；conftest 已建好。
- **Sonar 的抑制註解要標在它指出的那一行**，標在上一行完全沒作用。
  安全類規則（`pythonsecurity:*`）不吃 `# NOSONAR`，只能走 API 或網頁標記。
- **numpy 的 `reshape` 要傳 tuple**；色差平方要用 `int32`（`int16` 會溢位）。
- **行尾**：`.gitattributes` 是 `* text=auto`、`core.autocrlf=true`。
- Codacy PR issues：
  `curl -s "https://app.codacy.com/api/v3/analysis/organizations/gh/JeffreyChen-SteamProjects/repositories/FrontEngine/pull-requests/<PR>/issues?limit=100" -H "project-token: $CODACY_PROJECT_TOKEN"`
- SonarCloud（PR 用 `&pullRequest=<PR>`，main 省略該參數）：
  `curl -s -u "$SonarCloudToken:" "https://sonarcloud.io/api/issues/search?componentKeys=JeffreyChen-SteamProjects_FrontEngine&resolved=false&ps=100"`
