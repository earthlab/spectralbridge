# SpectralBridge Publication Checklist

> Living document for preparing the project for packaging and public release. Update
> the status boxes and notes as tasks are completed.

## 1. Package Structure & Metadata
- [x] Confirm the canonical package name (`SpectralBridge` project, `spectralbridge` package) and document legacy `cross_sensor_cal` compatibility.
- [x] Replace the minimal `setup.py` with a `pyproject.toml` using PEP 621 metadata (name, version, description, authors, URLs, keywords, classifiers). Keep `setup.py` as a compatibility shim only.
- [x] Add `__init__.py` exports and package-level documentation so users can discover public APIs easily. Common orchestration helpers are now lazy top-level exports.
- [x] Decide on versioning scheme (CalVer or SemVer) and document it in CONTRIBUTING along with release tagging conventions.
- [ ] Keep `pyproject.toml`, `src/spectralbridge/__init__.py`, `CITATION.cff`, `CHANGELOG.md`, and the release tag synchronized for every release. *(Current audit found metadata at `2.2.0`, changelog headed by `2.3.0`, and local tags still at `0.1` / `v1.0.0`.)*
- [x] Audit repository for large data or notebooks that should be excluded from source distributions. `MANIFEST.in` excludes root staging data, deprecated archives, generated docs reports, and container-only helpers.

## 2. Dependencies & Environment
- [x] Inventory required runtime dependencies, including Ray, separately from truly optional integrations. Ray is documented as required/default.
- [x] Translate core dependencies into `pyproject.toml` dependency groups (`tests`, `docs`, `dev`, `full`) and keep `requirements-dev.txt` aligned for contributors.
- [ ] Provide a lightweight sample dataset or clearly document external data requirements so users can run example pipelines after installing from PyPI.
- [x] Add a `requirements-dev.txt` or equivalent to unify tooling for contributors (formatters, linters, docs builders).

## 3. Code Quality, Testing & Tooling
- [x] Expand automated test coverage beyond `tests/test_file_sort.py` to cover public function import/signature smoke, Ray/default engine behavior, QA, pipeline, drone, polygon, and docs browser smoke paths.
- [x] Configure continuous integration (e.g., GitHub Actions) to run unit tests, linting (ruff/flake8), type checking (mypy/pyright), and documentation builds on each push/PR. Docs CI now includes Playwright browser smoke.
- [ ] Decide whether to add Black/isort. Ruff is installed, documented, and run in CI.
- [ ] Evaluate adding type hints and optional static typing checks to critical modules for maintainability.
- [x] Ensure `pytest` configuration (`pyproject.toml`/`pytest.ini`) ignores heavyweight data paths and sets up necessary environment variables for tests.

## 4. Documentation & Community Files
- [x] Finish filling placeholders in `README.md`, `CITATION.cff`, and MkDocs pages. Include feature overview, supported sensors, and end-to-end workflow diagrams.
- [ ] Verify that documentation builds cleanly with `mkdocs build` and publish instructions (`mkdocs gh-deploy` or Read the Docs) as part of release workflow.
- [x] Add usage examples demonstrating both library API calls and CLI entry points, ideally with runnable Jupyter notebooks linked from docs.
- [ ] Update `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (create if missing), and issue/PR templates to guide external contributors once the package is public. *(Contributing guide and Code of Conduct refreshed; templates still needed.)*
- [x] Provide citation and acknowledgement guidance consistent across README, docs, and metadata.
- [x] Add a maintainer-facing publication and software-citation tracker. `docs/dev/software-citation.md` now records preferred citation language, versioned release citation policy, and publication placeholders.

## 5. Distribution Artifacts & QA
- [ ] Run `python -m build` to generate sdist/wheel and inspect contents (ensure no unnecessary files, confirm console scripts are installed).
- [ ] Execute `twine check dist/*` to validate metadata and `pip install dist/*.whl` in a clean virtual environment for smoke tests.
- [x] Document hardware/software prerequisites (GDAL, PROJ) and include troubleshooting tips for installation on Linux/macOS/Windows.
- [ ] Automate changelog generation (`CHANGELOG.md`) per release with notable features and breaking changes.
- [x] Establish release checklist (tagging, GitHub release notes, PyPI upload) and capture in this document or `RELEASING.md`. `docs/dev/releasing.md` now documents the maintainer sequence, and `.github/workflows/release.yml` packages tagged releases and publishes GitHub release artifacts.
- [ ] Verify the Zenodo release record after each GitHub release (title, version, DOI target, and badge target). See `docs/dev/doi-zenodo.md`.

## 6. Licensing & Governance
- [ ] Complete a provenance/legal review before changing the repository from GPLv3 to any future Apache 2.0 target. Current repo text still references GPL-derived HyTools adaptations.
- [ ] Ensure all third-party code, data, and documentation comply with the chosen license and attribution requirements.
- [ ] Identify maintainers and add contact information/support policy in README and docs.
- [ ] Decide whether an Apache 2.0 migration is legally feasible for the current codebase or whether a future reimplementation is required for non-GPL distribution.

## 7. Post-Release Follow-up
- [ ] Monitor initial PyPI release install stats/issues and iterate on documentation gaps.
- [ ] Announce release channels (EarthLab blog, mailing lists) and track feedback for roadmap planning.
- [ ] Schedule periodic dependency and security audits (Dependabot, `pip-audit`) and plan for long-term maintenance.

---
_Last updated: 2026-06-02_
