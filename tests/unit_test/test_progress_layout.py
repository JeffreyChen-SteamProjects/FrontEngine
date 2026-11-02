"""
progress.md layout: real-device acceptance lives only in the top section.

Acceptance paragraphs used to be scattered through the plan sections, so
nobody could see in one place what still needed a real machine, a person or
hardware. The header of progress.md states the rule; this test holds it:
the first section is the acceptance list, no later section is about
acceptance, and no to-do line below it asks for real-device verification.
"""
from pathlib import Path
from typing import List, Tuple

PROGRESS = Path(__file__).resolve().parents[2] / "progress.md"
TOP = "## 實機驗收待辦"
# Words that mark an item as needing a real machine or a person to verify.
ACCEPTANCE_WORDS = ("實機", "驗收", "real device", "acceptance")


def _sections() -> List[Tuple[str, List[str]]]:
    sections: List[Tuple[str, List[str]]] = []
    for line in PROGRESS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            sections.append((line.strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return sections


def test_acceptance_section_comes_first() -> None:
    sections = _sections()
    assert sections, "progress.md has no sections"
    assert sections[0][0] == TOP


def test_header_states_the_rule() -> None:
    header = PROGRESS.read_text(encoding="utf-8").split(TOP)[0]
    assert "實機驗收只能放在最上方" in header


def test_no_acceptance_outside_the_top_section() -> None:
    offenders = []
    for title, lines in _sections()[1:]:
        if any(word in title.lower() for word in ACCEPTANCE_WORDS):
            offenders.append(title)
        for line in lines:
            item = line.lstrip()
            if not item.startswith("-"):
                continue  # prose pointers such as "acceptance goes above" are fine
            if any(word in item.lower() for word in ACCEPTANCE_WORDS):
                offenders.append(f"{title}: {item[:60]}")
    assert not offenders, "move these to the top acceptance section: " + "; ".join(offenders)


def test_only_one_acceptance_section() -> None:
    titles = [title for title, _ in _sections()]
    assert titles.count(TOP) == 1
