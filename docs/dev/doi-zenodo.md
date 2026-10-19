# DOI and Zenodo status

Review date: 2026-10-19

## Current repository versus archived release

The repository metadata identifies **2.3.0rc1**. This is a release-candidate
identity, not proof of a published tag, PyPI release or current Zenodo archive.
A matching SpectralBridge release DOI has not been confirmed in this audit.
`CITATION.cff` remains provisional pending author approval. Public API checks
on this date found only GitHub releases `0.1` and `v1.0.0`, and PyPI returned
404 for `earthlab-spectralbridge`; no current candidate publication was verified.

The historical pre-rename archive is
[`earthlab/cross-sensor-cal: Version 1`, DOI 10.5281/zenodo.11167877](https://zenodo.org/records/11167877),
published 2024-05-09. Cite it for that archived release; do not present it as the
DOI for SpectralBridge 2.3.0rc1. The current README does not display a DOI badge.

## Maintainer verification before publication

1. Confirm the GitHub–Zenodo integration and intended archive ownership.
2. Follow the [release gates](releasing.md), using the same tested artifacts.
3. Confirm the actual tagged version has been archived.
4. Verify the archive title, version, authors, license and repository link.
5. Decide between the release-specific DOI and a concept DOI for general links.
6. Update `CITATION.cff`, README and citation guidance only with verified metadata.

Keep [software citation and paper status](software-citation.md) aligned.
A software archive DOI and an accepted paper DOI identify different objects;
neither should be invented to fill a publication checklist.
