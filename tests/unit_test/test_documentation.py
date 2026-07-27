"""
文件的一致性測試。

寫這支測試的原因：文件曾經停在 2026-04-21，程式一路加到十六個分頁，文件卻只
描述其中八個，還列了兩個早就不存在的分頁（CHAT、IMAGE GENERATION）。缺頁至少
還看得出來是缺；寫錯的頁面則會誤導人。

現在有七種語言的文件樹，很容易變成「只在英文版加了一頁」。這裡守住三件事：
七棵樹的頁面集合一致、引用的圖片真的存在、以及文件不再提到已經移除的功能。

Documentation consistency.

This exists because the documentation sat at 2026-04-21 while the application
grew to sixteen tabs: it described eight of them and listed two that no longer
existed (CHAT, IMAGE GENERATION). A missing page at least reads as missing; a
wrong one misleads.

With seven language trees it is easy to add a page in English only. Three
things are pinned here: the trees carry the same pages, every referenced image
is really there, and nothing describes a feature that has been removed.
"""
import re
from pathlib import Path
from typing import Dict, Set

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs" / "source" / "docs"
# 只有 Eng / Zh 有貢獻者文件，其餘語言的 index 會指向英文版
CONTRIBUTOR = {"how_to_extend_ui", "release_process"}
REMOVED = ["CHAT (Chat", "IMAGE GENERATION", "Crosshair", "Teleprompter", "Soundboard"]


def _trees() -> Dict[str, Set[str]]:
    return {directory.name: {path.stem for path in directory.glob("*.rst")}
            for directory in sorted(DOCS.iterdir())
            if directory.is_dir() and directory.name != "image"}


def _content_pages(pages: Set[str]) -> Set[str]:
    return {name for name in pages
            if not name.endswith("_index") and name not in CONTRIBUTOR}


def test_the_application_languages_all_have_documentation() -> None:
    """介面支援的語言，文件也要有一棵樹。"""
    assert set(_trees()) == {"Eng", "Zh", "ZhCn", "De", "Ru", "Fr", "It"}


@pytest.mark.parametrize("language", sorted(set(_trees()) - {"Eng"}))
def test_every_language_carries_the_same_pages(language: str) -> None:
    trees = _trees()
    expected = _content_pages(trees["Eng"])
    actual = _content_pages(trees[language])
    assert actual == expected, f"{language} differs: {sorted(actual ^ expected)}"


@pytest.mark.parametrize("language", sorted(_trees()))
def test_every_tree_has_exactly_one_index(language: str) -> None:
    indexes = [name for name in _trees()[language] if name.endswith("_index")]
    assert len(indexes) == 1, f"{language}: {indexes}"


def test_the_top_level_index_lists_every_language() -> None:
    top = (DOCS.parent / "index.rst").read_text(encoding="utf-8")
    for language in _trees():
        assert f"docs/{language}/" in top, f"{language} is not linked from the top index"


def test_every_referenced_image_exists() -> None:
    """
    Sphinx 對缺少的圖片只給警告，頁面照樣產出，但讀者看到的是一個破圖。
    Sphinx only warns about a missing image and still emits the page, so the
    reader is the one who finds the broken box.
    """
    missing = []
    for path in DOCS.rglob("*.rst"):
        for reference in re.findall(r"\.\. image:: (\S+)", path.read_text(encoding="utf-8")):
            if not (path.parent / reference).resolve().exists():
                missing.append(f"{path.name} -> {reference}")
    assert not missing, f"referenced but not present: {missing}"


@pytest.mark.parametrize("removed", REMOVED)
def test_nothing_documents_a_feature_that_was_removed(removed: str) -> None:
    """
    寫錯比沒寫更糟：文件曾經長年列著兩個不存在的分頁。
    A wrong page is worse than a missing one: the docs listed two tabs that had
    not existed for a long time.
    """
    guilty = [str(path.relative_to(DOCS)) for path in DOCS.rglob("*.rst")
              if removed in path.read_text(encoding="utf-8")]
    assert not guilty, f"{removed!r} still documented in: {guilty}"


def test_the_underlines_are_long_enough() -> None:
    """
    底線太短 docutils 每頁抱怨一次；十八頁乘七種語言就是一整牆的警告。
    中日韓字元佔兩格，所以量的是顯示寬度而不是字元數。
    """
    import unicodedata

    def width(text: str) -> int:
        return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)

    short = []
    for path in DOCS.rglob("*.rst"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index in range(1, len(lines)):
            line, previous = lines[index].strip(), lines[index - 1].rstrip()
            if (len(line) >= 2 and len(set(line)) == 1 and line[0] in "-=~^"
                    and previous and not previous.startswith((".. ", "* ", "  "))
                    and len(line) < width(previous)):
                short.append(f"{path.name}:{index + 1}")
    assert not short, f"title underline too short: {short[:8]}"
