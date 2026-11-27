# FrontEngine 全專案程式碼審查

**結論為需修正。** 2026-11-27 審查 `dev` 的 `dfb3f90c183c3beffd57ed1c4c96d54c39f71189`，套件版本 1.0.100。共列 16 項本次發現，另核對 10 月報告的 5 項舊案。建議先處理 F01–F05。這五項影響已錄好的影片、螢幕分享、剪貼簿收集或匯出檔案的內容。

| 優先級 | 數量 | 處置依據 |
|---|---:|---|
| P1 | 5 | 正常提供的功能在特定條件下會遺失資料，或違反使用者的隱私選擇。 |
| P2 | 9 | 可觸發的功能錯誤，會讓結果、保存的狀態或發行版本偏離預期。 |
| P3 | 2 | 維護工具的輸出或執行流程有誤。 |

下列「重現」指在本機呼叫實際程式路徑並觀察結果。使用注入的時間、儲存錯誤或替代的 Steam 來源時，逐項標明。「靜態」指已追蹤入口、條件與後果，未在外部平台製造該情況。位置連結及行號以審查版本為準。

## P1　資料保存與隱私

### F01　一小時 AVI 可能在停止時整段消失〔重現〕

工具頁允許錄製 3,600 秒。計時回呼發現時間已到，再讀一次時鐘並把當下時間交給寫入器。若結尾距首幀已超過一小時，寫入器會拒絕結束時間並刪除暫存檔。用實際錄製器和 AVI 寫入器、4×4 測試畫面及可控制的時鐘，從第 0 秒推進到 3,600.05 秒，錄製結束後沒有輸出 AVI，並回報 `AVI recording exceeds one hour`。這條路徑不需要磁碟錯誤。[錄影上限](frontengine/ui/page/tools/tools_setting_ui.py#L340) · [到期判斷](frontengine/utils/recording/frame_recorder.py#L299) · [傳入結束時間](frontengine/utils/recording/frame_recorder.py#L245) · [寫入器收尾](frontengine/utils/recording/avi_writer.py#L131)

**修正與驗收。** 自動停止時，以排定的截止點計算結尾，並保留格式的容量與時間上限。用同一個寫入器測試整點、晚到一個 tick，以及暫停後恢復三種情況，確認已輸出的檔案可讀。

### F02　會議結束會解除使用者手動開啟的擷取隱藏〔靜態〕

控制中心的手動按鈕及會議偵測共用 `_hidden_from_capture`。使用者先手動隱藏、再進出會議，偵測回呼會寫入 `False`，也會解除既有視窗的擷取排除。若其他錄影仍在進行，原本手動保護的覆蓋層就可能出現在錄影裡。[會議狀態回呼](frontengine/ui/main_ui.py#L1158) · [套用旗標](frontengine/ui/page/control_center/control_center_ui.py#L579) · [手動切換](frontengine/ui/page/control_center/control_center_ui.py#L604)

**修正與驗收。** 分別保存手動選擇與自動隱藏需求，只要任一項啟用就維持排除。測試手動開啟、會議開始、會議結束的完整順序，並檢查既有及新開的視窗。

### F03　即使擷取排除失敗，分享提示仍宣告已隱藏〔靜態〕

控制中心只累計成功套用的視窗數，按鈕顯示則取決於要求的狀態。會議偵測未檢查回傳結果，直接顯示「Overlays hidden from screen capture」。因此不支援該功能、所有呼叫失敗，或只有部分視窗成功時，都可能給使用者錯誤的保證。新視窗繼承政策已在本版補上，詳見舊案 CR-01。[逐窗套用結果](frontengine/ui/page/control_center/control_center_ui.py#L583) · [成功提示](frontengine/ui/main_ui.py#L1158) · [平台回傳值](frontengine/utils/screen_privacy/capture_affinity.py#L98)

**修正與驗收。** 回傳適用、成功與失敗的視窗數，分開處理沒有適用視窗、平台不支援、部分成功和全部成功。用替代平台函式控制各窗的結果，驗證提示文字，再於原生 Windows 以另一端擷取的畫面驗收。

### F04　關閉剪貼簿紀錄時，設定寫入失敗會讓收集繼續〔靜態〕

「記錄剪貼簿」是可勾選的動作。取消勾選後，回呼先更新設定字典、寫入磁碟，最後才停止 watcher。若寫檔拋出錯誤，畫面已取消勾選，watcher 卻仍訂閱剪貼簿變更，會繼續讀取後續複製的文字。使用時間統計的停止路徑也有相同順序。[選單動作](frontengine/ui/menu/settings_menu.py#L221) · [兩個停止流程](frontengine/ui/main_ui.py#L1183) · [剪貼簿訂閱與解除](frontengine/utils/clipboard/clipboard_watcher.py#L43)

**修正與驗收。** 使用者選擇停止時，先停止本次工作階段的收集。若無法保存選擇，明示下次啟動仍可能沿用舊設定。測試寫入失敗後再傳入一筆剪貼簿變更，確認歷史沒有增加。

### F05　分享預設集時，普通文字欄位也可能夾帶本機檔案〔靜態〕

匯出 ZIP 逐一檢查各頁的字串。任何字串只要指向現存檔案，就會被改寫成媒體路徑並把內容加入 ZIP。文字覆蓋層的 `text` 也是同一層級的字串。因此，原本只想顯示的檔名字樣可能被改寫，分享出去的預設集也可能含有使用者未選為媒體的檔案。[匯出入口](frontengine/ui/menu/preset_menu.py#L334) · [文字頁的儲存格式](frontengine/ui/page/text/text_setting_ui.py#L379) · [匯出選檔邏輯](frontengine/user_setting/preset_repository.py#L184)

**修正與驗收。** 依各頁的狀態格式明列可攜媒體欄位。以無敏感內容的測試夾具驗證 ZIP 的成員清單，並確認文字與標籤能原樣往返。

## P2　播放、保存與發行

| 編號／證據 | 觸發條件與影響 | 修正與驗收 |
|---|---|---|
| **F06 空白預設集留下上一個媒體**〔重現〕 | 真實影片頁先保存空白狀態，再指定 `demo.mp4`，最後以 `apply_state_transaction` 還原空白快照。原應為 `None` 的路徑仍是 `demo.mp4`，且 `ready_to_play=True`。圖片、GIF 與聲音頁也以欄位真值決定是否更新，版本回復失敗時的回滾同樣受影響。[影片](frontengine/ui/page/video/video_setting_ui.py#L236) · [圖片](frontengine/ui/page/image/image_setting_ui.py#L387) · [GIF](frontengine/ui/page/gif/gif_setting_ui.py#L206) · [聲音](frontengine/ui/page/sound_player/sound_player_setting_ui.py#L152) · [回滾](frontengine/ui/menu/preset_menu.py#L98) | 區分舊預設集缺少欄位與明確保存空值。後者須清除路徑、畫面標籤及播放就緒狀態。四個頁面都做有檔→空白往返測試。 |
| **F07 成功匯出的 ZIP 可能無法再匯入**〔靜態〕 | 匯入端限制 4,096 個成員及 256 MiB 解壓總量，匯出端沒有對應檢查。只要影片與其他成員的合計超出上限，就能得到一個本程式拒收的備份。[封包寫入與匯入](frontengine/user_setting/preset_repository.py#L194) · [大小與成員上限](frontengine/utils/imervue/puppet_asset.py#L15) | 兩端共用同一預算，匯出前檢查，完成後再原子替換目的檔。測試剛好在上限及超過上限的往返結果。 |
| **F08 Workshop 會把舊內容當成已驗證的新版**〔重現〕 | 用替代 Steam 資料源讓版本 1 的驗證進行中收到版本 2。相同項目的第二個工作未被接受，但記錄中的版本已先被改成 2。舊工作完成後，實際內容仍為 1，訂閱服務卻註記已驗證 2。再次更新會跳過它。[排程及略過條件](frontengine/utils/workshop/workshop_subscriptions.py#L77) · [重複工作判斷](frontengine/utils/workshop/workshop_jobs.py#L37) · [完成回呼](frontengine/utils/workshop/workshop_subscriptions.py#L107) | 讓工作結果帶回它實際處理的版本，與最新觀測值不同時再排程。測試新版在舊工作完成前到達。 |
| **F09 暫停 2D 場景後，媒體仍可能前進或重啟**〔重現〕 | 播放專案內的 GIF 後暫停，時間軸仍為 `paused`，但 `QMovie` 在 1.2 秒內又送出 13 次換幀。另一例中，移動已暫停場景內的音效層 25 像素，媒體由未啟用變成啟用。前者未接到場景狀態，後者更新圖層時漏看暫停狀態。[場景暫停通知](frontengine/show/scene/compositor_view.py#L155) · [GIF 播放](frontengine/show/gif/paint_gif.py#L28) · [編輯圖層](frontengine/show/scene/scene.py#L79) | 讓 GIF 跟隨場景暫停及恢復，並讓圖層編輯沿用相同的播放條件。暫停後移動圖層，驗證幀不前進、音效不重啟，恢復後再繼續。 |
| **F10 家園切換模式失敗仍會取消活動**〔重現〕 | 居民正在 `wander` 時切到沙盒，對寫入器注入 `OSError`。切換回傳 `None`，仍在經營模式，但居民的活動已被清除。取消活動還會釋放預約，進行中的工作可能被改為暫停。[模式切換](frontengine/show/pet_game/home_service.py#L182) · [活動取消的副作用](frontengine/utils/pet_game/behaviour.py#L48) | 在副本上準備離開模式的狀態，儲存成功才提交，或完整回復活動、工作和預約。測試失敗前後的世界狀態一致。 |
| **F11 家園可複製超過 64 件的配置，卻無法貼回**〔重現〕 | 在可容納的房間放入 65 件家具，複製得到 1,545 字元的配置碼，原樣解碼即回報 `Invalid layout pieces`。編碼端輸出全部家具，解碼端限制 64 件。[複製與貼上入口](frontengine/ui/page/pet_game/home_panels.py#L444) · [編解碼限制](frontengine/utils/pet_game/arrangement.py#L112) | 對齊兩端可支援的件數及文字長度。若仍要限制分享規模，複製時就提示。測試 64、65 件和支援上限。 |
| **F12 時鐘倒退後會重複套用同一天的預設集**〔重現〕 | 對排程服務注入同一天的 01:29、01:30、01:00、01:29、01:30，收到兩次同一預設集事件。實作只比較前後兩次輪詢。夏令時間回撥或手動校時會再次跨過目標分鐘，覆蓋使用者中途的變更。[每日排程契約](frontengine/utils/preset_schedule/preset_schedule_service.py#L82) · [觸發判斷](frontengine/utils/preset_schedule/preset_schedule_service.py#L136) · [套用入口](frontengine/ui/main_ui.py#L429) | 依本地日期及排程識別記錄最近一次觸發。驗證回撥日僅一次、次日正常觸發。 |
| **F13 只選資料夾的圖片輪播無法當作閒置螢幕保護**〔靜態〕 | 使用者可只選有圖片的資料夾並勾選輪播，手動播放會從首張圖片開始。螢幕保護入口只看單張圖片的 `ready_to_play`，選資料夾不會設定此旗標，因此自動啟動時略過了有效來源。[輪播播放](frontengine/ui/page/image/image_setting_ui.py#L243) · [選取資料夾](frontengine/ui/page/image/image_setting_ui.py#L275) · [螢幕保護就緒判斷](frontengine/ui/main_ui.py#L566) | 共用不開啟對話框的來源就緒判斷。測試只有輪播資料夾時能啟動，空資料夾則保持未就緒。 |
| **F14 發行中斷後重跑會再升一版**〔靜態流程及本機版本步驟驗證〕 | Workflow 讀最新 `main`，先升版並推回，再上傳 PyPI、建立 GitHub Release。若 PyPI 已成功但建立 Release 失敗，重跑整個 release job 會再升版，沒有補建前一版的 Release。將工作流程原有的升版步驟放在暫存副本連跑兩次，結果為 1.0.101、1.0.102。[取版與升版](.github/workflows/release.yml#L66) · [推送](.github/workflows/release.yml#L160) · [上傳與建立 Release](.github/workflows/release.yml#L228) | 保存該次發行的 SHA、版本與成品。重跑時對照已完成的部分，沿用原版本補齊。以替身模擬上傳成功、建 Release 失敗，驗證重試不產生第二版。 |

## P3　維護工具

| 編號／證據 | 影響與處理 |
|---|---|
| **F15 家園效能基準無法產生報告**〔重現〕 | `measure_load` 將 `Path` 傳入需要 `StorageSession` 的 `HomeSaveStore`。保留真正的建構與儲存路徑、將暖機與取樣各縮為一步，第一組負載即出現 `AttributeError: 'WindowsPath' object has no attribute '_claim_home'`。在暫存目錄開啟儲存工作階段，依序關閉家園服務、存檔物件和工作階段，再以最小負載驗證回傳完整報告。[基準呼叫](benchmarks/pet_home.py#L104) · [建構子](frontengine/user_setting/pet_game_save.py#L64) |
| **F16 商店素材的相對輸出路徑落在暫存目錄**〔重現〕 | `generate.py` 匯入 `trailer` 時已切換工作目錄，稍後才把命令列輸出參數轉成絕對路徑。在隔離暫存區以相對參數載入入口，確認 `OUT` 位於 staging。下次執行會清理同名 staging 目錄。無參數時的預設輸出使用專案絕對路徑。以已保存的 `LAUNCH_DIR` 解析呼叫者的參數，再測試相對及絕對路徑。[輸出位置](steam_assets/generate.py#L43) · [暫存區及原始目錄](steam_assets/trailer.py#L43) · [切換目錄](steam_assets/trailer.py#L58) |

## 2026-10-22 舊案覆核

以下狀態以本次版本為準。11 月 26 日已有一批相關修正及獨立的實機驗收待辦。[10 月報告原文](https://github.com/JeffreyChen-SteamProjects/FrontEngine/blob/dfb3f90c183c3beffd57ed1c4c96d54c39f71189/code-review.md) · [11 月修正紀錄](docs/updates/2026-11-b.md#L191) · [實機待辦](progress.md#L9)

| 舊案 | 本次核對 |
|---|---|
| CR-01　分享隱私 | **部分修正。** `BaseWidget.showEvent` 會重套政策，提示卡也繼承此類別。排除失敗時的成功提示仍在，見 F03。另有手動選擇被覆寫的問題，見 F02。[顯示事件](frontengine/show/base_widget.py#L172) · [提示卡](frontengine/show/toast/toast_widget.py#L33) |
| CR-02　點擊穿透說明 | **仍有落差。** 英文使用說明只列寵物及簡報塗鴉，但場景與便利貼皆明確要求接收輸入。應同步各語系的互動覆蓋層說明。[說明字串](frontengine/utils/multi_language/english.py#L775) · [場景](frontengine/show/scene/compositor_view.py#L35) · [便利貼](frontengine/show/notes/sticky_note_widget.py#L114) |
| CR-03　依 PATH 尋找外部工具 | **原發現已修正。** 保持喚醒使用固定系統路徑，OCR 預設從列舉的安裝位置挑選。OCR 的跨平台清單仍可依作業系統分組，確保每個候選都是該平台的絕對路徑。[保持喚醒](frontengine/utils/keep_awake/keep_awake.py#L39) · [OCR](frontengine/utils/screen_text/local_ocr.py#L146) |
| CR-04　前景與取樣失敗缺少診斷 | **部分仍在。** Win32 查詢已有 debug 紀錄。無前景視窗時，遮罩有明確的整屏降級行為。部分週期取樣的例外仍被靜默處理。建議於狀態首次降級時記錄原因，避免每次輪詢洗版。[遮罩](frontengine/show/focus_shield/focus_shield_widget.py#L126) · [濾鏡](frontengine/show/screen_care/screen_filter.py#L146) · [頻譜](frontengine/show/spectrum/spectrum_widget.py#L117) · [桌布](frontengine/show/wallpaper/wallpaper_widget.py#L142) |
| CR-05　粒子視窗的 Win32 樣式更新 | **仍在，原生失敗情況未重現。** 讀取傳回 0 時未區分合法值與錯誤，隨即寫回。如果讀取失敗而寫入成功，既有的點擊穿透旗標可能遺失。應檢查原生錯誤並在讀取失敗時停止寫入。[樣式更新](frontengine/show/particle/particle_ui.py#L116) |

## 範圍與驗證紀錄

本次清點 Git 追蹤的 **1,590 個檔案**。跨全庫的自動檢查涵蓋全部 813 個 Python 檔。人工閱讀按入口、資料流及失敗路徑選取。下表說明各區檢查深度。

| 區域 | 實際檢查 |
|---|---|
| `frontengine/`，508 個 Python 檔 | 追蹤公開匯入、CLI 與嵌入入口、主視窗與系統匣、設定與預設集、覆蓋層生命週期、2D／3D 場景、媒體、寵物與家園、平台服務、隱私、外掛及 Workshop。針對時間、儲存、媒體和多個工作交錯的邊界另做定向驗證。 |
| `tests/`，284 個 Python 檔 | 檢查測試隔離方式、測試如何建構輸入、現有斷言與失敗案例的差距。實跑下列 19 個相關測試檔。 |
| 其餘 21 個 Python 檔與建置設定 | 納入 `benchmarks/`、`examples/`、`tools/`、`exe/`、`steam_assets/`、Sphinx 設定。核對兩個套件通道、套件資源、相依清單、Nuitka 參數、CI、nightly 與 release 的步驟。 |
| 文件、資料與外部元件 | 檢查架構契約、前次修正紀錄、文件樹與 UI 說明。解析全部 269 個追蹤的 JSON 與兩份 TOML。`steam_sdk/` 的第三方 C++ 範例、媒體素材、字型及二進位模型列入清單，未對其內容逐行審查或逆向分析。 |

**本機結果。** Windows、Python 3.14.7、PySide6 6.12.0。813 個 Python 檔全部編譯成功，以 Python 3.11 語法規則解析亦通過。靜態絕對 `frontengine.*` 模組引用可對應到原始檔。對上述 Python 來源和測試執行 `pyflakes` 無輸出。另從乾淨的追蹤來源分別建置 stable 與 dev wheel，兩個成品都含有 `frontengine/` 的全部 680 個追蹤檔案。分別解開後執行 `python -m frontengine --help`，退出碼皆為 0。

| 定向 pytest 分組 | 測試檔（省略共同的 `test_` 前綴及 `.py` 副檔名） | 結果 |
|---|---|---:|
| 發行、建置與文件 | `wheel_packages`、`sdist_manifest`、`workflow_actions`、`executable_build`、`commit_attribution`、`documentation` | 91 通過 |
| 預設集、分享與控制中心 | `preset_history`、`screen_privacy`、`control_center_batch` | 35 通過 |
| 媒體、動畫與家園存檔 | `scene_media_frames`、`scene_animation`、`pet_home_save_ordering` | 35 通過 |
| 平台服務與家園配置 | `recording_video`、`workshop_subscriptions`、`todo`、`pet_home_layout_editor`、`keep_awake`、`local_ocr` | 92 通過 |
| 排程 | `schedule_weekdays` | 16 通過 |
| **合計** | **19 個不同測試檔** | **269 通過** |

依專案測試範圍規則，本次執行定向回歸。額外的失敗案例及替代輸入記在各項發現內，未計入 269 項。Qt 使用 offscreen，未執行完整測試套件、原生多螢幕／混合 DPI、macOS／Linux 實機、實體音訊／GPU、登入 Steam、完整 Nuitka 編譯或遠端發版。正式擷取畫面與硬體相容性仍須依專案的實機驗收清單確認。

## 2026-11-27 結案

F01–F16 與舊案 CR-02 至 CR-05 的剩餘部分已全部修正，各附回歸測試；新測試在審查版本上失敗（F07 剛好在上限、F10 成功路徑兩例原本就通過）。這是對本報告所列項目的結案，不是重新審查整個程式庫。

| 項目 | 修正 commit |
|---|---|
| F01、F09、F12 | `02df04d1` |
| F05、F06、F07 | `5386095d` |
| F02、F03、F04、F13 | `a23bfca7` |
| F08、F10、F11 | `85f286c2` |
| F14 | `a99477a2` |
| F15、F16 | `bd3b695b`、`24deb1e6` |
| CR-02、CR-03、CR-04、CR-05 | `8eaf60dd`、`626faa89`、`217d82f3`、`2811cc91` |

合併後重跑相關測試共 668 項通過，`test_documentation.py` 23 項通過，`pyflakes` 無輸出。未跑完整測試套件。修正內容與驗證見 [U-20261127-01](docs/updates/2026-11-b.md)。需要實機或真實發版才能確認的部分（一小時錄影、另一端擷取畫面、夏令時間回撥、發版中斷後重跑等）列在 `progress.md` #127。
