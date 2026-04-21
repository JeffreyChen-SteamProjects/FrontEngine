發布流程
----

FrontEngine 從單一程式碼樹發布兩個 PyPI 套件：

* ``frontengine`` — 穩定版，由 ``main`` 分支發布。
* ``frontengine_dev`` — 開發版，由 ``dev`` 分支發布。

持續整合與發布由 ``.github/workflows/`` 底下的三個 GitHub Actions 工作流程驅動。

工作流程
====

* ``ci.yml`` — *CI*

  * 觸發時機：對 ``main`` 與 ``dev`` 分支 push 或 pull request，以及每日排程。
  * 於 ``windows-latest`` 上對 Python 3.10、3.11、3.12 進行 matrix 測試。
  * 編譯 ``frontengine/`` 底下所有模組，並執行 ``tests/unit_test/start/``
    底下的兩支 GUI 冒煙測試腳本。

* ``release-dev.yml`` — *Release Dev*

  * 觸發時機：push 到 ``dev`` 分支，或手動執行。
  * 從 ``pyproject.toml`` 讀取版本號，組成標籤 ``dev-v<version>``。
  * 若該標籤已存在則工作流程直接結束；否則會建置 sdist 與 wheel、以
    ``twine check`` 驗證、以 ``twine upload`` 上傳至 PyPI 的
    ``frontengine_dev`` 專案，並建立一個以所建置的發行檔為附件的
    GitHub **預發行版**。

* ``release-stable.yml`` — *Release Stable*

  * 觸發時機：push 到 ``main`` 分支，或手動執行。
  * 先把 ``stable.toml`` 覆蓋成 ``pyproject.toml`` 讓建置使用穩定版
    專案資訊，之後的建置／驗證／上傳／發行流程與 dev 工作流程相同。
  * 使用的標籤為 ``v<version>``，發行版不會被標記為預發行。

發布新版本
====

1. 調整 ``pyproject.toml`` (dev) 或 ``stable.toml`` (stable) 中的
   ``version`` 欄位。
2. Commit 並 push 到對應的分支。
3. 對應的 release 工作流程會自動開始。

由於兩條 release 工作流程都會拒絕重用既有標籤，日常沒有調整版本號的
推送完全安全：工作流程執行後看到標籤已存在，就會直接結束，不會重新
上傳套件。

必要的 Secrets
====

請在 repository secrets 中設定：

* ``PYPI_DEV_API_TOKEN`` — PyPI API token，權限範圍為 ``frontengine_dev``
  專案，供 ``release-dev.yml`` 使用。
* ``PYPI_STABLE_API_TOKEN`` — PyPI API token，權限範圍為 ``frontengine``
  專案，供 ``release-stable.yml`` 使用。

兩條工作流程皆使用 ``__token__`` 作為 twine 的使用者名稱，所以 secret
只需存放 token 本身即可。
