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

That workflow:

1. validates the requested `vMAJOR.MINOR.PATCH` tag against `pyproject.toml`,
   `spectralbridge.__version__`, `CITATION.cff`, and the first versioned
   changelog heading
2. runs Ruff, the full test suite, strict docs/link checks, validation-evidence
   drift checks, and AI-transparency drift checks
3. builds the sdist and wheel once and runs `twine check`
4. uploads those exact bytes as one release candidate
5. installs the exact wheel outside the checkout on Python 3.10, 3.11, and 3.12
6. installs the exact sdist outside the checkout on Python 3.10
7. runs the bounded, offline, stage-complete normal, drone, and bulk smoke in
   each clean environment
8. creates the GitHub release only after every source and artifact gate passes

No workflow publishes to PyPI yet.

## Two-tier validation requirement

The release gate intentionally separates package execution from production
science:

- **Tier A — installed-artifact CI smoke:** tiny 8 × 8 fixtures, one worker,
  no network, strict disk budget, every major production stage, every release.
  It proves package wiring and orchestration.
- **Tier B — production validation:** selected real flightlines on a suitably
  provisioned large-memory VM, periodically and for release candidates. It
  provides scientific QA and operational evidence at real scale.

CI is not required to run a workflow that may need roughly 250 GB of RAM.
Fixture scale may be reduced only while retaining the same production code
paths and algorithms. See the [production validation record](production-validation-record.md).

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
python -m venv /tmp/spectralbridge-release-smoke
/tmp/spectralbridge-release-smoke/bin/python -m pip install dist/*.whl
cd /tmp
/tmp/spectralbridge-release-smoke/bin/python \
  /path/to/spectralbridge/scripts/check_installed_artifact.py \
  --expected-version MAJOR.MINOR.PATCH
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
- PyPI trusted publishing and its protected environment are not configured

PyPI publishing remains a deliberate omission so release automation does not
outpace maintainer review. The workflow creates only a fully gated GitHub
release.
