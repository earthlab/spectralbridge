# Exhaustive fixed-library MESMA experiment

This packet extends `../v1` without changing its input files, target mixtures or
results. It searches all 16,918,447 one-, two- and three-category reference
combinations in the supplied 603-member library for every one of the 360 targets.
Each active category has exactly one reference. Fractions are nonnegative and
sum to one. Zero-fraction faces are searched as lower-dimensional models.

This is an **internal synthetic fraction-recovery diagnostic**, not independent
field-cover validation. The library was selected from the whole archive. The
synthetic target parent IDs are excluded from the fixed library, but selection
was not blind to the archive. Model family and seven-band spectral support are
unchanged from the earlier selected-endmember experiment.

Run from the repository root (requires the original arrays and source Parquet):

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python provenance/endmember-quality/2026-10-19/exhaustive-v1/run_exhaustive.py --pilot
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python provenance/endmember-quality/2026-10-19/exhaustive-v1/run_exhaustive.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python provenance/endmember-quality/2026-10-19/exhaustive-v1/validate_exhaustive.py
.venv/bin/python provenance/endmember-quality/2026-10-19/exhaustive-v1/build_report.py
```

`stream_mesma.py` is an analysis-only implementation, not a new supported public
API. It uses the established active-face logic and numerical tolerances from
`src/spectralbridge/mixtures.py`, specialized to at most three components. It
streams 1,024 model index tuples at a time. Memory scales with targets × batch
size, the library Gram matrix, and compact winners per category set, rather than
with the full model population. There are no nearest-reference screening or
residual pruning steps.

Each completed category set is saved by atomic file replacement. Restarting with
the same inputs and code reuses those checkpoints; interrupted category sets
restart from their beginning. Fingerprints reject changed inputs, solver code,
model order or batch size. Do not edit `stream_mesma.py` while a run is active.
Progress prints at least every 20 seconds during numerical search.

The admissibility thresholds match the existing kernel: smallest affine Gram
eigenvalue exceeds max(1e-12, largest × 1e-10); all active weights exceed 1e-9;
a new global winner must improve mean squared spectral error by more than
1e-14. Models on boundaries are represented by their smaller faces. Exhaustive
means every permitted discrete candidate is considered at these floating-point
thresholds, not exact arithmetic or an unrestricted continuous inverse.

Near-category-set counts retain one best feasible interior solution per class
set. They do **not** enumerate all near-optimal fractions, compute confidence
regions or establish biological uniqueness. The 0.001/0.005/0.01 RMSE tolerances
are descriptive in supplied-array units, not measured instrument noise.

Eight bundles share parents within each bundle. Paired bootstrap summaries
resample those bundles, not individual mixtures. With only eight bundles, their
ranges are conditional descriptions, not validated regional/population coverage.
The matched-random comparator is the preceding **single screened random draw**;
this run does not exhaustively search random selections or compare selectors.
