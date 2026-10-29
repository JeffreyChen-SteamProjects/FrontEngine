# progress.md：FrontEngine

只放還沒做的事。完成後移除該項，並在 `docs/updates/` 記錄驗證結果。編號不重用。
跨專案與工作區層級的待辦另見 `D:\Codes\progress.md`。

## 實機驗收待辦



- **#9** **macOS 權限與裝置驗收**〔阻塞：沒有可互動的 Mac 測試主機〕。驗證 TCC 權限拒絕／變更／重新啟動流程、原生音訊、MIDI 與多螢幕；入口為 `tests/integration/macos_native_smoke.py`。既有 Windows／Linux 支援與隔離測試不能替代 macOS 實機結果。
- **#11** **Steam Workshop 離線／無客戶端驗收**〔阻塞：沒有獨立 Steam 測試工作階段〕。在獨立環境驗證離線與未啟動客戶端時的失敗回饋、重試及資源釋放。參考 `tests/integration/steam_workshop_smoke.py` 與 `steam_failure_smoke.py`；無效 App ID 的既有測試不能替代這兩個情境。
- **#21** **覆蓋層跨螢幕跟隨驗收**。這台機器現已接兩台不同縮放的螢幕（100%／125%），可以驗收；寵物部分已完成（U-20261029-46）。尚待以同樣的隔離桌面方式驗證一般覆蓋層跨螢幕移動後仍可見，且邏輯尺寸正確。
- **#22** **多螢幕配置恢復驗收**〔接拔與主螢幕切換需要人實際操作〕。驗證接拔、主螢幕切換、解析度／縮放變更，以及混合 DPI 下的配置恢復與可見區域限制；兩台螢幕的混合 DPI 現已具備。
