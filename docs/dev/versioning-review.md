# Versioning Review

Review date: 2026-06-03

This note records the current versioning and release-state audit for
SpectralBridge. It is intended to reduce version drift across package metadata,
citations, changelog entries, and Git tags.

## Version sources reviewed

- `pyproject.toml`
- `src/spectralbridge/__init__.py`
- `CITATION.cff`
- `CHANGELOG.md`
- local Git tags
- `CONTRIBUTING.md`
- `publication_checklist.md`

## Current state

### Package metadata

The current packaged version is consistent across the main code-facing sources:

- `pyproject.toml`: `2.2.0`
- `src/spectralbridge/__init__.py`: `2.2.0`
- `CITATION.cff`: `2.2.0`

This is the strongest version signal in the repository today.

### Changelog state

`CHANGELOG.md` is ahead of the packaged version:

- top entry: `2.3.0 – 2025-11-03`
- next release entry: `2.2.0 – 2025-10-29`
- later section: `Unreleased`

This means the changelog currently reads like a future release has already been
cut even though the package metadata still advertises `2.2.0`.

### Git tags

Local tags observed during the audit:

- `0.1`
- `v1.0.0`

Those tags do not line up with the current packaged version `2.2.0`, which
creates release-history ambiguity.

## Findings

### 1. Metadata version is internally aligned

The package, import surface, and citation metadata all agree on `2.2.0`.
That is good and should remain the canonical source for the currently packaged
release.

### 2. Release-history records are not aligned

The changelog and tags do not currently tell the same story as the package
metadata.

Practical risk:

- maintainers may cut a release from the wrong baseline
- users may be unable to tell which tag corresponds to the published package
- citation/release notes may point to a release number that is not actually
  tagged

### 3. `setup.py` is not a second version source

`setup.py` acts only as a compatibility shim and does not define a separate
version value. That avoids one common source of drift.

## Recommended release policy

For each release, update and verify all of the following together:

1. `pyproject.toml`
2. `src/spectralbridge/__init__.py`
3. `CITATION.cff`
4. `CHANGELOG.md`
5. Git tag (`vMAJOR.MINOR.PATCH`)

If a future release section is being drafted early, keep it clearly marked as
unreleased until the package metadata and Git tag are updated in the same
release cut.

## Changes made in this pass

- Updated `CONTRIBUTING.md` so release guidance now explicitly includes
  `src/spectralbridge/__init__.py` and warns against leaving future release
  headings above the current packaged version unless they are clearly
  unreleased.
- Updated `publication_checklist.md` with an explicit version-sync checklist
  item capturing the drift found in this audit.

## Follow-up

Related existing queue items:

- `P19` Release automation and notes
- `P23` Release tag hygiene

No package version numbers or changelog headings were rewritten automatically
in this review, because doing so would amount to changing release history rather
than merely documenting drift.
