# DOI And Zenodo Status

This page documents the current DOI and Zenodo state for SpectralBridge so
release and citation behavior stays explicit.

Review date: 2026-06-03

## Current status

An existing Zenodo software record was found for the repository's pre-rename
release:

- Zenodo record: `earthlab/cross-sensor-cal: Version 1`
- Published: 2024-05-09
- DOI: [`10.5281/zenodo.11167877`](https://doi.org/10.5281/zenodo.11167877)
- Record URL: [zenodo.org/records/11167877](https://zenodo.org/records/11167877)

This confirms that Zenodo archiving is already present at the repository level.

## Important clarification

The current repository and package are now named `SpectralBridge`, while the
existing archived Zenodo release still reflects the earlier
`cross-sensor-cal` naming and release metadata.

That means:

- the README can safely display the existing DOI badge
- the DOI is real and citable for that archived release
- the DOI should not be presented as the DOI for the current `2.2.0`
  `SpectralBridge` package unless Zenodo has also minted a matching modern
  release record
- `CITATION.cff` should remain version-focused and repository-focused until a
  maintainers-approved current SpectralBridge DOI is confirmed

## What maintainers should verify for the next release

Before treating Zenodo as current release infrastructure, confirm:

1. the GitHub repository is still connected to Zenodo
2. the next tagged release is being archived automatically
3. the archived release title uses `SpectralBridge`, not only
   `cross-sensor-cal`
4. the archived version number matches `pyproject.toml`,
   `src/spectralbridge/__init__.py`, `CITATION.cff`, and the release tag
5. the README badge still points at the intended DOI

## Recommended release-to-DOI workflow

For each release:

1. synchronize version metadata locally
2. create the release tag using the documented canonical tag scheme
3. publish the GitHub release
4. confirm Zenodo archives the release and mints or updates the DOI record
5. verify the Zenodo title, version, authors, and repository link
6. update `CITATION.cff` if a release-specific DOI should now be cited
7. confirm the README badge still points at the intended DOI target

## Repository files updated in this pass

- `README.md` now shows the existing Zenodo DOI badge
- the README citation section now distinguishes the historic Zenodo release
  DOI from the current package version

## Follow-up recommendations

- mint and verify a new SpectralBridge-named Zenodo release for the current
  package line
- decide whether the project wants the README badge to point at a historic
  version DOI or a future concept/latest-release DOI once maintainers confirm
  the preferred Zenodo setup
