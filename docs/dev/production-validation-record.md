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
