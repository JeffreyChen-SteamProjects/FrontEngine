"""Every GitHub Actions step pins its action to a commit SHA.

A tag such as ``@v4`` can be moved to new code at any time (the 2025
tj-actions/changed-files compromise rewrote tags), so each ``uses:`` names a
full 40-hex commit and carries the release it corresponds to as a comment,
which is what Dependabot reads and updates. Pinning also keeps Node 20 actions
from lingering unnoticed: GitHub removed Node 20 from its runners on 2026-09-23.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".github" / "workflows").is_dir())
_WORKFLOWS = sorted((_ROOT / ".github" / "workflows").glob("*.yml"))
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$")
_PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
_LOCAL = re.compile(r"^\./")
_VERSION_COMMENT = re.compile(r"^\s+#\s*v\d+(\.\d+)*\s*$")


def _uses(path: Path) -> list[tuple[int, str, str]]:
    """Return ``(line number, action reference, rest of line)`` for each remote ``uses:``."""
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = _USES.match(line)
        if match and not _LOCAL.match(match.group(1)):
            found.append((number, match.group(1), match.group(2)))
    return found


def test_workflows_exist():
    assert _WORKFLOWS


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit_with_its_version(workflow):
    bad = [f"{workflow.name}:{number} {ref}{rest}"
           for number, ref, rest in _uses(workflow)
           if not (_PINNED.match(ref) and _VERSION_COMMENT.match(rest))]
    assert bad == []


def test_one_version_per_action():
    # The same action at two different commits means a partial upgrade.
    seen: dict[str, set[str]] = {}
    for workflow in _WORKFLOWS:
        for _number, ref, _rest in _uses(workflow):
            action, _, sha = ref.partition("@")
            seen.setdefault(action, set()).add(sha)
    assert {action: shas for action, shas in seen.items() if len(shas) > 1} == {}


def test_dependabot_keeps_pins_current_on_dev():
    # Pinned SHAs only stay current if something bumps them; every update
    # goes to dev because main is the release branch. Parsed as text: PyYAML
    # is not a test dependency.
    text = (_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    blocks = re.split(r"^\s*-\s*package-ecosystem:", text, flags=re.MULTILINE)[1:]
    ecosystems = {block.split()[0].strip("\"'") for block in blocks}
    assert {"pip", "github-actions"} <= ecosystems
    assert all(re.search(r"^\s*target-branch:\s*\"dev\"", block, re.MULTILINE)
               for block in blocks)


def _checkout_steps(path: Path) -> list[tuple[int, str]]:
    """Return ``(line number, step text)`` for each ``actions/checkout`` step."""
    lines = path.read_text(encoding="utf-8").splitlines()
    steps = []
    for index, line in enumerate(lines):
        if not re.search(r"uses:\s*actions/checkout@", line):
            continue
        column = line.index("uses:")
        body = [line]
        for following in lines[index + 1:]:
            indent = len(following) - len(following.lstrip())
            if following.strip() and (indent < column or following.lstrip().startswith("- ")):
                break
            body.append(following)
        steps.append((index + 1, "\n".join(body)))
    return steps


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_every_checkout_decides_on_persisted_credentials(workflow):
    # actions/checkout leaves the job token in .git/config unless told not
    # to, where every later step (and any uploaded workspace) can read it.
    # Only jobs that push keep it, and they say so.
    bad = [f"{workflow.name}:{number}" for number, step in _checkout_steps(workflow)
           if not re.search(r"^\s*persist-credentials:\s*(true|false)\b", step, re.MULTILINE)]
    assert bad == []
