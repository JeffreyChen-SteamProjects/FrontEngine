"""
守住公開匯入介面：`frontengine.__all__` 的每個名稱都要存在，且套件內每個模組
都要能單獨匯入。移除功能卻留下舊匯入的情況（例如已刪除的 ChatSceneUI）會在此被抓到。

Guard the public import surface: every name in ``frontengine.__all__`` must
resolve, and every module in the package must import on its own. This catches
imports left behind by removed features (e.g. the deleted ChatSceneUI).
"""
import importlib
import pkgutil
from pathlib import Path

import pytest

import frontengine


def test_all_is_declared() -> None:
    assert isinstance(frontengine.__all__, list)
    assert frontengine.__all__, "__all__ must not be empty"


@pytest.mark.parametrize("name", frontengine.__all__)
def test_exported_name_resolves(name: str) -> None:
    assert hasattr(frontengine, name), f"{name} is exported but missing"


def test_exported_names_are_unique() -> None:
    assert len(frontengine.__all__) == len(set(frontengine.__all__))


def _module_names() -> list:
    """列出 frontengine 底下所有子模組 / Every submodule under frontengine."""
    return [
        module.name
        for module in pkgutil.walk_packages(frontengine.__path__, prefix="frontengine.")
    ]


@pytest.mark.parametrize("module_name", _module_names())
def test_module_imports(module_name: str) -> None:
    importlib.import_module(module_name)


def test_every_package_directory_has_an_init_file() -> None:
    """
    每個放了 .py 的資料夾都必須有 __init__.py。setuptools 的 find 設定是
    `namespaces = false`，少了它那個資料夾就**不會被打包**——從原始碼跑得好好的，
    使用者 pip 安裝後卻會 ModuleNotFoundError（frontengine.utils.screen_text
    就是這樣漏掉的，直到裝好的套件連 import 都失敗才發現）。

    Every directory holding .py files needs an __init__.py. Packaging uses
    setuptools' find with ``namespaces = false``, so a directory without one is
    **left out of the wheel**: it runs fine from a checkout and raises
    ModuleNotFoundError once installed. That is exactly how
    frontengine.utils.screen_text escaped, until the installed package could not
    be imported at all.
    """
    root = Path(frontengine.__file__).parent
    missing = []
    for directory in sorted(root.rglob("*")):
        if not directory.is_dir() or directory.name == "__pycache__":
            continue
        holds_python = any(child.suffix == ".py" for child in directory.iterdir()
                           if child.is_file())
        if holds_python and not (directory / "__init__.py").exists():
            missing.append(str(directory.relative_to(root)))
    assert missing == [], f"these packages would be left out of the wheel: {missing}"
