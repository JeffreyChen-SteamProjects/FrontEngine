Release Process
----

FrontEngine ships two PyPI packages from a single source tree:

* ``frontengine`` — the stable release, published from the ``main`` branch.
* ``frontengine_dev`` — the development preview, published from the ``dev`` branch.

Continuous integration and publishing are driven by three GitHub Actions
workflows that live in ``.github/workflows/``.

Workflows
====

* ``ci.yml`` — *CI*

  * Runs on pushes and pull requests to ``main`` and ``dev`` and once a day on
    schedule.
  * Matrix-tests Python 3.10, 3.11 and 3.12 on ``windows-latest``.
  * Compiles every module under ``frontengine/`` and launches the two GUI
    smoke scripts in ``tests/unit_test/start/``.

* ``release-dev.yml`` — *Release Dev*

  * Runs on pushes to ``dev`` or via manual dispatch.
  * Reads the version from ``pyproject.toml`` and computes the tag
    ``dev-v<version>``.
  * If the tag already exists the job is a no-op; otherwise it builds an sdist
    and wheel, verifies them with ``twine check``, uploads them to PyPI as
    ``frontengine_dev`` using ``twine upload``, and creates a GitHub
    **prerelease** whose assets are the built distributions.

* ``release-stable.yml`` — *Release Stable*

  * Runs on pushes to ``main`` or via manual dispatch.
  * Copies ``stable.toml`` over ``pyproject.toml`` so the build uses the
    stable project metadata, then follows the same build/check/upload/release
    steps as the dev workflow.
  * The produced tag is ``v<version>`` and the release is marked as a normal
    (non-prerelease) release.

Cutting a release
====

1. Bump the ``version`` field inside ``pyproject.toml`` (for dev) or
   ``stable.toml`` (for stable).
2. Commit and push to the matching branch.
3. The corresponding release workflow starts automatically.

Because both release workflows refuse to re-use an existing tag, day-to-day
pushes that don't touch the version field are safe: the job runs, sees the
tag, and exits without republishing.

Required secrets
====

Configure these as repository secrets:

* ``PYPI_DEV_API_TOKEN`` — a PyPI API token scoped to the ``frontengine_dev``
  project, used by ``release-dev.yml``.
* ``PYPI_STABLE_API_TOKEN`` — a PyPI API token scoped to the ``frontengine``
  project, used by ``release-stable.yml``.

Both workflows use ``__token__`` as the twine username, so only the token
itself needs to be stored.
