# 寵物整組回歸與 Puppet 原生反應

在同一個 pytest 程序執行 `tests/unit_test` 下所有 `test_pet_*.py` 與 `test_puppet_*.py`，共 33 個模組、337 項測試通過。這包含換裝、配色、部件、存檔、玩具、撫摸、回收位置、Puppet 與照片流程的現有測試；不代表未製作的角色素材已完成。

`tests/integration/puppet_photo_native.py` 增加實際 `.petscript.json` 綁定。合成模型宣告 CareOpacity 參數、drawable opacity curve 與 care 表情，餵食時由 FrontEngine 的共同互動驅動 Imervue 原生表情。測試沒有替換 canvas 或渲染 API。

Windows 原生 OpenGL 執行退出碼為 0，`result.json` 為 passed。餵食時中心 alpha 從 128 變成 64；完成兩秒共同互動後，照片逐像素恢復基準。事先手動選取的表情在另一輪餵食完成後仍保留，影像與該表情的基準一致。取消手動表情後恢復原圖。原有透明背景、PNG 往返與重複擷取檢查仍通過，pyflakes 通過。

本機結果與圖片位於 `.audit/pet-implementation/native-reaction-2026-10-29`。沿用不接受焦點、螢幕外視窗與 pythonw 隱藏程序，不注入宿主鍵鼠輸入。互動時間由測試直接推進，因此沒有驗證真人滑鼠操作或長時間排程。

範圍限制仍包含正式模型動畫、複雜遮罩、多 GPU、混合 DPI，以及六角色及十四套服裝的完整素材。這次驗收證明合成測試模型的原生表情輸出與所有權還原，不能替代上述交付。
