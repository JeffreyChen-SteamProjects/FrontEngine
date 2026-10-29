# Puppet 共同互動的原生動作對應

Puppet 腳本可新增 frontengine_actions，把 feed、groom、sleep、celebrate 等狀態明確對應到模型現有的 motion／expression。未提供對應時保留既有行為，不依名稱猜動畫。名稱與欄位在配置原生視窗前驗證，腳本讀取限制 1 MiB。格式範例見 `docs/formats/puppet-companion-actions.md`。

共同互動仍管理時間與獎勵；原生 player 和 expression stack 只負責呈現。重複狀態通知不重播。完成／中斷時只停止自己啟動的動作、移除自己新增的表情；使用者原先選的表情保留。手動選動作、表情或點擊模型熱區會先交還控制權。隱藏、打字安靜與關閉會釋放反應。

驗證：原生 API 狀態、腳本驗證、生命週期、拍照與複製 25 項通過；修正熱區表情切換後，反應、生命週期與文件 40 項通過，兩組有重疊。pyflakes 通過。測試建立實際 Imervue Motion／Expression 與 player/canvas，但在 Qt offscreen 執行，沒有證明原生 GL 的實際視覺結果。

各模型正式對應腳本、動作美術、原生畫面和效能驗收仍待完成。
