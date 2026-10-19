# Publication surface map and editing plan

Reviewed main at 38f646a, 19 October 2026. P138 audit files and prompt/transparency
changes were already present and must be preserved. This is an editorial task;
no package refactor, scientific fitting, release or human declaration is authorized.

| Classification | Surface | Responsibility / proposed action |
| --- | --- | --- |
| USER ENTRY POINT | README.md; docs/index.md; docs/getting-started.md | Purpose, audience, distribution/import identities, install/verify, workflow choice, docs/API/citation links. Shorten README's duplicated research narrative; retain progressive disclosure on homepage. |
| SCIENTIFIC DOCUMENTATION | docs/concepts and docs/spectral-library | Definitions and current conditional conclusions. Link the latest selected-library/exhaustive result from synthesis; retain five researcher categories and evidence ladder. |
| API REFERENCE | docs/api; docstrings; CLI reference | Contracts, maturity, optional dependencies, shapes/units, identity assumptions. Keep current 12 numerical functions distinct from pending promotion. |
| VALIDATION/EVIDENCE | docs/validation; tests; scientific integration JSON | Software checks versus empirical agreement, reproducible contracts. Supplement is historical evidence, not a current tutorial. |
| DEVELOPER DOCUMENTATION | CONTRIBUTING; docs/dev; scripts/README | Build/test/contribution/release/citation routes. Correct stale renamed paths and prerelease prose; do not invent maintainer or private incident contact. |
| PUBLICATION MATERIAL | paper canonical sources; CITATION.cff; pyproject; release docs | Software paper versus software citation versus distribution metadata. Compare 12 people against placeholder/organizational authorship; prepare conditional exact CFF proposal, leave human decision unresolved. |
| HISTORICAL/PROVENANCE | provenance; archive; paper/archive; deprecated | Immutable evidence and source snapshots. Extend top-level provenance index only; never rewrite dated packets or recorded scientific conclusions. |
| INTERNAL/MAINTAINER | queue; prompt log; publication checklists; audit reports | Explicit status/decisions and reproducibility. Add requested root audit/blocker/human-action/JSON files, not a duplicate manuscript. |

The current Home / Understand / Use / Spectral Library / Validate / Reference /
Develop navigation already expresses the desired hierarchy. No radical navigation
redesign is indicated. Non-navigation pages must remain discoverable via existing
landing pages or page catalog; inventory every Markdown source, title and nav role.

## Execution order

1. Verify dated official JOSS, PyPA, CFF/GitHub, Zenodo and SPDX requirements;
   inspect author/ORCID, bibliography, version and archive evidence.
2. Freeze historical file hashes, inventory active sources/placeholders and reader
   routes, then make surgical evidence-backed editorial changes.
3. Keep authorship/consent, unknown ORCIDs, funding, sponsor involvement, COI,
   legal sufficiency, private conduct contact and final AI responsibility human-only.
4. Run source/reference/CFF tests, pytest/Ruff, strict site/links, exact wheel/sdist
   builds and smokes, official JOSS PDF build where tooling permits; render site,
   PyPI long description and paper and inspect the actual outputs.
5. Record every failure/unavailable check and residual human blocker. No blanket
   readiness declaration, publication, submission or tag.
