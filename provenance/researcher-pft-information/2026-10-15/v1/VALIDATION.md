# Validation and practical limits

Completed locally on 2026-10-16. Original source spectra were read in place;
no duplicate pixel-scale spectral dataset was created. Earlier scientific outputs
remain preserved; historical labels are excluded from this primary analysis.

## Numerical and leakage checks

- `numerical_validation.json`: passed. Source and reused inference hashes match;
  116 earlier owned analytical products are unchanged. Prior sealed source audit
  reports zero exact source-pixel overlap across polygon identities.
- All ten pairs at all 360 retained coordinates are present. Twenty univariate
  domain cases and 230 training-only blocked permutation cases were checked.
  Nested training membership, feature paths and saved classification predictions
  reconstruct independently. Weighted AUC agrees with scikit-learn.
- All 384 abundance evaluation cases have disjoint proper-training, tuning and
  target identities, valid projected fractions and independently reproduced RMSE.
  The no-spectrum control uses only the proper-training fraction mean.
- `model_replay_validation.json`: 73 representative saved abundance prediction
  cases replayed, including independently solved ridge normal equations,
  transformations, both sensors, tree models, two-stage and physical baselines.
- Oracle inversion reaches maximum fraction RMSE 3.90e-13 under the ideal linear
  construction. This is a numerical control, not a deployable field model.

## Software and artifacts

The full repository test run passed: **705 passed, 7 skipped, 2 deselected**,
30 warnings, 175.68 seconds; coverage **68.25%**, above the configured 45% gate.
Optional dependency/network/full checks excluded by the existing environment or
markers remain unverified. Targeted helper and documentation tests also passed.

`rebuild_validation.json` records all 44 figure exports rebuilt byte-identically
in fresh processes with access to the original Parquet and analysis caches
explicitly denied. Six compact training-correlation matrices and a filtered
researcher-only upstream effect table are retained with source/target hashes in
`compact_figure_sources.json`. They contain statistics, not copied source spectra.

`pdf_validation.json` checks the 20-page PDF, all 15 figure explanations, table
and figure hashes, absence of retired group codes, text geometry and byte-identical
PDF rebuilding. Every page was rendered and visually reviewed. Main figures have
PNG/PDF/SVG exports; the supplementary confusion panel has PNG/SVG exports.

Strict documentation build, source and built-site links, generated scientific
snapshots, AI transparency, targeted Ruff and whitespace checks pass. No browser
interaction test, commit, push or publication is claimed.

## What these checks do not establish

Results are conditional on sampled categories, footprints and observed domains.
Repeated synthetic mixtures are not independent plants; uncertainty resamples
parent bundles. Historical annotations are not independent annual biological
truth. Global-year holds confound year and site. The global-year ridge average
fails to improve on the no-spectrum fraction prior. Better synthetic fraction
prediction does not prove unique physical inversion or field-cover validity.
Independent contemporaneous field fractions, purity evidence and geographically
broader validation remain necessary. See LIMITATIONS.md and NEXT_DATA_NEEDED.md.
