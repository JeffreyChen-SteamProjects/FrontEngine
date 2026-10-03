# FrontEngine 串流錄製、平台補齊與 Imervue 互通設計草案

日期：2026-10-03。狀態：待使用者審閱；尚未修改產品程式碼。

## 目標與範圍

涵蓋使用者提出的八項變更：錄製區域串流寫檔、手機操控 HTTPS 與自簽憑證、
本機優先 OCR、Imervue 寵物整合與格式文件、macOS 平台補齊、外掛沙箱或權限宣告、
場景與 Imervue puppet 互通、覆蓋層 GPU 合成。

成功標準是每項變更都有可操作的 UI、錯誤處理、相容策略與驗證證據。
以下採分階段交付，各階段完成後再接下一階段；未完成的項目持續留在進度檔。

## 已確認的現況

| 項目 | 現況與入口 |
| --- | --- |
| 錄製 | `frontengine/utils/recording/frame_recorder.py` 的 `frames` 留存全部 RGB 影格；停止後才呼叫 `encode_gif`。工具頁在停止後詢問輸出位置。 |
| 手機操控 | `frontengine/utils/remote/remote_server.py` 使用 `ThreadingHTTPServer`，網址為 HTTP；已有啟動時權杖、動作白名單與 Qt signal。 |
| OCR | `frontengine/utils/screen_text/screen_text_service.py` 只送截圖到 Anthropic；工具頁與對話框的可用性目前綁定雲端同意與 API key。 |
| 寵物 | `frontengine/show/pet/desktop_pet.py` 使用 GIF/WebP/PNG 狀態包與 `pet.json`。 |
| Imervue | 相鄰專案 `D:/Codes/Imervue` 提供 `.puppet` v1 規格、讀寫器、`PuppetCanvas`、`PetWindow` 與 `.petscript.json`。 |
| 場景 | 舊 JSON 是 entry mapping，目前支援 TEXT、IMAGE、GIF、SOUND、VIDEO、WEB；`ExtendGraphicView` 使用一般 viewport。 |
| 外掛 | `frontengine/utils/plugins/plugin_loader.py` 直接 import Python，支援 QWidget 分頁，尚未在執行前驗證權限宣告。 |
| macOS | 部分系統資訊與自動啟動已有支援；音訊、外部視窗操作等仍限 Windows，CI 目前只用 Windows runner。 |

現有工作區有使用者修改與已 staged 的 Steam SDK 檔案。後续提交只能包含本次產生的檔案與修改。

## 架構選擇

建議在現有介面外加入小型服務與 adapter，逐項遷移。這能保留既有設定、預設集與寵物包，
也能分別驗證錄製、TLS、OCR、native 平台與 GL 行為。

其他方案：一次將所有覆蓋層改為統一渲染 runtime，會同時改動 web/video、互動與生命週期，
回歸範圍大；僅新增可用性旗標或包裝舊入口，則無法達成串流、本機 OCR 與 GPU 合成的實際目標。

## 第一階段：錄製區域串流寫檔

### 流程與介面

保留 GIF 輸出與現有幀率、時長設定。框選區域後、開始擷取之前選擇輸出檔；取消時不開始錄製。
新增增量 GIF writer，逐幀寫入 header、palette、frame blocks，停止時寫入 trailer，
不把整段影片或編碼結果累積成一個 bytes。

`FrameRecorder` 接收輸出位置，提供 `frame_count` 與結果路徑，移除 UI 對 `frames` 的依賴。
現有 `encode_gif` 保留供小型資料與既有使用端使用，與增量 writer 共用單幀編碼邏輯。

擷取與 QPixmap 操作留在 GUI 執行緒；複製後的 RGB 陣列交給背景 writer。
queue 同時限制張數與總位元組，預設上限三張／64 MiB。單張超過上限時在開始前明確拒絕，
queue 滿時略過本次擷取，記錄掉幀數；writer 依擷取時間補入影格延遲，避免掉幀造成影片加速。
writer 與 UI 使用明確的 queued signal。

### 檔案與生命週期

在目標同目錄建立唯一的暫存檔，錄製時持續寫入；成功完成、關閉檔案後再原子替換目標。
使用者在儲存對話框確認覆寫前不替換原檔。I/O 失敗停止擷取並顯示原因，不報成功；
未完成檔不被當成最終輸出。停止與應用程式關閉採非阻塞收尾，釋放 queue、timer 和檔案 handle。
無影格錄製與使用者取消時清理暫存檔。磁碟寫入失敗時保留原有目標檔。

保留目前時長與幀數上限，這次只改寫入資料流；延長或無上限錄製可另行變更。

### 驗收

- 第一張影格寫入後，暫存檔在停止前即有 frame blocks。
- 多幀 GIF 用 Qt 真實讀回，驗證尺寸、影格數、顏色與時間；保留攝影機子母畫面。
- 長序列錄製不留存全量 RGB，queue 的張數與位元組界限可被測試觀察。
- 慢速 writer、磁碟滿、覆寫失敗、重複停止、關閉與取消都有測試；失敗不覆蓋原檔。
- 工具頁開始、停止、自動達上限與重新錄製都走同一套生命週期。

## 第二階段：HTTPS 與本機 OCR

### 手機操控

使用 Python `ssl.SSLContext` 包裝現有 HTTP server，只開 HTTPS，保留每次啟動的新權杖。
用 `cryptography` 產生自簽 X.509 憑證，保存於使用者資料目錄；SAN 包含本機 hostname、
loopback 與此次綁定位址。憑證過期、SAN 不符或無法載入時重新生成。
私鑰限制於目前使用者，憑證與金鑰不得進 repository、設定匯出或 log。

UI 顯示 HTTPS 連結、憑證 SHA-256 指紋、匯出公開憑證與重建憑證入口；
說明首次連線的自簽信任步驟。瀏覽器不會因伺服器改用 HTTPS 就自動信任自簽憑證。
TLS 建立失敗即啟動失敗，不回退到明文。驗證使用真實 TLS handshake、憑證信任與權杖拒絕。

### 本機 OCR

新增可注入的本機 OCR backend：Windows 使用 Windows.Media.Ocr 投影，macOS 使用 Vision，
Linux 與可選通用回退使用本機 Tesseract。依賴以平台 marker／extras 管理，列明系統語言資料。

抽取文字先走本機，不要求雲端同意或 API key。區分成功但無文字、backend 不可用與辨識失敗；
空白辨識結果不觸發雲端。雲端回退須有使用者明確允許與 API key。
翻譯與問答先用本機文字；需要雲端時盡量只送文字，另行同意後才可送截圖。
UI 顯示本次使用的 backend，所有辨識工作在背景執行緒執行。

驗證覆蓋本機成功時零網路呼叫、缺 key 仍可抽取、沒有同意時不外送、
空白結果、缺語言模型與各 backend 失敗；平台整合測試使用可核對的文字圖片。

## 第三階段：Imervue 寵物與場景互通

以 `D:/Codes/Imervue/Imervue/puppet/FORMAT.md` 與 `docs/schemas/puppet.schema.json` 為格式基準，
不另外發明同名的 `.puppet`。FrontEngine 透過可選 Imervue adapter 重用 document I/O、
runtime 與 GL canvas，正式安裝依賴不得依靠開發者的相鄰目錄或臨時 `sys.path`。

保留舊 sprite 寵物；新增 `.puppet` 寵物入口，接上 FrontEngine 的顯示、關閉、透明度、
螢幕選擇、控制中心與 preset 生命週期。Imervue 的設定保存透過 adapter 隔離，
不讓 FrontEngine 修改使用者的 Imervue 偏好。動作、表情與 petscript 使用 Imervue 現有引擎。

場景新增有版本的 envelope，讀取時仍支援舊 entry mapping。
新增 `PUPPET` entry，包含 asset path、位置、尺寸、透明度、初始參數、motion、expression 與可選 script。
匯入與匯出保留 `.puppet` 本體；場景組合用 sidecar／場景 package，
不把整個 FrontEngine 場景偽裝成一份單角色 puppet。

資源相對於場景檔定位；package 匯入拒絕 traversal、越界路徑、符號連結與超額解壓，
驗證未知格式版本、損毀 archive、缺 texture／motion 與非數值參數。
互通驗收使用 Imervue 提供的樣本與雙方實際讀寫器往返，不能只用自製假 parser。

文件包含 `.puppet` 引用、FrontEngine `pet.json`、`.petscript.json` 支援範圍、
新場景 schema、完整樣例與版本遷移規則；雙方 `architecture.md` §6 更新共用契約。

## 第四階段：macOS 平台補齊

設置獨立平台 backend，將能力判定、授權狀態與失敗原因回傳 UI。
建議新 native backend 以 macOS 13+ 為基準，採 PyObjC 的公開 framework bindings：
ScreenCaptureKit 做螢幕／視窗與系統音訊擷取，Vision 做 OCR，Quartz／Accessibility
提供可取得的視窗幾何與移動縮放，支援寵物站窗、焦點遮罩與跨螢幕版面。

補上 macOS 啟動與退出快捷鍵、MIDI、媒體操作、麥克風、擷取授權說明及打包資料。
功能按實際 framework／權限判定，不能用 `darwin` 分支返回成功代表已支援。
Accessibility、螢幕錄製與麥克風權限被拒時顯示可理解的原因和恢復方法。

外部應用視窗的強制置頂／透明度、其他程式擷取時排除本程式、指定 Space 等行為，
須逐項確認公開 API 是否支持。沒有公開能力的項目保留明確限制；替代的浮層副本
不能被描述為已改變原視窗。相關行為列入平台矩陣供審閱。

新增 macOS CI 的 wheel 安裝、啟動與 backend 測試。實際音訊、TCC、多螢幕座標和 GL
需要 macOS 實機驗證；目前 Windows 工作區不能出具這些實機通過證據。

## 第五階段：外掛權限宣告

本次採 manifest 權限宣告與載入前授權，保留現有 QWidget 外掛介面。
`plugin.json` 宣告 schema version、plugin id、API version、entrypoint 與 permissions，
permissions 使用固定集合，例如 filesystem、network、screen_capture、microphone、native_code。
未知值與無效 manifest 在 import 前拒絕。單檔外掛也有對應 sidecar manifest。

載入前顯示宣告能力與執行模式，授權以 plugin identity 與內容 digest 綁定；
檔案、宣告權限或 entrypoint 改變就重新授權，撤銷後重啟不再 import。
舊的無宣告外掛須明確選擇完整信任，不能因啟用外掛總開關而默默執行。

Python 同行程宣告無法強制阻止程式碼越權；UI 和文件須如實說明。
若後續要求真正沙箱，另建獨立 worker／OS 隔離與能力 RPC，
現有任意 QWidget 外掛不能直接被宣稱已沙箱化。
測試驗證拒絕授權時連 import 副作用都不執行、摘要變更與權限升級重新授權。

## 第六階段：覆蓋層 GPU 合成

新增明確的 GPU compositor，將 image、GIF、text 與可支援的場景 primitive
轉成 texture layers，處理 transform、z-order、alpha 與 clip；使用 QOpenGLWidget、
shader 與 framebuffer，僅在資源變更時上傳 texture。Puppet 透過既有 GL 渲染介面接入。

對現有 `draw_content(QPainter)` 提供 raster-to-texture adapter，先遷移可重用內容，
再針對高頻來源提供直接更新。這類 adapter 的內容生成仍使用 CPU，不能宣稱為完整 GPU 繪製。
Web、video 與需原生互動的 widget 先採明確的分離視窗路徑，
避免任意 QGraphicsProxyWidget 與 OpenGL viewport 的相容性限制。

backend 支援 auto、gpu、software；無 GL／初始化失敗時可回退並顯示實際 backend。
關閉時在有效 context 釋放 texture、FBO、shader 和 timer，正確處理 DPI 與跨螢幕尺寸。
虛擬攝影機與錄製用共享輸出介面，讀回 GPU frame 不被描述為零拷貝。

驗證 alpha、z-order、transform、clip、DPI 與 software/GPU 輸出一致性，
實際 GL 測試不得以 stub 通過替代。Windows／macOS 分別記錄 CPU、GPU、記憶體與 frame time，
用相同場景比較；效能改善幅度以測量結果為準。

## 文件與全程驗證

每個實作階段同步更新英文與九份 README、七個 Sphinx 語言樹、七個 UI 字典、
`architecture.md`／`architecture_explore.md` 和更新紀錄；依階段必要性調整 dependencies，
保持 requirements 與 pyproject 一致。

共用檢查：`py -m pytest tests/ -q`、`py -m pyflakes frontengine/ exe/ tests/`、
Sphinx HTML build；另加 TLS 真實連線、GIF 真實讀回、Imervue 真實往返與 GL 實機驗證。
涉及 OS、相機、音訊與視窗的測試注入來源，不能操作使用者既有視窗或媒體播放器。

## 官方技術依據

- Qt Graphics View：<https://doc.qt.io/qt-6.11/graphicsview.html>
- Qt OpenGL viewport 相容性：<https://doc.qt.io/qt-6/qgraphicsview.html>
- Windows OCR：<https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.recognizeasync>
- Apple ScreenCaptureKit：<https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos>

## 設計審閱決策

建議採上述相容遷移方案，從串流 GIF 實作開始；外掛選擇權限宣告，
Imervue 選擇可選 runtime 依賴。使用者可調整這些選擇、macOS 支援基準與階段順序。
設計審閱通過後，下一個交付物是第一階段的實作計畫；其餘階段仍需各自詳細計畫與驗收。
