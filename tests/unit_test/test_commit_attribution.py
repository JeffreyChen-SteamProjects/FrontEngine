"""CI rejects AI attribution in new commit messages (CLAUDE.md, Authorship)."""
import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "tools" / "check_commit_attribution.py"
_SPEC = importlib.util.spec_from_file_location("check_commit_attribution", _PATH)
check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check)


@pytest.mark.parametrize("line", [
    "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
    "co-authored-by: Claude <someone@example.com>",
    "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
    "Co-authored-by: GitHub Copilot <copilot@github.com>",
])
def test_attribution_is_found(line):
    assert check.offending_lines(f"Fix a thing\n\nWhy it was broken.\n\n{line}\n") == [line.strip()]


@pytest.mark.parametrize("message", [
    "Update CLAUDE.md with the release rules",
    "Explain the Anthropic model ids in the API notes",
    "Bump nuitka\n\nCo-authored-by: dependabot[bot] <support@github.com>",
    "Pair on the pet walk\n\nCo-Authored-By: A Teammate <teammate@example.com>",
])
def test_ordinary_messages_pass(message):
    assert check.offending_lines(message) == []


def _fake_git(log_output, calls):
    def run(arguments):
        calls.append(arguments)
        return log_output
    return run


BASE, HEAD = "1" * 40, "2" * 40


def test_only_the_new_range_is_checked_and_offenders_fail_the_job(capsys):
    log = ("a" * 40 + "\x00Clean commit\n\x1e\n"
           + "b" * 40 + "\x00Tainted\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n\x1e\n")
    calls = []
    assert check.main([BASE, HEAD], run=_fake_git(log, calls)) == 1
    assert calls[0][-1] == f"{BASE}..{HEAD}"
    output = capsys.readouterr().out
    assert "bbbbbbbbbbbb: Co-Authored-By: Claude <noreply@anthropic.com>" in output
    assert "aaaaaaaaaaaa" not in output


def test_a_clean_range_passes_and_a_new_branch_checks_its_head_alone():
    calls = []
    assert check.main(["0" * 40, HEAD], run=_fake_git("c" * 40 + "\x00Clean\n\x1e\n", calls)) == 0
    assert calls[0][-2:] == [HEAD, "-1"]


@pytest.mark.parametrize("arguments", [
    ["HEAD~1", HEAD], [BASE, "--output=/tmp/x"], [BASE, f"{HEAD};rm"], [BASE],
])
def test_anything_but_two_commit_hashes_is_refused_without_running_git(arguments):
    calls = []
    assert check.main(arguments, run=_fake_git("", calls)) == 2
    assert calls == []
