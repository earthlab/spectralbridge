# SpectralBridge repository and publication cleanup

12 October 2026. Audited HEAD: `b105c2e7a57e7d33466a649a0e993c6497b733ff`.
All changes are local and reviewable. No commit, push, website deployment, JOSS
submission, release tag or PyPI publication was performed.

## What changed

The audit inventoried 705 artifacts (689 tracked at the audit boundary), 87
Markdown pages, all seven workflows, packaging configuration and the test suite.
The migration preserved 147 checksummed files and retained compatibility paths.
Production code under `src/`, correction equations, coefficients, units, output
names and restart/compact-bulk contracts are unchanged.

The README is now a short introduction with installation, an offline public-API
example, workflow choice and citation/contribution links. The beginner path
explains reflectance, bands, response functions, geometry and spatial support
before technical methods. The full supplement is a clearly labeled publication
record, not a second tutorial system.

## Repository structure before/after

| Before | After / decision |
| --- | --- |
| `drafts/joss/` mixed editable sources, exports, original PDFs and reports | `paper/` sources; `paper/archive/` immutable PDFs/extractions; `paper/generated/` renders/exports/checks. Old shared paths are symlinks. |
| 44 root campaign notebooks | `archive/notebooks/campaigns/`; cells and output preserved byte-for-byte |
| Large root polygon layers | `archive/research/polygons/`; root symlinks preserve notebook input paths |
| Root bulk research bundle | `archive/research/bulk-calibration/`; manifest/results left immutable |
| Root prompt and work history | `provenance/prompts/` and `provenance/work-queue/`; stable root symlinks preserve agent/generator interfaces |
| Forensic report and PDF split across `reports/` and `output/` | `provenance/audits/reflectance-scale-factor/` |
| Root historical monkeypatch / contribution report | `archive/scripts/` / `provenance/history/` |
| Root Linux-only `gocmd` binary | Portable launcher over installed GoCommands; exact old bytes retained in ignored local archive |
| Identical root and packaged sensor JSON copies | Packaged JSON is the single editable source; root compatibility symlinks and immutable original snapshots |
| Third-party PDFs under public docs | Local ignored reading archive; citations/authoritative links retained |
| Accidental HDF5 `:memory:` and local generated files | Preserved locally; HDF5 fixtures now use core driver with backing store disabled |

`src/`, `tests/`, `docs/`, `examples/`, `scripts/`, `validation/`, `paper/`,
`provenance/` and `archive/` now have explicit roles. `MANIFEST.in` excludes
research/publication archives and private local assets while preserving attribution.
The source distribution explicitly whitelists the HyTools provenance record and
prunes other history. An actual rebuilt tar listing verifies no research/private
history slipped in through cached setuptools file lists. The source distribution
is for installed code/source/attribution; build publication
and website infrastructure from the complete Git checkout, not from an sdist.

## Documentation architecture before/after

Before: Learn / Validation / Technical reference / Project, with repeated drone,
bulk and module links and a large supplement appearing before concise guidance.

After: Home / Understand / Use / Validate / Reference / Develop. Primary navigation
has no duplicate destinations. Beginners move from measurement concepts to the
small offline example and workflow choice. Validation begins with the evidence
hierarchy; Publication evidence contains the complete technical supplement.
The spectral-library guide is a canonical separate page; its old bulk anchor is
retained as a link. Historical developer records keep their URLs/content, dated
notices and a history index, and are excluded from normal search. A retained-page
catalog makes previously orphaned specialized/compatibility pages discoverable.

Website inspection caught word splitting in the large hero headline; shorter copy
preserves the visual identity. The rendered-path audit repaired 40 raw HTML links
that the earlier Markdown-only checker missed. Code fences were preserved.

## Files moved

See `moves.json` for every original path, destination, byte count, SHA-256 and
preservation reason. `move-verification.json` distinguishes unchanged archival
bytes from canonical/derivative files subsequently edited for this task. Original
manuscript PDFs, scientific figure assets, research tables and notebook cells
remain preserved. Old `drafts/joss` editing links remain usable through symlinks.

## Files removed

No scientific or user-supplied file was destroyed. Sixteen literature PDFs are
excluded from the current public build and repository additions but retained
locally; seven were tracked and nine were initially untracked. Their prior Git
history was not rewritten. The old executable is no longer a tracked binary;
its checksum and local copy remain. Superseded root placements are moves, not
lost files. Empty retired directories were removed after verifying they were empty.

## Generated artifacts and their canonical sources

| Derivative | Canonical source / ownership |
| --- | --- |
| Official JOSS draft PDF | `paper/paper.md`, `paper/paper.bib`, `paper/figures/`; pinned offline Open Journals renderer |
| Website supplement and downloads | `paper/supplement.md`, `.bib`, figures, explicitly archived original PDF and recorded DOCX export; source fingerprint and completeness checks |
| SI HTML | Canonical SI rendered through Pandoc/citeproc; never an independent edit target |
| Optional new SI PDF | `build_publication.sh supplement-pdf`; layout review required before circulation. The archived 44-page source PDF is explicitly a snapshot. |
| DOCX / Google Docs import copies | Recorded collaboration derivatives; reconcile returned edits to Markdown before regenerating |
| AI transparency | Canonical verbatim prompt log, accessed through the stable root interface |
| Validation pages | Campaign JSON and the prose catalog/generator; the earlier hand-edited index inconsistency is fixed in the generator |
| Inventories, move ledger and checks | Audit boundary and explicit source/artifact hashes; evidence of this cleanup, not scientific validation |

Generated website assets stay version controlled deliberately so offline CI builds
and reviewer downloads work. Source fingerprints, tables/figures/equations/reference
counts and exact download bytes are checked. All 23 SI tables, two figures, three
equations, 101 references and 23 source/provenance notes remain available.
Correspondence now comes from canonical manuscript metadata, not hard-coded text.

## Scientific messaging corrected

The novice model is “common framework, sensor-specific treatment.” NEON can be
weighted into configured sensor-like band spaces; drone inputs have their own
preparation/correction path. Landsat-like representations do not establish
agreement with observed Landsat. Spectral weighting does not solve spatial support.
Execution → requested readable artifacts → internal QA → independent observations
are explicit, separate evidence levels. The original technical figure is preserved
behind progressive disclosure with captions limiting its conceptual/calibration
labels; it is not presented as independent agreement evidence.

## Tests/builds run

- `ruff check src tests scripts` (also the launcher): passed.
- Full `pytest -q`: 500 passed, 7 skipped; existing 29 warnings retained.
- Existing browser smoke, updated for content links/new learning/evidence pages:
  passed separately at desktop/mobile widths, including local assets and search.
- Strict MkDocs build: passed. Rendered internal path/anchor/asset check: zero
  errors. Markdown link checks: passed. New retained catalog addresses ten
  previously orphaned built pages; the catalog itself is in navigation.
- AI, validation and supplement generated-source checks: passed. The initial full
  run exposed an existing stale validation index; its generator now owns the edit.
- JOSS source checks: passed with author declarations still explicitly unresolved.
  Official pinned offline render: ten pages, visually inspected.
- Wheel and sdist built and installed separately; bounded installed-artifact smokes
  passed on Python 3.12 from outside the checkout with network blocked. Dependencies
  were reused from the existing environment, so this is not fresh dependency
  resolution or the complete release matrix. Exact tested hashes/results are in
  `installed-artifact-smoke.json`; these are cleanup packaging checks, not approval
  to publish those exploratory artifacts.
- Release identities/version check for `v2.3.0rc1`: passed.
- Production source/data diff: empty. Migration checksum verification: no lost or
  unexpectedly modified archival evidence.

See `TEST_RESPONSIBILITY_MATRIX.md` for responsibility-level coverage and its
scientific limits. External publisher/DOI availability is not a deterministic gate.

## Remaining warnings

Existing warnings concern compatibility-namespace and datetime deprecations,
Pandas copy behavior, and deliberately all-NaN QA boundary fixtures. They were not
silenced or “fixed” by changing numerical behavior. Local browser launch required
permission outside the macOS sandbox; the actual browser test then passed.

Prompt logging preserves verbatim historical trailing whitespace, so ordinary
`git diff --check` can report those literal spaces; structural whitespace checks
were run with trailing-space checking disabled for that reason. The archive's
manifests/pinned citations retain historical paths/revisions; the move ledger
provides the new physical location without rewriting historical evidence.

Symlink compatibility paths require symlink-capable checkouts. On systems without
that support, use the canonical paths documented in the repository map. No
production package behavior depends on the repository-only compatibility links.

## Items requiring human review

- Literature redistribution: per-file notices and DOI candidates are recorded in
  `literature-review.json`. Some notices indicate open licenses; others reserved
  rights or institutional use. This cleanup does not certify applicable rights.
- Dataset provenance, licensing and external hosting: research vectors, legacy
  datasets and large deprecated rasters remain preserved. Do not externalize them
  without a reliable retrieval/provenance record.
- Real CyVerse replay and historical gocmd version: forwarding/mocked workflows
  are tested, but the original Linux binary's exact version and live campaign
  behavior are not newly certified. Use the [official CyVerse installation
  instructions](https://learning.cyverse.org/ds/gocommands/installation/) and
  [upstream assets](https://github.com/cyverse/gocommands/releases), recording the
  actual selected version/checksum.
- JOSS author consent/contribution, funding, COI, AI review/core-design declarations,
  approved software citation roster and post-rename archive/version identity.
- Historical incomplete production/source provenance and independent scientific
  validation remain the explicit gaps in the supplement; this cleanup does not
  resolve or reinterpret them.
- Confirm GitHub Pages is configured for GitHub Actions and the protected
  `github-pages` environment before deployment; remote Actions have not run here.
- Complete the supported Python 3.10/3.11/3.12 exact-artifact release gates through
  the existing protected release workflow after reviewing/tagging the final source.

## Recommended next steps before JOSS submission

Review changes in separable groups: publication-source migration; archival moves
and compatibility interfaces; novice/documentation architecture; CI ownership and
rendered-link checks; bounded regression tests. The full move ledger permits
reviewing rename-only material separately from authored edits.

Reconcile coworker edits to canonical Markdown, obtain author declarations and
citation/archival approvals, then rerun the deterministic gates. Commit/push the
reviewed changes; `gh-pages.yml` is now the only deployment owner and publishes
exactly the artifact verified by reusable documentation checks. JOSS and software
release workflows keep their distinct source/render/build-once responsibilities.

Deliberately retained: active root Drone/Raster notebooks (tested reference paths
and working-directory conventions); tested root transfer helper modules (existing
imports); HYTOOLS_PROVENANCE/NOTICE/license paths (attribution and sdist contracts);
legacy import/CLI aliases (public compatibility); `deprecated/`, `vendor/`, `data/`
and `Datasets/` (historical/pinned references and uncertain data ownership).
