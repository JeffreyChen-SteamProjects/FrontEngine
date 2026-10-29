# Puppet 混合測試清理

修復 `progress.md` #24。`test_pet_recovery.py` 的 Puppet 案例在 finally 關閉寵物後，現在處理 `QEvent.DeferredDelete`，再交還控制權給模組級垃圾回收。這只改測試清理，沒有變更產品視窗行為。

定位證據：

- 不執行新的撫摸測試，只執行 recovery 與 reactions 兩個模組，仍得到 Windows 存取違規退出碼 `3221225477`。
- 六個 recovery 案例各自搭配 reactions 的視窗案例，全數通過。
- 同一程序執行 recovery 模組但排除最後的 Puppet 案例，11 項通過。保留該案例但排除其他個別案例仍會崩潰。
- 在該 Puppet 案例關閉後完成 Qt 延後刪除，兩模組 12 項通過。
- 原始完整順序 `test_puppet_petting.py test_pet_recovery.py test_puppet_reactions.py test_puppet_startup_lifecycle.py test_puppet_photo.py` 連續兩次通過，各 38 項，退出碼均為 0。

這些證據定位到測試結束時尚未完成的 QWidget 延後刪除與後續模組垃圾回收的組合。沒有以分程序執行代替混合驗收，也沒有忽略崩潰案例。尚未做的原生手勢操作、正式角色動畫與整體效能驗收不在此結果涵蓋範圍。
