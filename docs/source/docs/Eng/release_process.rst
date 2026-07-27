Release Process
---------------

FrontEngine is published to PyPI as ``frontengine`` whenever a pull request is
merged into ``main``. Development work happens on the ``dev`` branch and is
released by opening and merging a pull request targeting ``main``.

Continuous integration and publishing are driven by two GitHub Actions
workflows that live in ``.github/workflows/``.

Workflows
=========

* ``ci.yml`` — *CI*

  * Runs on pushes and pull requests to ``main`` and ``dev`` and once a day on
    schedule.
  * Matrix-tests Python 3.10, 3.11 and 3.12 on ``windows-latest``.
  * Compiles every module under ``frontengine/`` and launches the two GUI
    smoke scripts in ``tests/unit_test/start/``.

* ``release.yml`` — *Release*

  * Runs only when a pull request is **merged** into ``main`` (a closed-but-
    unmerged pull request will not trigger a release). The workflow can also
    be re-run manually via ``workflow_dispatch`` — the manual trigger takes a
    ``bump`` input (``patch`` / ``minor`` / ``major``, default ``patch``).
  * **Before** building or uploading, the workflow reads the current
    ``version`` field from ``stable.toml``, bumps the selected segment (the
    PR-merged trigger always does a patch bump), writes the new version back
    to ``stable.toml`` and ``pyproject.toml``, and commits that change to
    ``main`` with ``[skip ci]`` in the commit message so it doesn't trigger
    CI on itself.
  * Then it copies ``stable.toml`` over ``pyproject.toml``, builds an sdist
    and wheel, verifies them with ``twine check``, uploads them to PyPI as
    ``frontengine`` using ``twine upload``, and creates a GitHub release
    tagged ``v<new-version>`` with the built distributions attached.
  * If the computed tag somehow already exists the workflow aborts before
    touching PyPI, so a run can never republish an existing version.

Cutting a release
=================

1. Merge a pull request into ``main``. The patch segment bumps automatically.
2. The workflow publishes to PyPI and creates the GitHub release in one run.

For a minor or major bump — or to re-run a failed publish without cutting a
fresh PR — trigger the workflow manually via **Actions → Release → Run
workflow** and pick the ``bump`` segment.

Required secrets
================

Configure this as a repository secret:

* ``PYPI_API_TOKEN`` — a PyPI API token scoped to the ``frontengine`` project.

The workflow uses ``__token__`` as the twine username, so only the token
itself needs to be stored. Pushing the version-bump commit back to ``main``
uses the default ``GITHUB_TOKEN`` that GitHub Actions provides automatically.
