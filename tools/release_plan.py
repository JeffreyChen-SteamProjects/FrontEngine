"""Decide what the release job publishes: a new version, or the unfinished one before it.

release.yml runs this before anything is pushed or uploaded:

    python tools/release_plan.py <patch|minor|major>

A release is finished once its tag exists; ``gh release create`` makes the tag as the last step.
When the version in stable.toml has no tag, a previous run stopped part-way and this run finishes
that version instead of minting another one:

- ``bump``: the current version is tagged. Raise it, write stable.toml and pyproject.toml, and let
  the job commit and push the bump as before.
- ``resume``: the untagged version is already on PyPI. Rebuild the commit that bumped to it (what
  was uploaded), skip the files PyPI already has, and create the missing release and tag there.
- ``republish``: the untagged version never reached PyPI. Nothing was published under it, so it
  is released from the current main without another bump commit.

The outputs (``mode``, ``version``, ``tag``, ``sha``) go to ``$GITHUB_OUTPUT``; ``sha`` is empty
for ``bump`` because that commit does not exist yet.
"""
from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - only runs git from a fixed absolute path, with a fixed argv
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

_VERSION_LINE = re.compile(r'^(version\s*=\s*)"(\d+)\.(\d+)\.(\d+)"', re.MULTILINE)
_NAME_LINE = re.compile(r'^name\s*=\s*"([A-Za-z0-9][A-Za-z0-9._-]*)"', re.MULTILINE)
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_SHA = re.compile(r"[0-9a-f]{40}")
_BUMP_KINDS = ("patch", "minor", "major")
_GIT_CANDIDATES = ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git")
_RECORD, _FIELD = "\x1e", "\x00"

GitRunner = Callable[[List[str]], str]
PyPILookup = Callable[[str, str], bool]


@dataclass(frozen=True)
class ReleasePlan:
    mode: str
    version: str
    sha: str = ""

    @property
    def tag(self) -> str:
        return f"v{self.version}"


def read_version(text: str) -> str:
    """The ``x.y.z`` version of a metadata file's first ``version = "..."`` line."""
    match = _VERSION_LINE.search(text)
    if not match:
        raise ValueError("no semver version line found")
    return ".".join(match.group(2, 3, 4))


def read_name(text: str) -> str:
    """The project name of a metadata file."""
    match = _NAME_LINE.search(text)
    if not match:
        raise ValueError("no project name found")
    return match.group(1)


def bumped(version: str, kind: str) -> str:
    """``version`` with its ``kind`` segment raised and the lower segments reset."""
    if kind not in _BUMP_KINDS:
        raise ValueError(f"invalid bump type: {kind!r}")
    major, minor, patch = (int(part) for part in version.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def with_version(text: str, version: str) -> str:
    """``text`` with its first version line set to ``version``."""
    return _VERSION_LINE.sub(rf'\g<1>"{version}"', text, count=1)


def bump_commit(version: str, run: GitRunner) -> Optional[str]:
    """The newest commit on HEAD whose subject is the release job's bump to ``version``."""
    output = run(["log", "--format=%H%x00%s%x1e", "HEAD", "--", "stable.toml"])
    subject = re.compile(rf"^Bump version to {re.escape(version)}(\s|$)")
    for record in output.split(_RECORD):
        sha, _, message = record.strip().partition(_FIELD)
        if _SHA.fullmatch(sha) and subject.match(message):
            return sha
    return None


def tag_exists(tag: str, run: GitRunner) -> bool:
    """Whether the clone has ``refs/tags/<tag>``."""
    return bool(run(["tag", "--list", tag]).strip())


def decide(current: str, kind: str, run: GitRunner, published: PyPILookup, name: str) -> ReleasePlan:
    """Plan the release from the version in stable.toml, the tags and what PyPI already holds."""
    if tag_exists(f"v{current}", run):
        version = bumped(current, kind)
        if tag_exists(f"v{version}", run) or published(name, version):
            raise RuntimeError(f"{version} is already tagged or on PyPI; refusing to republish it")
        return ReleasePlan("bump", version)
    if published(name, current):
        sha = bump_commit(current, run)
        if sha is None:
            raise RuntimeError(f"{current} is on PyPI without a tag, and no commit bumps to it")
        return ReleasePlan("resume", current, sha)
    head = run(["rev-parse", "HEAD"]).strip()
    if not _SHA.fullmatch(head):
        raise RuntimeError(f"unexpected HEAD: {head!r}")
    return ReleasePlan("republish", current, head)


def pypi_has(name: str, version: str, opener: Callable = urllib.request.urlopen) -> bool:
    """Whether PyPI serves ``name`` at ``version``; anything but 200 or 404 is an error."""
    if not _NAME.fullmatch(name) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"refusing to look up {name!r} {version!r}")
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with opener(url, timeout=30) as response:  # nosec B310 - fixed https host, validated path
            return json.load(response).get("info", {}).get("version") == version
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def _git(arguments: List[str]) -> str:
    """Run git from a fixed absolute path with arguments built in this module."""
    git = next((path for path in _GIT_CANDIDATES if Path(path).is_file()), None)
    if git is None:
        raise RuntimeError("git not found at a known absolute path")
    return subprocess.run([git, *arguments], capture_output=True, text=True, encoding="utf-8",
                          check=True, shell=False).stdout  # nosec B603 # nosemgrep - fixed git path, fixed argv


def plan(kind: str, root: Path, run: GitRunner = _git, published: PyPILookup = pypi_has) -> ReleasePlan:
    """Plan the release in ``root`` and, for a bump, write the new version into both metadata files."""
    stable = root / "stable.toml"
    text = stable.read_text(encoding="utf-8")
    result = decide(read_version(text), kind, run, published, read_name(text))
    if result.mode == "bump":
        for path in (stable, root / "pyproject.toml"):
            if path.exists():
                path.write_text(with_version(path.read_text(encoding="utf-8"), result.version), encoding="utf-8")
    return result


def main(argv: List[str], root: Optional[Path] = None, run: GitRunner = _git,
         published: PyPILookup = pypi_has) -> int:
    if len(argv) != 1 or argv[0] not in _BUMP_KINDS:
        print(__doc__)
        return 2
    result = plan(argv[0], root or Path.cwd(), run, published)
    lines = [f"mode={result.mode}", f"version={result.version}", f"tag={result.tag}", f"sha={result.sha}"]
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("".join(f"{line}\n" for line in lines))
    print("\n".join(lines))
    if result.mode != "bump":
        print(f"::notice::{result.tag} was not finished; finishing it ({result.mode}) instead of bumping again.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
