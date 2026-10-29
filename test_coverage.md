# 測試覆蓋度：FrontEngine

測量日期：2026-10-28。數字來自這台 Windows 機器上的一次實測，不是估計，也不是只數檔案。

| 項目 | 內容 |
|---|---|
| 直譯器 | 3.14.4 |
| 直譯器說明 | 專案 .venv |
| 工具 | coverage 7.15.0，`coverage run --branch` |
| 測量範圍 | `frontengine` |
| 測試路徑 | `tests` |
| 命令 | `python -m coverage run --branch --source=frontengine -m pytest tests` |
| 敘述覆蓋 | 69.57%（22739 / 32683） |
| 分支覆蓋 | 52.29%（4731 / 9048） |
| 測試結果 | 1854 passed, 1 skipped in 128.78s (0:02:08) |
| 耗時 | 134.3 秒 |

敘述覆蓋是執行到的敘述數除以全部敘述數。分支覆蓋是執行到的分支數除以全部分支數。兩者分開算，沒有把分支混進敘述百分比。

## 覆蓋較低的檔案

只列這次測量裡敘述覆蓋最低的檔案，最多 12 個。

| 檔案 | 敘述覆蓋 | 已覆蓋 / 敘述 |
|---|---:|---:|
| `frontengine/utils/scene_format/scene_3d_verification.py` | 6.34% | 13 / 205 |
| `frontengine/show/scene/renderer3d.py` | 9.4% | 22 / 234 |
| `frontengine/utils/scene_format/scene_3d_media_acceptance.py` | 10.0% | 9 / 90 |
| `frontengine/utils/scene_format/scene_3d_camera_acceptance.py` | 12.15% | 13 / 107 |
| `frontengine/show/scene/view3d.py` | 13.19% | 69 / 523 |
| `frontengine/utils/linux/windows.py` | 14.73% | 19 / 129 |
| `frontengine/utils/platform_info/capabilities.py` | 14.81% | 4 / 27 |
| `frontengine/show/compositor/gl_widget.py` | 16.96% | 19 / 112 |
| `frontengine/utils/scene_format/scene_3d_stress.py` | 17.02% | 8 / 47 |
| `frontengine/ui/dialog/window_pin_dialog.py` | 17.59% | 19 / 108 |
| `frontengine/show/particle/particle_ui.py` | 18.92% | 21 / 111 |
| `frontengine/ui/dialog/usage_report_dialog.py` | 21.13% | 15 / 71 |
