# Puppet 原生透明照片驗收

新增 `tests/integration/puppet_photo_native.py`，以 Windows Qt 平台建立真正的 OpenGL canvas，呼叫 `PuppetPetWidget.photo_image()`，不使用替代渲染函式。模型由 Imervue 官方存檔 API 建立，僅含一塊半透明測試網格；個體資料保存在記憶體，不改使用者存檔。

本機執行通過。照片為 128 × 128，背景 alpha 為 0，中心 RGBA 為 `(255, 128, 0, 128)`。重複拍照、canvas 重繪後再拍照，以及 PNG 寫入後讀回的像素一致；拍照前後個體狀態相同。PNG 比較先統一為 RGBA8888，避免 QImage 儲存格式不同造成假失敗。

測試以 `pythonw.exe`、隱藏程序啟動。視窗設定不接受焦點與不啟用顯示，放在所有螢幕右側之外。驗收確認視窗與所有螢幕不相交；26 次前景視窗觀測相同，且不是測試視窗。游標位置只作讀取觀測，沒有注入鍵鼠輸入。

重跑方式：設定 `QT_QPA_PLATFORM=windows` 與 `PYTHONPATH` 為專案根目錄，使用虛擬環境的 `pythonw.exe` 執行此檔，唯一參數是獨立輸出目錄的絕對路徑。由 PowerShell 啟動時加上 `Start-Process -WindowStyle Hidden`。輸出包含 `fixture.puppet`、`photo.png` 與 `result.json`；程序成功退出碼為 0。

本次證據位於 `.audit/pet-implementation/native-photo-rerun-2026-10-29/result.json`。這只證明測試網格的原生照片流程，不代表正式角色、複雜遮罩、動作綁定、多 GPU 或混合 DPI 已驗收。六角色與服裝的正式素材仍待完成。
