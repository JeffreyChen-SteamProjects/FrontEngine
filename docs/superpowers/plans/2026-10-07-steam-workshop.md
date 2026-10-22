# Steam Workshop implementation plan

日期：2026-10-07。狀態：已開始規劃，實作與 Steam 實機驗收待完成。

對應 `progress.md` #11、#13、#15、#39–#44。第一版以 Windows x64 為交付平台；原生 adapter 保留跨平台介面，但 macOS／Linux runtime 必須另行驗證。

## 目標與第一版範圍

完成 FrontEngine 場景、預設集與 sprite 寵物包的「製作 → 發布 → 更新 → 訂閱下載 → 匯入 → 使用」。使用現有 `.fescene`、預設集媒體封包與 `pet.json` 格式，第一版不依賴未完成的視覺化場景編輯器。

第一版提供發布／更新對話框、訂閱內容清單及開啟 Steam 項目頁面。社群搜尋、評分、收藏等完整瀏覽體驗留待後續；Python 外掛不納入可發布內容。

## 已確認的本機證據

- 根目錄 `appid` 與 `workshop_content.APP_ID` 均為 `2793470`。
- `steam_sdk/public/steam/steam_api_flat.h` 提供 `SteamAPI_SteamUGC_v021`，`isteamugc.h` 宣告 UGC interface 021。
- 靜態讀取 `steam_sdk/redistributable_bin/win64/steam_api64.dll` 的 PE export table：AMD64，具備 `SteamAPI_InitFlat`、`SteamAPI_Shutdown`、`SteamAPI_SteamUGC_v021`、manual dispatch、CreateItem、SubmitItemUpdate 與 GetItemInstallInfo 等必要入口。這不是初始化、回呼 ABI 或上傳成功證據。
- `utils/workshop/workshop_content.py` 只掃描已下載資料夾，分類 pet_pack／preset／media。任意 JSON 都可能被當成預設集，新增 manifest 必須修正此處。
- `ui/menu/preset_menu.py` 複製預設集，寵物包只列出原路徑；目前缺乏 scene／新版封包辨識、訂閱事件與發布實作。
- `exe/build_exe.py` 尚未明確納入 Steam runtime；SDK 目錄被忽略，乾淨 checkout 與 CI 不能假設它存在。

## 外部條件與官方依據

Steam 客戶端需能辨識 App ID，使用者工作階段及 App 授權需有效。根目錄 `appid` 並非開發用 `steam_appid.txt`；開發啟動方式需單獨處理，Steam depot 不攜帶開發用 App ID 檔。一般使用者操作採 Steam 客戶端工作階段。[Steam API 初始化文件](https://partner.steamgames.com/doc/api/steam_api#SteamAPI_Init)

上傳前仍待確認 App 後台已啟用 ISteamUGC file transfer，並設定預覽圖所需的 Cloud 容量與檔案數配額。保存 published ID；處理條款未接受狀態；SubmitItemUpdate 開始後沒有 API 可取消上傳。[Workshop 實作指南](https://partner.steamgames.com/doc/features/workshop/implementation)

預覽圖使用 PNG／JPEG，設定保守的 1,000,000 bytes 以下產品上限；逐一檢查 setter 結果、上傳 EResult 與安裝狀態。[ISteamUGC 參考](https://partner.steamgames.com/doc/api/ISteamUGC)

上述後台條件尚未登入確認；規劃不宣稱已配置或發布成功。

## 設計選擇

### 內容格式

UGC 的內容是資料夾；新項目以 `k_EWorkshopFileTypeCommunity` 建立。建議結構：

```text
item/
  workshop.json
  preview.jpg
  content/
    scene.fescene | preset.zip | pet-pack/
```

`workshop.json`：`format=frontengine.workshop`、`version=1`、`kind`、`title`、`entry`、`content_revision`、`min_frontengine_version`、`required_capabilities`。`entry` 為受約束的相對路徑；published ID／作者 Steam ID／本機來源路徑保存在本機發布索引，並依 App／使用者隔離。Manifest 不能授予外掛權限或包含 API 金鑰。

每個項目一個主要內容入口。第一版 `kind` 為 scene／preset／pet_pack；scene 內 Puppet 資源沿用既有驗證與選用 runtime 要求。單獨 puppet／media 發布可另擴版本或種類。

發布前複製到受管理的 staging snapshot，列出實際上傳檔案供檢視。封裝器只收入明確引用的資源，不遞迴上傳整個使用者目錄。驗證 manifest 大小、種類與版本、路徑穿越、符號連結／Windows reparse point、解壓總量、項目數與檔名碰撞；預設集封包需補足既有解壓資源上限檢查。

### 原生介面與生命週期

新增 `utils/steam/steam_runtime.py`：延遲載入經設定的絕對 runtime 路徑，透過 `ctypes.CDLL` 綁定本機 SDK 的 C calling convention。使用 `SteamAPI_InitFlat`，分別檢查所需 interface pointer 與實際 App ID，回報缺 DLL、位元數不符、缺 symbol、初始化失敗等原因。

先完成 read-only spike，對照本機 headers 的 function signatures、64-bit handles、enum、bool、callback packing／size／offset。以小型 C++ probe 或等價 header 驗證方法確認 ABI，不靠 Python 模擬推定 native layout 正確。

選用 manual dispatch。Qt 主執行緒的 QTimer 約 50 ms 驅動 callback pump，限制單次處理量；用 async-call handle 分派結果，複製資料後於 finally 釋放 callback。不得混用 SteamAPI_RunCallbacks。檔案掃描、雜湊與封裝移到背景 worker，以 QueuedConnection 回 UI。

服務可注入 fake backend，Steam 初始化失敗時仍可使用一般覆蓋層與檔案匯入。關閉時先停止工作與 callback pump、清理 handles，最後只對成功初始化的 runtime 呼叫一次 Shutdown。不得在 module import 時初始化 Steam 或自動重啟應用程式。

### 發布、更新與復原

流程：選內容 → 驗證／封裝 → 填寫 metadata／預覽 → 檢視上傳清單與可見性 → 使用者提交 → CreateItem（新項目）→ 保存 published ID → StartItemUpdate → 設定各欄位 → SubmitItemUpdate → 等待結果。

初始新項目採私人可見性；公開是使用者在產品中的明確選擇。更新前查詢項目 owner／consumer App ID，避免只信任可修改的本機索引。每個 setter 失敗即中止送出，保留錯誤原因。

狀態至少包含 preparing、creating、configuring、uploading、awaiting_terms、completed、failed、outcome_unknown。Submit 前可取消本機準備；Submit 後按鈕改為關閉視窗／持續背景上傳，不宣稱取消成功。離線、逾時或關閉後可能結果未知，重開需查詢遠端與本機 operation journal，不能自動 CreateItem 造成重複項目。

以 GetItemUpdateProgress 顯示階段與已處理／總 bytes；總量改變或未知時顯示不定進度。Create 成功立即保存 ID，即使後續 upload 失敗也能更新同一項目。只有收到成功結果才標記內容版本完成。處理需要接受條款的 flag，開啟相對應的項目頁面。

上傳中的 staging 資源保留至結果確定；中途退出記錄未知結果與待清理 snapshot。清理策略必須與 runtime 壽命、重試一致，不得在仍可能讀取資源時刪除它們。

### 訂閱內容與匯入

以 GetSubscribedItems／GetItemState／GetItemInstallInfo 取得可用內容及安裝位置，不硬編碼預設 Steam library。必要時 DownloadItem，等待安裝／下載事件後再讀檔；核對事件 App ID 與項目 ID。

先驗證新版 manifest，legacy 無 manifest 的項目保留辨識路徑，但不能把未知 JSON 當成可套用配置。匯入到受管理的版本目錄，再原子更新本機索引；Steam 下載目錄唯讀使用，不原地修改。執行中的場景保留舊版本 lease，新版本下次載入或由使用者明確重載。

使用者修改匯入內容後形成獨立副本，訂閱更新不覆蓋它。取消訂閱先更新來源狀態，保留使用者副本；舊資料版本在沒有使用中 lease 後才能清理。離線模式顯示最後已驗證內容及來源狀態，保留原資料夾匯入入口。

## 分階段任務與檔案

1. **#39 格式與封裝**：新增 `utils/workshop/workshop_manifest.py`、`workshop_package.py`；調整 `workshop_content.py` 與 preset package import。驗證 round-trip、legacy 相容、錯誤 JSON、惡意路徑、資源上限與檔名碰撞。
2. **#40 Runtime spike**：新增 `utils/steam/steam_runtime.py`、`utils/workshop/workshop_service.py` 與 native read-only smoke 工具。先確認 symbol／ABI，再確認真實初始化、App ID 與回呼生命週期。
3. **#41 發布／更新**：新增 `workshop_publisher.py`、`workshop_repository.py`；注入後端測試建立後上傳失敗、setter 失敗、回呼亂序、條款要求、重試、未知結果與關閉收尾。
4. **#42 訂閱同步**：新增 `workshop_subscription.py`；測試未下載、下載中、更新、其他 App callback、離線、使用中舊版本與本機修改衝突。
5. **#43 UI 與發佈封裝**：新增 `ui/dialog/workshop_dialog.py`，調整 preset menu、scene／pet 入口、main_ui 服務收尾與 `exe/build_exe.py`。Steam runtime 來自明確建置輸入；不把整份 SDK 發到 PyPI，也不預設 PyPI 安裝具備 DLL。確認 redistribution 範圍及 clean build；同步所有 README、七組 UI 字典、七棵文件樹與架構文件。
6. **#44 實機驗收**：Windows x64 Steam client、App 授權與後台設定確認後，以私人測試項目完成建立／更新／訂閱／下載／載入，再測重開、離線與關閉。公開發布由使用者在完成的產品流程中操作。

## 驗收矩陣

| 層級 | 必須取得的證據 |
| --- | --- |
| 純邏輯與封裝 | 三種內容 round-trip；壞資料拒絕；資源與路徑上限；舊格式相容 |
| 注入後端 | upload／download 狀態機；未知結果復原；重試不建重複項目；關閉不阻塞 |
| Native 只讀 | 真實 DLL／ABI／初始化；App ID；callback pump／shutdown |
| Steam 寫入 | 私人項目發布與同 ID 更新；條款／錯誤狀態；下載後實際播放 |
| 乾淨安裝 | 打包 artifact 在獨立目錄啟動；缺 Steam／DLL 時功能降級有原因 |
| 回歸 | `py -m pytest tests/ -q`；pyflakes；Sphinx `-W`；git diff --check |

單元測試與 CI 不做真實發布。實機檢查區分 pass／fail／環境 unavailable；未配置後台或無授權不能記成通過。測試項目與遠端發布屬後續實作驗收，本次規劃未執行。

## 品牌素材

品牌名稱採 FrontEngine Workshop，素材與中英文說明放在 `steam_assets/workshop/`。品牌卡使用既有 FrontEngine 圖示與商店素材樣式，由 `steam_assets/generate_workshop.py` 以 QPainter 重製；不當作真實介面截圖，頁面文案與實際可用功能維持一致。
