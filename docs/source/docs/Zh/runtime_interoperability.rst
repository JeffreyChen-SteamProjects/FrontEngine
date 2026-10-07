執行環境、隱私與互通
====================

錄製：框選範圍後，先選擇輸出 GIF 才開始擷取；取消不會啟動錄製。影格由背景執行緒逐張寫入，佇列上限為三張與 64 MiB，單張超限會拒絕。佇列已滿時略過擷取，並保留實際經過的播放時間。仍保留幀率、時長、影格數上限與攝影機子母畫面。停止後非同步完成寫檔，只有成功時才原子替換目標；取消與寫入失敗會清除暫存檔，保留既有目標檔。

手機操控：Settings → Remote control 只提供 HTTPS，權杖每次啟動都會更換，可執行動作採固定清單。手機不會自動信任本機自簽憑證。請先匯出公開憑證，比對顯示的 SHA-256 指紋，再依手機或瀏覽器設定匯入或信任。私鑰留在使用者資料目錄。IP 變更、到期或重新產生憑證時，可能需信任新憑證。TLS 啟動失敗不會退回 HTTP。

畫面文字：Tools → Read text 優先使用本機 OCR：Windows 的 Windows.Media.Ocr、macOS 的 Vision，或已安裝且具有語言資料的 Tesseract 執行檔。本機擷取文字不需雲端同意或 ANTHROPIC_API_KEY；成功但沒有文字時不會上傳截圖。翻譯與提問只有在另行同意傳送文字且提供金鑰時，才會將辨識文字送至 Anthropic。本機失敗後的截圖回退需要獨立的畫面傳送同意與金鑰。結果會顯示後端及錯誤，也能撤回同意。

Puppet 寵物：安裝選用的 puppet extra 與可用的 Imervue runtime，再於寵物頁選擇或拖入原始 Imervue .puppet v1 檔案。既有圖片與 sprite 寵物包仍可使用。Puppet 寵物使用 Imervue 畫布、動作與表情，可複製或關閉，並支援 FrontEngine 覆蓋層控制與預設集。可另選 .petscript.json 使用 Imervue 原有腳本引擎；FrontEngine pet.json 寵物包不是 puppet 檔。未知版本、不安全的封存路徑與無效資源會在載入 runtime 前拒絕。

場景：場景頁支援舊 entry mapping JSON、有版本的 frontengine.scene envelope，以及可攜式 .fescene 套件。PUPPET 項目可設定位置、大小、不透明度、有限數值參數，以及選用動作、表情與腳本。JSON 路徑相對於場景檔解析。.fescene 包含引用媒體、原始 .puppet 與選用 .petscript.json，可移到其他電腦。匯入會檢查路徑、符號連結、版本與解壓上限。FrontEngine 場景維持場景套件；.puppet 維持單一 Imervue 角色。

macOS：選用 macos extra 以 macOS 13+ 與公開 PyObjC framework 為基準。後端提供 ScreenCaptureKit 螢幕／視窗擷取與系統音訊、麥克風擷取、Quartz 視窗幾何、Accessibility 視窗版面與移動、CoreMIDI、媒體鍵及 F12 退出。螢幕錄製、輔助使用與麥克風權限分別檢查；請到系統設定 → 隱私權與安全性，依提示重新啟動。其他程式視窗的透明度／強制置頂、Space 指定，以及讓其他程式擷取時排除覆蓋層仍不可用。本 Windows 開發環境尚未驗證 macOS 原生授權、硬體與效能。 Settings → macOS 權限與能力會逐項列出可用、不可用或不支援，並顯示權限或安裝原因。

外掛：啟用載入不代表授權外掛。plugin.json 或單檔 sidecar 宣告版本、身分、入口與能力；Python import 前檢查同意，授權綁定內容摘要。程式或宣告改變就需重新同意；舊外掛需明確完全信任。Settings → Revoke plugin grants 可撤銷保存的授權；已在執行的程式需重新啟動才能卸載。Python 外掛仍具有完整應用程式權限，宣告與同意不是作業系統沙箱。

算圖：Settings → Overlay rendering 可選 Auto、GPU 或 Software，並查看實際後端。GPU 合成器以 OpenGL texture、shader 與 framebuffer 處理圖層順序、變換、不透明度與裁切；初始化失敗時回退軟體並顯示原因。既有 QPainter 內容仍可能先由 CPU 轉成點陣圖再上傳；web／video／原生 widget 可能使用獨立視窗。擷取與錄製可能將 GPU 畫面讀回 CPU，這不代表零拷貝擷取或已測得效能提升。 場景 GPU 合成目前涵蓋 IMAGE、GIF 與 TEXT；puppet 使用自己的 Imervue 視窗繪製。

Windows OCR 的 WinRT 投影套件包含於 FrontEngine 的一般 Windows 安裝；請安裝需要的 Windows 辨識語言。Tesseract 的執行檔與訓練語言資料需另行安裝。選用 puppet extra 會安裝 Imervue>=1.0.90；macos extra 安裝 macOS 13+ 的公開 PyObjC framework。請使用下列指令。docs/formats/ 提供 puppet、pet.json、petscript 與場景範例。

.. code-block:: console

    pip install "frontengine[puppet]"
    pip install "frontengine[macos]"

Workshop 內容宣告採版本化格式，使用前會驗證；未知的中繼資料 JSON 不會當成預設集。預設集封包會拒絕不安全的封存路徑、超出資源上限及媒體檔名碰撞。

預設集 → 管理創意工坊可開啟 Steam 管理介面；場景與寵物頁也提供入口。Windows x64 需已連線 Steam 客戶端、App 2793470 工作階段及 steam_api64.dll。可發布已儲存的 .fescene／場景 JSON、預設集 ZIP 或 sprite 寵物資料夾，並附小於 1 MB 的 PNG/JPEG 預覽。新項目預設私人，更新時核對擁有者。上傳顯示進度與條款狀態，保存項目 ID 供重試，隱藏管理視窗仍繼續；中斷後須在 Steam 確認結果。訂閱內容先驗證並複製到獨立版本資料夾，本機修改衝突可選下載版本或本機版本。載入會填入對應功能頁，播放從該頁啟動；預設集匯入須使用新名稱。既有離線資料夾匯入保留。Steam 封裝時於 exe/build_exe.py 加上 --steam-runtime DLL路徑，選定 DLL 放在執行檔旁（--onefile 亦同），不包含整套 SDK 或開發用 steam_appid.txt。

Windows 安裝現在包含 winrt-Windows.Media.Control，讓「正在播放」小工具透過 SMTC 顯示歌名與演出者；舊 winsdk 仍可備援。沒有媒體工作階段時回傳空結果，並保留既有音訊程式名稱備援。
