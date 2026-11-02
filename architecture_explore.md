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

- 執行環境：Python 3.10+、PySide6 6.11.1、PyOpenGL、numpy、pynput（介面樣式為自有設計系統，不再使用 qt-material）
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
   ui/nav  ui/style  ui/menu   ui/page/*   ui/dialog/*   system_tray/（ui 之外）
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
| `pet/desktop_pet.py` | 1,981 | 整個 repo 最大的檔案，內含一整組**純邏輯類別**與一個 Qt widget：<br>• `PetMotion` — 移動模型（重力、彈跳、爬牆、走天花板、站視窗、追游標、遊蕩），行為 `actions`（預設，選單「循環所有動作（隨機）」）在內部是地面模式加 `random_actions`，閒置時依 `AUTONOMOUS_ACTIONS` 權重從整套動作隨機挑選下一個（走、待機、坐、玩、理毛、爬較近的牆、揮手、睡、慶祝、展示服裝）；`floor` 只走路與待機；`behaviour` 對外仍回報 floor 以沿用地面模式的判斷，存檔與顯示改讀 `mode`，完全不依賴 Qt<br>• `PetMood` / `PetHunger` / `PetGrowth` — 心情、飽足、親密度與等級<br>• `PetTagGame` — 多隻寵物的鬼抓人<br>• `PetTimeline` — 依秒數觸發的動作時間軸<br>• `scan_pet_pack()` / `read_pet_manifest()` — 動作包（walk/idle/sleep/climb/fall/drag + `pet.json`）<br>• `classify_drop()` / `classify_food()` — 拖檔案進來是換裝還是餵食<br>• `SpeechBubble`、`pick_message()` — 對話泡泡與時段/心情台詞<br>• `DesktopPetWidget(BaseWidget)` — 把上面全部接起來，另接麥克風對嘴、AI 對話、提醒、音效、電量警告 |

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
| `main_ui.py` | 1,364 | `FrontEngineMainUI(QMainWindow)`。組裝帶功能搜尋入口的側欄、分頁、選單與系統匣，持有背景服務並分派全域快速鍵／手機遙控／MIDI 動作，負責關閉時完整收尾。另有 `start_front_engine()` 與 CLI `main()`。 |
| `nav/sidebar.py` | 114 | `NavigationSidebar(QListWidget)`：分組的分頁清單（On screen / Desktop / Work / Control / Extensions），選取時送 `page_requested`，完整名稱以工具提示顯示。每列頁面帶 `nav_icons` 線條圖示（`add_page(..., icon_name=)`，選取時改用文字色），群組標題一律大寫、收合箭頭是同風格的 chevron；調色盤改變時重繪圖示。 |
| `nav/shell.py` | 110 | 外框元件：`BrandMark`（橘底墨色腳印標誌 + 名稱）與 `CommandSearchButton`（放大鏡、「指令」、Ctrl+K 提示，點擊開指令面板）；皆隨調色盤重繪。 |
| `style/tokens.py` | 110 | 自有設計系統的色票與尺寸刻度：亮／暗兩組（INKSIDE 墨黑、紙白、橘色）、圓角、控制項高度、字級。`resolve_theme()` / `normalise_theme()` 把 system / light / dark 與舊版 qt-material 主題名稱（`dark_amber.xml` 等）對應成亮或暗。 |
| `style/nav_icons.py` | 90 | 單一風格的 24×24 線條圖示（側欄各頁、搜尋、chevron），以 SVG 路徑保存並在執行期用 token 顏色算成圖，主題切換不需要另一套圖檔。 |
| `style/app_style.py` | 380 | 由 tokens 產生整份樣式表（所有標準控制項、外框、分區卡片、主要／危險按鈕、選單、提示、捲軸）與 QPalette；`apply_app_style(window, theme)` 取代整份樣式表並設定調色盤，只影響該視窗與其子元件（覆蓋層不受影響）。`contrast_ratio()` 依 WCAG 計算；勾選與箭頭圖示是 `style/icons/*.svg`（套件資料）。 |
| `color/global_color.py` | 4 | 兩個常數：log 面板的一般與錯誤顏色。 |
| `frontengine/system_tray/extend_system_tray.py`（在 `ui/` 之外，自成一個套件） | 111 | `ExtendSystemTray`：系統匣選單（顯示／隱藏主視窗、全部關閉、退出），文字接 `retranslator`。 |

#### 分頁共用元件

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `page/layout_kit.py` | 363 | **分頁的版面語彙**：`SettingPage`（頁首、捲動內容與固定底部動作列）與卡片式 `Section`。`QFormLayout.WrapLongRows` 在窄視窗將標籤移到欄位上方；`add_inline` 自動換行，`add_actions` 只顯示常用按鈕，次要操作收進選單。進階設定可收合，獨立編輯器可用 compact 頁面；無法縮小的內容仍可橫向捲動。寬控制項維持 260–460px。頁首、內容與底部列放在同一條置中欄（`CONTENT_MAX_WIDTH` 960px，`_column()` 以兩側伸縮包住，不在 resizeEvent 裡改邊距——那樣會在重繪中遞迴崩潰）；`wide=True`（家園、場景）與 compact 使用全寬。`add_header_action()` 把頁面層級動作放在標題右側。 |
| `page/flow_layout.py` | 83 | `FlowLayout`：依可用寬度排列按鈕與勾選框，保留鍵盤順序，排除已隱藏控制項，並回報換行後的高度與最小尺寸。 |
| `page/action_menu.py` | 49 | `ActionMenu`：以 QAction 代理既有 QPushButton 的操作，原按鈕由選單持有並隱藏。開啟選單與換語言時同步文字、圖示、勾選及可用狀態；執行仍走原按鈕的 callback。 |
| `page/utils.py` | 374 | 分頁的共用行為：多螢幕分派（`dispatch_to_monitors`、`resolve_span`、`virtual_desktop_geometry`）；目標螢幕下拉選單第一項「這個螢幕」（data None）由 `resolve_preferred_monitor` 換成主視窗所在螢幕的索引，所以有下拉選單的分頁開始時不再跳出選螢幕對話框，只有沒有下拉選單的呼叫者才會走詢問流程；`ask_for_input` 讓空白的必填欄位取得焦點並顯示提示，取代警告對話框、最近使用檔案下拉選單、拖放檔案過濾器、以及一整組 `apply_*_state()`（把預設集載回控制項）。 |

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
| `page/pet/pet_setting_ui.py` | 830 | 桌寵：動作包、行為模式、多隻與鬼抓人、麥克風對嘴、AI 對話、打字時安分、專注計時（番茄鐘）。頁面最上方是 `pet_quick.PetQuickStart`，其餘區塊（更多來源、身分、外觀、行為、聲音、專注、互動）預設收合。 |
| `page/pet/pet_quick.py` | 150 | 「你的寵物」：每個內建角色一張卡片（圖示取 `inkside/sprites/<id>-sit.png` 第一格），點了就 `quick_builtin` 安裝並直接放一隻穿成該角色的寵物到桌面；「自己的圖片…」走 `choose_and_play`。下方清單列出桌面上的寵物（每秒對照 `pet_list` 更新），附衣櫃、找回（雙擊亦可）與收起來（關閉並從 `pet_list` 移除）。 |
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
| `menu/features_menu.py` | 150 | **Features** menu, first in the menu bar. `CATEGORIES` groups every page (by stable page ID), ActionRegistry command and existing menu (Presets/Settings/Language/Help, the same QMenu objects) by purpose; plugin pages appear under Extensions. Rebuilt on open and on language change, with Search (opens the palette), Pinned and Recent from `CommandHistory`; menu use is recorded as recent like palette use. `test_features_menu.py` fails if a sidebar page or menu action is not reachable from it. |

#### 對話框（`ui/dialog/`）

| 檔案 | 行數 | 功用 |
| --- | ---: | --- |
| `dialog_kit.py` | 35 | 對話框共用版面：`button_row()` 讓按鈕維持自身寬度並靠左（不再塞進格子被拉滿），`roomy()` 給頂層版面與分頁一致的邊距與間距。對話框底部 `QDialogButtonBox` 的預設按鈕由樣式表套用強調色。規則、App 設定檔、提醒、遙控、視窗釘選／複本、文字辨識、快捷鍵與衣櫃都已改用。 |
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
| `logging/loggin_instance.py` | 130 | 全域 logger（RotatingFileHandler）。日誌寫在 `$FRONTENGINE_LOG_FILE` 或 `~/.frontengine/logs/FrontEngine.log`，第一筆紀錄才開檔（import 不寫檔）、附加、UTF-8；開不了就改寫到 `os.devnull`。 |
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
`control_center_ui.clear_all()` 共用登錄來源；背景服務仍列在 `_CLOSING_SERVICES`。

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
| `.github/requirements/` | `publish.in` 與由它產生、鎖定版本與雜湊的 `publish.txt`：`release.yml` 那個握有 PyPI token 的 job 只裝這一份。建置後端 `setuptools` 也鎖在裡面，job 用 `python -m build --no-isolation` 建置，所以建置時不會再下載鎖定清單以外的東西（`tests/test_workflow_actions.py` 有守著，Dependabot 負責更新）。 |
| `progress.md` | 只放未完成的待辦（跨 session 交接）；規則與環境備忘在 `CLAUDE.md`，完成紀錄在 `docs/updates/`。 |

---

## 7. 擴充點

**新增一種覆蓋層**要動的地方（缺一個就會出現「只有某條路徑失效」的問題；新分頁還要加進 `ui/menu/features_menu.py` 的 `CATEGORIES`，`test_features_menu.py` 會擋）：

1. `show/<kind>/<widget>.py` — 繼承 `BaseWidget`，實作 `draw_content()`
2. `ui/page/<kind>/<kind>_setting_ui.py` — 繼承 `SettingPage`，用 `add_section()` /
   `add_row()` 描述欄位，實作 `get_state()` / `set_state()`
3. `main_ui._add_tabs()` — 加進對應的導覽分組
4. `main_ui._register_extra_overlays()` — 把 widget 清單註冊給控制中心
5. 共用覆蓋層登錄來源與 `register_cleanup`（批次關閉及退出共用）；頁面／工作執行緒於退出清理
6. **七份語言字典**都要加鍵（`test_translations.py` 會擋）
7. **七棵文件樹**都要加頁（`test_documentation.py` 會擋）
8. 該資料夾要有 `__init__.py`（`find` 設定是 `namespaces = false`，少一個就不會進 wheel，
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


## Runtime interchange and platform services (2026-10-03)

| Module | Boundary and lifecycle |
|---|---|
| `utils/recording/gif_writer.py` / `frame_recorder.py` | Incremental GIF encoder; copied RGB transfer to a bounded writer queue; timestamp-aware dropped frames; nonblocking stop/cancel; atomic output replacement |
| `utils/remote/tls_certificate.py` / `remote_server.py` | Persistent SAN-aware self-signed credentials, owner-protected private key, HTTPS token-authenticated commands; Qt receives queued events |
| `utils/session_lock/session_lock.py` | `is_session_locked()`: on Windows, the current input desktop through ctypes (`OpenInputDesktop` + `GetUserObjectInformationW`; unopenable or `Winlogon` means locked), elsewhere always unlocked; read-only, no subprocess. `SessionLockWatcher(QObject)`: a GUI-thread `QTimer` poll (2 s) with an injectable probe (resolved at call time, so `tests/conftest.py` stands it in for every test) that emits `locked_changed(bool)` on changes only; an `OSError` reads as unlocked. The pet home page pauses `HomeService` with `LOCKED_REASON` while locked and stops the watcher in `shutdown()`. |
| `utils/screen_text/local_ocr.py` / `screen_text_service.py` | Windows OCR, Vision, optional Tesseract; structured empty success/unavailable/failure; separate cloud image/text consent |
| `utils/imervue/puppet_asset.py` / `runtime.py` | Version/resource/path validation before optional upstream imports; no local repository path mutation |
| `show/pet/puppet_pet.py` | FrontEngine native pet window with upstream Canvas, motion/expression/idle/input/script; hide pauses, close clears document and native drivers |
| `utils/scene_format/` / `user_setting/scene_setting.py` | Legacy and versioned scene JSON, relative resources, portable ZIP copies; extraction leases survive until closed scene shutdown |
| `show/scene/compositor_view.py` | Visual layer textures including video/web/native Puppet frames, scene transforms/z/opacity and quality-aware refresh; native hosts provide explicit interaction |
| `utils/plugins/plugin_manifest.py` / `plugin_loader.py` | Permissions and SHA-256 content/location grants checked before import; imported settings cannot grant executable code; full application privileges after approval |
| `utils/macos/` | Lazy public PyObjC bindings; explicit TCC availability; ScreenCaptureKit frames/system audio, AVFoundation microphone, Quartz/AX geometry and movement, CoreMIDI lifetime |
| `show/compositor/` / `show/base_widget.py` | Software reference and actual OpenGL renderer; DPR-aware RGBA output; premultiplied alpha, clip, transforms/depth; persistent texture resources and CPU raster revision cache |
| `tests/integration/` | Real desktop OpenGL/puppet smoke checks; macOS capability report and own-window capture/movement with permission-dependent skips |

Capture uses a single selected display in logical coordinates. ScreenCaptureKit callbacks
copy the latest frame/audio state; Qt accesses it through region/audio adapters. Foreign
window opacity/forced stacking, Spaces and capture exclusion are unavailable on macOS.
The capability menu reports permission, missing-binding and unsupported states distinctly.
Mac hardware/TCC verification remains a target-host check rather than an injected-test claim.

## Workshop publication boundaries


Windows installs include `winrt-Windows.Media.Control`; Now playing prefers its modern namespace and retains legacy winsdk fallback. Nuitka explicitly includes the `winrt` namespace for dynamically selected projections.

`exe/build_exe.check_dependencies` evaluates project requirements and environment markers against installed distribution versions before compilation; missing or incompatible runtime requirements stop the build with an installation instruction.

`tests/integration/steam_workshop_private.py` explicitly publishes or updates private test content and persists operation IDs. `steam_workshop_download.py` verifies ownership/private visibility, subscribes only that item, downloads/validates/renders its scene and restores its prior subscription status. `steam_workshop_smoke.py` reads App-license and Cloud-quota diagnostics; these scripts require the real client and are excluded from unit-test side effects.

`ui/dialog/workshop_dialog.py` owns management controls, publisher/subscription controllers and background file jobs. Opening it does not connect Steam; Connect initializes the main-owned service. Closing hides the window and leaves submitted uploads running. Main shutdown stops workers/controllers before the runtime. Scene/Pet buttons and the Presets menu share one dialog. Scene packages loaded by a worker are installed through `user_setting/scene_setting.adopt_scene_entries`, which retains their extraction leases on the GUI thread. Preset media imports get isolated persistent directories and require unused local names. `exe/build_exe.py` optionally validates a selected x64 Steam DLL and copies it beside standalone/onefile output.

`workshop_jobs.py` delivers file-work results through explicit queued Qt connections with no UI updates after shutdown. `workshop_cache.py` validates installed content, atomically copies content-addressed versions, detects local modifications and switches an active pointer without deleting old content. `workshop_subscriptions.py` checks App IDs/result layouts, waits for install flags, re-queries native install locations and schedules at most two file-validation jobs at a time. Legacy offline preset/pet/media recognition remains available; new manifests use strict payload validation.

`workshop_publications.py` owns account/App-scoped publication journals, validated snapshots and content fingerprints. `workshop_publisher.py` consumes call-result events, verifies item ownership, configures private-by-default uploads and reports progress/terms/failures. Created IDs are persisted before upload; interrupted creation without an ID cannot be blindly retried. `WorkshopService.stopping` lets publishers persist uncertain outcomes before native shutdown. Snapshot preparation can run outside the GUI thread; native operations and callback handling stay with the Qt service.

`utils/workshop/workshop_manifest.py` validates versioned scene/preset/pet-pack and pet home (`home_furniture`, `home_theme` - a content pack folder; `home_blueprint` - a file) declarations, an optional `requires` list of content pack ids, and confines resources. `workshop_package` checks home items with the home's own loaders, copies only `pack.json`, the thumbnail and furniture PNGs into `content/<pack id>`, ships a blueprint as `canonical_blueprint` output and writes its `required_packs` into the manifest; the Workshop dialog shows `needs: …` for items whose packs are missing, opens a subscribed blueprint as a visit and says a pack arrives in the home on the next start. `workshop_package.py` creates validated publication snapshots with explicit media only. Native publishing is implemented separately. Legacy empty/known presets remain readable; arbitrary metadata JSON cannot become preset settings. Preset ZIP imports validate archive limits and reject flat-name collisions before extraction.

`utils/steam/steam_runtime.py` lazily loads the Windows x64 flat API, checks interface 021 and App identity, owns copied manual-dispatch events and shuts down exactly once. `utils/workshop/workshop_service.py` pumps a bounded callback batch through a Qt timer. Native ABI and read-only initialization checks are explicit tools in `tests/integration/steam_workshop_abi.cpp` and `steam_workshop_smoke.py`; native availability is not inferred from fake tests.

## Visual scene editing

`utils/scene_format/scene_editor_document.py` validates finite geometry and owns a bounded QUndoStack of deep-copied scene edits while preserving existing fields. `ui/page/scene_setting/scene_visual_editor.py` provides QGraphicsObject previews, image/GIF/text layers, group movement, corner resizing, properties/alignment/lock/visibility and export. Add layer/Edit/Align menus share the original callbacks; a horizontal splitter places the layer list and canvas beside Properties/Preview/Animation inspector tabs. Independent scene output stays in the page footer. SceneManagerUI emits `entries_changed`; the visual editor updates shared scene_json and Script text with a recursion guard. Applying external JSON resets undo history. SceneManager resizes and transforms playback proxies; legacy entries without dimensions retain their previous sizing. Video/web/Puppet/audio previews are explicitly enabled and preserve original fields. QMovie previews pause while hidden and are destroyed with scene items.

Application actions: `utils/actions/action_registry.py` owns stable built-in IDs and translated labels. MainUI binds instance callbacks once; hotkeys, authenticated remote commands, MIDI and rule dispatch use the same registry. Existing remote/rule allow-lists remain at their input boundaries. Duplicate IDs are rejected, unknown IDs are ignored, and parameterized actions require values. Hotkey/rule dialogs share these label definitions.

`utils/actions/command_history.py` validates bounded recent/favorite stable IDs in user settings and searches localized labels plus English/IDs with Unicode folding. `ui/dialog/command_palette_dialog.py` provides keyboard search/selection/value input and GUI-thread dispatch through ActionRegistry. Failed synchronous dispatch restores the dialog without clearing input and displays plain-text errors; changing the selected command clears its previous argument. List rebuilds preserve the same command's argument and synchronize favorite state. MainUI owns one persistent palette, exposes it in the sidebar and menu, installs Ctrl+K/Ctrl+Shift+P shortcuts and closes it on shutdown. Arguments/search queries are not persisted.

`utils/text_source/local_file_source.py` reads bounded regular UTF-8 TXT/JSON/CSV files with a single pending QRunnable per QObject feed, explicit queued delivery, metadata cache and recoverable status codes. LocalFileTextSource owns its polling timer; TextWidget adopts its lifetime and stops it on replacement/close. TextSettingUI exposes file/field/interval and bounded previews; MainUI stops page previews during shutdown. Scene text factories accept the same local source fields; scene asset normalization/packages include text_file explicitly. Preset state preserves source configuration. No file I/O occurs on the GUI thread.

`utils/measure/color_palette.py` validates and persists bounded named/grouped RGB swatches and recent samples, rejects duplicate group/name identities, rolls back failed saves and atomically exports JSON/CSS with unique slugs. `MeasureWidget.color_sampled` emits canonical hex on clicks only. ToolsSettingUI collects only when enabled and owns `ui/dialog/color_palette_dialog.py`; the manager edits/searches/exports the model, and MainUI registers its command and closes it during shutdown. Palette settings are separate from overlay preset state.

`user_setting/preset_history.py` keeps bounded immutable SHA-256 configuration snapshots under `presets/.versions/<sanitized-name>/`, validates finite JSON/digests/timestamps and prunes to 50 distinct versions. PresetRepository records old/new configurations before atomic active-file replacement and discards a newly prepared candidate on failure. `ui/menu/preset_menu.apply_state_transaction` snapshots every target page before strict application and restores touched pages (including a partially failed page) on error. `ui/dialog/preset_versions_dialog.py` compares settings, applies a cancellable preview to page controls and restores/saves a selected version transactionally. MainUI closes the manager before shutdown session persistence. Media files remain referenced, and existing JSON/ZIP preset layouts do not change.

`user_setting/pet_profiles.py` provides independent UUID pet records in the versioned pet_profiles section of user settings. It validates 256 bounded named records and mood/fullness/affection ranges, migrates legacy shared stats into the first identity only, commits record changes without overwriting peers and restores settings on save failure. Atomic portable frontengine.pet-save v2 JSON exports contain one identity only; v1 imports remain supported; imports always receive a new ID. `show/pet/pet_profile_session.py` leases one live session per settings/identity, reads current widget stats, debounces sprite saves and flushes/stops/releases on close. DesktopPetWidget uses record stats instead of shared globals; PuppetPetWidget retains its upstream rendering/geometry and supports independent feeding stats. `ui/page/pet/pet_profile_controls.py` selects saved/new identities, renames, refreshes and imports/exports saves (flushing live stats first); PetSettingUI clones into a new identity. Local profile IDs stay outside portable presets.

`show/reference/image_compare.py` bounds image file/dimension/canvas sizes, decodes oriented first frames, aligns RGBA images at origin/center or proportionally fits B inside A, and computes absolute RGB differences after compositing on white. `ui/dialog/image_compare_dialog.py` decodes/aligns/compares through a shared two-thread comparison pool with one outstanding request per dialog, close-cancellation checks and generation-based latest-selection coalescing and explicit queued delivery. A shared QGraphicsView synchronizes zoom/pan; retained pixmaps support side/overlay/clipped-wipe/difference modes without re-decoding on slider changes. ImageSettingUI owns the comparison dialog; page/main shutdown clears pixmaps and ignores late worker output. Invalid replacements preserve the previous pair and alignment.

`utils/rules/rule_engine.py` normalizes stable independent IDs, bounded priorities/cooldowns and at most 200 rules; RuleTracker uses monotonic cooldowns, consumes suppressed rising edges without delayed execution and sorts low-to-high priority with stable ties. RuleEngineService exposes non-mutating previews and a bounded session-only receipt deque with sampled context/conditions; transient receipt IDs pair application outcomes even across nested dispatch. ActionRegistry honors explicit False callback results. MainUI records failed/executed outcomes without stopping later rules. RulesDialog edits priority/cooldown, preserves identity and non-table conditions, rejects invalid named rows, rolls settings back on persistence failure and previews unsaved rows / displays execution receipts without internal IDs. Scene/layer actions use deferred completion receipts and named playback instances.

`utils/scene_format/scene_source.py` reads bounded scene files without changing globals and owns rejected extraction leases. `scene_action_values.py` validates scene paths/explicit screen selection and exact layer action values. `ui/page/scene_setting/scene_actions.py` owns one worker read plus one latest queued request, cancellation, GUI-thread hidden candidate construction and adoption into existing SceneManager list objects. Following layer actions wait for their scene result; superseded/failed/stopped requests resolve their deferred receipts explicitly. `utils/actions/deferred_action.py` provides one-shot completion; ActionRegistry.invoke returns receipts while execute preserves acceptance semantics. MainUI records asynchronous outcomes on completion. SceneManager tags named proxies/native monitor instances and synchronizes document geometry/visibility/opacity edits and undo; invisible proxies are excluded from compositor frames. RulesDialog uses `ui/dialog/scene_action_dialog.py` for file/monitor/layer selection. SceneSettingUI closes views/previews before extraction leases on shutdown; stopping playback preserves editor assets. Current-scene playback rejects a document changed during preparation. Legacy unnamed add_* methods remain compatible.

`utils/scene_format/scene_templates.py` defines three self-contained translated TEXT layouts, independent editable entries, proportional fitting to logical available screen size and missing-resource diagnostics. `ui/dialog/scene_templates_dialog.py` owns bounded QGraphics preview items, template/screen selection, target revalidation and owner-specific cancellation. SceneManagerUI and the command palette open one page-owned library. SceneActions.request_entries uses the same hidden candidate/adoption path as file scenes; cancel_request cancels only its matching pending/wanted operation. Application replaces the document after successful candidate preparation, preserving existing portable scene exports. The focus starter contains static editable reminders; existing scheduling/timer tools retain those responsibilities.

`show/scene/media_frame.py` owns bounded Qt video sink polling, hidden web surfaces and Imervue public offscreen Puppet rendering. Native decoder callbacks never run Python directly: polling retains the newest sink frame without queued-frame accumulation or stop/GIL deadlocks. Explicit activity pauses media and hidden hosts; shutdown stops and disconnects before disposal. Named VIDEO/WEB/PUPPET scene entries now share software/GPU layer transforms/z with IMAGE/GIF/TEXT; SOUND exposes a transparent frame. Standalone overlays and legacy unnamed add_puppet remain compatible. SceneCompositorView tracks visible-view owners, forwards mute and opens the same native web/Puppet host on double-click. `ui/page/scene_setting/scene_media_preview.py` retains at most eight manually enabled, initially muted providers across geometry edits; disabling/replacing closes them. Hidden editor previews pause, scripts are disabled for preview, and scene Puppet profiles are ephemeral. Provider factories permit device/network-free tests.

`utils/recording/avi_writer.py` implements silent incremental MJPEG AVI using Qt JPEG encoding, disk-streamed RIFF chunks and a disk index (one JPEG retained; 2 GiB/one hour/72,000 frames bounded). Dropped-frame intervals repeat the last JPEG to retain effective timing. It implements the existing AsyncGifWriter worker factory contract without changing GIF import paths. FrameRecorder selects GIF/AVI, exposes recording/paused/finalizing/cancelling/idle signals and accepted-frame/effective-duration/drop progress, excludes pauses using a monotonic offset and stops native region capture during pause. Resume reopens capture; stop while paused finalizes the same clip. GIF defaults/limits remain compatible; AVI supports teaching-length clips. ToolsSettingUI owns format, pause/resume/cancel controls and localized live status. Worker errors/cancel remove temporary output before any target replacement; index storage does not grow RAM with clip length.

`utils/scene_format/scene_animation.py` validates optional animation tracks at normalize_scene boundaries (128 unique increasing frames/layer, one hour, finite bounded x/y/opacity, linear/smooth interpolation). Scene v1 and portable exports retain tracks. `show/scene/timeline.py` shares monotonic pause/resume/seek/replay clocks, hidden suspension and baseline restoration across editor/playback. Scene-owned callbacks do not retain closed views; clear stops/disposes timelines. Named proxies retain saved entries separately from sampled geometry. `ui/dialog/scene_animation_dialog.py` edits tracks as one undoable change with fade/slide starters. SceneVisualEditor scrubs transient values, blocks geometry edits during preview and restores saved values on reset; playback controls reach each unique scene clock. SceneActions snapshots at most eight outgoing composed views (1920x1080 maximum), closes old native resources before adoption and starts a 0.5s dissolve on new views. Transition composition temporarily uses software raster plus premultiplied RGBA mixing with bounded row temporaries, then returns to normal layers. Animation pause also suspends media; replay applies to animation tracks, not arbitrary web application state.

`show/scene/render_session.py` owns an independent, hidden, software SceneCompositorView at fixed 640x480/1280x720/1920x1080 physical pixels, normalizes device-pixel ratio and never captures desktop pixels. It validates 256 layers/eight native sources/16 MP total raster bounds, source image sizes/resources and forwards media errors. Named SOUND uses a suspended SceneMediaFrame (transparent outside editor preview) so output can mute before any playback; legacy unnamed add_sound retains its factory behavior. `utils/virtual_camera/frame_sender.py` owns one camera worker and one latest detached RGB pending frame; startup/send/close occur off the GUI thread with explicit queued signal delivery. `ui/dialog/scene_output_dialog.py` requires explicit preview/send, displays renderer surfaces, keeps audio muted, handles slow/failing devices and closes on stop/Escape/owner shutdown/editor changes. It stops old file readers synchronously before SceneActions releases extraction leases; camera disposal is asynchronous and independent of files. SceneSettingUI owns/reuses one output dialog and closes it before SceneActions shutdown.

`utils/pet_pack/pack_builder.py` validates image action mappings and bounded traits, reads legacy aliases, copies only selected resources with cancellation into a staged new directory, and exports portable canonical sprites plus pet.json; no .puppet conversion or sound/script import. `ui/dialog/pet_pack_editor.py` runs at most one bounded file worker with queued results and cancellation, maps six actions and selects a completed export on PetSettingUI without spawning it. `pet_pack_preview.py` owns uncached scaled QMovie/static preview and a walk-speed timer, suspends on hide and releases on replacement/close. MainUI closes the editor before scene asset leases; no overlay registry entry because the preview is an ordinary child QWidget.

`utils/capture_editor/document.py` owns one detached physical-pixel original, a crop, bounded vector marks and twenty undo states; render flattens current edits with solid redactions last, QSaveFile atomically writes PNG only. `ui/dialog/capture_editor.py` maps view gestures through the crop offset, has a read-only original toggle and explicit edited copy/save/pin, and never mutates ToolsSettingUI.last_capture. ToolsSettingUI owns one delete-on-close editor, identity-checks dialog completion during replacement and adds pinned results to its existing registered pinned_widget_list. MainUI closes the editor at shutdown.

`utils/whiteboard/document.py` validates version-one .fewhiteboard JSON (50 pages/2000 strokes per page/100000 total points/eight MiB) and publishes atomic cancellable QSaveFile snapshots; WhiteboardDocument owns independent page views and twenty bounded active-page undo snapshots globally. `utils/whiteboard/raster.py` validates and renders one page using QPainter/QImage with full pen margins and bounds 8192 pixels/side/16 MP; no controls, selection or pan/zoom appear in exported PNG. `show/canvas/whiteboard_widget.py` keeps legacy active-page strokes/zoom/offset interfaces, selects by canvas-space segment distance and converts movement deltas through zoom. `whiteboard_controls.py` is a show-layer child toolbar (no upward UI dependency), owns one queued file worker, snapshots before background writes, applies fully validated reads on GUI, disables gestures while work is pending, requests cancellation and ignores late callbacks on close. Existing PresentationSettingUI whiteboard_widget_list remains the control-center/preset lifecycle source; no new registry required.

`utils/image_history/repository.py` is a worker-owned SQLite repository (memory by default, clipboard-images.sqlite3 beside settings only with consent). PNG payloads are bounded to 16 MP/eight MiB each, 10–200 images/8–128 MiB total; favorites count toward hard bounds. SQL transactions deduplicate, evict unpinned images and delete associated OCR text together; QImageReader checks dimensions before decoding database payloads. Persistent opt-out migrates to memory and removes disk data; clear VACUUM releases pages. Database max_page_count bounds main-file size to 132 MiB, not temporary rollback journals. `service.py` starts lazily, reads QClipboard only after opt-in, owns one repository thread and one latest pending detached image. Command and result mailboxes retain one newest value per allowed kind; GUI QTimer polls results, avoiding queued-image accumulation and cross-thread QWidget calls. Stop drops queues/disconnects clipboard and asynchronously closes the database. MainUI owns/configures/stops it; `ui/dialog/image_history_dialog.py` offers explicit settings, bounded thumbnail lists and explicit copy/pin/reference output. Pinned images and reference boards join existing registered lists; `ReferenceBoardWidget.add_pixmap` accepts bounded memory images. This does not enable existing text clipboard history, cloud upload or OCR.

`utils/screen_text/live_ocr.py` owns one GUI RegionSource (screen-local Qt coordinates on Windows/X11, one-frame asynchronous RegionCaptureAdapter on macOS) and one detached daemon OCR job per LiveOcrSession. GUI timers poll one result; close drops late results without waiting on an external API request. make_live_reader keeps local-only calls out of ScreenTextService cloud fallback even if global consent exists. `show/pinned/live_ocr_widget.py` is a temporary topmost QDialog with explicit refresh/5–60s automation, overlap rejection, twenty unique memory texts and explicit displayed-text copy; cloud fallback is opt-in per window and asks ToolsSettingUI to review existing screenshot/text consent only on an explicit button. No translation or cloud text action is implemented. ToolsSettingUI limits four windows, owns capture pickers and ocr_widget_list, while MainUI adds the list to control-center batch operations and closes windows during shutdown. These capture regions are not automatically resumed from sessions.

`utils/image_history/capture_service.py` specializes the bounded image history worker with local-only OCR and no clipboard provider. MainUI owns a separate default-off capture_history setting and capture-history.sqlite3; ToolsSettingUI.captured emits only explicit region capture QImages. The same single pending input/result mailbox bounds OCR work. Recognition failure saves the image with empty text and an explicit reason; successful text stays in the same SQL row, so remove/clear atomically remove the index. ImageHistoryDialog capture_mode adds debounced case-insensitive text/exact local-day search, reuse controls and independent opt-in. UTC/offset timestamps remain stored; repository date filtering and UI display use the user local timezone. No ScreenTextService/cloud consent/network path is involved. Lifecycle stops capture history with other MainUI services and closes both history dialogs.

`utils/todo/calendar_import.py` implements bounded local UTF-8 RFC5545 VEVENT/VTODO records: byte unfolding/TEXT decoding, UID+RECURRENCE-ID hashing, sequence/cancellation, date/floating/UTC/IANA-zone normalization and DST RelativeToBefore. DURATION nominal days preserve wall time; all-day/midnight end is exclusive in today_items. Unsupported recurrence sets and unknown TZID reject the whole transaction; no calendar synchronization, alarm, attachment or URL execution. `repository.py` validates version-one tasks.json, 500 records/four MiB and atomic QSaveFile save-before-publish, merging imports without duplicating checked items. `service.py` lazily starts one daemon document job, rejects overlap and polls one result; stop prevents not-yet-started writes and ignores late results without blocking. MainUI owns/stops TodoService. WidgetsSettingUI exposes TodoDialog and one todo_widget_list; MainUI registers/clears this list for batches/shutdown. `ui/dialog/todo_dialog.py` shares TodoPanel between manager and Today overlay; `show/notes/todo_widget.py` receives an injected panel factory to keep show→ui inversion out of modules. Date polling stops while hidden/closed. Task data persists independently from explicit widget visibility, is not part of presets and does not auto-reopen widgets.

Cancellation tombstones count toward the 500-record limit and prevent stale imports from resurrecting cancelled events. Clear all asks for confirmation and removes tasks, events and cancellation metadata. Interactive Today controls use ordinary Qt software painting so the compositor cannot cover them. Desktop pets also pin ordinary Qt software painting (`DesktopPetWidget.set_render_backend`): a pet moves its window every tick, and on the GPU compositor its animation frames were not presented while it moved.

`utils/asset_library/inspect.py` decodes one bounded static image/GIF frame, first sprite/puppet texture and static scene image/text composition without executing native content. Portable scene extraction leases close after thumbnailing. `repository.py` persists 200 bounded version-one asset-library.json records independently from resources; tags/favorite/search retain missing files. `references.py` restricts rewrites to exact scene ASSET_FIELDS and known preset page path fields, leaves immutable history/literal text alone, and treats packages/external/managed Workshop documents as read-only. Relink plans snapshot reviewed raw bytes, validate matching type and limit 50 files/16 MiB. Atomic .asset-relink.json journals known old bytes/new hashes before multi-file updates; recovery verifies every current target and registered local scene/active preset authority before restoring, retaining unexpected conflicts. `file_lock.py` wraps OS-owned nonblocking byte/flock locks across a whole lazy serialized service job, so another app instance cannot recover a live transaction. `service.py` polls one result and cancels pending commit writes on stop. MainUI owns service/dialog and restores an unchanged in-flight editor path edit before scene teardown. `ui/dialog/asset_library_dialog.py` offers static thumbnail search/organization/reference review, applies current SceneEditorDocument as an undoable edit before durable commit, and restores it on failure only if the user has not subsequently edited it. Restart live playback after media path changes. No automatic scan, resource deletion or Steam content mutation.

`utils/window_pin/follow_window.py` isolates Win32 selected-target identity cookies/PID/thread checks and physical frame/move/monitor geometry. SetProp registration is reversible and may fail under UIPI; absence on HWND reuse stops following. WindowFollowService holds at most 64 weak temporary overlay bindings, polls only while bound, preserves initial proportional anchor, moves without native size/activation and clamps physical work areas. Event filters detach closing overlays and preserve manual visibility; ControlCenterUI.overlay_visibility_changed prevents target restoration undoing hide-all. MainUI owns/stops service, registers detach_all cleanup and reuses window_follow_dialog with existing overlay registry. Dialog never persists target handles; only verified Windows backend is enabled. Target hidden/closed/lost cookie detaches; minimize temporarily hides. Current native environment has one 125% display, so cross-monitor mixed-DPI remains explicit acceptance work.

`utils/window_pin/topology_profiles.py` keeps bounded versioned atomic monitor-profiles.json (20 hardware combinations/200 overlays/512 KiB). Hardware name/manufacturer/model/serial identities reject ambiguity; topology identity ignores resolution/DPI/primary, placements store proportional Qt work-area anchors and logical sizes. Existing registered unique kind/title windows only; ambiguous duplicates excluded from saved placement but clamped when outside. Fullscreen/scene windows and active WindowFollowService bindings excluded. MonitorProfileService observes Qt screen changes and newly shown registered overlays only after separate opt-in, debounces 500 ms, clamps new combinations onto primary work area, disconnects screen signals on shutdown. No native handle guessing or Qt-to-Win32 coordinate conversion. MainUI owns service/dialog/settings; ControlCenter requests reusable monitor_profiles_dialog. Native current acceptance limited to single Windows125% screen; real hotplug/primary/mixed-DPI stays pending.

`show/compositor/widget.py` signatures image cacheKey/DPR, copied transforms/clips, z/order/opacity and physical output geometry; identical set_layers skips both repaint requests and static software frame composition. One detached-return software cache is bounded to 16 MP (larger surfaces uncached); mutation/resize/DPI/shutdown invalidates. GPU readback path unchanged. benchmarks/scene_composition.py is a seeded developer-only baseline module comparison with exact pixel hashes and static/changing timing distributions, no timing CI assertions. App shutdown shares ControlCenterUI.clear_all registry with id-deduplicated close-before-clear and wallpaper owner cleanup; notes/state save first, scene resources release afterward. ui/plugin_pages.py attaches trusted QWidget overlay_widgets and optional release_overlay_resources/shutdown; preset_menu includes loaded API-v1 get_state/set_state pages in plugin:<name> namespace with strict transaction rollback and no code loading. examples/plugins/clock demonstrates API-v1 lifecycle, preset bounds, hide/close timers; plugin manifests already reject other API versions. utils/shutdown_barrier.py polls canceled local worker threads/global Qt jobs before owned QApplication exit without GUI joins; does not terminate unrelated apps.

`utils/linux` provides explicit X11/Wayland session policy, EWMH/python-xlib window list/physical-frame geometry/pin/move, compositing-manager-gated opacity and physical XRandR work areas. Native Wayland arbitrary-window control/global pynput input/profile positioning are rejected with concrete reasons, not described as global Xwayland support. Linux-only python-xlib dependency aligns requirements and both manifests. PulseCapture launches fixed distro parec paths on one worker, default output monitor or microphone, one sanitized 2048-float memory frame; lazy PulseMeter construction does not start disabled reactive audio. Stop handles spawning races, kills only own child, worker reaps; shared captures stop on MainUI shutdown and join only through GUI-polled barrier. WASAPI peak-only behavior unchanged; Linux meter requires real audio samples, explicit docs distinction. LoopbackSpectrum/SystemAudioMeter/MicrophoneMeter route Linux to this adapter. platform_info/capabilities.py and Help platform_capabilities_dialog display read-only prerequisites/original failure reasons without enabling capture/listeners. Protocol acceptance uses isolated Linux display/audio servers; physical Mac/Linux audio/multi-monitor acceptance remains separate.

- Windows entry `exe/start_front_engine.py` delegates normal startup to the published main_ui.main CLI (--preset/--debug). Explicit --verify-scene-build FIXTURES REPORT calls the fixed exe/scene_build_acceptance.py probe with isolated temporary settings and local seven-type inputs (tests/integration/scene_build_fixtures.py). It verifies compiled native media/editor/export/cleanup and writes bounded owned screenshots/report, never supplied Python scripts. Fixture generation optionally needs PyAV; native Puppet acceptance needs the optional runtime in the build environment. Installed Pillow decoder plugins and Imervue package data are included by build_exe.py.


## Companion state and active sessions

`utils/pet_companion/stats.py` owns the shared mood, hunger and growth models. `utils/pet_companion/companion.py` owns energy, persistent play/work/rest modes, timed interactions, cooldowns and completion-only rewards without Qt rendering. Cancellation gives no reward; full pets reject feeding, and drag/appearance changes do not award affection. Care advances only during active time, independently of chatter, without hidden/offline catch-up.

`user_setting/pet_profile_schema.py` validates version 2 identity records, including energy, mode, preferences and bounded appearance references. Migration retains version 1 UUIDs and stats. `user_setting/pet_profiles.py` owns storage/import/export; `show/pet/pet_profile_session.py` owns one live identity lease, the companion session, persistence and lifecycle boundaries. Widgets request actions and render state; they do not maintain competing care clocks. Sprite menus expose greeting, petting, grooming, play/work/rest and cancellation. Puppet uses the common session and feeding rules while native presentation remains dependent on runtime/model capabilities. Appearance references are used by the layered wardrobe described below; finished artwork and toy UI remain pending.

`show/pet/companion_menu.py` shares companion menu actions between sprite and Puppet pets. `ui/dialog/pet_customization.py` edits a detached preferences draft for one identity, reached from profile controls or that pet's menu. Apply checks for conflicting preference edits and persists atomically before publishing to a live session; save failures preserve the draft. Cancel does not mutate state, and Reset defaults only stages changes until Apply. The schema accepts an optional `preferences.presentation` record; `None` inherits page defaults. Explicit records validate size 16–512, speed 1–20, floor/wander/chase behaviour, climbing, window sitting, speech bubbles, volume 0–100 and settling while typing. Automatic rest, throwing and social preferences remain per identity; clone/import retain them and presentation settings. Puppet disables unsupported controls and applies only size, speech bubbles and settling while typing among presentation fields. Native wardrobe controls and layered artwork remain unfinished.

`utils/pet_pack/layered.py` validates bounded layered-pet.json assets into immutable frame/anchor/layer definitions and checks garment slots, templates and exact action timelines. Layers may draw a `source` rectangle from an atlas image up to 2048 pixels a side; `image_bounds`/`check_sources` keep whole-image layers within the canvas and rectangles within their image. `show/pet/layered_renderer.py` preloads bounded static PNGs and composes character and clothing from one sampled frame before mirroring, with one detached-return image cache. The renderer owns no timers or profile state. The format is documented in `docs/formats/layered-pet-v1.md`; it is wired to live pets through WardrobeDraft, and its wardrobe UI. Existing pet.json loading is unchanged.

`show/pet/wardrobe.py` owns a version-exact AssetCatalog and detached WardrobeDraft. Character choice, equipping, multi-slot removal and saved-outfit edits validate and preload before replacing the draft. Apply reloads resources, checks the saved appearance baseline and commits through the active session when present, preserving current care stats. Cancel releases the preview and restores the last applied appearance. Missing assets retain their saved references until explicit repair; duplicate catalog identities and partial multi-slot equips are rejected. The controller publishes prepared renders to active desktop pets after saving and is used by the wardrobe dialog below.

Desktop publication now follows successful appearance persistence: PetProfileSession publishes the prepared renderer before emitting changed, and DesktopPetWidget adopts it. `show/pet/layered_playback.py` tracks active animation time without owning a timer; existing desktop ticks select actions and repaint composed frames before existing whole-pet transforms. Hidden pets pause playback and suspend movement/chatter/reminder timers, restoring active timers on show. Companion menu mode checks use a menu-owned QObject receiver for automatic signal cleanup. The wardrobe dialog below exposes this live-rendering path.

`show/pet/asset_library.py` installs manifest-declared resources into the startup directory's pet-assets library, under a hash of exact asset ID/version. Bounded copying, staging validation and directory rename publish complete packages without overwriting installed versions. Scans report broken packages while retaining valid entries. DesktopPetWidget resolves its saved appearance on startup and exposes restore_appearance for retry after repair, preserving saved references and recording appearance_error on failure. QImageReader devices close explicitly even on validation errors to release Windows file locks before staging cleanup. The wardrobe dialog below exposes installation and resource refresh. Loading validates image references against one link-free listing of the asset folder, and `install_many` installs a batch after a single library scan.

`show/pet/inkside/` draws the built-in INKSIDE characters and wardrobe as ordinary layered-pet v1 assets. `ink.py` holds the three-ink Brush that replays one part description per output layer (palette regions, fixed paper, ink); `rig.py` defines template-independent poses and the timelines for every supported action; `template.py` is the per-body drawing contract (head, ears, torso outline, arms, feet, tail, crown/chin metrics, part groups) implemented by `cast_mochi/moss/pip/bolt/ink/gill.py`; `faces.py` provides eye and mouth styles with every expression; `garments.py` defines thirty slot pieces of fourteen outfits drawn from template geometry so each piece fits every body; `assemble.py` turns a template or garment plus a pose into placed elements; `builder.py` renders, crops, deduplicates and packs them into per-layer atlases and writes the manifest; `puppet_export.py` writes a character as an Imervue v1 `.puppet` (part textures composed from the layered asset, rotation and warp rigs, motions with fade-outs, eye/mouth expressions) plus a `frontengine_actions` pet script, run from the Pet page as PuppetExport off the GUI thread; `sprite_sheet.py` keys image-model sprite sheets drawn on flat magenta, folds off-palette pink and magenta tint into the three inks, clears stray specks, aligns the frames (per-frame on the ground with the head centred for walking, one shared offset against the wall line for climbing) and stores them as square-frame atlases in `sprites/`, which ship as package data; a template's `sprite_actions` turns an atlas into an optional `<action>_sprite` whole-body action that the layered renderer plays in place of `<action>` only for an undressed pet with default parts and colours (walk and climb, plus the four-frame home poses sit, sleep, feed, play, write, garden and craft for all six characters; `sprite_sheet.character_sprites(name)` declares them, `layered.HOME_POSES` lists the poses and `LayeredRenderer.has_action()` tells whether a pose would really play; `tools/codex_home_poses.py` reruns the Codex sheets and the atlas cut); `labels.py` localizes built-in labels through the language dictionaries while leaving third-party labels as authored; `library.py` builds one character with its fitted wardrobe in a temporary folder and installs it through PetAssetLibrary; every built-in asset carries `builder.ASSET_VERSION` (2 since the home poses), and `upgrade_builtin(appearance)` returns the appearance with older built-in character/garment references, and the `id@version` keys of their colour overrides, at the current version (third-party references untouched) so a pet can be moved by an explicit, stale-checked appearance change — `AssetCatalog` itself still never substitutes versions. The wardrobe dialog runs it as PetBuiltinInstall off the GUI thread; closing cancels. The Pet page's Use built-in character runs PetBuiltinSprite (ui/dialog/pet_asset_install.py) off the GUI thread: it installs the character into the default PetAssetLibrary and renders its idle frame to pet-previews/<id>.png as the source image; Start spawns an ordinary DesktopPetWidget from that image and dresses its identity as the character through WardrobeDraft unless it already wears it. Use built-in Puppet model beside it keeps the PuppetExport path.

`ui/dialog/pet_wardrobe.py` exposes character and four-slot choices, a separate active-time preview with action/facing controls, named outfit create/update/delete/wear, Apply and Cancel, and resource refresh/error feedback. PetProfileControls owns one dialog per identity; the sprite context-menu signal uses the same entry. Active Puppet identities reject layered wardrobe commits. `ui/dialog/pet_asset_install.py` runs cancellable resource installation on the global thread pool with queued GUI result delivery; closing cancels pending installation and releases preview/timers. Installation persists library resources independently of applying an appearance. UI labels are present in all seven dictionaries; official artwork and native acceptance remain pending.

`utils/pet_pack/palette.py` validates at most eight RGB regions per asset and five exact-asset override maps per outfit. Layered assets optionally declare palettes and per-layer tint references; undeclared references fail loading. LayeredRenderer applies SourceIn color to designated PNG alpha masks during preload, preserves untinted details, and counts distinct tinted variants toward its decoded-image limit. Profile appearance and saved outfits optionally retain color overrides without rewriting older records. WardrobeDraft stages colors, restores authored defaults, removes overrides when removing garments, and preserves detached colors in outfit snapshots. The wardrobe exposes region selection, QColorDialog and reset only for supported assets.

PetProfileSession.close returns failure without releasing its identity lease, renderer or retry timer when persistence fails. Sprite and Puppet close events then ignore closure and preserve runtime resources. ControlCenter retains overlays whose close explicitly returns False and defers global cleanup while any remain. MainUI flushes each distinct active pet session before beginning shutdown and aborts teardown with a status message on failure. PetGrowth and profile validation share MAX_AFFECTION to keep completed rewards inside the supported persistence range.

DesktopPetWidget.can_socialize is the shared availability check for visible, active, autonomous Play-mode pets with social permission and no dragging or typing settlement. PetSettingUI uses it for both peer targets and tag participants, clears excluded roles, and restarts games after availability returns. Session changes, show/hide and typing transitions update participation. Speech visibility only controls greeting presentation; reward deduplication remains in the companion domain.

`show/pet/focus_companions.py` observes the existing FocusTimer phase transitions without owning another timer. It temporarily moves initially visible idle pets into Work and Rest, records session mode revisions and restores earlier modes only while it still owns that choice. Per-run completed-round tracking deduplicates rewards; hidden/closed/interacting/manual-override pets do not receive them. Session mode revisions include explicit choices and automatic mode transitions. Default FocusTimer time derives from monotonic elapsed time while preserving injectable datetime clocks for tests. Work/Rest suppress proactive sprite chatter. App shutdown stops pet focus and restores owned modes before flushing profiles.
# 專注位置補充

`show/pet/puppet_reactions.py` validates optional frontengine_actions script bindings against loaded native motions/expressions before allocating a widget. PuppetReactions transitions only on companion visual-action changes and owns only effects it starts. PuppetPetWidget routes common actions through the native player, releases reaction ownership before manual motion/expression/hit choices, and resets on hide/typing/shutdown. Existing scripts remain valid without bindings. Native visual acceptance is separate from API/state tests.

`show/pet/recovery.py` returns a selected live identity to the monitor's available work area without activating it. Its `follow_screen` restores a pet's intended logical size and clamps it into the new monitor after a DPI rescale; both pet widgets call it on `screenChanged` and on any foreign resize, and sprites adopt the new monitor as their movement bounds. Window-perch edges come from `platform_info.standable_windows_native` (physical pixels plus monitor) and `desktop_pet.native_edges_to_logical` converts them per monitor, pairing Win32 monitors with QScreens by origin, then native size. PetProfileControls exposes recovery independently of spawning. Recovery cancels unfinished interactions/toys, invalidates focus-placement restoration, updates Sprite physics bounds and actual coordinates, and shows hidden pets. Oversized or inactive pets receive feedback before mutation. Puppet model and identity stay attached; native mixed-DPI acceptance remains pending.

CompanionState owns an optional two-second cosmetic presentation on its existing active clock. `celebrate` and `outfit_show` never enter snapshots or reward paths; actions/mode changes cancel them and presentation expiry emits through PetProfileSession's visual-state comparison. FocusCompanions requests celebration only after a deduplicated reward and Rest transition; repeated phase notifications neither restart nor cancel it. Successful changed wardrobe commits request outfit_show without interrupting active care actions. Desktop rendering uses existing action selection; authored assets and native Puppet mapping remain separate gates.

PetSettingUI clone spawning accepts the source pet alongside its detached profile. Resource type/path and constructor defaults come from that source rather than the mutable page selection. Sprite clones reuse the versioned asset library but own separate profile sessions and renderers; native Puppet clones retain model/script, parameter values and active expressions. Normal Start continues to use the page settings.

`show/pet/light_toy.py` provides a draggable range-bounded light target. A released target held within reach for half a second requests the shared timed play action; rewards require its completion and cooldown. DesktopPetWidget owns one `_toy`, advances it with the existing tick, and uses shared start/stop/eligibility for both BallToy and LightToy. Switching toys disposes of the previous overlay and clears guidance. Light targeting projects to the floor in floor mode; wander/chase use the bounded two-dimensional target. Native focus and authored character-specific play animation remain pending.

`show/pet/ball_toy.py` is a pet-owned input-enabled ball overlay with no keyboard focus and no independent timer. DesktopPetWidget's existing tick advances bounded flight, chase and return; motion guidance uses the same movement engine for floor/wander/chase. Ball ownership excludes social play. Completed returns request the shared `ball` reward, separately cooled down from URL fetch. Mode/interaction/visibility/typing changes and explicit dismissal clear guidance and dispose of the overlay. Native focus acceptance remains pending.

`utils/pet_companion/petting.py` recognizes three alternating stroke segments with a size-relative distance threshold. Sprite menu requests arm this gesture through an optional companion-menu request adapter. DesktopPetWidget suppresses dragging/autonomous motion/social participation while armed; validated strokes request the existing timed pet action, retaining its completion and cooldown ownership. Leave/hide/mode changes and explicit cancel end the gesture. Puppet retains the existing timed command until native gesture adaptation is verified.

`ui/dialog/pet_photo.py` owns a frozen pet-only snapshot, optional authored layered pose/time selection and atomic PNG output through QSaveFile. DesktopPetWidget opens one photo dialog from its context menu and renders its own content into a transparent QImage, excluding bubble children and desktop capture. The dialog retains the captured renderer for outfit consistency and uses no timer or companion rewards. PuppetPetWidget uses Imervue's render_offscreen_puppet with transparent background, guarded by runtime capability and GL validity checks. Native rendering failures show retry feedback; adapter tests replace the GL boundary, so native photo acceptance remains pending.

`utils/pet_pack/variants.py` validates bounded character-part group definitions and saved selections. Layered assets declare optional groups and per-layer selectors with complete per-frame coverage. The renderer preloads all alternatives under the same resource limits and filters selected layers during composition. WardrobeDraft stages selections and snapshots character/parts in saved outfits; the dialog exposes asset-defined group and choice labels. Legacy assets and profiles omit these optional fields.

`frontengine/show/pet/focus_placement.py` 負責工作區角落排列與可恢復的位置紀錄；`FocusCompanions` 持有紀錄並沿用模式所有權檢查。Sprite 的 `place_for_focus` 同步視窗與物理座標。使用者拖曳增加 placement_revision，即使拖回同一位置也不被停止專注的操作覆寫。


寵物點心選單補充：show/pet/companion_menu.py 的 add_food_actions 共用四種虛構食物選項，Sprite 與 Puppet 的 feed(kind) 只負責結束撫摸／收玩具並交給 PetProfileSession.request；食物效果、完成與共用冷卻仍由 CompanionState 擁有。

口味偏好補充：pet_profile_schema.py 驗證可選 preferences.taste 的 favorite/disliked；pet_customization.py 只編輯草稿。CompanionState 接受餵食時凍結當餐判定，完成時只調整心情並發出 food_like/food_dislike 短呈現。分層 ACTIONS 與 Puppet 顯式綁定共用這兩個動作名，無新獎勵或獨立計時器。

過來指令補充：show/pet/call_target.py 的 CallTarget 延伸 LightToy 有界拖動落點，改用 greet 抵達動作及箭頭繪製。LightToy.arrival_action 預設 play；DesktopPetWidget.start_call 透過既有 _start_toy 管理單一目標所有權、工作區及中斷，不建立第二套移動計時器。

PetProfileControls also exposes selected-identity care, mode and treat commands. It resolves the live PetProfileSession at execution, refuses inactive/hidden owners, releases pointer interactions and delegates completion/cooldowns to the existing session. Manager petting is timed care without pointer arming; no additional interaction timer or saved state is introduced.

Keyboard call destinations: PetProfileControls exposes horizontal/vertical logical-pixel offsets, delegating to DesktopPetWidget.start_call(*, offset=None), which returns accepted/busy. CallTarget configures its bounded destination before showing; _start_toy returns success and retains ownership on refusal. Manager call refusal precedes generic care cleanup. LightToy discards vertical distance before radius limiting in floor mode, so vertical input cannot change the horizontal destination. No persisted destination or additional timer.

Puppet call movement: show/pet/target_marker.py owns nonactivating draggable target visuals and radius/center limits; LightToy retains Sprite guidance and arrival. show/pet/puppet_target.py owns a call-only 33ms timer, float window translation and center-based arrival with full-window and marker-safe work-area bounds. PuppetPetWidget exposes start_call/stop_toy/place_for_focus without a motion attribute, cancels on manual interaction/lifecycle changes, and routes optional walk reactions through existing bindings. Recovery separates generic target cancellation from Sprite drag reset and clears Puppet drag origin. show/pet/puppet_stroll.py owns autonomous Puppet behaviour: after a 3-8 s rest it picks at random a walk or an in-place action (sit, play, groom, greet, celebrate); a 33 ms timer moves the window left or right along its current height inside the screen work area or holds the action, and it yields whenever can_play_with_toy is false or a call/toy target exists; PuppetPetWidget._show_activity picks idle, walk, the stroll's action or the companion action from the call target and the stroll. Native GL movement and authored walk acceptance remain pending.

Native call evidence: tests/integration/puppet_call_native.py runs real Windows GL/timers/window translation with only an off-screen synthetic work-area override. It verifies walk-expression pixels, exact arrival restoration, shared greeting completion and manual-expression retention on cancellation. Helper nonactivation flags and readonly foreground observations are explicit; production artwork, real monitor geometry and normal application show paths remain separate gates.

Puppet light play: PuppetTargetController uses a fixed call/light activity map for marker appearance and greet/play arrival, with one marker and timer. Puppet exposes start_light and stop_toy; Sprite start_light accepts keyword-only offsets and returns accepted/busy. Manager light and call branches share offset fields and preserve busy interactions. TargetMarker adds translated light hints/accessibility. All old controller imports and private _call references migrated, including the native Windows probe, which accepts an optional light argument.

## Desktop pet home (domain layer)

`utils/pet_game/` is the Qt-free core of the pet life and work game (`progress.md` #23–#34). The Pet home page (below) is its first user; the desktop presentation comes later. Dependency direction: UI sends commands to a `World`, only `simulation.advance` moves time, a renderer will read state and events and never touch the ledger or tasks.

| Module | Responsibility |
| --- | --- |
| `catalog.py` | Frozen `FurnitureDefinition` / `Recipe` data with boundary validation (footprint cells, interaction points, integer per-minute need effects, sell-back at most half the price, workstation ↔ profession). `builtin_catalog()` is the vertical slice: basic bed, dining table and writing desk (essential, never sold), plant, lamp, toy box, armchair, cozy bed; letter and story commissions. `STARTER_KIT` / `STARTER_COINS` 35 furniture definitions (three for platforms: pet stairs, cat tree, climbing wall; the bath tub is the one `bath` piece, activity `wash`) (1.0 target), each with `unlock_level`; `Recipe.unlock_level` too (story and flowers 2, stool 3). `goals.unlocked(world, level)` gates `World.buy`/`create_task` (`locked`) and `behaviour.auto_task`; free arranging has everything. `goals.RENAMED_GOALS` maps the old *set_routine* tutorial state onto *decorate* on load. |
| `rng.py` | `GameRandom` (SplitMix64); its whole state is one saved integer, so replays are exact |
| `ledger.py` | `Ledger`: integer coins and item stacks, reservations (visible, not spendable), all-or-nothing `apply(transaction_id, …)`. A repeated ID returns `duplicate`; the last 1,024 IDs are remembered and a 100-entry journal is kept |
| `layout.py` | `Zone` (one floor strip on one screen in local logical coordinates; entrance and restricted cells), `Furniture` (placed instance, flip, bed owner; `users` = runtime reservations per interaction point) and `placement_problem()` → `outside_zone` / `restricted` / `entrance_blocked` / `overlap` |
| `schedule.py` | Game clock (one day = 60 effective minutes, homes start at 08:00) and four routine templates of sleep / meal / work / free blocks |
| `resident.py` | `Resident` keyed by the pet profile UUID: needs (energy, fullness, mood, comfort, social, hygiene - comfort and social added in save version 2, hygiene in 7 and loaded as `FRESH_HYGIENE` 80 from older homes), affection, profession experience, traits, routine, parked flag. `Activity` and the command queue are runtime only |
| `jobs.py` | `Task`: recipe × units with the waiting-materials → reserved → travelling → working → paused → settled / cancelled lifecycle; settlement ID `<task>:u<unit>` |
| `behaviour.py` | Decision order safety → direct command → urgent needs → routine → work → free activity, and the reserve → move → use → release lifecycle. `cancel_activity()` is the only interruption path: it releases the point and pauses work with its progress. Basic rest (nap) and food (snack) never need furniture; automatically chosen stations are not stored on the task, so a paused order never blocks a desk Automation: with no open task during a *work* routine block, `auto_task()` creates one itself - only recipes whose profession has a workstation in the zone, the resident's skill allows and whose inputs are already available, ranked by the resident's own trade (`PROFESSION_TRAITS`), then skill, then pay - and emits `auto_job`. `World.automatic` (runtime only, default on) turns this and the goal automation off for tests of the bare mechanics. |
| `arrangement.py` | Whole-zone layouts on top of `World.buy/place/store`: `snapshot`/`restore` (definition, cell, mirroring, bed owner), `LayoutHistory` (undo/redo, 30 steps, session memory), layout codes (`encode_layout`/`decode_layout`: `frontengine.home-layout` v1 JSON, at most 64 pieces and 16 KiB, known definitions and integer cells only, nothing personal), `plan` (missing pieces, their cost, what cannot be bought yet) and `apply_layout` (buys what is missing when asked and affordable, stores the zone, sets the layout out). `PRESETS`: starter, cozy, workshop, garden - each fits a 24-cell home. The Furniture tab drives it (undo/redo, copy/paste, ready-made layouts with a preview), the overview drags pieces while arranging (`drag_enabled`, `piece_hovered`/`piece_dropped`) and ←/→ nudge the selected piece. |
| `blueprint.py` | Home blueprints (`frontengine.home-blueprint` v1): `export_blueprint(world)` writes each zone's width, theme, entrance, restricted cells and areas plus `[zone index, kind, cell, flipped]` per piece - never pets, names, coins, goals, screen names or ids. `parse_blueprint` validates at the boundary (128 KiB, at most 8 zones and 400 pieces, zones rebuilt through `Zone.from_dict`, piece kinds must be catalog-style identifiers, exact ints and bools). `visit_blueprint(text, catalog)` builds a throwaway free-arranging `World` (never run or saved), places known pieces stairs first and returns the unknown or unplaceable ones as `missing`. UI: the Furniture tab's *Share blueprint…* / *Visit a blueprint…* (`LayoutPanel.choose_save_path` / `choose_open_path` stand in for the file dialogs in tests) and `ui/page/pet_game/blueprint_dialog.py` (`BlueprintVisit`, a read-only `HomeView` per room plus what is missing); the page closes open visits on shutdown. `canonical_blueprint` rewrites one from its checked parts (what the Workshop ships) and `required_packs` lists the content packs its pieces and themes come from; the visit names the ones not installed (`blueprint_dialog.missing_packs`). |
| `content_pack.py` | Furniture packs from `pet-home-packs/<id>/`: `pack.json` (`frontengine.home-pack` v1; id = folder name; name, source, licence; 1-64 pieces with id, name, category, width, solid, points, activity, effects, price, comfort, poses, profession, art) and `furniture/<theme>/<art>.png` (warm_home required). `load_pack` refuses the whole pack for unknown fields, a manifest over 64 KiB, more than 400 files, any link, any file that could run (`FORBIDDEN_SUFFIXES`), a picture that is not a PNG, over 2 MB or reached outside the folder, duplicate ids, or a piece `check_furniture` rejects; nothing is executed. Ids become `<pack>__<id>` (sell-back half the price, unlock level 1). `load_packs` returns good packs and a reason per refused folder; `catalog_with_packs` merges them into the built-in catalog. `home_page.default_service` loads them, registers their pictures with `furniture_art.register_pack_pictures` and keeps `store.packs` / `store.pack_errors` for the Settings tab (`packs_text`, *Open the packs folder*). A removed pack's pieces stay dormant in the save (`snapshot._dormant`). A pack may also bring up to 8 themes (`ThemeDefinition`: `<pack>__<id>`, name, built-in `base`, floor / day / night colours; a pack needs furniture or a theme) - `Catalog.themes`, `World.set_theme` accepts them, `layout.known_theme` lets saves and blueprints keep one whose pack is gone, `themes.register_themes` / `base_theme` draw it (pictures from the base set, a missing pack as the warm home). `load_packs(folder, extra_roots)` also takes Workshop items (`home_page.workshop_pack_roots` → `workshop_content.home_pack_roots`); a local pack wins an id clash. |
| Zones and areas | `Zone.areas` (save version 4; older saves load with none): labelled stretches `(first, last, tag)` - living, work, leisure, dining - set with `World.set_area` (neighbours trimmed, at most 16, never overlapping); `behaviour._area_rank` makes residents prefer a piece in an area meant for the activity without forbidding others. `World.move_zone` (one zone per screen, `screen_taken`; pieces that no longer fit go to storage), `transfer_resident` (explicit, arrives at the entrance, drops a bed claim elsewhere), `set_offline(zones)` (runtime: pets of a disconnected screen's zone are parked and resumed, never ones the player parked; furniture stays, nothing is copied). The page keeps one desktop strip per connected zone, reacts to `screenAdded`/`screenRemoved`, offers a zone menu, *Add a zone on that screen* / *Move this zone there*, *Paint areas on the floor* (the overview's `area_tool` / `area_painted`) and a resident's *Move to that zone*. |
| Platforms and crossings | `FurnitureDefinition.raised` (cat tree, climbing wall; never a workstation) and `.steps` (pet stairs, not solid). `layout.has_steps` (stairs touching or overlapping the footprint) and `can_climb(traits)` (`CLIMBING_TRAITS` = playful) decide reachability: `World.reachable(resident, piece)` filters `behaviour._free_piece`, and `World.preview` returns `unreachable` for a raised piece nobody in the zone could reach, or for moving stairs that would strand one (so `place`/`move` refuse it). `arrangement` places stairs first when restoring or applying a layout. `Zone.link` (save version 5; older saves load with none) is a crossing point set with `World.link_zones` (symmetric, one partner each); `World.crossing(zone)` ignores offline zones; free time may pick `visit` (`behaviour.start_visit` walks to the entrance, `simulation._walk` then calls `World.cross`, which keeps bed claims) and `start_rest` walks a pet home first when its bed is across the crossing. The Furniture tab's *Entrance leads to* sets it; the overview draws a linked entrance solid with ⇄. |
| Upgrades and helping | `Progress.upgrades` (save version 6; older saves load with none; unknown or non-workstation kinds dropped on load) holds a level 2..`MAX_STATION_LEVEL` (3) per workstation kind, shared by every station of that kind so storing and layouts never lose it. `World.upgrade_cost` (`max(price, UPGRADE_BASE_COINS)` × level, 0 when free arranging, None when it cannot go higher) and `World.upgrade(kind, transaction)` (ledger-idempotent). `simulation._work` scales progress by `(3 + level) / 4` and by `(4 + helpers) / 4`; `behaviour._help_partner` / `start_help` / `help_completed` / `helpers` let a free pet help one at work (`HELP_WEIGHT`, at most `MAX_HELPERS`, a point of the trade's experience, company and relation). `auto_task` skips recipes whose every output already has `AUTO_STOCK_LIMIT` (20) in storage. The strip's piece menu and the Furniture tab offer *Upgrade*; `piece_lines` shows the level and speed. |
| Furniture badges | `HomeView.piece_badge` / `_paint_badge`: ✓ for `DONE_SECONDS` after a `settled` event at that station (`note_events`, fed by the page's and the strip's event handlers; `badge_clock` injectable), the trade's `TOOL_ICONS` symbol while someone works there, a dot while in use, nothing when free. |
| Focus companion and dropped files | `PetSettingUI.focus_phase(str)` (`focus`, `break`, `long_break`, `stopped`) is connected in `main_ui` to `PetHomePage.focus_phase_changed`; with the Work tab's *Pets work alongside my focus sessions* (`pet_home_focus_companion`) a focus phase calls `World.focus_begin()` - a `work` request appended (never `World.command`, which cancels) for each free pet that passes `refusal`, an automatic job taken first when it has none, the home's own requests remembered in `_focus_owned` - and any other phase calls `World.focus_end()`, which removes only those still-pending requests. `show/pet/focus_companions.py` keeps owning the desktop pets. `HomeStrip` accepts local-file drops over a pet as `World.interact(pet, 'feed')`; the file is never opened. |
| Play with the player | `World.INTERACTIONS` adds `groom` and `toy`; `toy` (`PLAYFUL`) is refused with `busy` while the pet's activity is in `BUSY_KINDS` (work, eat, snack, sleep). `World.call(pet, x)` cancels leisure and starts `come` toward x (the strip passes where it was right-clicked); `simulation._walk` starts its `COME_WAIT_MS` wait on arrival. `World.play_tag(pet)` picks the nearest free, non-busy pet in the zone (`no_partner` otherwise) and starts `tag` for both (runner to the far side, chaser behind); `behaviour.tag_completed` gives mood, company and friendship. Busy pets are never moved, so one controller at a time drives a pet. The strip's pet menu adds *Come here*, *Play tag* and *Take a photo* (`action_requested('photo')` → `PetHomePage.photo_of`, a crop of the overview saved by `GoalsPanel.save_photo` into `pet-album`). |
| Data model and moving in | `FurnitureDefinition.art` (picture name, a plain identifier; `catalog.art_name`) and `.poses` (wanted character poses from `catalog.POSES`, best first; `wanted_poses` falls back to `ACTIVITY_POSES`), both validated in `check_furniture`; `HomeView` draws by `art_name` and `resident_art.semantic_action` uses the next wanted pose a character has, then idle. `goals.Goal.window` (days of the 28-day home year, may wrap; `offered`, `day_of_year`): outside it `goal_state` is `unavailable` and the Goals tab leaves it out - claims and skips stand. `goals.LIFE_EVENT_RULES` (`EventRule(per_resident, cooldown_days)`, 0 = once) and `goals.due` replace the per-call checks; `LIFE_EVENTS` is derived from the rules. The create-home stage lists saved pets in `newcomers` (all ticked); `PetHomePage.move_in_newcomers` adopts the ticked ones through `HomeService.adopt` after `create_home`, so identity and values come from the profile and nothing is copied; the starter kit is ledger-idempotent. |
| Seasons and advanced trades | `environment.SEASONS` / `season(time_ms)` (seven game days each, `YEAR_DAYS` 28); `weather` turns winter rain into `snow` (seeded as before, so replays hold). `themes._paint_season` adds petals, leaves or snow specks to the overview's sky (still under reduced motion); `WEATHER_GLYPHS` has ❄; the page's status line names the season. `goals.SEASONAL` (one windowed goal per season, paid once; `ALL_GOALS` = tutorial + seasonal for claiming, automation, validation and the Goals tab). Advanced recipes `novel`, `bouquet` (→ item `bouquet`), `music_box` (→ item `music_box`), each `min_level` 4 and `unlock_level` 4; item icons rendered by `tools/blender_furniture.py --items`. |
| `simulation.py` | 200 ms fixed steps from accumulated effective time (never paint frames); integer need accumulators; walking at 64 px/s; low energy or mood halves work speed; `settle()` pays each unit once through the ledger, then continues, breaks or closes the order |
| `world.py` | `World`: state plus player commands returning result codes (buy/sell/place/move/store/assign bed, add/remove resident, command/drag/park/routine, create/cancel task). IDs are prefixed counters (`z`/`f`/`t`), never indices. Free-layout (`sandbox`) mode places without storage or cost `free_cell()` / `place_anywhere()` find the leftmost spot that fits, preferring one free cell on each side; `furnish(zone)` sets out the starter kit, `buy_and_place()` buys a piece straight into the home (`bought_no_room` when it must wait in storage). |
| `snapshot.py` | Versioned `frontengine.pet-home` v1 JSON. Loading validates every field and cross-reference before a world exists; in-flight work is saved as paused; content that is not installed is kept verbatim as dormant records and revived when it returns; pieces that no longer fit go back to storage. `NewerSaveError` for future versions |
| `user_setting/pet_game_save.py` | `HomeSaveStore`: one file per mode (`pet-home.json`, `pet-home-sandbox.json`), 2 MiB limit; `encode()` serialises (GUI thread), `write_encoded()` runs `verify()` (reload check), then temp + fsync + `os.replace`, previous good file copied to `.bak`. Corrupt or newer files make the store read-only and are never overwritten; `restore_backup()` and `set_aside()` recover. The writer is injectable for disk-failure tests |

Care values start from the pet profile when a resident moves in; while the home owns the pet the world is their only writer. Offline time is never simulated.

`show/pet_game/home_service.py` — `HomeService(QObject)` owns one home: one shared 200 ms timer (no per-object timers), a monotonic clock whose gaps above 5 s are dropped, named pause reasons (`pause(reason)` / `resume(reason)`; nothing runs until `start()`), and commands through `run(callable)`. Each resident holds the ordinary `PetProfileSession` lease for its UUID, so the same pet cannot also run as a desktop pet, and the session's care timer is never started. A resident whose identity is live elsewhere loads as runtime-only `away` (not simulated, not saved as parked) until `retry_leases()`. Saving: commands and settle/place/arrive events debounce a save (800 ms; 30 s periodic while dirty); the world is serialised on the GUI thread, then verified and written by one worker (`executor`, latest wins, result delivered by a queued signal); failures emit `save_failed` and retry after 5 s. After the home file succeeds, care values are mirrored into each pet profile through its session — the home save is the record of truth if that second write fails. `shutdown()` stops time, cancels activities without rewards, saves synchronously and releases every lease; it returns False (keeping everything) when the save fails. Measured: six residents, 54,000 steps (three game days) in about 1.2 s, about 22 µs per step. `create_home(..., home=)` fixes the home identity for replays; `tests/integration/pet_game_smoke.py` uses it with seed-derived pet identities to run a test home for a given number of effective game minutes and record settlements, screenshots of its own overview and a save fingerprint (media keys refused, offscreen unless `--native`, which uses a separate Windows desktop).

Pet home UI:

| Module | Responsibility |
| --- | --- |
| `show/pet_game/home_view.py` | `HomeView(QWidget)`: draws one zone from world state (floor, entrance, restricted cells, furniture as its Blender-rendered picture for the zone's theme (a labelled category-coloured block when a piece has none) with owner dots, a placement preview that is green or red with its translated reason, residents as labelled markers with an activity glyph). Emits `resident_selected` / `furniture_selected` / `cell_clicked`; it never mutates the world, so the future desktop strip can reuse it without computing rewards |
| `show/pet_game/furniture_art.py` | `picture(theme, definition)` / `aspect()`: cached `QImage` of a piece from package data `show/pet_game/furniture/<theme>/<id>.png` (96 px per cell, bottom edge = floor), falling back to the warm-home set, `None` for pieces without one. The images come from `tools/blender_furniture.py` (Blender 4.2 LTS, bevelled primitives, cel-ramp emission shading, Freestyle outline, orthographic transparent render; themes only swap colours), rerun with `blender -b --factory-startup -P tools/blender_furniture.py -- frontengine/show/pet_game/furniture` `item_picture(id)` loads the Blender item icons from `show/pet_game/items/` (wood, herb, flower, toy, coin, letter, story; the identifier never leaves that folder). |
| `show/pet_game/home_strip.py` | `HomeStrip(HomeView)`: the home on the desktop. A frameless, non-activating Tool window (`WindowDoesNotAcceptFocus`, `WA_ShowWithoutActivating`) on the bottom edge of the zone's screen work area, stacked above or below windows (`set_layer`). Draws at one cell = 32 px × the chosen size (`set_scale`, `SCALES` 75-200 %, page setting `pet_home_strip_scale`, asked for by Ctrl+wheel or ⌂ → Size through `scale_requested`) with no background; every horizontal position goes through `HomeView.cell_x` / `x_cell`, so a home wider than its screen keeps its window on the screen and scrolls its content (`scroll_x`, eased each frame toward `_scroll_target`: the pet last clicked, else the pets' middle, kept in the middle half) - drawing, hit-testing and the input mask all follow. A double-click on a pet pats it; a window mask limits input to residents, furniture and the ⌂ button, and Windows additionally passes clicks through fully transparent pixels, so arranging paints a faint tint to take the whole strip. Interpolates resident positions between 200 ms world steps at the quality tier's frame rate (`set_quality_tier`: 60/30/15 FPS). Left click selects and shows a tooltip card (`captions.card_text`), right click offers commands or Put away, drag uses `World.drag`. Hiding pauses the home with reason `hidden`; closing resumes and emits `closed`. `overlay_lockable = False` so Lock all cannot make it unclickable |
| Strip toolbar and menus | Beside ⌂, `HomeStrip.toolbar` holds a toggle and, when open, *Arrange* / *Residents* / *Work* shortcuts and an info label (coins, the pet last clicked here as `chosen`, open jobs); `pet_home_toolbar_open` / `pet_home_toolbar_dock` (left or right end of the strip) live in `user_setting_dict`, the toolbar is part of the input mask. The strip emits `action_requested(action, target)` - `arrange`, `move` (piece; arranging stays on the desktop), `tab`, `wardrobe`, `work`, `follow` - and `PetHomePage.strip_action` handles it (`_follow` keeps a pet in view in the zoomed overview each tick). A pet's right-click menu offers `World.interact(pet, feed/pat/talk)` (`INTERACTIONS`, a 30 s game-time cooldown per pet and kind, runtime only, no interruption, `parked` for resting pets) before the *Ask to* commands; a piece's menu lists `piece_lines` (name, use, users, bed owner) and *Move* / *Put away*. |
| `show/pet_game/captions.py` | Translated activity/reason/refusal text and the desktop card, shared by the overview and the strip |
| `show/pet_game/ambience.py` | `Ambience(QObject)`: at most one looping `QSoundEffect` (`loop_for`: rain or snow by weather, otherwise night or day by the sky) from package data `ambience/*.wav`, made by `tools/ambient_sounds.py` (numpy, seeded, 12 s seamless loops, no recorded material). Off by default (`pet_home_ambient`), its own volume (`pet_home_ambient_volume`, 0-100); `PetHomePage.update_ambience()` runs each tick and on `running_changed`, so a paused, locked or meeting home is silent; `shutdown()` releases the players. The player factory is injectable (`_sound_effect`) so tests never open an audio device |
| `ui/page/pet_game/home_page.py` | `PetHomePage(SettingPage)`: the first page. Owns a `HomeService` (`default_service()`: `pet-home.json` in the working directory, the shared `PetProfiles`, one `pet-home-save` writer thread). Opening never creates a home; *Create a home* uses the primary screen's available width. Shows status, a damaged/newer save's recovery buttons (restore backup, set aside), Start/Pause (remembered in `user_setting_dict["pet_home_running"]`), and refreshes numbers each tick and lists on settle/place/arrive events and language changes. Esc leaves arranging. Owns `strip_list` (registered with the Control Center in MainUI, so hide/show/close all and quality reach it) and `sync_strip()`; *Show the home on the desktop* and *Desktop layer* are `pet_home_on_desktop` / `pet_home_layer` settings. The strip's ⌂ menu asks MainUI to bring the window back on this page. `shutdown()` closes the strip, then the service Laid out as a game screen: a stage section (status line with *Start*/*Pause* or *Create a home* on the right, the overview at `STAGE_HEIGHT` 220 px, or `EmptyHome` before there is a home) above `HomeTabs`; while the panels are built, `add_section()` collects their sections (titles hidden) and they become tabs in `TAB_ORDER`, plus a *Settings* tab for the desktop strip, motion, mode, meeting and layer options. |
| `ui/page/pet_game/home_stage.py` | `HomeTabs(QTabWidget)` (one tab per panel section, retranslated through `bind_call`, `select(key)`), `TAB_ORDER` (residents, work, furniture, shop, backpack, goals, inbox, settings) and `EmptyHome` (paints the starter bed, table and desk from the Blender pictures on a floor line). |
| `ui/page/pet_game/home_pending.py` | `pending(world, unread)`: up to five `(text, tab key)` lines for what the home cannot settle itself (no pet yet, unread inbox, furniture in storage, jobs waiting for materials, a ready celebration, a wish); the stage lists them under the overview and a click opens the tab. The stage also has *Back to the desktop* (`desktop_requested` → `FrontEngineMainUI.step_aside()`: tray or minimise), *Backpack* / *Goals* shortcuts, zoom (`HomeView.set_zoom`/`step_zoom`, `ZOOMS` 1-2x, Ctrl+wheel where `zoomable`; the page scales the stage height with it) and, for a newer save, *Get the latest FrontEngine* (`UPDATE_URL`). The desktop strip shows a no-focus *Done arranging* button (`arrange_finished`) while arranging. |
| `ui/page/pet_game/collection_panel.py` | The *Collection* tab: the furniture guide (`how_to_get`: owned, comes with every home, made at a workstation, the home level it opens at, or its price), `creations()` from the `settled:<recipe>` counters, and `album_photos()` (newest PNGs inside `pet-album` only) with cached thumbnails and *Open the album folder*. |
| `ui/page/pet_game/home_things.py` | `thing_pixmap(key, theme)` / `thing_icon()` turn `furniture:<id>`, an item id or `recipe:<id>` (`RECIPE_ICONS`) into a square picture; `ThingGrid(QListWidget)` shows them as wrapping tiles (name, then price or count) and keeps the selection when refilled. The furniture, shop and backpack tabs and the work list are built on it. The home panels no longer carry the manual job form, routine menu, position/mirror controls, claim/deliver buttons, inbox category switches or the mode/meeting/layer settings: work, rewards, commissions and furniture placement are automatic, and mode and layer stay on the desktop strip's ⌂ menu. |
| `ui/page/pet_game/home_panels.py` | `ResidentPanel` (move in / new pet / move out, needs bars, activity and refusal text, routine, direct commands), `LayoutPanel` (storage, position, mirror, preview, place / move / put away / give bed), `ShopPanel` (buy, sell from storage), `WorkPanel` (job, units, task list with state and progress, cancel). Every action goes through `HomeService.run` and reports the translated result code |

`NavigationSidebar` items also carry a stable page ID (`ROLE_PAGE_ID`, default: the title key); `page_index(page_id)` / `select_page_id(page_id)` resolve it, so inserting the Pet home page first did not break callers that need a specific page. MainUI shuts the home down after flushing desktop pet profiles; a failed home save keeps FrontEngine open with a status message.

Navigation after the game became the first page: sidebar group headings fold their pages (`set_group_collapsed`, persisted as `sidebar_collapsed_groups`; selecting a page in a folded group unfolds it), command-palette page commands open pages by stable ID, and the tray menu offers Open Pet home. `tests/integration/entry_inventory.py` regenerates `docs/design/entry-inventory.md`, the per-entry inventory (original entry, action ID, new entry, state saving, measured acceptance) required by `progress.md` #24.

Professions and goods (G4a): `catalog.py` adds `ItemDefinition` (material/food/goods with buy and sell prices; buying must cost more than selling returns), recipe `phases` with `phase_at()`, item references checked against items or `furniture:<id>`, and `_reject_loops()` so no recipe chain turns an item back into itself. Built-in: planter (gardening: herbs, flowers), workbench (crafting: toy from wood, stool straight into storage), stool; wood, herbs, flowers, toy. `World.buy_item()` / `sell_item()` go through the ledger (reserved stock cannot be sold). Sitting down to eat at a table uses one herb from storage, when present, for extra mood (`simulation._season_meal`, transaction `meal:<resident>:<time>`). The page gains `StoragePanel` (the backpack: stacks, amounts set aside for work, sell prices) and a work panel with details (inputs, outputs, coins, energy, level), workstation choice and priority; tasks show their phase.

Life together (G4b): save format 2 adds `comfort` and `social` needs (version 1 residents load them at 60; `LEGACY_NEEDS`) and `World.relations` (sorted UUID pair → −100..100, cleared when a resident leaves). Furniture effects raise comfort; home comfort slows its decay and comfort below 30 costs mood. Social rises 20/min while sharing a table, toy box or seat in use; `behaviour.start_greet` walks to a nearby free resident (also a weighted free-time choice, more for sociable pets), the answer comes from the partner if it is free, and completion gives both +15 company and +2 relationship; finishing a shared meal or game gives +1 (`shared_completed`); waiting for a seat someone holds is a squabble (−1, −2 mood). Every pair action has a cooldown in the runtime-only `World.social_ready`. `resident.traits_for` derives two lasting traits from the UUID (SHA-256); a liking for a profession adds 10% speed and mood while doing it. `captions.py` adds time left, personality and friends to the card; `HomeStrip` shows 3-second bubbles for started activities, greetings, squabbles and pay, and keeps them inside the input mask so they are not clipped.

Growth (G5): `utils/pet_game/goals.py` owns `Progress` (event counters filled by `World.emit`, goal states, today's commissions, wishes per resident, arrival times, the last 50 life events) and runs from `simulation.step` every 30 s of world time. Ten `TUTORIAL` goals measure world state and pay once when claimed (`goal:<id>` transactions; skipping pays nothing); `home_level` counts `MILESTONES` reached by living; commissions are seeded from the home ID and the game day, never from `World.rng`, so checking them cannot change a replay; wishes measure a world quantity against a base and grant mood and affection; life events (first creation, friends' dinner, birthdays every seven game days) and the one-time celebration (two or more residents, all three professions) are recorded with their game day. Save format 3 adds `progress`; older homes start counting on load. `ui/page/pet_game/goals_panel.py` shows level, tutorial, commissions, celebration and recent moments, and *Take a photo* saves only `HomeView.grab()` to `pet-album/`.

Atmosphere (G5b): `utils/pet_game/environment.py` gives the sky phase and daylight from the game clock and a weather spell (clear / cloudy / rain) per six game hours, seeded from the home and the day like commissions, so it never touches `World.rng`. `show/pet_game/themes.py` holds the three theme palettes and paints the overview's sky (gradient by daylight, greyer when cloudy, rain streaks that stand still under reduced motion); `HomeView.ink()` switches to light text at night; the strip only shows a weather or moon glyph on its ⌂ button. `World.set_theme()` changes a zone's look and nothing else. `goals.LIFE_EVENTS` now has the plan's twelve moments (once-per-home milestones, daily dinner / rain / starry night, per-resident first close friend and skilled profession). *Reduce motion* (`pet_home_reduced_motion`) turns off strip interpolation. In the evening the strip dims what it has drawn (`themes.night_shade`, source-atop, so clear pixels stay click-through and the input mask is unchanged); the strip cannot draw weather itself, because its window mask (`setMask`, so empty pixels click through) also clips drawing on Windows. `show/pet_game/strip_weather.py` `StripWeather` is a separate frameless Tool window over the strip (`WindowTransparentForInput`, `WA_TransparentForMouseEvents`, no focus, the strip's layer flags) that the strip syncs on every tick, move, resize, show, hide, layer change and close; it shows only while it rains or snows (`precipitation`) on a shown strip that is not quiet, repaints on the strip's frame timer, and its drops (an R2 low-discrepancy spread) stand still under reduced motion. `tests/integration/pet_home_strip_native.py` checks with `WindowFromPoint` that clicks still reach the strip and the window behind while it rains.

Desktop usability (#31): `PetHomePage` modes (`pet_home_mode`): normal, focus (strips `quiet`: no bubbles or cards), meeting (pause reason `meeting`, strips hidden, status says so) and saver (strips at the saver frame rate; the 200 ms world timer never changes). `sharing_changed()` (called from `MainUI._on_sharing_changed`) borrows meeting mode while the screen is shared when `pet_home_auto_meeting` allows. `ui/page/pet_game/inbox_panel.py` sorts world events into work / needs / life / errors (each switchable), folds repeats of the same pet and kind within a game minute, keeps 50 lines and an unread count, and never opens a window. `benchmarks/pet_home.py` measures the fixed loads and the long run; `benchmarks/startup_compare.py` compares startup, search and page switching with a baseline checkout in interleaved fresh processes. Results are in `docs/benchmarks/`.

Residents as characters: `show/pet_game/resident_art.py` maps a resident's activity to a layered character action (`semantic_action`: walking while moving, sleep, feed, sit for work and relaxing, play, greet, drag, idle; work uses the recipe profession's pose — write, garden, craft — when the renderer `has_action` it, else sits) and keeps one `LayeredRenderer` per resident. A resident still wearing an older built-in version is upgraded in the same background job (install the current built-in, prepare, then `PetProfileSession.apply_appearance(expected, upgraded, …, present=False)` on the GUI thread; a stale profile skips it). Renderers come from the profile session's `appearance_renderer` when the wardrobe or a desktop pet prepared one, otherwise from a `QRunnable` on the global pool (asset scan and image decoding off the GUI thread) delivered through a queued signal; `changed` makes the page redraw and refit the strip's input mask. `HomeView` draws the frame `SPRITE_CELLS` (2.2) cells tall, standing on the floor (raised to `furniture_art.SURFACES` while using a bed or the armchair) and mirrored when facing left, and falls back to the marker for pets without a layered character. The resident panel's *Wardrobe…* opens `PetWardrobeDialog`, whose Apply commits through the home's own session lease. Picture and Puppet pets are drawn from the look the pet page recorded (`user_setting/pet_looks.py`: `pet_home_looks` in the settings, `sprite` = the GIF/picture file or sprite-pack folder a desktop pet was started with, `portrait` = `pet-home-looks/<id>.png`, a still that `PetSettingUI._remember_portrait` takes from a Puppet's own `photo_image()` 1.5 s after it starts; entries, ids and paths are checked at the boundary). `show/pet_game/picture_renderer.py` decodes it on the pool (`load_picture`: up to 96 frames per action, at most 256 px tall; a pack's walk / idle / sleep / drag) into a `PictureRenderer` with the layered renderer's `character.canvas` / `has_action` / `render`; missing actions borrow idle (playing borrows walk) and a single still frame bounces, hops or settles down. A look that fails to load is remembered as unusable for that file version. Pets with no usable look are drawn as a built-in stand-in (`fallback_character(identifier)`: a stable sha256 pick among the six) built by `_PrepareFallback` into a temporary folder and decoded off the GUI thread - nothing is installed, the profile is not changed and the session's `appearance_renderer` is left alone, so the desktop pet keeps its own look.
