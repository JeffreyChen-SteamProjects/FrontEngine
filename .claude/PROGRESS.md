# 進度記錄檔（本機暫存，未納入版控）

> 用途：跨 session 記錄「進行中／未完成」的工作。**全部事項做完就清空本檔**（只留下方標題與說明）。
> 更新規則：開始一項工作時寫進「進行中」；完成並合併後移到「已完成（本波）」或直接刪除；全清後恢復空白。

---

## 進行中 / 待辦

（無）

---

## 已知但刻意保留

- **PyPI 上的 v1.0.39 / v1.0.40 是壞的**（缺 `__init__.py` 導致 import 失敗）。
  要不要 yank 由專案擁有者決定，需要 PyPI 憑證，我沒有動。v1.0.41 之後都正常。
- **PyPI 上的 `frontengine_dev` 還停在 1.0.0**，pyproject 已經是 1.0.48；
  workflow 裡沒有發佈 dev 套件的步驟。要不要補由專案擁有者決定（需要 PyPI 憑證）。
- **main 上有 3 筆既有的 SonarCloud `python:S1192`（2026-07-26 產生，不是 PR #193 帶進來的）**：
  `italy.py` 的 "Velocità"、`russian.py` 的 "Скорость" 與 "Удалить"。
  已用 `git show d564f33:` 比對過，合併前後出現次數完全相同（3/3/4）。
  這是語言字典的典型誤判——同一個詞本來就會當成好幾個鍵的值，抽成常數只會讓
  翻譯者看到變數名而不是譯文。要處理的話走 API 標 `falsepositive` 並寫清楚理由，
  不要真的抽常數。quality gate 仍是 OK（門檻只看新程式碼）。
- SonarCloud 上有一筆 `pythonsecurity:S6549`（寵物音效路徑）標成 **WONTFIX** 並附了理由：
  路徑確實來自外部資料，但下一行就用 `acceptable_sound` 驗證（必須是既存的音訊檔），
  唯一用途是播放音效，再收緊會擋掉「使用者自己挑音效」這個正常情境。

---

## 下一步候選（未動工）

1. 本機離線 OCR（Windows.Media.Ocr）需要 WinRT 投影套件，目前沒有。
2. 音訊頻譜、視窗釘選／版面、螢幕錄影只有 Windows 完整支援。
3. 「正在播放」的歌名需要選用套件 `winsdk`。
4. Steam Workshop 的**發布**需要 Steamworks SDK 與 App 憑證。

---

## 刻意移除的（不要再實作回來）

- **直播分頁整個拿掉了**（PR #186）：準心、提詞機、音效板、OBS 控制。
  OBS 那塊什麼都不顯示，只是連去按別的程式的按鈕，卻背了 435 行自己手寫的
  RFC 6455 與 OBS 5.x 協定，而且**從來沒跟真的 OBS 講過話**——測試驗的是我對
  規格的理解，不是 OBS 的行為。OBS 自己就有快速鍵。
  **虛擬攝影機留著**（工具頁在用，它送的是本專案自己的覆蓋層）。
5. **臉部追蹤 Live2D**：需要 mediapipe 之類的臉部特徵點模型，這裡沒安裝也跑不起來，
   不想交出沒執行過的程式碼。麥克風對嘴（已完成）涵蓋了「說話時寵物會動」那部分。
6. **通知彙整**：`UserNotificationListener` 需要 WinRT projection 套件，不是本專案相依，
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
  repo 內：`py -m pytest tests/ -q`（main 目前 840 passed）。
- **改 UI 後要一併更新 docs/**。Sphinx 文件樹有七種語言（Eng / Zh / ZhCn / De /
  Ru / Fr / It），`test_documentation.py` 會檢查七棵樹頁面一致、圖片存在、
  沒有提到已移除的功能。加分頁時七種語言都要加，只加英文會被測試擋下來。
  建置驗證：`py -m sphinx -b html docs/source <暫存目錄>`，應該 0 警告。
- **改語言字典後跑 `test_translations.py`**。七種語言的鍵集合必須完全一致：
  之前英文／繁中到 529 鍵，其餘五種還停在 125，而且有一個鍵是用沒有 fallback
  的 `.get("key")` 取用的，訊息框就直接顯示 "None"。測試把這件事釘住了。
- **測語言要寫真的設定檔**：`read_user_setting()` 在 `reset_language()` 之前跑，
  直接改 `user_setting_dict` 會被蓋掉，七種語言會全部顯示英文（假通過）。
- **整批操作要用哨兵驗證**：往每個分頁的清單塞一個標記物件，再看
  `_all_overlay_widget_lists()` 撈不撈得到。之前「全部關閉」漏掉一堆
  後來註冊進來的覆蓋層，隱藏／顯示卻是好的，光看畫面看不出來。
- **SonarCloud 目前 0 issues、quality gate OK**（從 81 筆降到 0）。
  `$SonarCloudToken` 除了讀，也**可以**改狀態：
  `api/issues/do_transition`（`falsepositive` / `wontfix` / `reopen`）與
  `api/issues/add_comment`。真的要標記時務必寫清楚理由，不要無聲抑制。
- **`QTimer.singleShot(0, callback)` 從背景執行緒呼叫永遠不會觸發**（計時器建在沒有
  事件迴圈的那條執行緒上）。一定要用三參數版 `singleShot(0, context_qobject, callback)`。
  寵物 AI 對話與螢幕文字辨識都是這樣整個功能失效的。
- **執行期會換字的按鈕要用 `retranslator.set_text`，不要用 `setText`**。用 setText 的話
  換語言時按鈕會跳回「開始」，但覆蓋層其實還開著，狀態就對不上了。
- **關閉覆蓋層要先 `close()` 再清清單**：只丟 Python 參考不會跑 `closeEvent`，
  計時器、媒體、全域監聽都停不掉。
- **`QWidget::close()` 在 Qt 不是虛擬函式**：從標題列 X、登出、`closeAllWindows()`
  關閉時只會走到 `closeEvent`，Python 這邊的 `close()` 覆寫永遠不會被呼叫。
  收尾邏輯要放在 `_shutdown()` 並由兩邊各自呼叫。
- **用絕對路徑跑暫存目錄裡的腳本時要設 `PYTHONPATH`**：`sys.path[0]` 是腳本所在
  目錄而不是工作目錄，不設就會 `ModuleNotFoundError: frontengine.ui.page.focus`。
- 靜態檢查：`py -m pyflakes frontengine/ exe/ tests/` **現在應該完全沒有輸出**。
  以前 `particle_ui.py` 的 `from OpenGL.GL import *` 會產生上百筆雜訊，
  等於整個檔案的未定義名稱檢查失效；現在 35 個名稱都明列。
  **看到任何輸出就是真的有問題**，不要再手動過濾。
- **重構行為邏輯時的驗證方式**：用 `git show HEAD:<file>` 把舊版寫到暫存目錄、
  載成另一個模組，然後用相同的亂數種子逐步比對兩邊的狀態。這次寵物移動
  （320 情境 × 400 步）、粒子（100 次 × 300 步）、打招呼（600 情境）都是這樣
  證明「行為完全沒變」，比只看測試綠燈可靠得多。
- **每個放 .py 的資料夾都要有 `__init__.py`**（`find = { namespaces = false }`），
  少一個那個子套件就不會進 wheel。`test_public_api.py` 有測試守著。
- **`requirements.txt` 要和 `pyproject.toml` 的 dependencies 一致**，也不能列
  `frontengine` 自己。同樣有測試守著。
- **CI 的啟動測試會先用 checkout 打包出 wheel 再安裝**，測的是眼前的程式碼。
- **offscreen 測不到**：原生視窗 handle（Win32 `SetWindowPos`）、音效卡、攝影機。
- **`QPixmap`／`QMovie` 沒有 QApplication 會讓行程直接中止**；conftest 已建好。
- **Sonar 的抑制註解要標在它指出的那一行**，標在上一行完全沒作用。
  常見誤判：`for x in list(self.xs)` → 改用 `self.xs[:]`；i18n 裡含 password 的鍵
  → `# NOSONAR`；RFC 規定的 SHA-1 → `# nosec B324 # nosemgrep # NOSONAR`。
  安全類規則（`pythonsecurity:*`）不吃 `# NOSONAR`，只能走 API 或網頁標記。
- **numpy 的 `reshape` 要傳 tuple**；色差平方要用 `int32`（`int16` 會溢位）。
- **行尾**：`.gitattributes` 是 `* text=auto`、`core.autocrlf=true`。
  用 Python 腳本改檔時，`read_text` 會把 CRLF 讀成 LF，就算寫回時用
  `newline=""` 也只會寫出 LF——工作目錄整份變成 LF。改完要自己轉回 CRLF。
- Codacy PR issues：
  `curl -s "https://app.codacy.com/api/v3/analysis/organizations/gh/JeffreyChen-SteamProjects/repositories/FrontEngine/pull-requests/<PR>/issues?limit=100" -H "project-token: $CODACY_PROJECT_TOKEN"`
- SonarCloud（PR 用 `&pullRequest=<PR>`，main 省略該參數）：
  `curl -s -u "$SonarCloudToken:" "https://sonarcloud.io/api/issues/search?componentKeys=JeffreyChen-SteamProjects_FrontEngine&resolved=false&ps=100"`
