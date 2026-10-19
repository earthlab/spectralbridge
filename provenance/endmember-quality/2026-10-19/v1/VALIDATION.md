# Verification and interpretation limits

- 16 small synthetic/control tests passed, including existing mixture contracts.
- All three supplied input hashes checked; source-array orientation, label order,
  source Parquet scaling relation and numeric class mapping verified.
- All 4,261 target-coverage rows independently replayed with broadcast distances.
- All 223 saved cross-category convex-mixture certificates reconstructed against
  the original NPY values and checked for other-category membership, nonnegativity,
  sum-one and spectral RMSE <=1e-8.
- All 360 synthetic targets reconstructed from their stored source parent IDs;
  no generating ID overlaps the selected library or another bundle.
- All 1,800 screened-model reconstructions and category fractions replayed from
  their actual selected array indices and component weights.
- Twelve prespecified targets independently searched by affine least-squares
  face enumeration; spectral objective agrees with the existing solver.
- Dense/sparse no-spectrum controls independently checked against the balanced
  design's analytic MSE difference (2/75); neither uses target spectra or fits
  fractions from target outcomes.
- All 1,053 prior owned scientific, manuscript, formal and report files unchanged.
- Six figures visually inspected and annotations revised for readability. The
  self-contained HTML report rendered on desktop/mobile with six working images
  and no horizontal page overflow. Numeric results and claims reviewed separately.
- Scoped Ruff and AI-transparency consistency pass. Whitespace checked outside the
  verbatim prompt log, where the user's original trailing blank is preserved.

## Scope

This is an internal fixed-library evaluation, since selection saw the whole
archive. Nearest-reference agreement is a descriptive rule, not a trained nested
classifier or abundance accuracy. Pixel-count-matched controls address within-parent
selection, with a separate parent/flight-matched sensitivity.

Convex-hull certificates permit multiple references per category and up to eight
active references, unlike the at-most-three-category MESMA configuration. Near-fit
ranges retain one solution per evaluated class set and use illustrative tolerances.
They are not exhaustive uncertainty or calibrated sensor-noise bounds.

Screened MESMA searches 375 primary models per target, not the full 16.9-million
library combinations. Sparse/dense priors have different nonzero-category budgets;
both are shown. Eight-bundle bootstrap ranges are conditional internal summaries,
not validated population coverage; spatial correlation is not modelled. Source
category labels and synthetic algebraic fractions are not independent field cover.
No universal judgment of the unknown selector's objective is possible without its
script/design. Independent validation remains future work, not an implementation
blocker for these diagnostics.
