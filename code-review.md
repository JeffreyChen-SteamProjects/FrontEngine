# 程式審核：FrontEngine

## 審核者

- 審核者：工作區程式審核
- 日期：2026-10-22
- 對象：`FrontEngine`（套件 `frontengine/`；桌面覆蓋層工作樹熱點）
- 結論：需修正

## 審核規範

共通規範在工作區 repo [JE-Chen/Codes](https://github.com/JE-Chen/Codes) 的 `docs/code-review-standard.md`。下面留下 2026-10-22 這次審核所用的條款，讓審核紀錄的依據對得上那一次。之後的審核以工作區那份為準。本專案更嚴的條款仍以本節與本專案的 `CLAUDE.md` 為準。

1. 設計：分層、依賴方向與既有契約是否仍成立。
2. 可讀性：圈複雜度 15、函式 80 行、巢狀 4、參數 7、行寬 120；專案更嚴者從嚴。
3. 錯誤處理：失敗要看得見；不可把權限或隱私失敗當成成功。
4. 死碼：熱點路徑上是否留著不會執行、卻仍改變行為的分支。
5. 型別與 docstring：公開介面有型別；註解與實作一致。
6. 安全：覆蓋層權限、子行程、動態執行、使用者設定檔路徑、例外是否被吞。
7. 測試：熱點行為是否有可對上的測試邊界（本次不執行測試）。
8. 效能：覆蓋層不在本次熱點裡新增會堵住 GUI 的路徑。
9. §6：跨專案邊界（嵌入建構子、工作目錄設定、PySide6 版本腳位）未被熱點改寫。
10. 文件同步：使用者看得到的說明與覆蓋層實際權限一致。

嚴重度：缺陷（行為與安全承諾不符，未關閉即不可通過）、建議（應修，尚無立即損害）、備註（已核對、不立案）。通過＝無未關閉缺陷；有條件通過＝無立即損害；需修正＝有未關閉缺陷。

## 審核紀錄

### 方法

讀 `architecture.md`（含 §6、§7）、`CLAUDE.md` 慣例與進度段、`progress.md` 前 80 行。未整份讀 `architecture_explore.md`。在 `frontengine/` 的 `*.py` 檢索 `eval(`、`exec(`、`shell=True`、`pickle`、`yaml.load`、`verify=False`、裸 `except:`、`subprocess`（不含 `tests/`、`build/`、`__pycache__`；略過 `steam_sdk/`）。每一則發現都先讀過對應原始碼。未改其他檔、未執行 git、未跑測試、未啟動 GUI、未載入套件。

### 總評

子行程主路徑維持 `shell=False`，沒有 Python `eval`、`pickle`、`yaml.load` 或 `verify=False`。外掛預設關閉，且授權綁在內容摘要上。手機遙控預設關閉、每次啟動換權杖、只綁區域位址與固定動作。設定檔仍在工作目錄，與架構契約一致。

未通過的原因是分享隱私：排除擷取只在切換當下套到當時已存在的覆蓋層，隨後的提示仍宣稱已經隱藏。這會在使用者開啟該功能時，把新覆蓋層和提示卡本身送進擷取畫面。

### 發現

#### CR-01

- 嚴重度：缺陷
- 位置：`frontengine/ui/page/control_center/control_center_ui.py`（`set_hide_from_capture`，約 477–504 行）；`frontengine/ui/main_ui.py`（`_on_sharing_changed`，約 969–983 行）；`frontengine/show/toast/toast_widget.py`（`show_toast`，約 129–143 行）；`frontengine/show/base_widget.py`（`showEvent`，約 145–153 行）；`frontengine/utils/screen_privacy/capture_affinity.py`（`apply_to_widget`，約 98–111 行）
- 說明：`WDA_EXCLUDEFROMCAPTURE` 只在呼叫當下走一遍現有清單。旗標先寫成已隱藏，按鈕文字也改成已隱藏，不管 `apply_to_widget` 是否回傳 False。分享狀態變為真之後，`_on_sharing_changed` 不看成功次數，一律跳出「覆蓋層已從擷取隱藏」的提示。該提示在掃描之後才建立，不在任何覆蓋層清單裡，本身不會被排除。其後新開的覆蓋層也不讀 `_hidden_from_capture`，`showEvent` 沒有補套。非 Windows 上親和性一律做不到，但若設定檔把功能打開，提示仍會說已隱藏。
- 依據：安全（覆蓋層擷取隱私）；錯誤處理（失敗仍對使用者顯示成功）。`capture_affinity` 自己的說明寫這是隱私而不是保全，但連這條普通擷取管道都沒有維持到新視窗。
- 狀態：未關閉
- 建議：覆蓋層顯示後若控制中心仍處於隱藏擷取，要補套親和性並在關閉時還原。提示卡若在此狀態下出現，必須一併排除，或改成不宣稱成功。`applied == 0` 或平台不支援時，不要顯示成功提示。

#### CR-02

- 嚴重度：建議
- 位置：`frontengine/show/scene/compositor_view.py` 第 35 行；`frontengine/show/scene/extend_graphic_view.py` 第 22–26 行；`frontengine/ui/page/scene_setting/scene_manager.py` 第 199 行；`frontengine/utils/multi_language/english.py` 的 `how_to_use_clicks_body`（約 712–713 行；其他語言字典有同一鍵）
- 說明：場景合成視窗以 `allow_input=True` 建立，舊的 `ExtendGraphicView` 未加點擊穿透，播放時 `showMaximized()`。滑鼠用來平移、縮放與雙擊互動，因此一整個螢幕的點擊不會落到下面的程式。使用說明仍寫只有寵物與簡報塗鴉會接收滑鼠。白板、便利貼、待辦、框選與量尺也預設接收輸入。全域鎖定對未設 `overlay_lockable = False` 的視窗仍可改回穿透，但預設狀態與說明不符。
- 依據：文件同步；設計（覆蓋層點擊穿透契約）。程式裡的滑鼠行為是刻意的，所以不列為缺陷，但使用者看到的承諾是錯的。
- 狀態：未關閉
- 建議：場景預設改為穿透，需要互動時再解鎖；或在全部語言的使用說明裡寫明哪些覆蓋層會吃掉點擊，以及最大化場景會擋住桌面。

#### CR-03

- 嚴重度：建議
- 位置：`frontengine/utils/keep_awake/keep_awake.py` 第 39–52 行與第 136–138 行；`frontengine/utils/screen_text/local_ocr.py` 第 148–167 行
- 說明：兩處都是 `shell=False`，參數也沒有把使用者字串拼進 shell。Linux 保持喚醒的執行檔是 `systemd-inhibit`，經 `shutil.which` 沿 `PATH` 尋找，不是絕對路徑。Tesseract 同樣用 `which("tesseract")` 再 `resolve()`。對照 `utils/linux/capabilities.py` 的 `parec` 與 `utils/platform_info/platform_info.py` 的固定絕對路徑清單，這兩處沒有達到專案自己的子行程規則。`PATH` 上同名程式可在功能開啟時被啟動。預設安裝下沒有立即的遠端利用鏈。
- 依據：安全（子行程絕對路徑白名單）；§7 與慣例中的安全段。
- 狀態：未關閉
- 建議：與 `parec` 相同，只接受寫死的絕對路徑；找不到就回報做不到，不要搜尋 `PATH`。

#### CR-04

- 嚴重度：建議
- 位置：`frontengine/show/focus_shield/focus_shield_widget.py` 第 110–115 行；`frontengine/utils/focus_shield/focus_shield.py` 第 44–54 行；`frontengine/show/screen_care/screen_filter.py` 第 125–130 行；`frontengine/show/spectrum/spectrum_widget.py` 第 111–118 行；`frontengine/show/wallpaper/wallpaper_widget.py` 第 127–135 行
- 說明：這些週期回呼用 `except Exception` 吃掉錯誤且不記 log。聚焦遮罩把失敗當成「沒有前景視窗」，`surrounding_rects` 於是把整塊螢幕壓暗。閱讀尺、頻譜與桌布音量反應則停在原位或縮回最小，畫面上看不出查詢失敗。方向是多遮或少更新，不是把權限悄悄打開。系統監控的取樣失敗有記 log，不在此列。
- 依據：錯誤處理。裸 `except:` 不存在；這裡是過寬的 `except Exception` 加上無紀錄。
- 狀態：未關閉
- 建議：至少記下例外型別與訊息。聚焦遮罩失敗時不要改成整屏壓暗，除非那是明示的降級狀態。

#### CR-05

- 嚴重度：建議
- 位置：`frontengine/show/particle/particle_ui.py` 第 90–100 行
- 說明：粒子視窗先用共用旗標設成點擊穿透，稍後 `apply_winapi` 讀取延伸樣式再 OR 上 `WS_EX_LAYERED`。`GetWindowLongW` 失敗時回傳 0，程式不檢查，接著寫回的樣式只剩 `WS_EX_LAYERED`，`WS_EX_TRANSPARENT` 會消失，穿透被拿掉。成功時既有位元會保留。
- 依據：安全（覆蓋層點擊穿透）。只在 Win32 讀樣式失敗時發生。
- 狀態：未關閉
- 建議：讀取失敗就不要改樣式；用 `GetWindowLongPtrW`／`SetWindowLongPtrW`，並確認寫入後透明穿透位元仍在。

沒有第 6 則。下列項目檢索或閱讀後不立案，理由見「已核對」。

### 已核對

- `eval(`、`pickle`、`yaml.load`、`verify=False`、`shell=True`、裸 `except:`：`frontengine/` 內無相符程式。檢索到的 `exec(` 是 Qt 對話框的 `exec()`，以及外掛載入的 `exec_module`。
- 外掛：`plugin_loader.py` 預設不載入；`plugin_manifest.py` 拒絕符號連結與逸出目錄，授權比對內容摘要，對話框預設為否。`except BaseException` 見於外掛以外的復原路徑，且會再拋出，沒有吞掉。
- 子行程白名單本體：`platform_info.py` 只跑固定絕對路徑，`shell=False`；`parec` 只接受 `/usr/bin/parec` 與 `/bin/parec`。保持喚醒的 macOS 參數是 `/usr/bin/caffeinate`。
- 設定檔：`user_setting_file.py` 讀寫 `getcwd()/user_setting.json`，與 `architecture.md` §3 一致。匯入／匯出會拿掉 `plugin_grants`。壞檔由 `JsonRepository.load_into` 留下警告並沿用預設，不會讓啟動崩潰。手機遙控在設定啟用時才 `start()`，權杖不寫入設定檔。
- 預設集 zip：`preset_repository.py` 解媒體時只用路徑最後一段。
- §6：熱點沒有改 `FrontEngineMainUI` 的建構子關鍵字、CLI，或 Imervue 的讀取邊界。建構子仍會讀工作目錄設定並啟動熱鍵與背景服務，這是已記載的副作用。
- `progress.md` 前 80 行僅有實機阻塞項（macOS、Steam 離線、第二螢幕），與本次程式缺陷無衝突。

### 未涵蓋

- 未跑測試、靜態檢查或 GUI。未量全庫圈複雜度、函式長度、巢狀與參數個數。
- 未讀完 `architecture_explore.md`，未逐頁對七種語文說明與 README。
- 未確認 Win32 子視窗（OpenGL、WebEngine）是否跟著父視窗的 DisplayAffinity。未在實機驗證混合 DPI 與 macOS TCC（`progress.md` #9、#21、#22）。
- 未審 `steam_sdk/`、`build/`、`tests/` 內的實作。PySide6 四份版本腳位只對過 §6 文字，未逐檔比對。

### 本專案加嚴

- 函式長度以慣例的 50 行為準，嚴於本次規範的 80 行。本次未做全庫計量，不另立超長函式缺陷。
- 子行程必須是固定絕對路徑且 `shell=False`，嚴於「不要用 shell」而已。CR-03 依此立案。
- 使用者路徑須留在意圖中的目錄；工作目錄設定檔是 §3 的意圖位置，不把「檔案在 cwd」本身當成缺陷。
- 新程式註解應為英文。熱點裡中英並存的註解屬於既有檔案，不另立案。

### 結論

需修正。發現 5 則：缺陷 1（CR-01，未關閉），建議 4（CR-02 至 CR-05，未關閉）。沒有立即的遠端程式執行或設定檔越界寫入；不能通過，是因為分享隱私在功能開啟時會把之後出現的覆蓋層和提示卡留在擷取畫面裡，並向使用者顯示已隱藏。
