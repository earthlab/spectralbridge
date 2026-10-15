# Documentation, website and scientific-test integration results

## Outcome and navigation

The website now follows Home → Understand → Use → Spectral Library → Validate
→ Reference → Develop. Existing URLs and good operational pages remain; no
redirect is needed. The new section links empirical observation structure,
biological association, synthetic sensor reduction, independent comparison and
experimental mixture readiness without recasting the package as MESMA software.

Created six scientific library pages (overview, atlas, labels, biological
variation, sensor transfer, MESMA readiness), three validation pages (method audit,
actual Landsat pilot, six evidence levels), an API maturity/contract page and a
scientific testing page. Generated snippets/JSON and three checked local images
provide source-specific counts and figures without raw-data website builds.

Substantially revised home and navigation; README, quick start, API index,
existing library/atlas guides, CI guidance and evidence links were extended.
Pipeline/QA/sensor-harmonization text now distinguishes processing from empirical
calibration and Collection 2 Level-2 SR from conceptual NBAR artwork. The published
site was older than local sources at inspection; this work builds/reviews the
local site, and does not deploy it.

## Usable capabilities and examples

Stable top-level entry points remain unchanged. The API maturity page exposes
module-level atlas, harmonization, statistical, Gaussian-projection and actual
Landsat workflows with explicit dimensions, units, missingness, exceptions and
scientific assumptions. Research helpers remain explicitly research/experimental.
Selected callable docstrings/return annotations were completed. New experimental
holdout and residual-adequacy guards are integrated into readiness; fraction
detection calculations are reused under an explicit threshold contract. The OLI
diagnostic now rejects invalid dimensions/nonfinite/unsorted coordinates without
changing valid-input response weights or numerical assumptions.

The new fast offline example constructs six invented teaching records, inspects
the library, builds a compact empirical atlas, preserves gaps, projects a flat
spectrum and checks agreement. The documentation snippet is executable. Neither
example is presented as empirical validation. Full source-specific research runs
remain separately linked from provenance and examples.

## Tests and verification

Added 40 collected test cases: 21 sampling/statistical/response/mixture/detection
invariants, seven evidence/docs/example/figure-composition contracts, eleven
crosswalk/PFT-input/actual holdout-pool contracts, and one additional browser
case. Existing analytic FCLS, independent optimizer, QA/scaling/CRS and paired
bootstrap tests were reused rather than duplicated.

Final offline suite: **655 passed, 7 skipped, 2 deselected, 30 warnings**, 162.89 s.
The two explicitly excluded browser tests pass separately (desktop/mobile,
figures, API anchors, assets and overflow). Existing core browser checks also
remain intact. Strict MkDocs, source links, all rendered internal links/anchors/
assets (zero errors), focused Ruff, generated scientific snapshot/images,
AI transparency and whitespace checks pass. Offline two-figure composition and
the full canonical figure numerical validator pass. No new scientific figure
replaces or alters the canonical publication evidence.

Coverage includes branches: **68.31% overall**, above the existing 45% gate.

| Module | Combined statement/branch coverage | Covered / total branches |
|---|---:|---:|
| plant_spectral_atlas | 94.3% | 74/84 |
| plant_spectral_quantiles | 85.5% | 134/182 |
| plant_spectral_years | 88.9% | 43/56 |
| plant_spectral_pfts | 28.5% | 29/102 |
| plant_pft_statistics | 73.0% | 53/82 |
| researcher_pft_statistics | 87.0% | 32/42 |
| pft_method_audit | 90.2% | 66/82 |
| sensor_pft_transfer | 88.0% | 89/110 |
| landsat_agreement | 92.2% | 50/62 |
| landsat_flight_validation | 72.1% | 92/134 |
| mixtures | 93.2% | 97/112 |
| mesma_readiness | 85.6% | 161/206 |

Important remaining branches: PFT orchestration/individual-reference reuse and
large plotting paths have lower coverage than the tagging/grouping contracts;
real-Landsat remote/cache failure branches and large reporting/transfer loops are
not exhaustively exercised. These are visible gaps, not hidden behind total
coverage. Hypothesis is not installed; seeded parameterized algebraic properties
provide targeted protection without another dependency.

## CI / test data

Unit CI now has Python 3.10/3.11/3.12 jobs, unique coverage artifacts and an
aggregate gate preserving `CI / unit`. Local execution used Python 3.12; the
GitHub matrix itself was configured, not claimed to have run remotely. Normal
jobs explicitly exclude live network/external/full/browser markers. Docs CI
checks generated scientific assets and small regressions before its strict build
and browser suite. Additional triggers cover the actual figure/evidence inputs.
No deployment, release tag, version bump or publication is performed.

Tiny frozen JSON fixtures preserve six derived real-pilot records and all 21
canonical inferred contrast/cohort summaries, with source identifiers/hashes and
review-only update instructions. They are not raw imagery or a pixel-library
cache. No live STAC/CyVerse service tests were run. Cached original-data and
credential-dependent tests remain opt-in. The new CLI example test runs in a
fresh subprocess, as a user would, avoiding legacy test interpreter IO-module
replacement effects uncovered by the first full run.

## Claims / JOSS assessment

CLAIMS_AUDIT.md records important claims, evidence levels and wording boundaries.
Significance, prediction, identifiability, fraction recovery, synthetic sensor
reduction and independent validation remain separate. Library scaling and
MicaSense coordinate provenance remain unresolved; one next-day Landsat pair is
not multisite validation. No class is promoted to operational abundance READY.

Metadata versions agree at 2.3.0rc1; distribution/import/software/repository names
and GPL license identity remain distinct and unchanged. JOSS format checks pass,
but human review/AI contribution, funding and conflict declarations remain
incomplete. CITATION author/ORCID approval and a real archival DOI require
maintainer action. The software/docs are substantially more reviewable; this is
not a declaration of completed JOSS submission or broad ecological validation.

Five highest-value remaining actions: (1) maintainers finalize authors/citation,
funding/conflict/AI review declarations; (2) recover source units and physical
sensor metadata, including MicaSense/P122; (3) obtain purity, missing background
materials and independent abundance truth; (4) replicate same-day independent
Landsat comparisons across sites; (5) extend grouped predictive/generalization
and uncertainty evidence plus the lower-covered orchestration/failure branches.
P126 is the explicitly requested next scientific analytics audit.
