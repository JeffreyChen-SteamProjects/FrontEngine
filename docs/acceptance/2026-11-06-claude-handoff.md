# FrontEngine 交接給 Claude

使用者要求完成目前這份修正後記錄進度並轉交。交接點是螢幕預設集語言修正，產品提交 `4e98b94d`。整體 UI/UX、完整程式碼審查與桌面寵物事件目標尚未完成。

## 從正確工作目錄開始

- 最新工作目錄為 `D:/Codes/FrontEngine/.audit/worktrees/monitor-state-language`，分支 `fix/monitor-state-language`。此分支包含前面所有已累積的變更，不要從原始 checkout 重新實作。
- 本次基底為 `9ef5164b`，上一份產品提交為排程無障礙修正 `8b13ba28`。
- 原始 `D:/Codes/FrontEngine` 仍在 `fix/pet-home-lifecycle-review`，HEAD 為 `c1d07274`。不要將它誤認為最新版本，不要清除 `.audit` 或其他 worktree。
- 先讀此文件，再讀最新工作目錄的 `progress.md`。其中 #111 是本次交接後第一優先事項；其他條目保留各項未完成驗收與既有證據。
- 本機證據存在各 worktree 的 `.audit`，不在 Git 提交內。交接是同一台機器上的工作，不代表已上傳證據。

## 使用者限制

- 不轉換或建置 EXE。不 push、merge、release。允許本機提交。
- 全程背景執行，不搶前景、不移動游標、不注入 OS 鍵盤滑鼠。原生 Qt 探測用 `tests/integration/hidden_desktop.py`，不得切換輸入桌面。
- 不因等待逾時就重跑或終止活躍回歸。先查程序與終端結果。
- Tripo 必須沿用插件帳戶登入、Studio 點數優先、原生功能優先及費用授權限制。不要改用環境 API key 代替登入帳戶。本次未涉及 Tripo。
- 使用者另問過 GitHub LFS 為何顯示已使用 90%。此問題尚未調查或回答，勿假稱已確認儲存量或下載流量。

## 本次完成內容

十個頁面的 `target_monitor` 原本保存 `currentText()`，切換語言後設定就改變，舊預設集跨語言載入也找不到原選項。文字、圖片、影片、GIF、網頁、粒子、寵物、聚焦、簡報及螢幕保護頁面現統一使用 `frontengine/ui/page/utils.py` 的兩個 helper。

- `target_monitor_state` 保存字串 `here`、零起算編號或 `span`。
- `apply_target_monitor_state` 接受穩定值及七種已註冊語言的舊顯示文字。缺席、null、不合法值或當下不可用的螢幕均保持原選取。
- 數字字串保持原格式；未更改實際螢幕派送規則。這不是硬體螢幕永久身分或接拔重排修正。
- 新增 `tests/unit_test/test_monitor_state_language.py`。十頁 × 四種選擇 × 七語驗證保存與重新載入，另驗證舊翻譯及不合法／不可用值。
- Model the Domain 原則用在把目的地身分與顯示文字分開。比較過直接保存 None/int/span；選擇字串格式以維持數字預設集相容，並保留 null 的不變更語意。設計探索是單人順序比較，不宣稱多代理設計共識。

驗證紀錄位於本 worktree 的 `.audit`。

| 證據 | 結果 |
| --- | --- |
| `monitor-state-red.log` | 原有 live-language 測試修正前失敗，1 failed、18 deselected |
| `monitor-pages-red.log` | 新跨頁測試修正前失敗，保存值仍為英文標籤 |
| `monitor-final-focused.log` | Python 3.14.5，73 passed，32.53 秒 |
| `native-monitor-state-final/pytest.log` | Python 3.11、Qt 6.12、Windows 原生平台，41 passed，28.39 秒 |
| `native-monitor-state-final/result.json` | exit 0，確認載入目前 worktree |
| `native-monitor-state-final/desktop.json` | 子程序位於獨立桌面，與輸入桌面不同 |
| `native-monitor-state-final/observer.json` | 前後 foreground 133262，游標 625,406，child exit 0 |

第一次原生測試 `native-monitor-state` 是 1 failed、40 passed。原因是測試把本機假定為單螢幕，錯判 span 不可用。改為注入單螢幕測試清單後完成上表重跑，失敗紀錄未覆蓋。第一次前後觀測不同，不推斷原因。最終相同的兩點取樣也不等於持續監測或 OS 輸入驗收。跨螢幕測試使用合成清單，不代表實體多螢幕接拔驗收。

獨立代理 `monitor_handoff_review` 靜態檢查十一個產品檔案、新測試與 preset repository/history，未發現功能阻擋問題。三個 set_state 文件字串位置建議已修正。此審查不涵蓋整條累積分支，也未由代理重跑完整測試。

## 完整回歸的真實狀態

較早佇列快照已過時。停止原因已確認，不能把後面的排隊版本視為通過。

- `shared-option-translations/.audit/full-regression-9eba3a44/result.json` 為 exit 1，752 個來源檔未改變。
- 該次結果為 1 failed、3295 passed、3 skipped，2011.35 秒。失敗是 `test_live_language_switch.py::test_switching_leaves_the_user_alone`，target_monitor 從英文變成德文。
- 下游程序因父結果檢查失敗而退出。`signage-accessibility` 的舊 PID 70172 已不存在，沒有該版本完整結果。不要盲目重建所有舊佇列，也不要覆寫失敗祖先結果。
- 最後已嚴格核實的全套成功版本為 `scene-tabs` 產品 `7743fd6b`，3279 passed、3 skipped，3282 total，752 個來源檔未改變。
- 上一份 `schedule-accessibility` 產品 `8b13ba28` 收集 3502 項、756 個來源／測試檔，尚未啟動全套。本次同樣未啟動全套。
- 本次最終收集為 3513 項，12.23 秒。測試後的 Python 來源清單與原始證據 SHA-256 存於 `docs/acceptance/2026-11-06-monitor-state-language.json`，這不是完整回歸前後來源一致性的證明。
- 當前定向成功只證明此修正，不證明後續累積約二十多份變更的完整回歸。

完整 runtime 為 `D:/Codes/FrontEngine/.audit/test-runtime-3145/Scripts/python.exe`。原生驗證 runtime 為 `D:/Codes/FrontEngine/.audit/host-runtime-612/Scripts/python.exe`。既有全套 runner、manifest 及嚴格核對腳本可在各 worktree `.audit` 找到。

## Claude 接手後的順序

1. 核對最新 worktree 的 HEAD、工作樹與程序狀態。使用 Git common-dir 的 pstack resume locator 可找到此交接。不要重跑已存在的程序。
2. 對目前累積版本建立新的、獨立輸出目錄與來源雜湊清單，執行全套回歸。保留祖先失敗證據，核對 exit、JUnit、收集數、三個預期 skip、執行前後來源一致性。不要沿用舊預期總數。
3. 預期 Windows skip 為 default_storage_binding 的 POSIX fork、remote_tls 的 POSIX permission、storage_session 的 POSIX fork。其他 skip 需查明。
4. 全套通過後，安排完整累積差異的獨立審查。較早 reviewer 因使用額度失敗，不能當作完成。此次小範圍靜態審查也不能替代。
5. 按 `progress.md` 完成 UI/UX、寵物事件、儲存生命週期與實機驗收。排程／螢幕保護 accept 寫入失敗 rollback、來源選項即時重譯是已記錄但尚未確認的相鄰問題，先重現再修。

仍待驗證的範圍包括實際讀屏、混合 DPI／螢幕接拔／負座標／工作列／全螢幕／鎖屏／休眠／RDP、macOS TCC／MIDI、Steam 真實與離線流程、真實歷史玩家資料遷移、最新版本乾淨機器安裝、正常速度與長時間測試。既有 wheel 不是最新版本，亦非乾淨機器驗收。詳細編號以 `progress.md` 為準。

此交接不宣稱整體目標完成，也不授權 EXE、發佈或付款。
