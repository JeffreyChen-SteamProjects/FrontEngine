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


def test_requirements_agree_with_the_packaged_dependencies() -> None:
    """
    requirements.txt 必須和 pyproject.toml 的 dependencies 說同一件事。
    先前 requirements 釘 PySide6 6.8.2.1、pyproject 釘 6.10.2，兩份互相矛盾，
    照著 README 安裝的人拿到的環境和實際發佈的套件不一樣。

    requirements.txt has to say the same thing as pyproject.toml's dependencies.
    They used to disagree - 6.8.2.1 against 6.10.2 - so anyone following the
    README got an environment unlike the one that actually ships.
    """
    import tomllib

    root = Path(frontengine.__file__).parent.parent
    with (root / "pyproject.toml").open("rb") as handle:
        declared = tomllib.load(handle)["project"]["dependencies"]

    listed = [line.strip() for line in (root / "requirements.txt").read_text(
        encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

    def name_of(requirement: str) -> str:
        for separator in ("==", ">=", "<=", "~=", ">", "<"):
            if separator in requirement:
                return requirement.split(separator)[0].strip().lower()
        return requirement.strip().lower()

    assert {name_of(item) for item in listed} == {name_of(item) for item in declared}
    pinned = {item for item in declared if "==" in item}
    for requirement in pinned:
        assert requirement in listed, f"{requirement} is pinned differently in requirements.txt"


def test_requirements_do_not_install_frontengine_itself() -> None:
    """
    requirements.txt 不該列 frontengine：那會把 PyPI 上的版本裝進來蓋掉工作目錄，
    測試就會在測已發佈的版本而不是眼前的程式碼（CI 曾經因此完全沒發現打包壞掉）。

    requirements.txt must not list frontengine: that installs the published
    build over the working tree, so checks end up validating the release rather
    than the code in front of them - which is exactly how a packaging break went
    unnoticed.
    """
    root = Path(frontengine.__file__).parent.parent
    for name in ("requirements.txt", "dev_requirements.txt"):
        lines = [line.strip().lower() for line in (root / name).read_text(
            encoding="utf-8").splitlines()]
        assert "frontengine" not in lines, f"{name} must not install frontengine itself"
