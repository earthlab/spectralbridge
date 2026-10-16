# Verification and scientific limits

Completed locally 2026-10-16. No commit, push or publication. The original polygon
Parquet is read in place, and no source spectral dataset was copied.

## Independent checks

- `source_identity_validation.json`: all 3,639 raw GlobalIDs match the analytical
  cohort, category labels agree exactly, no missing source ID or conflicting label.
- `foundation.json`: 85,706 pixel rows, 4,807 polygon/year spectra, 1,168 repeated
  IDs, 360 retained NEON coordinates and seven synthetic OLI channels. Each pixel
  has 426 finite native corrected values in a union schema of 1,140 columns;
  structural null padding is distinguished from analysis-grid missingness.
- `tables/duplicate_spectra.csv`: all 4,807 annual NEON and OLI vectors unique;
  no exact cross-ID spectral duplicates. This does not rule out spatial dependence.
- `control_validation.json`: all 352 fitted classifier model exports and 364
  target evaluations replay from saved parameters. Exact inner memberships,
  training/target GlobalID exclusion, random feature paths, inner-only C choice
  and agreement with all 54 selected-budget replays of the prior analysis pass.
- `candidate_validation.json`: all 24 same-candidate ridge target predictions
  reconstruct with independently solved normal equations; max absolute prediction
  difference 5.995e-13. Exact 15-parent membership, role exclusion and tuning-only
  alpha selection are verified.
- `synthesis_validation.json`: all 384 previous canonical abundance evaluations
  independently recomputed against saved truth; fractions finite/nonnegative/sum-one,
  per-class RMSE reproduced. All 196 sealed previous packet files unchanged.
  The prior independent oracle, source-pixel and permutation checks are reused
  with their original scope, not called new field validation.
- `figure_rebuild_validation.json`: all 30 exports from ten figure families rebuild
  byte-identically with original-data and analysis-cache reads explicitly denied.
- `artifact_validation.json`: 26 pages, ten complete figure explanations, zero
  out-of-bounds words, no retired group codes, no orphan/near-empty pages,
  36 numerical source files, 38 saved table files and 30 figure files checked.
  The PDF rebuild is byte-identical. Every final page rendered and visually
  reviewed; dense wavelength, class-confusion, fairness and detection pages
  additionally inspected at larger resolution.

## Software verification

Full feasible offline suite: **709 passed, 7 skipped, 2 deselected, 30 warnings**
in 178.00 seconds; coverage **68.28%**, above the configured 45% gate. Existing
optional dependency/full/network/browser exclusions remain unverified. The three
new helper regression tests also passed separately. CLI help/staging inspected.

Targeted source/helper/example/report Ruff checks pass; dated exploratory scripts
use explicit F401/F841/E741 exclusions for unused research imports/aliases, without
cosmetic changes to fitting files whose hashes protect restart identities.
Strict MkDocs, source and built-site links, scientific snapshot, AI transparency
and whitespace checks pass. No new browser interaction tests are claimed.

## Failed interpretations are scientific results

The no-spectrum control defeats ridge120 on global-year mean. Reducing ridge to
MESMA's exact 15 retained NEON parent spectra removes its original advantage.
Small selected wavelength budgets do not uniformly beat random subsets; large
budgets narrow the average gap. Derivatives worsen the existing abundance
benchmark. Stage-A/final-fraction detection, low-fraction misses and quantification
have different tradeoffs. None of these failures is hidden by a favorable mean.

The same-candidate experiment changes retained biological diversity and training
bundle count, as well as the effective learning problem. It cannot uniquely
attribute the original gain to one mechanism or establish intrinsic algorithm
superiority. Ambiguity is candidate/tolerance-specific, not exhaustive physical
uncertainty. Paired intervals are conditional pointwise bundle/identity intervals,
not multiplicity-corrected discoveries or new geographic replication.

Absolute units, pure materials, independent annual labels, independent field
fractions and broader balanced geographic/temporal support remain missing. These
limits appear explicitly as NOT TESTABLE and block a defensible field-cover claim.

## Additional diagnostic contracts

The previous nominal-fraction summaries already handled floating-point-equivalent
truth fractions. A new synthetic regression fixture protects count-weighted
prediction/detection means and root-mean-square aggregation. The presentation
summary preserves existing observations and errors; it does not fix or replace
any previous numerical model result.

`presence_validation.json` independently reproduces all 24 saved two-stage
aggregate presence evaluations and separates raw threshold decisions, existing
forced highest-score admission and final fraction detection, for each supported
truth fraction/category. `restart_validation.json` confirms 34 completed training
cases reused without refitting or changed aggregate exports.
