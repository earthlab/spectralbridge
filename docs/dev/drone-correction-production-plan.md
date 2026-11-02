# Proposed drone correction policy and implementation plan

2026-11-02. **Proposal only.** No production behavior, imagery, coefficients or libraries were changed by P161. Scientific evidence is in the [three-flight investigation](drone-brdf-identifiability-investigation.md).

## Immediate decision for Gordon, Goldhill and Ruby

Preserve the spatially repaired source grid and original numerical arrays. Provide an explicit, provenance-backed per-band inverse-normalization option for numerical recovery. Keep recovered data labelled source DN until physical calibration is established. Do not apply Ross–Li to these orthomosaics: all three fail rank and conditioning. Do not promote the current topographic output on appearance alone: illumination/terrain provenance, high gains, mask losses and mixed polygon effects need review.

This interim choice preserves numerical information; it does not establish that uncorrected DN is the scientifically optimal final representation. A useful library need not have BRDF normalization, but physical interpretation and transfer require verified source units and a clear directional/application domain.

## Stage acceptance criteria

| Stage | Required evidence and acceptance | Failure behavior |
| --- | --- | --- |
| Spatial ingest | Source CRS/affine, north-up/orientation, band/alpha identity and independently verified polygon membership; retain existing TIFF corner contract | Reject malformed source conventions; no new guessed flips or shifts |
| Numerical recovery | Verified per-band mapping and source identity, floating output, masks/alpha unchanged, round-trip validation and untrimmed original-resampling residuals | Retain source; report numerical recovery uncertainty; do not equate with physical calibration |
| Physical radiometry | Panel certificate and images or justified DLS-based calibration, exposure/gain/sensor metadata, Metashape band-sensitivity/export settings, declared scale/offset direction and traceable band order | UNSUPPORTED; keep explicit diagnostic DN outside physical-library/bulk contracts |
| Solar/terrain | Authoritative acquisition date/timezone, pixel-time policy, solar-angle conventions; slope/aspect units, aspect north convention, DEM/DSM identity/resolution and source-grid alignment | UNSUPPORTED; never invent geometry to unblock a correction |
| Topography | Verified physical inputs and illumination, supported C fit and conditioning, well-resolved positive denominators, explicit shadow/invalid masks, gain distributions, matched spatially held-out checks preserving real category structure | Hold for review; no arbitrary gain cap or silent neutral fallback as approval |
| Ross–Li BRDF | Genuine observation geometry/provenance, at least four eligible observations, rank three, current float32 condition limit, supported scene/stratum population, uncertainty-resolved positive predictions and reference support, held-out angular performance | UNSUPPORTED or INVALID. Explicit user-selected omission may produce a BRDF NOT_REQUESTED product if all other required gates pass; requesting an unsupported correction must remain visibly blocked |
| Translation | Accepted input stages and physical units compatible with coefficients, wavelength mapping, target/input support and independent empirical validation for calibration claims | Block unverified historical coefficients; synthetic common-reference relationships remain descriptive |
| Native library | Verified units, accepted/omitted stage provenance, valid masks/grid, researcher identities/labels, polygon or spatial grouping, documented directional/date/phenology domain | Retain as diagnostic/unapproved; do not silently relabel DN as physical reflectance |
| Bulk/restart | Immutable source identities plus calibration, geometry, algorithm and correction-policy fingerprints; compact sufficient-statistic checkpoints only | Reject stale scientific products; rebuild derived data in fresh directories after approval |

A high R², low variance, bounded NDVI, full-rank matrix or successful program exit is insufficient on its own. Gain review thresholds must be justified for the intended scientific use; no universal cutoff is proposed here. Shadow exclusions and robust plot limits must not silently change analytical populations.

## Small implementation sequence

1. **Read-only correction preflight.** Extend existing drone QA/audit records in `pipelines/drone.py` and `drone_qa.py` with explicit angle provenance (observed, reconstructed, assigned or missing), calibration status, independent stage eligibility and the shared angular diagnostics. Reuse `_brdf_design` and existing numerical thresholds. Keep scientific model acceptance sensor-agnostic; do not make NEON automatically valid or drones automatically invalid.
2. **Explicit recovery contract.** Extend the established TIFF ingest path rather than add a second pipeline. Apply a separately recorded, verified per-band numerical inverse before the existing scalar physical boundary when appropriate; validate composition with the authoritative physical calibration. Preserve masks, alpha, wavelengths, affine and provenance. Existing `Radiometry` is scalar; do not pretend its current fields can encode Goldhill/Ruby's band-specific offsets directly.
3. **Independent correction plan.** Resolve requested versus eligible stages before processing. Keep raw, topographic and BRDF status distinct. Preserve current scientific blocking when a requested stage is unsupported. Add an explicit no-BRDF production choice with truthful header/state metadata; never write BRDF VALID for an identity/no-fit result. Preserve file/naming contracts and atomic completion behavior. Do not silently change existing defaults.
4. **Topographic validation.** Independently validate the source terrain and acquisition geometry, then evaluate denominator/fit uncertainty and spatially held-out within-target or invariant-target performance. Reuse the SCS+C implementation; improvements to scene-fit validation should be narrow and shared. The present numerical replay does not authorize changing its scientific formula or selecting a correction solely by PFT variance minimization.
5. **Translation and extraction.** Continue to require physical-unit-compatible coefficient records and accepted source headers. Native, calibrated, no-BRDF spectra may feed library extraction if the explicit directional domain is suitable. Validate cross-sensor agreement independently before promoting translated libraries. Preserve compact bulk checkpoints and sufficient statistics; no ordinary pixel-scale analysis cache.
6. **Controlled regeneration.** Inventory and mark affected historical products unapproved without altering them. After calibration/policy approval, create a new immutable run for the three native corrected contributions, their 12 translated contributions and dependent merged/bulk fits. Compare against the preserved run; only promote after scientific review. Unrelated NEON libraries do not automatically need regeneration.

## Original-image feasibility gate

Before building another BRDF implementation, obtain the raw M300 SD1/SD2 images, calibration panel/DLS records, actual date/timezone, intrinsics/extrinsics or complete Metashape project, terrain surface and image-to-ground visibility/blend provenance. Reconstruct repeated observations of the same stable targets and quantify real angle/illumination coverage. Test a bounded set of targets with held-out views, then decide whether the existing Ross–Li implementation is supported. Camera image count alone is not the angular sample size. No full raw-photo reprocessing is proposed until this feasibility gate passes.

## Regression and verification plan

- Preserve all existing spatial round-trip, mask, ancillary and signed-affine contracts.
- Synthetic constant-nadir and nearly singular full-rank matrices must remain unsupported; well-conditioned multi-angle fixtures must pass the existing kernel/acceptance tests.
- Verified per-band recovery must preserve zero/finite nodata, alpha, negative valid values, band order and physical mapping direction; historical source files remain read-only.
- Explicit no-BRDF must report the omitted stage and preserve unit/library gates; requested unsupported BRDF must block. Test topography independently and never stamp it valid before full output completion.
- Header, Parquet and bulk scientific-unit status must survive merges. Policy/calibration changes invalidate only affected derived outputs/checkpoints, without overwriting prior runs.
- Use realistic chunk/memory tests on the new ingest/preflight path. The isolated P161 full-memory numerical replay is not a production implementation or large-VM benchmark.
- Obtain matched independent field/target-sensor observations before claims of absolute accuracy, empirical calibration or improved ecological discrimination. Use polygon/spatial groups and independent sites/angles where available; report support, uncertainty and phenological limits.

## External dependencies and next action

P159 remains the acquisition/calibration dependency. First recover the actual camera project and calibration provenance, resolve August 14 notes versus August 15 CSV times, and confirm terrain and illumination conventions. Keep P158's fail-closed scientific contracts intact while that work proceeds. This proposal does not authorize replacing production artifacts or regenerating libraries.
