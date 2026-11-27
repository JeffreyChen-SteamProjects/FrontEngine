"""The release job finishes an unfinished version instead of minting another one (tools/release_plan.py)."""
import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "tools" / "release_plan.py"
_SPEC = importlib.util.spec_from_file_location("release_plan", _PATH)
release_plan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = release_plan  # dataclasses look their module up there
_SPEC.loader.exec_module(release_plan)

OLD_BUMP, NEW_BUMP, HEAD = "a" * 40, "b" * 40, "c" * 40


class FakeRepo:
    """The git state the planner reads: tags, bump commits on stable.toml (newest first) and HEAD."""

    def __init__(self, tags, bumps, head=HEAD):
        self.tags, self.bumps, self.head = set(tags), list(bumps), head

    def __call__(self, arguments):
        if arguments[:2] == ["tag", "--list"]:
            return f"{arguments[2]}\n" if arguments[2] in self.tags else ""
        if arguments[0] == "log":
            return "".join(f"{sha}\x00Bump version to {version} [skip ci]\x1e\n" for sha, version in self.bumps)
        if arguments == ["rev-parse", "HEAD"]:
            return f"{self.head}\n"
        raise AssertionError(f"unexpected git call: {arguments}")


def _pypi(versions):
    return lambda name, version: name == "frontengine" and version in versions


def _project(root, version):
    (root / "stable.toml").write_text(f'[project]\nname = "frontengine"\nversion = "{version}"\n', encoding="utf-8")
    (root / "pyproject.toml").write_text(f'[project]\nname = "frontengine_dev"\nversion = "{version}"\n',
                                         encoding="utf-8")


def _versions(root):
    return [release_plan.read_version((root / name).read_text(encoding="utf-8"))
            for name in ("stable.toml", "pyproject.toml")]


def test_a_finished_release_is_bumped(tmp_path):
    _project(tmp_path, "1.0.100")
    repo = FakeRepo({"v1.0.100"}, [(OLD_BUMP, "1.0.100")])
    result = release_plan.plan("patch", tmp_path, repo, _pypi({"1.0.100"}))
    assert (result.mode, result.version, result.tag, result.sha) == ("bump", "1.0.101", "v1.0.101", "")
    assert _versions(tmp_path) == ["1.0.101", "1.0.101"]


def test_a_rerun_after_the_upload_but_before_the_release_reuses_the_version(tmp_path):
    _project(tmp_path, "1.0.100")
    repo = FakeRepo({"v1.0.100"}, [(OLD_BUMP, "1.0.100")])
    pypi = {"1.0.100"}
    first = release_plan.plan("patch", tmp_path, repo, _pypi(pypi))
    # The first attempt pushes its bump commit and uploads to PyPI, then gh release create fails: no tag.
    repo.bumps.insert(0, (NEW_BUMP, first.version))
    pypi.add(first.version)

    rerun = release_plan.plan("patch", tmp_path, repo, _pypi(pypi))

    assert (rerun.mode, rerun.version, rerun.sha) == ("resume", "1.0.101", NEW_BUMP)
    assert _versions(tmp_path) == ["1.0.101", "1.0.101"]


def test_a_rerun_before_the_upload_releases_the_bumped_version_from_main(tmp_path):
    _project(tmp_path, "1.0.101")
    repo = FakeRepo({"v1.0.100"}, [(NEW_BUMP, "1.0.101"), (OLD_BUMP, "1.0.100")])
    result = release_plan.plan("minor", tmp_path, repo, _pypi({"1.0.100"}))
    assert (result.mode, result.version, result.sha) == ("republish", "1.0.101", HEAD)
    assert _versions(tmp_path) == ["1.0.101", "1.0.101"]


def test_a_bump_onto_a_published_version_is_refused(tmp_path):
    _project(tmp_path, "1.0.100")
    repo = FakeRepo({"v1.0.100"}, [(OLD_BUMP, "1.0.100")])
    with pytest.raises(RuntimeError, match="1.0.101"):
        release_plan.plan("patch", tmp_path, repo, _pypi({"1.0.100", "1.0.101"}))
    assert _versions(tmp_path) == ["1.0.100", "1.0.100"]


def test_an_untagged_published_version_without_its_bump_commit_is_refused(tmp_path):
    _project(tmp_path, "1.0.101")
    repo = FakeRepo({"v1.0.100"}, [(OLD_BUMP, "1.0.100")])
    with pytest.raises(RuntimeError, match="no commit bumps"):
        release_plan.plan("patch", tmp_path, repo, _pypi({"1.0.101"}))


@pytest.mark.parametrize(("kind", "expected"), [("patch", "1.4.10"), ("minor", "1.5.0"), ("major", "2.0.0")])
def test_bumped(kind, expected):
    assert release_plan.bumped("1.4.9", kind) == expected


def test_bump_commit_needs_the_exact_version():
    repo = FakeRepo((), [(NEW_BUMP, "1.0.101"), (OLD_BUMP, "1.0.10")])
    assert release_plan.bump_commit("1.0.10", repo) == OLD_BUMP
    assert release_plan.bump_commit("1.0.1", repo) is None


def test_main_writes_the_plan_to_the_step_outputs(tmp_path, monkeypatch):
    _project(tmp_path, "1.0.101")
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    repo = FakeRepo({"v1.0.100"}, [(NEW_BUMP, "1.0.101")])
    assert release_plan.main(["patch"], tmp_path, repo, _pypi({"1.0.101"})) == 0
    assert output.read_text(encoding="utf-8").splitlines() == [
        "mode=resume", "version=1.0.101", "tag=v1.0.101", f"sha={NEW_BUMP}"]
    assert release_plan.main(["sideways"], tmp_path, repo, _pypi(set())) == 2


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener(status, payload=None):
    def opener(url, timeout):
        assert url == "https://pypi.org/pypi/frontengine/1.0.101/json" and timeout
        if status != 200:
            raise urllib.error.HTTPError(url, status, "status", {}, None)
        return _Response(json.dumps(payload).encode())
    return opener


def test_pypi_lookup():
    assert release_plan.pypi_has("frontengine", "1.0.101", _opener(200, {"info": {"version": "1.0.101"}}))
    assert not release_plan.pypi_has("frontengine", "1.0.101", _opener(404))
    with pytest.raises(urllib.error.HTTPError):
        release_plan.pypi_has("frontengine", "1.0.101", _opener(503))
    with pytest.raises(ValueError):
        release_plan.pypi_has("frontengine/../x", "1.0.101", _opener(200))
