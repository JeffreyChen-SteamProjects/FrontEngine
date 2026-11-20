"""Fail when a commit added between two revisions carries AI attribution.

CLAUDE.md (Git workflow, Authorship): commits are authored by the developer and never name an AI
tool or assistant, neither in the message nor in a Co-Authored-By trailer. Twenty commits from
2026-10-29/30 still carry one; rewriting the published history was decided against, so CI checks
only what each push or pull request adds.

    python tools/check_commit_attribution.py <base sha> <head sha>

Both arguments must be commit hashes. A base of all zeros (a branch that did not exist before the
push) checks the head commit alone.
"""
from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - only runs git, resolved to an absolute path, with a fixed argv
import sys
from typing import Callable, Dict, List

ATTRIBUTION = re.compile(
    r"^\s*co-authored-by:.*\b(claude|anthropic|openai|chatgpt|copilot|gemini)\b"
    r"|generated with \[?(claude|chatgpt|copilot)"
    r"|noreply@anthropic\.com",
    re.IGNORECASE)

_RECORD, _FIELD = "\x1e", "\x00"
_SHA = re.compile(r"[0-9a-fA-F]{4,64}")


def offending_lines(message: str) -> List[str]:
    """The lines of one commit message that attribute it to an AI tool."""
    return [line.strip() for line in message.splitlines() if ATTRIBUTION.search(line)]


def commit_messages(base: str, head: str, run: Callable[[List[str]], str]) -> Dict[str, str]:
    """Message of every commit in base..head (head alone when base is all zeros), keyed by hash."""
    for revision in (base, head):
        if not _SHA.fullmatch(revision):
            raise ValueError(f"not a commit hash: {revision!r}")
    revisions = [head, "-1"] if not base.strip("0") else [f"{base}..{head}"]
    # git expands %x00/%x1e itself; a raw NUL cannot travel in a command-line argument.
    output = run(["log", "--format=%H%x00%B%x1e", *revisions])
    messages = {}
    for record in output.split(_RECORD):
        if _FIELD in record:
            sha, message = record.split(_FIELD, 1)
            messages[sha.strip()] = message
    return messages


def _git(arguments: List[str]) -> str:
    """Run git with arguments built by commit_messages (validated hashes only)."""
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is not on PATH")
    argv = [git, *arguments]
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", check=True, shell=False).stdout  # nosec B603 # nosemgrep - absolute git path, argv of validated hashes, shell=False


def main(argv: List[str], run: Callable[[List[str]], str] = _git) -> int:
    if len(argv) != 2 or not all(_SHA.fullmatch(value) for value in argv):
        print(__doc__)
        return 2
    found = {sha: lines for sha, message in commit_messages(*argv, run).items()
             if (lines := offending_lines(message))}
    for sha, lines in found.items():
        for line in lines:
            print(f"{sha[:12]}: {line}")
    if found:
        print(f"{len(found)} commit(s) carry AI attribution; reword them before merging "
              "(CLAUDE.md, Authorship).")
        return 1
    print("No AI attribution in the new commits.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
