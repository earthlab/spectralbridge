# Software Citation And Publication Tracking

This page is the maintainer-facing source of truth for how SpectralBridge
should be cited, how associated publications are tracked, and how software
release citations should relate to papers.

Review date: 2026-10-19

## Current citation posture

The repository currently supports three different citation surfaces:

1. `CITATION.cff` as the machine-readable repository citation source
2. the README citation section as the user-facing summary
3. the Zenodo DOI documentation in `docs/dev/doi-zenodo.md`

These are complementary and should stay aligned.

## Preferred citation policy

When users publish work based on SpectralBridge, the preferred guidance is:

1. cite the software release actually used
2. cite any associated project publication or software paper when one exists
3. cite relevant methods papers when a specific scientific method is central to
   the analysis

This keeps software credit, reproducibility, and scientific-method attribution
separate but compatible.

## Recommended user-facing citation language

Use the following wording as the default project guidance unless maintainers
approve a different policy:

> If you use SpectralBridge in research, cite the software release you used,
> any associated SpectralBridge publication or software paper, and relevant
> methods papers for the workflow components your analysis depends on.

`CITATION.cff` is the intended machine-readable citation source, but currently
contains provisional team authorship. Its schema validity does not establish
author approval. The 12-person paper list and organizational package metadata
must be reconciled by the authors before publication; do not copy the placeholder
team name as a finalized personal author list.

## Versioned release citation policy

Current policy:

- users should cite the specific release they used whenever possible
- `CITATION.cff` should match the current intended repository release metadata
- Zenodo DOI handling should be verified separately for each release
- the README badge must not imply that an older archived DOI automatically
  covers the current package version

Until a maintainers-approved post-rename SpectralBridge Zenodo release record
is confirmed, repository text should distinguish between:

- the historical archived DOI
- the current package version
- any future concept DOI or latest-release DOI strategy

## Associated publication tracker

This tracker is intentionally explicit about what is known and what still needs
maintainer confirmation.

| Item | Status | Notes |
| --- | --- | --- |
| Primary software citation source | Active | `CITATION.cff` |
| Zenodo archived software record | Active | `10.5281/zenodo.11167877` for the pre-rename `cross-sensor-cal` release |
| Current SpectralBridge-specific Zenodo release record | Needs verification | See `docs/dev/doi-zenodo.md` and `P27` |
| Software paper sources | Prepared draft | [Canonical paper and build instructions](https://github.com/earthlab/spectralbridge/tree/main/paper); preparation does not establish submission or acceptance |
| Canonical published paper citation | Not confirmed | Add an accepted/published citation only after verification |
| Associated project/manuscript list | No additional published list verified | Maintainers must supply stable references before adding publication claims |
| Publication sources | [Canonical paper directory](https://github.com/earthlab/spectralbridge/tree/main/paper) | Prepared sources and submission checklist; no acceptance implied |

## Software paper tracking

If the project is preparing or maintaining a software paper, track at least:

- target venue
- current status
- canonical title
- canonical author list
- citation string once published
- relationship between the paper and versioned software releases

The [submission checklist](https://github.com/earthlab/spectralbridge/blob/main/paper/SUBMISSION_CHECKLIST.md)
records author actions, including consent, funding, conflicts and AI declarations.
The source-format check cannot certify those decisions or JOSS acceptance.

Repository version **2.3.0rc1** and the
[2026-10-13 RC audit](https://github.com/earthlab/spectralbridge/blob/main/provenance/release/2026-10-13/RC_READINESS.md)
are release preparation evidence. That audit describes its recorded revision and
artifacts; it does not certify later working-tree changes or demonstrate a public
release. See [DOI status](doi-zenodo.md) before citing an archive.

## Maintainer update rules

Update this page when any of the following changes:

- a software paper is submitted, accepted, or published
- the preferred citation wording changes
- the Zenodo DOI strategy changes
- a current SpectralBridge release DOI is confirmed
- the project wants to distinguish concept DOI vs version DOI citation policy

When updating this page, also review:

- `README.md`
- `CITATION.cff`
- `docs/dev/doi-zenodo.md`
- `docs/dev/releasing.md`
- `publication_checklist.md`

## What this page intentionally does not do

- It does not invent publications that are not confirmed.
- It does not replace `CITATION.cff` as the software metadata source.
- It does not declare a DOI strategy that maintainers have not approved.


## Publication evidence

For the historical manuscript evidence and complete SI, use the
[technical supplement](../validation/supplement.md). Current instructions and
contracts remain in the workflow/reference pages.
