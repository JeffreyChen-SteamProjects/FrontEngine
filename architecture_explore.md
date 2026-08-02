# FrontEngine 架構探勘 / Architecture Exploration

> 本檔是一次完整的原始碼掃描結果，逐一記錄每個模組的職責、彼此的相依方向，
> 以及跨模組的共同約定。用途是讓人在動手改之前先知道「東西放在哪、為什麼放在那」。
>
> 掃描範圍：`frontengine/` 267 個 `.py`、約 28,900 行；`tests/` 50 個檔、約 5,400 行。
> 對應版本：`pyproject.toml` 1.0.76（`main` 分支）。

---

## 1. 這是什麼程式

FrontEngine 是一個 PySide6 桌面**覆蓋層（overlay）框架**：把影片、圖片、GIF、網頁、
文字、粒子、音效、桌寵等東西放到螢幕最上層（或最底層）播放，並附帶一整套
「螢幕周邊工具」——護眼濾鏡、簡報塗鴉、量測取色、錄影、虛擬攝影機、專注遮罩等。

- 執行環境：Python 3.10+、PySide6 6.11.1、qt-material、PyOpenGL、numpy、pynput
- 發佈：PyPI `frontengine`（穩定，`stable.toml`）／ `frontengine_dev`（開發，`pyproject.toml`）；
  另有 Steam 版本（`steam_assets/`、`utils/steam/`、`utils/workshop/`）
- 進入點：
  | 進入方式 | 位置 |
  | --- | --- |
  | 命令列 `frontengine` | `pyproject.toml [project.scripts]` → `frontengine.ui.main_ui:main` |
  | `python -m frontengine` | `frontengine/__main__.py` → `main()`（支援 `--preset` / `--debug`） |
  | 程式內嵌 | `frontengine.start_front_engine()` |
  | 打包執行檔 | `exe/start_front_engine.py`，由 `exe/build_exe.py`（Nuitka）建置 |

---

## 2. 分層與相依方向

```
                    ┌─────────────────────────────┐
                    │  ui/main_ui.py（組裝與協調）│
                    └──────────────┬──────────────┘
        ┌──────────────┬───────────┼────────────┬──────────────┐
        ▼              ▼           ▼            ▼              ▼
   ui/nav  ui/style  ui/menu   ui/page/*   ui/dialog/*   system_tray
                                    │
                                    ▼
                         show/*（覆蓋層 widget）
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   user_setting/               utils/*（無 Qt 或僅 QObject 的服務層）
```

相依規則（實際掃描結果）：

- `utils/` 是最底層。多數模組**不依賴 Qt**，或只用 `QObject`+`QTimer` 包一層訊號；
  純邏輯（規則、狀態機、數學）和平台呼叫都在這裡，所以整層可離線測試。
- `show/` 依賴 `utils/` 與 `user_setting/`，不依賴 `ui/`。
- `ui/page/` 依賴 `show/` + `utils/` + `user_setting/`；分頁之間原則上不互相依賴，
  例外是 `control_center` 需要握有其他分頁的參考（那正是它的職責）。
- `user_setting/` 依賴 `utils/json`。
- **已知的一處反向相依**：`user_setting/scene_setting.py` 匯入
  `ui/dialog/choose_file_dialog`（設定層叫得動 UI 層）。可用但破壞分層，
  之後若要整理，把 `choose_scene_json` / `write_scene_file` 搬到 `ui/dialog/` 即可。
- `frontengine/__init__.py` 直接匯入 `main_ui`，所以 `import frontengine` 會把整個 UI
  拉進來。想只用某個 widget 的人請改用完整路徑匯入。

---

## 3. 啟動流程

`start_front_engine()` → `FrontEngineMainUI.__init__()`，依序做這些事
（`frontengine/ui/main_ui.py:109`）：

1. Windows 設定 AppUserModelID（工作列圖示正確分群）
2. `read_user_setting()` 讀 `user_setting.json`，再 `language_wrapper.reset_language()`
   （第一次啟動會問 `utils/steam/steam_language` 跟著 Steam 客戶端的語言走）
3. 建左側 `NavigationSidebar` + 右側 `QStackedWidget`，建立 15 個功能分頁
4. 建 `ControlCenterUI`，把「較新的分頁」的覆蓋層清單透過
   `register_overlay_source()` 註冊進來（`_register_extra_overlays()`）
5. 選單：語言 / 說明 / 教學 / 預設集 / 設定
6. `CriticalExit`（F12 強制退出）、`HotkeyService`（全域快速鍵）、系統匣
7. 依序啟動 14 個背景服務（見 §4.4；`_CLOSING_SERVICES` 是關閉時的完整清單）
8. 還原上次工作階段 → 還原便利貼 → 套用啟動預設集

關閉流程刻意分成兩段（`_shutdown()` 與 `close()`）：
**`QWidget::close()` 在 Qt 不是虛擬函式**，從標題列 X、登出、`closeAllWindows()`
關閉時只會走 `closeEvent`，Python 的 `close()` 覆寫不會被呼叫，所以存檔與
停服務全部放在 `_shutdown()`，由 `closeEvent` 與 `close()` 各自呼叫一次
（`_shutdown_done` 旗標防重入）。

---

## 4. 模組逐一說明

### 4.1 `frontengine/show/` — 覆蓋層 widget

所有東西畫到螢幕上的地方。共同基底是 `BaseWidget`（Template Method）。

#### 共用骨架

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `base_widget.py` | 181 | `BaseWidget(QWidget)`。定義覆蓋層的共同契約：不透明度（預設 0.2）、`WA_TranslucentBackground` + `WA_DeleteOnClose`、鎖定/點擊穿透、拖曳擺位、位置記憶、綠幕背景色、畫質檔位、`keep_in_capture`。`paintEvent()` 統一開 painter → 子類別只實作 `draw_content(painter)`。 |
| `window_helpers.py` | 68 | 覆蓋層視窗旗標的單一出處：`apply_overlay_window_flags()`（置頂/置底、無邊框、Tool、點擊穿透）、`set_overlay_locked()`、`load_overlay_icon()`。 |
| `draggable_window.py` | 65 | `DraggableTopWindow`：無邊框置頂小視窗，可拖曳、雙擊或 Esc 關閉。釘選截圖與視窗複本的底座。 |
| `overlay_factory.py` | 125 | Abstract Factory：把場景 JSON 的 `{kind, ...}` 轉成對應 widget（image/gif/sound/text/video/web）。`build_overlay(kind, setting)` 是唯一入口，欄位缺失會明確報錯（場景 JSON 是外部資料）。 |

#### 基本媒體覆蓋層

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `gif/paint_gif.py` | 53 | `GifWidget`：GIF / WebP 動畫，可調速度與不透明度。 |
| `image/paint_image.py` | 57 | `ImageWidget`：靜態圖片。 |
| `video/video_player.py` | 79 | `VideoWidget(QVideoWidget)`：影片播放（音量、播放速率、循環）。 |
| `web/webview.py` | 87 | `WebWidget(QWebEngineView)`：網頁或本機 HTML，含縮放與自動重新整理。 |
| `text/draw_text.py` | 163 | `TextWidget`：文字覆蓋層。字型、顏色、外框、對齊、跑馬燈，並可接 `utils/text_source` 顯示時鐘／倒數／系統負載／天氣。 |
| `sound_player/sound_player.py` | 65 | `SoundPlayer`：音樂播放（mp3/wav/mp4）。 |
| `sound_player/sound_effect.py` | 61 | `SoundEffectWidget`：WAV 音效（低延遲、可重複觸發）。 |
| `particle/particle_ui.py` | 199 | `ParticleOpenGLWidget(QOpenGLWidget)`：OpenGL 粒子效果，唯一走 GPU 的覆蓋層。 |
| `load/load_someone_make_ui.py` | 91 | 載入使用者自製的 Qt `.ui` 檔並全螢幕顯示，含驗證與參考保留。 |

#### 場景（多元件組合）

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `scene/scene.py` | 66 | `SceneManager`：把多個覆蓋層放進同一個 `QGraphicsScene` 的統一入口（`add_image` / `add_gif` / …）。 |
| `scene/extend_graphic_scene.py` | 32 | `ExtendGraphicScene`：可清空的場景基底。 |
| `scene/extend_graphic_view.py` | 78 | `ExtendGraphicView`：透明背景 + 滾輪縮放的 view。 |

#### 桌面寵物

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `pet/desktop_pet.py` | 1,981 | 整個 repo 最大的檔案，內含一整組**純邏輯類別**與一個 Qt widget：<br>• `PetMotion` — 移動模型（重力、彈跳、爬牆、走天花板、站視窗、追游標、遊蕩），完全不依賴 Qt<br>• `PetMood` / `PetHunger` / `PetGrowth` — 心情、飽足、親密度與等級<br>• `PetTagGame` — 多隻寵物的鬼抓人<br>• `PetTimeline` — 依秒數觸發的動作時間軸<br>• `scan_pet_pack()` / `read_pet_manifest()` — 動作包（walk/idle/sleep/climb/fall/drag + `pet.json`）<br>• `classify_drop()` / `classify_food()` — 拖檔案進來是換裝還是餵食<br>• `SpeechBubble`、`pick_message()` — 對話泡泡與時段/心情台詞<br>• `DesktopPetWidget(BaseWidget)` — 把上面全部接起來，另接麥克風對嘴、AI 對話、提醒、音效、電量警告 |

#### 螢幕工具類覆蓋層

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `camera/camera_widget.py` | 192 | 攝影機畫面覆蓋層（方形／圓形／圓角、外框、鏡像）。影像來源可注入，測試不需真攝影機。 |
| `canvas/whiteboard_widget.py` | 248 | 無限畫布白板：拖曳平移、滾輪縮放、筆畫以畫布座標保存、可存成圖片。 |
| `capture/region_capture.py` | 187 | 區域截圖框選層。含 `safe_capture_path()` 擋路徑穿越。擷取函式可注入。 |
| `measure/measure_widget.py` | 239 | 量測層：取色器 / 像素尺 / 量角器三合一，共用同一層全螢幕覆蓋。 |
| `pinned/pinned_image.py` | 103 | 把截下來的畫面釘在螢幕上，可拖曳縮放。 |
| `replica/replica_widget.py` | 113 | 視窗複本：顯示另一個視窗的即時畫面（底層是 DWM 縮圖）。 |
| `freeze/freeze_widget.py` | 93 | 凍結畫面：把某螢幕當下的樣子拍下來鋪滿蓋上（簡報時定格）。 |
| `reference/reference_board.py` | 155 | 參考圖板：一塊畫布放多張圖，各自可搬、整塊可縮放。 |
| `notes/sticky_note_widget.py` | 160 | 便利貼：可直接打字，內容與位置跨工作階段保存。 |
| `toast/toast_widget.py` | 143 | 提示卡：畫面上方短暫顯示一行字，時間到自己關掉（提醒、規則觸發用）。 |
| `shortcuts/shortcut_sheet.py` | 152 | 快速鍵速查表，把目前綁定畫在畫面中央、點擊穿透。 |
| `monitor/monitor_widget.py` | 341 | `SystemMonitorWidget`（CPU／記憶體／磁碟／電池／網路上下行折線圖，使用者挑要顯示哪幾條）與 `NowPlayingWidget`（正在播放）。折線分百分比與速率兩種：百分比縱軸固定 0~100，速率跟著視窗內最大值並有下限。資料來源皆可注入。 |
| `spectrum/spectrum_widget.py` | 167 | 音訊頻譜（長條／環形），含平滑與慢慢落下的峰值。 |
| `wallpaper/wallpaper_widget.py` | 169 | 桌布層：位於所有視窗底下，可播圖片／動圖，可隨系統音量脈動。 |

#### 護眼與專注

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `screen_care/screen_filter.py` | 147 | `ScreenFilterWidget`（整片色彩濾鏡）與 `ReadingRulerWidget`（閱讀亮帶跟著游標）。 |
| `screen_care/color_vision_widget.py` | 147 | 色覺模擬層：擷取畫面 → 套色覺缺陷矩陣 → 蓋回去。 |
| `focus_shield/focus_shield_widget.py` | 156 | `DimBackgroundWidget`（作用中視窗以外壓暗、會跟著切換）與 `DistractionMaskWidget`（蓋掉工作列／通知角落）。 |

#### 簡報與教學

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `presentation/annotation_overlay.py` | 161 | 螢幕塗鴉：筆／螢光筆／橡皮擦、復原、全部清除。 |
| `presentation/cursor_effects.py` | 173 | 游標亮環、點擊漣漪、聚光燈。 |
| `presentation/keystroke_display.py` | 287 | 把剛按下的按鍵與滑鼠點擊顯示在角落（教學影片用），數秒後淡出。位置（四個角落／置中）、字級、要不要顯示滑鼠都可調；`panel_origin()` 是純算術，排版不必開視窗就驗得了。 |
| `presentation/magnifier.py` | 139 | 區域放大鏡：抓游標周圍畫面放大顯示。 |

---

### 4.2 `frontengine/ui/` — 介面

#### 主視窗與外框

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `main_ui.py` | 1,015 | `FrontEngineMainUI(QMainWindow)`。組裝分頁、選單、系統匣，持有並協調全部背景服務，分派全域快速鍵／手機遙控／MIDI 動作，處理智慧暫停、看板輪播、螢幕保護、分享隱私、提醒、主題排程，最後負責關閉時的完整收尾。另有 `start_front_engine()` 與 CLI `main()`。 |
| `nav/sidebar.py` | 112 | `NavigationSidebar(QListWidget)`：分組的分頁清單（On screen / Desktop / Work / Control / Extensions），選取時送 `page_requested`。 |
| `style/app_style.py` | 200 | 疊在 qt-material 之上的樣式表。顏色全部由主題色票算出（含對比色計算），**必須接在 `apply_stylesheet()` 之後**，否則會被整份覆蓋。 |
| `color/global_color.py` | 4 | 兩個常數：log 面板的一般與錯誤顏色。 |
| `system_tray/extend_system_tray.py` | 111 | `ExtendSystemTray`：系統匣選單（顯示／隱藏主視窗、全部關閉、退出），文字接 `retranslator`。 |

#### 分頁共用元件

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `page/layout_kit.py` | 316 | **分頁的版面語彙**：`SettingPage`（頁首 + 可捲動內容 + 底部動作列）與 `Section`（`add_row` / `add_slider_row` / `add_button_grid`）。控制項寬度統一收在 260–460px。所有分頁都用它描述欄位，不要再自己寫 `QGridLayout` 座標。 |
| `page/utils.py` | 374 | 分頁的共用行為：多螢幕分派（`dispatch_to_monitors`、`resolve_span`、`virtual_desktop_geometry`）、最近使用檔案下拉選單、拖放檔案過濾器、以及一整組 `apply_*_state()`（把預設集載回控制項）。 |

#### 功能分頁（每頁都有 `get_state()` / `set_state()`，預設集就是靠這對方法存取）

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `page/video/video_setting_ui.py` | 238 | 影片：選檔、不透明度、播放速率、音量、目標螢幕。 |
| `page/image/image_setting_ui.py` | 334 | 圖片：單張、資料夾輪播（slideshow），以及開啟參考圖板。 |
| `page/web/web_setting_ui.py` | 308 | 網頁：URL 或本機檔案、是否可互動、**儀表板模式**（多網址輪播 + `dashboard_next` 快速鍵）。 |
| `page/gif/gif_setting_ui.py` | 209 | GIF / WebP。 |
| `page/text/text_setting_ui.py` | 355 | 文字：字型、顏色、外框、跑馬燈，以及動態來源（時鐘／日期／倒數／碼表／系統負載／天氣）。 |
| `page/sound_player/sound_player_setting_ui.py` | 147 | 音效與音樂播放。 |
| `page/particle/particle_setting_ui.py` | 253 | 粒子效果。 |
| `page/scene_setting/` | 46 + 185 + 7 頁 | 場景編輯：`scene_setting_ui.py` 是外框，`scene_manager.py` 負責 JSON 讀寫與啟動，`scene_page/` 是七個子頁（gif/image/sound/text/video/web + `base_scene_page.py` 的 Template Method 基底 + `registry.py` 註冊表）。 |
| `page/pet/pet_setting_ui.py` | 562 | 桌寵：動作包、行為模式、多隻與鬼抓人、麥克風對嘴、AI 對話、打字時安分、專注計時（番茄鐘）。 |
| `page/wallpaper/wallpaper_setting_ui.py` | 328 | 桌布：資料夾播放清單、每螢幕不同資料夾、隨機、時段切換清單、音量反應。 |
| `page/widgets/widgets_setting_ui.py` | 360 | 桌面小工具：頻譜、正在播放、系統監控、便利貼。 |
| `page/focus/focus_setting_ui.py` | 215 | 專注：背景壓暗、干擾區域遮罩。 |
| `page/screen_care/screen_care_setting_ui.py` | 364 | 護眼：色彩濾鏡、閱讀尺、20-20-20 休息提醒、色覺模擬。 |
| `page/presentation/presentation_setting_ui.py` | 477 | 簡報：塗鴉、游標效果、按鍵顯示、放大鏡、白板、凍結畫面。 |
| `page/tools/tools_setting_ui.py` | 710 | 工具：量測取色、區域截圖與釘選、畫面文字辨識（Claude）、錄影成 GIF、虛擬攝影機、攝影機覆蓋層、視窗釘選／複本／版面。 |
| `page/control_center/control_center_ui.py` | 518 | **控制中心**：全部隱藏／顯示／關閉／靜音／鎖定／綠幕／重設位置／畫質檔位／不透明度加減，以及 log 面板。其他分頁用 `register_overlay_source(provider)` 把自己的覆蓋層清單交過來，用 `register_cleanup(cb)` 交出批次關閉後要收的資源。 |

#### 選單

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `menu/preset_menu.py` | 387 | 預設集：儲存／載入／刪除／匯出／匯入、單檔與**封包（含媒體的 zip）**、啟動預設集、上次工作階段還原、Steam 創意工坊內容匯入。 |
| `menu/settings_menu.py` | 377 | 設定選單：快速鍵、智慧暫停、程式對應預設集、提醒、遙控/MIDI、分享隱私、螢幕保護、看板、排程、剪貼簿、使用報告、保持喚醒、開機自啟、外掛開關、設定匯出入。 |
| `menu/language_menu.py` | 64 | 七種語言切換，**即時重寫畫面文字**，不必重啟。 |
| `menu/help_menu.py` | 93 | 說明選單 + 使用說明對話框 + 「如何強制退出」。 |
| `menu/how_to_menu.py` | 44 | 線上文件／教學連結。 |

#### 對話框（`ui/dialog/`）

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `choose_file_dialog.py` | 123 | 所有選檔的單一出處，含副檔名驗證（gif/image/wav/audio/pet/video）。 |
| `how_to_use_dialog.py` | 118 | 程式內的使用說明。 |
| `hotkey_settings_dialog.py` | 134 | 以 pynput 語法重新綁定全域快速鍵，存檔前驗證。 |
| `smart_pause_dialog.py` | 87 | 智慧暫停規則（全螢幕／電池／指定程式）。 |
| `app_profile_dialog.py` | 115 | 程式 → 預設集對照表。 |
| `preset_schedule_dialog.py` | 150 | 星期幾、幾點自動套用哪個預設集。 |
| `reminder_dialog.py` | 175 | 自訂提醒（每隔 N 分鐘 / 每天 HH:MM）。 |
| `rules_dialog.py` | 221 | 條件式規則表：一列一條規則，條件留白代表不限。 |
| `remote_control_dialog.py` | 227 | 手機網頁遙控開關與網址、MIDI 綁定學習。 |
| `screen_privacy_dialog.py` | 104 | 哪些程式算「正在分享」、要不要自動藏出擷取。 |
| `screensaver_dialog.py` | 113 | 閒置多久、顯示哪一頁。 |
| `signage_dialog.py` | 100 | 看板輪播清單與間隔。 |
| `usage_report_dialog.py` | 120 | 今天各程式用了多久、最近七天總量。 |
| `clipboard_dialog.py` | 147 | 剪貼簿歷史：搜尋、釘選、貼回。 |
| `window_pin_dialog.py` | 147 | 列出視窗，釘最上層或調透明度。 |
| `window_replica_dialog.py` | 145 | 挑一個視窗做即時複本。 |
| `screen_text_dialog.py` | 121 | 顯示 Claude 從截圖讀出的文字，並管理「送出截圖」的同意狀態。 |

---

### 4.3 `frontengine/user_setting/` — 設定持久化

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `user_setting_file.py` | 256 | 全域 `user_setting_dict` 與其預設值（語言、主題、快速鍵、各功能開關與規則）。提供讀寫、匯出匯入、覆蓋層位置記憶、最近使用檔案、快速鍵對照表。設定檔是工作目錄下的 `user_setting.json`。 |
| `preset_repository.py` | 233 | 預設集儲存庫：`presets/` 下一個預設集一個 JSON。含檔名淨化、匯出／匯入、**封包（zip，內含 `media/`）**；解壓時只取檔名最後一段以防 zip-slip。 |
| `scene_setting.py` | 46 | 場景 JSON 的選檔與寫檔（⚠ 目前反向依賴 `ui/dialog`）。 |

---

### 4.4 `frontengine/utils/` — 服務與純邏輯

這一層的共同設計：**能純函式就純函式，需要週期性動作才包成 `QObject` + `QTimer` 並用訊號往外送**；
外部來源（時鐘、螢幕擷取、程式名稱、裝置）一律可注入，因此 offscreen 測得到。

#### 基礎設施

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `logging/loggin_instance.py` | 80 | 全域 logger（RotatingFileHandler）。日誌優先寫工作目錄，寫不了退到家目錄，再不行就不寫檔。 |
| `json/json_file.py` | 61 | `read_json` / `write_json`，寫入為**原子操作**（先序列化 → 寫暫存 → 置換）。 |
| `json/json_repository.py` | 53 | `JsonRepository`：單一 JSON 文件的 Repository 包裝（`load` / `load_into` / `save`）。 |
| `exception/exceptions.py` | 26 | 五個自訂例外；`FrontEngineJsonFileException` 刻意繼承 `OSError`。 |
| `exception/exception_tags.py` | 11 | 例外訊息字串常數。 |
| `redirect_manager/redirect_manager_class.py` | 91 | 把 stdout/stderr/logging 導進 queue，供控制中心的 log 面板顯示。 |
| `browser/browser.py` | 21 | 開系統預設瀏覽器。 |
| `web_url.py` | 93 | YouTube 連結 → 可自動播放循環的內嵌網址；儀表板多網址解析與翻頁索引。 |

#### 多語系

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `multi_language/language_wrapper.py` | 70 | 語言註冊表與 `reset_language()`。 |
| `multi_language/retranslate.py` | 171 | **即時換語言的核心**：`Retranslator` 記住「哪個控制項的文字來自哪個鍵」，換語言時原地重寫。`tr(widget, key, fallback)` 回傳 widget 本身，可直接寫在指派右邊。<br>⚠ 執行期會換字的按鈕要用 `retranslator.set_text`，用 `setText` 會讓換語言時狀態文字跳回初始值。 |
| `multi_language/{english,traditional_chinese,simplified_chinese,germany,russian,france,italy}.py` | 676–686 | 七份語言字典。**鍵集合必須完全一致**，由 `test_translations.py` 守著。 |
| `steam/steam_language.py` | 118 | 第一次啟動時讀 Steam 客戶端語言（Windows 讀登錄檔、其他平台從 `registry.vdf` 撈字串）。 |

#### 平台與系統資訊

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `platform_info/platform_info.py` | 400 | 跨平台系統狀態：使用者閒置秒數、電池、可站立的視窗上緣、前景程式名稱。Windows 走 ctypes，macOS 走 `osascript`/`ioreg`/`pmset`，Linux 走 `/sys` 與 wmctrl/xdotool。外部指令走**白名單 + 絕對路徑**，不查 PATH。 |
| `system_stats/system_stats.py` | 379 | CPU／記憶體／磁碟／網路流量／電池取樣（Windows ctypes、Linux `/proc`），含 32 位元計數器繞回處理。電池讀數借自 `platform_info` 並快取 30 秒（macOS 要 fork `pmset`，而監控是每秒取樣）。`SAMPLE_FIELDS` 宣告產出的欄位名稱，供文字覆蓋層列出可用的 `{欄位}`，由測試與 `sample()` 釘在一起。 |
| `power_mode/power_mode.py` | 72 | 省電與畫質檔位的純計算：`scaled_interval()`、`TIER_HIGH/BALANCED/SAVER`、`tier_interval()`、`tier_render_scale()`。 |
| `critical_exit/critical_exit.py` | 97 | 背景執行緒監聽緊急退出鍵（預設 F12）。 |
| `critical_exit/check_key_is_press.py` | 19 | Windows 的按鍵狀態查詢。 |
| `critical_exit/win32_vk.py` | 368 | 虛擬鍵碼表。 |

#### 輸入與遙控

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `hotkey/hotkey_service.py` | 99 | 包一層 `pynput.GlobalHotKeys`，把每個組合鍵轉成 Qt 訊號（主視窗以 `QueuedConnection` 接回 UI 執行緒）。 |
| `input_watch/input_watch_service.py` | 156 | 全域鍵盤／滑鼠監聽，供按鍵顯示與點擊漣漪使用。滑鼠拆成兩個訊號：`mouse_clicked(x, y)` 給漣漪、`mouse_pressed(name)` 給按鍵顯示，各取所需。 |
| `input_watch/typing_watch.py` | 73 | 「使用者現在還在打字嗎」——桌寵打字時安分用。 |
| `remote/remote_server.py` | 247 | 手機遙控：本機小型 HTTP 伺服器 + 一次性權杖 + **動作白名單**（只能呼叫既有的快速鍵動作），內嵌單頁 HTML。 |
| `midi/midi_input.py` | 230 | MIDI 輸入（Windows winmm）：旋鈕調不透明度、按鍵切預設集；訊息在 winmm 執行緒送達，用 Qt 訊號轉回。 |
| `media_keys/media_keys.py` | 130 | 送出系統媒體鍵（播放/暫停、下一首、上一首、停止），走 ctypes `keybd_event`，**不需要 WinRT**。動作名稱沿用快速鍵命名，所以快速鍵／手機遙控／MIDI 三條路都吃得到。回傳值是「有沒有送出」而非「播放器有沒有照做」——媒體鍵沒有任何回報。僅 Windows。 |

#### 音訊

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `audio_meter/system_audio_meter.py` | 356 | WASAPI `IAudioMeterInformation` 峰值電表與 COM 基礎工具（端點列舉、介面啟用），其他音訊模組都建在這上面。 |
| `audio_meter/loopback_capture.py` | 289 | WASAPI 回送擷取：把「正在播出去的聲音」讀進來做頻譜，背景執行緒擷取。 |
| `audio_meter/microphone_meter.py` | 147 | 麥克風峰值（桌寵對嘴用）。 |
| `audio_meter/screen_audio.py` | 130 | 把「螢幕」對應到「輸出端點」（多螢幕各自帶 HDMI 音訊時）。 |
| `audio_meter/spectrum_analyzer.py` | 143 | FFT → 對數間隔頻段 → 0~1 強度，含 `SpectrumSmoother`（上升快、下降慢 + 峰值落下）。 |
| `audio_meter/audio_envelope.py` | 56 | 把逐次峰值平滑成自然的脈動包絡。 |
| `now_playing/now_playing.py` | 232 | 「正在播放什麼」：優先問 Windows SMTC（需選用套件），退回「哪個程式正在出聲」。 |

#### 螢幕與視窗操作

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `window_pin/window_pin.py` | 172 | 把別人的視窗釘最上層／調透明度（Win32 `SetWindowPos` + 分層視窗）。透明度下限 20%，避免使用者找不回視窗。 |
| `window_pin/window_layout.py` | 146 | 記下目前所有視窗位置，之後一鍵擺回去。 |
| `window_pin/monitor_move.py` | 268 | 把前景視窗搬到下一個螢幕，並保留相對位置（Windows 內建的 Win+Shift+方向鍵只會整個貼過去）。幾何全部是純函式，螢幕以 `(x, y, w, h)` 傳入；判斷「目前在哪一台」是比重疊面積而不是看左上角。**螢幕矩形取 Win32 實體像素**，不能用 Qt 的邏輯像素——`SetWindowPos` 用實體像素，混合 DPI 下兩者差 25%（實機 100%+125% 量到 1536 vs 1920）。跨 DPI 時 Windows 會在我們之後再依比例放大視窗（維持視覺大小，是對的），所以落地後要再夾回螢幕內一次。僅 Windows。 |
| `window_replica/dwm_thumbnail.py` | 232 | DWM 縮圖：另一個視窗的即時複本（含裁切比例與等比縮放）。 |
| `screen_privacy/capture_affinity.py` | 123 | `WDA_EXCLUDEFROMCAPTURE`：把視窗排除在螢幕擷取之外（自己看得到、對方看不到）。 |
| `virtual_desktop/virtual_desktop.py` | 306 | 把覆蓋層綁在開啟它的虛擬桌面：切走隱藏、切回還原。只用**有文件的** `IVirtualDesktopManager`（每桌不同桌布要靠未公開介面，那會隨 Windows 版本壞掉）。`DesktopVisibility` 是純邏輯：只還原自己藏過的，並在覆蓋層關閉後忘掉 handle（handle 會被回收再配給別的視窗）。探測「不知道」時一律不動，否則沒有這個 API 的機器會把全部覆蓋層藏掉。實機量過：切到另一個虛擬桌面確實回傳 False、服務確實藏起來、切回來確實還原；**不認識的 handle 回傳 True 而非錯誤**（安全方向，關掉的覆蓋層不會被誤藏）。僅 Windows。 |
| `screen_privacy/share_watch.py` | 142 | 偵測會議程式是否開著（以視窗標題比對，要求字界），狀態改變時發訊號。 |
| `measure/measure.py` | 116 | 量測的純計算：色碼格式（hex/rgb/hsl/css var）、距離、三點夾角。 |
| `color_vision/color_vision.py` | 113 | 色覺模擬矩陣（紅／綠／藍色盲、全色盲）與「這兩色還分得出來嗎」。 |
| `focus_shield/focus_shield.py` | 93 | 專注遮罩的純幾何：螢幕扣掉作用中視窗的四塊矩形、依區域與比例算遮罩矩形。 |

#### 擷取與輸出

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `recording/frame_recorder.py` | 199 | 定時抓一塊螢幕存成序列畫面，可把攝影機縮小疊右下角，最後寫成 GIF。 |
| `recording/gif_writer.py` | 245 | **自己寫的最小 GIF89a 編碼器**：固定調色盤（216 色立方 + 16 灰）、最近色查表、LZW 壓縮、NETSCAPE 循環擴充。 |
| `virtual_camera/virtual_camera.py` | 166 | 虛擬攝影機輸出（`pyvirtualcam`，選用），含尺寸調整與補邊。 |
| `virtual_camera/camera_feed.py` | 103 | 定時抓一塊螢幕送進虛擬攝影機。 |

#### 排程、規則與狀態機（幾乎全部是可注入時鐘的純邏輯 + 一層 QTimer 服務）

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `rules/rule_engine.py` | 331 | 條件式規則：「當 <條件> 成立時，做 <動作>」。條件可組合（星期＋時段＋前景程式＋全螢幕＋電池＋閒置），動作對應到既有能力（套用預設集／隱藏／顯示／關閉／畫質）。**邊緣觸發**：只在「不成立 → 成立」那一刻執行一次，否則每次輪詢都會重套預設集、把使用者手動改的蓋掉。既有的四套排程沒有被取代，這裡補的是它們之間的組合。 |
| `smart_pause/pause_rules.py` | 104 | 暫停規則的純判斷：全螢幕／電池／指定程式；程式名稱正規化。 |
| `smart_pause/smart_pause_service.py` | 174 | 週期性檢查上述三件事，狀態改變時發 `pause_changed`。 |
| `app_profile/app_profile_service.py` | 102 | 前景程式換到有設定的程式時，發出要套用的預設集名稱。 |
| `preset_schedule/preset_schedule_service.py` | 147 | 每天在指定時間套用預設集，用「跨越目標分鐘」偵測，一天只觸發一次。 |
| `theme_schedule/theme_schedule_service.py` | 97 | 依時間切換日／夜主題。 |
| `signage/signage_service.py` | 156 | 看板模式：依序輪播一組預設集。 |
| `screensaver/screensaver_service.py` | 177 | 閒置到門檻就把選定分頁的覆蓋層放上來，人回來就收掉。 |
| `reminder/reminder_service.py` | 199 | 自訂提醒（每 N 分鐘 / 每天 HH:MM），到期發訊號 → 提示卡。 |
| `break_reminder/break_reminder.py` | 104 | 20-20-20 護眼休息狀態機。 |
| `focus_timer/focus_timer.py` | 112 | 番茄鐘狀態機（專注 → 休息 → 長休息）。 |
| `keep_awake/keep_awake.py` | 154 | 阻止螢幕睡著：Windows `SetThreadExecutionState`、macOS `caffeinate`、Linux `systemd-inhibit`。 |
| `autostart/autostart_service.py` | 172 | 開機自啟：Windows 寫 HKCU Run、Linux 放 XDG autostart、macOS 放 LaunchAgent。 |
| `playlist/playlist.py` | 140 | 桌布播放清單（循環、隨機不重複）與依時段切換清單。 |
| `text_source/text_source.py` | 190 | 動態文字來源：時鐘、日期、倒數、碼表、系統負載、天氣，含樣板 `{key}` 套用。 |
| `weather/weather_service.py` | 205 | Open-Meteo 免金鑰天氣（只送座標），背景更新 + 10 分鐘快取。`FORECAST_FIELDS` 同 `SAMPLE_FIELDS`，宣告樣板可用的欄位。 |
| `clipboard/clipboard_history.py` | 186 | 剪貼簿歷史資料結構：釘選優先、上限淘汰、搜尋。 |
| `clipboard/clipboard_watcher.py` | 75 | 把 `QClipboard` 變更接到歷史（只有明確啟用才監看）。 |
| `usage_tracking/usage_tracker.py` | 218 | 每天每個程式的前景時間累積（只寫本機檔）。 |
| `usage_tracking/usage_service.py` | 85 | 定時取樣前景程式，閒置超過 90 秒不計。 |

#### AI 與外部內容

| 模組 | 行數 | 功用 |
| --- | ---: | --- |
| `screen_text/screen_text_service.py` | 208 | 把框選到的畫面交給 Claude：取出文字／翻譯／就圖發問。金鑰只讀 `ANTHROPIC_API_KEY` 環境變數（**永不寫進設定檔**），且需要使用者明確同意。 |
| `pet_chat/pet_chat_service.py` | 176 | 桌寵 AI 對話（預設關閉），同樣只從環境變數取金鑰，保留最近 10 輪。 |
| `plugins/plugin_loader.py` | 138 | 載入 `plugins/<名稱>/plugin.py`，模組用 `FRONTENGINE_TABS` 註冊分頁。**預設關閉**——外掛與本程式同權限，無法沙箱化。 |
| `workshop/workshop_content.py` | 149 | Steam 創意工坊已訂閱內容的掃描與分類（動作包／預設集／媒體），供匯入使用。 |

---

## 5. 跨模組的共同約定

以下這些是「改東西之前必須知道」的規則，多數是踩過坑之後固定下來的。

### 5.1 覆蓋層的契約

1. 繼承 `BaseWidget`，只實作 `draw_content(painter)`；不要自己覆寫 `paintEvent`。
2. 自己處理滑鼠的覆蓋層（畫筆、白板、框選、量尺、寵物）要設
   `overlay_draggable = False`，否則拖曳作畫會連整個視窗一起搬走。
3. 每個實例位置各異的（便利貼、寵物）要設 `overlay_remembers_geometry = False`，
   否則會全部被拉到同一個位置與大小（位置記憶是以**類別名稱**為鍵）。
4. 遮蔽類覆蓋層要設 `keep_in_capture = True`，分享畫面時不能跟著藏起來。
5. 計時器要用 `tier_interval()` / `scaled_interval()` 取間隔，並實作
   `apply_quality_tier()`，才能被控制中心的畫質檔位管到。
6. **關閉一定要先 `close()` 再清清單**：只丟 Python 參考不會跑 `closeEvent`，
   計時器、媒體、全域監聽都停不掉。

### 5.2 新覆蓋層要接到控制中心

分頁自己持有的清單（`xxx_widget_list`）必須透過
`control_center_ui.register_overlay_source(lambda: page.xxx_widget_list)` 註冊，
否則「全部隱藏／關閉／鎖定／畫質」會漏掉它。註冊點集中在
`main_ui._register_extra_overlays()`。關閉時的清理另外列在
`_CLOSING_WIDGET_LISTS` 與 `_CLOSING_SERVICES`。

### 5.3 執行緒

背景來源（pynput 快速鍵、HTTP 遙控、winmm MIDI、音訊擷取執行緒）**一律用
Qt 訊號 + `QueuedConnection`** 回到 UI 執行緒。另外：
`QTimer.singleShot(0, callback)` 從背景執行緒呼叫**永遠不會觸發**，
必須用三參數版 `singleShot(0, context_qobject, callback)`。

### 5.4 設定與預設集

- 執行期狀態放 `user_setting_dict`，`write_user_setting()` 落地成 `user_setting.json`。
- 分頁狀態走 `get_state()` / `set_state()`，預設集選單就是靠這對方法把整組
  分頁設定序列化進 `presets/*.json`（或含媒體的 zip 封包）。
- 覆蓋層位置記在 `overlay_geometry`，鍵是 widget 類別名稱。

### 5.5 安全邊界

外部輸入集中在幾個地方，都有對應處理：場景 JSON 缺欄位明確報錯、
截圖存檔擋路徑穿越、預設集封包解壓只取檔名最後一段（zip-slip）、
外部指令走白名單絕對路徑且 `shell=False`、遙控伺服器有動作白名單與
常數時間權杖比對、API 金鑰只從環境變數讀、外掛預設不載入。

---

## 6. 支援目錄

| 目錄 | 內容 |
| --- | --- |
| `exe/` | `start_front_engine.py`（打包進入點）與 `build_exe.py`（Nuitka 建置，旗標寫在程式裡而不是 shell 歷史）。 |
| `docs/` | Sphinx 文件。`docs/source/docs/` 下有**七棵語言樹**（Eng / Zh / ZhCn / De / Ru / Fr / It）+ 共用 `image/`。`test_documentation.py` 會檢查七棵樹頁面一致、圖片存在、沒有提到已移除的功能。 |
| `tests/unit_test/` | 50 個測試檔、約 5,400 行。`conftest.py` 強制 `QT_QPA_PLATFORM=offscreen`、整個 session 跑在暫存目錄、共用一個 `QApplication`（`QPixmap`/`QMovie` 沒有 QApplication 會讓行程直接中止）。 |
| `steam_assets/` | Steam 商店素材產生器。 |
| `.github/workflows/` | `ci.yml`（多版本 Python：編譯 → 單元測試 → 打 wheel 安裝後啟動煙霧測試）、`nightly.yml`（只放 cron，避免排程被停用時連 PR CI 一起停）、`release.yml`（PR 合併到 main 後自動 bump 版本並發佈）。 |
| `.claude/PROGRESS.md` | 跨 session 的進行中工作記錄與環境備忘（測試指令、已知誤判、刻意移除的功能）。 |

---

## 7. 擴充點

**新增一種覆蓋層**要動的地方（缺一個就會出現「只有某條路徑失效」的問題）：

1. `show/<kind>/<widget>.py` — 繼承 `BaseWidget`，實作 `draw_content()`
2. `ui/page/<kind>/<kind>_setting_ui.py` — 繼承 `SettingPage`，用 `add_section()` /
   `add_row()` 描述欄位，實作 `get_state()` / `set_state()`
3. `main_ui._add_tabs()` — 加進對應的導覽分組
4. `main_ui._register_extra_overlays()` — 把 widget 清單註冊給控制中心
5. `main_ui._CLOSING_WIDGET_LISTS`（若需關閉時收尾）
6. **七份語言字典**都要加鍵（`test_translations.py` 會擋）
7. **七棵文件樹**都要加頁（`test_documentation.py` 會擋）
8. 該資料夾要有 `__init__.py`（`find = { namespaces = false }`，少一個就不會進 wheel，
   `test_public_api.py` 有守著）

**其他擴充點**：
- 場景新種類 → `show/overlay_factory.py` 加一個 Factory + `scene_page/registry.py`
- 外部分頁 → 外掛模組提供 `FRONTENGINE_TABS`（使用者需自行開啟外掛載入）
- 新語言 → `language_wrapper.register()`
- 新快速鍵動作 → `user_setting_file.default_hotkeys` + `main_ui._handle_hotkey()`
  （順便會出現在速查表與手機遙控白名單裡）

---

## 8. 觀察到的架構張力

不是缺陷清單，是「之後若要整理，這幾處最值得動」：

1. **`show/pet/desktop_pet.py`（1,981 行）** — 裡面其實有兩個東西：一組完全不依賴
   Qt 的行為模型（`PetMotion` / `PetMood` / `PetHunger` / `PetGrowth` / `PetTagGame` /
   `PetTimeline` / 動作包掃描 / 食物分類），和一個把它們接起來的 widget。
   純邏輯的部分可以整批搬到 `utils/pet/`，`show/` 只留 widget。
2. **`ui/main_ui.py`（1,015 行）** — 主視窗同時是「版面組裝者」與「12 個背景服務的
   協調者」。服務的建立與接線可以抽成一個 service registry，`__init__` 會短很多。
3. **`user_setting/scene_setting.py` → `ui/dialog`** — 唯一一處分層反向。
4. **`frontengine/__init__.py` 匯入 `main_ui`** — 任何 `import frontengine` 都會連帶
   建立整個 UI 匯入鏈；只想用單一 widget 的使用者付了不必要的成本。
5. **Windows 專屬功能的比重** — 視窗釘選／複本、擷取排除、WASAPI 音訊、MIDI、
   SMTC「正在播放」都只有 Windows 完整支援。這些模組都有 `available()` 並在
   其他平台安靜降級，但功能落差在 UI 上不一定看得出來。
6. **語言字典的規模** — 七份各約 680 行、共約 4,750 行，佔全專案 16%。加一個欄位
   就是七處要改；目前靠測試守住一致性，長期可考慮改成單一來源 + 產生器。
