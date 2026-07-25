"""
守住公開匯入介面：`frontengine.__all__` 的每個名稱都要存在，且套件內每個模組
都要能單獨匯入。移除功能卻留下舊匯入的情況（例如已刪除的 ChatSceneUI）會在此被抓到。

Guard the public import surface: every name in ``frontengine.__all__`` must
resolve, and every module in the package must import on its own. This catches
imports left behind by removed features (e.g. the deleted ChatSceneUI).
"""
import importlib
import pkgutil

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
