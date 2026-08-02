發布流程
--------

工作流向是 ``功能分支 -> dev -> main``，而且只有最後一步會發布::

    feat/xyz  --PR-->  dev  --PR-->  main
                        |              |
                   CI，不發布      CI + 發布

功能分支從 ``dev`` 長出來、再合併回 ``dev``，這一段只會跑 CI，不會產生任何
版本。要發版時才刻意開一個 ``dev`` 指向 ``main`` 的 pull request：合併它是
唯一會把 FrontEngine 以 ``frontengine`` 的名義發布到 PyPI 的動作。

持續整合與發布由 ``.github/workflows/`` 底下的三個 GitHub Actions 工作流程
驅動。

工作流程
========

* ``ci.yml`` — *CI*

  * 觸發時機：對 ``main`` 與 ``dev`` 分支 push 或 pull request、從
    **Actions → CI → Run workflow** 手動觸發，以及由 ``nightly.yml`` 每日呼叫。
    手動觸發是必要的：帶 ``[skip ci]`` 的 commit（版本號那一筆就是）會讓分支
    停在一個沒有 CI 紀錄的 HEAD 上，沒有手動觸發就補不回來。
  * 於 ``windows-latest`` 上對 Python 3.10、3.11、3.12 進行 matrix 測試。
  * 編譯 ``frontengine/`` 底下所有模組，並執行 ``tests/unit_test/start/``
    底下的兩支 GUI 冒煙測試腳本。

* ``release.yml`` — *Release*

  * 只會在 **來自 ``dev``** 的 pull request 實際 **合併** 進 ``main`` 時觸發。
    關閉但未合併的 pull request 不會發布；功能分支直接對著 ``main`` 合併也
    不會——那樣合併照樣成功，只是不產生版本，之後的 ``dev -> main`` 會一起
    帶上去。錯的方向是「少發一版」而不是「多發一版」。也可以透過
    ``workflow_dispatch`` 手動重新執行——手動觸發可以指定 ``bump`` 參數
    （``patch`` / ``minor`` / ``major``，預設 ``patch``）。
  * 在 **建置或上傳之前**，工作流程會先從 ``stable.toml`` 讀取目前的
    ``version``，依指定段位自動遞增（PR 合併觸發固定做 patch 遞增），將
    新版本寫回 ``stable.toml`` 與 ``pyproject.toml``，並以附帶
    ``[skip ci]`` 的 commit 把這次版本異動推回 ``main``，避免對自己觸發
    CI。
  * 接著把 ``stable.toml`` 覆蓋成 ``pyproject.toml``、建置 sdist 與 wheel、
    以 ``twine check`` 驗證、以 ``twine upload`` 上傳至 PyPI 的
    ``frontengine`` 專案，並以標籤 ``v<new-version>`` 建立一個 GitHub
    發行版並附上建置產物。
  * 若計算出來的標籤已存在，工作流程會在碰到 PyPI 之前中止，確保同一個
    版本不會被重複發布。
  * 最後把 ``dev`` fast-forward 到這次發布的 commit，下一輪才不會從「落後
    一個 commit」開始。這一步是盡力而為：發布期間若有人推了 ``dev``，它只會
    警告而不會讓一個已經上架的發布算成失敗，事後執行
    ``git push origin main:dev`` 即可。

發布新版本
==========

1. 先把這次要出的功能合併進 ``dev``，這個階段不會發布任何東西。
2. 開一個 ``dev`` 指向 ``main`` 的 pull request 並合併，patch 版號會自動遞增。
3. 同一次工作流程執行就會發布到 PyPI、建立 GitHub 發行版，並把 ``dev``
   fast-forward 過去。

如果要做 minor 或 major 版本遞增——或者要在不開新 PR 的情況下重新執行
失敗的發布——請到 **Actions → Release → Run workflow** 手動觸發，並
選擇 ``bump`` 段位。

必要的 Secrets
==============

請在 repository secrets 中設定：

* ``PYPI_API_TOKEN`` — PyPI API token，權限範圍為 ``frontengine`` 專案。

工作流程使用 ``__token__`` 作為 twine 的使用者名稱，所以 secret 只需存放
token 本身即可。把版本異動 commit push 回 ``main`` 使用 GitHub Actions
自動提供的 ``GITHUB_TOKEN``。
