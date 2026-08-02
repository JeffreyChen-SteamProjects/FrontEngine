Release Process
---------------

Work flows ``feature -> dev -> main``, and only the last step publishes::

    feat/xyz  --PR-->  dev  --PR-->  main
                        |              |
                  CI, no release   CI + release

Features branch off ``dev`` and merge back into it, which runs CI and mints
nothing. A release is a deliberate pull request from ``dev`` to ``main``:
merging that is the only thing that publishes FrontEngine to PyPI as
``frontengine``.

Continuous integration and publishing are driven by three GitHub Actions
workflows that live in ``.github/workflows/``.

Workflows
=========

* ``ci.yml`` — *CI*

  * Runs on pushes and pull requests to ``main`` and ``dev``, on demand via
    **Actions -> CI -> Run workflow**, and once a day through ``nightly.yml``.
    The manual trigger matters because ``[skip ci]`` commits - the version
    bump among them - otherwise leave a branch with no CI record and no way
    to ask for one.
  * Matrix-tests Python 3.10, 3.11 and 3.12 on ``windows-latest``.
  * Compiles every module under ``frontengine/`` and launches the two GUI
    smoke scripts in ``tests/unit_test/start/``.

* ``release.yml`` — *Release*

  * Runs only when a pull request **from** ``dev`` is **merged** into ``main``.
    A closed-but-unmerged pull request does not release, and neither does a
    feature branch merged straight into ``main`` - that still merges, it just
    mints no version, and a later ``dev -> main`` picks it up. The failure
    direction is a missing release rather than an unwanted one. The workflow
    can also be re-run manually via ``workflow_dispatch`` — the manual trigger
    takes a ``bump`` input (``patch`` / ``minor`` / ``major``, default
    ``patch``).
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
  * Finally it fast-forwards ``dev`` to the released commit, so the next round
    does not start a commit behind. This is best effort: if someone pushed to
    ``dev`` mid-release it warns instead of failing a release that already
    published, and ``git push origin main:dev`` finishes the job.

Cutting a release
=================

1. Merge the features you want to ship into ``dev``. Nothing is published.
2. Open a pull request from ``dev`` to ``main`` and merge it. The patch
   segment bumps automatically.
3. The workflow publishes to PyPI, creates the GitHub release, and
   fast-forwards ``dev`` — all in one run.

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
