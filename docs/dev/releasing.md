# Releasing SpectralBridge

This page documents the current maintainer release process for SpectralBridge.
It is intentionally conservative: the workflow automates packaging and GitHub
release creation for version tags, but it does not attempt to publish to PyPI
or rewrite project metadata automatically.

Review date: 2026-06-03

## What is automated now

The repository now includes a tag-driven GitHub Actions workflow:

- workflow file: `.github/workflows/release.yml`
- trigger: push a tag matching `vMAJOR.MINOR.PATCH`
- manual fallback: `workflow_dispatch` with a `release_tag` input

That workflow currently:

1. checks out the tagged revision
2. builds `sdist` and wheel artifacts with `python -m build`
3. runs `python -m twine check dist/*`
4. installs the built wheel and imports `spectralbridge`
5. uploads the built artifacts to the workflow run
6. creates or updates the GitHub release and attaches the built artifacts
7. enables GitHub-generated release notes

## What is still manual

Maintainers still need to:

- synchronize version metadata before tagging
- review and curate `CHANGELOG.md`
- review GitHub-generated release notes
- verify `CITATION.cff`
- verify the Zenodo record after the GitHub release
- decide separately whether and how to publish to PyPI

## Pre-release checklist

Before cutting a release, verify all of the following together:

1. `pyproject.toml`
2. `src/spectralbridge/__init__.py`
3. `CITATION.cff`
4. `CHANGELOG.md`
5. `README.md` citation/release references if needed
6. the intended release tag, using `vMAJOR.MINOR.PATCH`

Also confirm:

- CI is green on `main`
- docs links still validate
- any release-critical docs updates are merged
- the changelog entry is not left as a future-looking unreleased section by
  accident

## Recommended release sequence

1. update version metadata and changelog
2. review `CITATION.cff` author, version, and repository information
3. run local release checks if the environment supports them:

```bash
python -m build
python -m twine check dist/*
pip install dist/*.whl
python -c "import spectralbridge; print(spectralbridge.__version__)"
```

4. commit the release-prep changes
5. create and push the tag:

```bash
git tag vMAJOR.MINOR.PATCH
git push origin vMAJOR.MINOR.PATCH
```

6. confirm `.github/workflows/release.yml` succeeds
7. review the generated GitHub release title, notes, and attached artifacts
8. confirm Zenodo archives the release and that the DOI target remains correct
9. if the project is publishing to PyPI for that release, do so only after the
   build artifacts and metadata have been verified

## Changelog and release-note guidance

Use `CHANGELOG.md` as the curated human summary and GitHub release notes as the
automation-backed supplement.

Recommended changelog sections:

- `Added`
- `Changed`
- `Fixed`
- `Deprecated`
- `Docs`

Recommended release-note review points:

- scientific workflow changes are described accurately
- no internal-only cleanup dominates the release summary
- compatibility notes are visible when imports, CLIs, or output contracts are
  affected
- citation and release links point at the correct repository identity

## Citation and DOI refresh

For every tagged release, check:

1. `CITATION.cff` version matches the tag
2. the GitHub release points at the correct repository version
3. Zenodo has archived the tag correctly
4. the README DOI badge still reflects the maintainers' intended target

If Zenodo mints a new post-rename SpectralBridge record, update the repository
documentation consistently rather than changing only the badge.

## Current limits

- no automatic PyPI publish is configured in this repository
- no automatic changelog rewriting is configured
- no automatic version bumping is configured
- no release-blocking metadata sync test exists yet

Those are deliberate omissions for now so release automation does not outpace
maintainer review.
