# Contributing

Thank you for your interest in improving SpectralBridge! This guide
summarizes the project conventions so that contributions are easy to review and
safe to deploy in scientific, notebook, cloud, and container workflows.

## Ways to contribute
- Report issues and pipeline regressions through
  [GitHub Issues](https://github.com/earthlab/spectralbridge/issues).
- Improve documentation, tutorials, and example notebooks.
- Add tests that increase coverage without expanding production data size.
- Triage dependency compatibility problems or OS-specific installation bugs.

## Development workflow
1. **Fork and branch**: create a feature branch for every change.
2. **Environment**: use Python 3.10+ and install from `pyproject.toml`.
   `environment.yaml` remains useful for reproducing conda-style environments,
   but Python package metadata is the publication source of truth.
3. **Editable install**: run `pip install -e ".[dev]"` or install
   `requirements-dev.txt` to get pytest, Ruff, docs, Playwright, and packaging
   check tools.
4. **Pre-commit checks**: run `ruff check src tests`, targeted pytest commands,
   and docs checks before opening a pull request.
5. **Documentation**: update MkDocs pages or docstrings when behaviour changes.
   New user-facing features must include a docs update or changelog entry.

## Versioning and releases
- We follow **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`.
- Tag releases in Git with `vMAJOR.MINOR.PATCH` (e.g., `v0.2.0`).
- Update the version in `pyproject.toml`, `src/spectralbridge/__init__.py`,
  and `CITATION.cff` as part of release preparation. `setup.py` is a
  compatibility shim only.
- Review citation metadata, release notes, and any DOI/Zenodo instructions as
  part of each release cut so software citation stays in sync with the tagged
  artifact.
- Keep `CHANGELOG.md` aligned with the package version and the release tag. Do
  not leave future release headings above the current packaged version unless
  they are clearly marked as unreleased work.
- Follow the maintainer release sequence in `docs/dev/releasing.md`. Tagged
  releases now trigger `.github/workflows/release.yml`, which builds artifacts,
  runs `twine check`, installs the built wheel, and attaches release assets to
  the GitHub release.

## Licensing and provenance
- The repository currently distributes under GPLv3. Keep `LICENSE`,
  `pyproject.toml`, `README.md`, and `CITATION.cff` consistent with the actual
  legal status of the codebase.
- Do not claim an Apache 2.0 migration is complete unless maintainers have
  finished provenance review for GPL-derived content and explicitly approved the
  license change.
- When adapting or vendoring external scientific code, preserve attribution and
  record any license implications in documentation and release notes.

## Testing guidelines
- Tests must run via `pytest` using fixture data or synthetic data generated
  inside temporary directories.
- Integration tests should rely on the minimal public sample flight line; do not
  reference private or cloud-only paths.
- When working on modules that interact with external systems such as iRODS,
  CyVerse, cloud buckets, or NEON downloads, isolate the integration points so
  local unit tests remain deterministic.
- Ray is a required dependency and the default parallel engine. Thread and
  process engines are explicit alternatives for runs that should avoid Ray
  initialization.

## Coding standards
- Follow [PEP 8](https://peps.python.org/pep-0008/) and ensure Ruff passes with
  the repository configuration.
- Use type hints for new or refactored functions where they make contracts
  clearer.
- Keep file path manipulations centralized in the existing helper modules. When
  in doubt, open an issue before changing any production path conventions.
- Keep Parquet as the authoritative tabular output. CSV files, when present, are
  convenience sidecars only.
- Avoid committing large data artifacts to active paths. Move historical or
  provenance material to `deprecated/` instead of deleting it.

## Communication
- Use GitHub Issues or Discussions for asynchronous questions.
- Flag urgent operational issues with the `priority:high` label so maintainers
  can triage quickly.
- Pull requests require at least one review from a maintainer before merging.

Thanks for helping make SpectralBridge reliable and reproducible!
