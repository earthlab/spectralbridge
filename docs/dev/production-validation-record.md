# Production validation record

SpectralBridge uses two deliberately separate release-evidence tiers. Tiny
installed-artifact smoke tests and real production validation answer different
questions and must not be presented as substitutes for one another.

## Tier A: installed-artifact CI smoke

Every release candidate builds the wheel and source distribution once, then
installs those exact artifacts in clean environments outside the repository
checkout. The smoke uses deterministic 8 × 8 synthetic rasters, one worker,
small row groups, blocked network access, and a strict output-size ceiling. It
runs the production orchestration and scientific transformation functions for
the normal NEON, drone, and bulk pipelines.

This tier proves packaging integrity, installed resource availability,
orchestration, stage connectivity, output readability, and selected restart
behavior. Reducing fixture scale is acceptable because the same production code
paths and algorithms run. The fixture does not establish scientific accuracy,
production-scale performance, cross-site stability, or empirical calibration
validity.

## Tier B: real production validation

Selected release candidates must also have a durable record from real
flightlines on appropriately sized infrastructure. GitHub Actions is not
expected to reproduce workflows that may require roughly 250 GB of RAM. This
tier establishes operational behavior at real scale and supplies evidence for
scientific review.

The repository currently retains one real-run record:

- [R10C L002, 2021-09-15 walkthrough](../validation/real-data-example.md)
- input: `NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5`
- input size: 2,532,249,598 bytes
- dimensions: 1,115 × 5,351 × 426
- outputs: approximately 21 GB locally, with a 4.6 MB report bundle retained
- result: the full process exited normally; acquisition, correction,
  convolution, polygon extraction, merge, and QA evidence are recorded

That run predates the eventual PyPI release candidate and is evidence about a
real workflow, not proof for the bytes of a future distribution artifact.

### 2026-09 production bulk-analysis evidence

A completed streaming bulk run on the staged Aug 2026 collection provides the
current production-scale evidence for the bulk architecture. The following
figures are operator-reported observations from that completed run; they were
not independently rerun in the macOS release-preparation workspace, and they
are not constants, thresholds, or expected values in package tests.

- 122 accepted flightlines across NIWO, WREF, and YELL;
- approximately 215+ GB of staged immutable source products;
- 899,692,166 selected observation rows reduced during streaming analysis;
- 122 compact per-flightline sufficient-statistics checkpoints;
- 18 unique sensor-pair × band translation regressions;
- 54 candidate coefficient rows spanning pixel-pooled,
  flightline-balanced, and site-balanced estimates;
- 2,196 per-flightline fits, 54 per-site fits, and 54 leave-one-site-out
  evaluations;
- no ordinary pixel-scale Parquet cache.

The observed translation summaries included a median slope near 0.9660, slope
range near 0.8675–0.9970, median R² near 0.9940, and R² range near
0.5944–0.9998. At a representative source value, the median absolute fitted
correction was about 7.54%, while the largest observed absolute correction was
about 110.92%. These observations support the reporting design: strong
relationships can coexist with scientifically meaningful corrections, and
weak or extreme cases must remain visible rather than being hidden by medians.

Operational issues exposed and corrected during staging and production work
included matched MicaSense product classification/translation eligibility,
literal `ETM+` filename handling, and replacement of the earlier pixel-cache
design with direct bounded-window reduction and compact restart checkpoints.
The reusable results layer was then added to compare weighting schemes,
flightline/site heterogeneity, correction magnitude, and held-out-site
transferability from compact completed-run outputs alone.

This record supports the algorithms and architecture incorporated into
2.3.0rc1, but it is not evidence that the exact RC wheel or sdist processed the
archive. The exact installed artifacts are covered by Tier A; a post-publication
production rerun may be recorded separately if required by the maintainers.

## Maintainer record for the next large-VM run

Copy this checklist into a dated Markdown or JSON record under
`docs/validation/` or `validation/results/`. Do not commit raw production
rasters or tables merely to satisfy the checklist.

- canonical flightline ID
- NEON site and acquisition date
- SpectralBridge version, Git commit, and dirty-tree status
- wheel or source origin and SHA-256 when an installed artifact was used
- Python version, operating system, and key dependency versions
- approximate CPU count, RAM, temporary storage, and final storage
- complete pipeline configuration, including extraction and QA modes
- input size and raster dimensions
- major output artifact paths, sizes, and hashes where practical
- stage QA statuses and links to retained JSON/HTML/figures
- wall time and peak operational observations
- warnings, fallbacks, failed optional diagnostics, and reviewer disposition
- maintainer/scientific reviewer name and review date

A release record should link both the successful Tier A workflow run and the
selected Tier B evidence. Neither tier should be relabeled as the other.
