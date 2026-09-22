# progress.md：FrontEngine

只放還沒做的事。做完就在同一個 commit 裡刪掉這條，並在 `docs/updates/` 新增一筆 `#done` 紀錄（格式與查詢方式見 `docs/updates/README.md`）。不放已完成的項目、不寫流水帳、不寫規則（規則與環境備忘在 `CLAUDE.md`）。
編號 `#n` 不重用。標記：〔決定〕需擁有者拍板、〔候選〕還沒決定要不要做、〔阻塞〕在等別的事。
跨專案與工作區層級的待辦在 `D:\Codes\progress.md`（與本專案相關：X-1、X-6、X-13、X-16）。

## 待辦

- **#1** 〔決定〕PyPI 上的 v1.0.39 / v1.0.40 是壞的（缺 `__init__.py`，import 失敗）；要不要 yank 需要 PyPI 憑證。v1.0.41 之後都正常。
- **#2** 〔決定〕PyPI 上的 `frontengine_dev` 停在 1.0.0，`pyproject.toml` 已到 1.0.77，workflow 沒有發佈 dev 套件的步驟（工作區 X-13）。
- **#4** `dev_requirements.txt` 沒有 pyflakes，但專案用它做靜態檢查；README 標成需另外安裝，可以改成加進 dev_requirements。
- **#5** `stable.toml` 開頭的註解寫「dev version」，但它是穩定通道 `frontengine` 的設定，會誤導。
- **#6** `architecture_explore.md` 把 `system_tray` 列在 `ui/` 底下，實際套件在 `frontengine/system_tray/`。
- **#8** 〔候選〕本機離線 OCR（Windows.Media.Ocr）需要 WinRT 投影套件，目前沒有。
- **#9** 〔候選〕音訊頻譜、視窗釘選／版面、螢幕錄影只有 Windows 完整支援。
- **#10** 〔候選〕「正在播放」的歌名需要選用套件 `winsdk`。
- **#11** 〔阻塞〕Steam Workshop 的**發布**需要 Steamworks SDK 與 App 憑證。
- **#12** 〔候選〕Steam 商店頁只有 2 則評論、討論區 0 個主題，沒有真實使用者的需求訊號；目前功能取捨是靠 Lively、Rainmeter、PowerToys、DisplayFusion 等鄰近產品推論的。
