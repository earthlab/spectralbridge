# Exploratory boosted spectral signatures — 2026-10-13

User selected both species and individual models, percentiles 1–99 (99 curves).
Run: `examples/plant_spectral_quantiles.py --workers 8`; XGBoost 3.4.1,
80 rounds, depth 5, learning rate 0.1, seed 0; exact parameters and hashes are
in the ignored run manifest/checkpoints. No scaling, clipping, normalization or
source-grid remapping. Full artifact root: `artifacts/plant_spectral_atlas/quantile_models`.

7,960 fitted signatures (208 full species, 208 train-only species, 7,544
individual), 1,886 independent GlobalIDs, 363 held-out plants. Individual PDFs:
NIWO 193 pages / 964 plants; WREF 111 / 553; YELL 74 / 369. Every modeled
GlobalID appears once. 62 selected plants have one flight observation.

Pooled corrected species top-1: 15.70%; median-RMSE: 15.70%; majority: 22.04%.
Corrected species top-1 by site: NIWO 18.62%, WREF 17.31%, YELL 37.88%.
Individual-reference corrected matches: NIWO 34.04%, WREF 32.08%, YELL 52.17%;
these do not consistently outperform empirical individual templates.
See matching_baselines.csv for all stages and comparison metrics.

Tail fitting is inadequate in some groups: NIWO Abies lasiocarpa corrected,
425 nm, q99 fitted 3529.3 versus empirical 286.6 (stored units). Nearly flat
outer curves are model underfit, not observed spectra. Experimental residual
and alternative-rate pilots were not adopted. No reliable identification or
calibrated uncertainty claim is supported.

MicaSense export labels [475,560,668,717,840,841,842,843,844,845] match legacy
fallback/padding rather than the packaged ten-band grid. Band identity is
unverified until original headers are inspected. Values/order are preserved;
figures disclose this and the matching API rejects physical-wavelength queries
by default. Archive-label comparisons require an explicit override.

59 focused regression/contract tests passed; focused Ruff passed. PDF QA checked
first/middle/last individual pages and verified unique full-cohort coverage.
Large generated artifacts are ignored; no commit or publication was performed.

## Presentation update: separate sensor plots

Quantile row reports now show four separate columns (raw NEON, corrected NEON,
derived Landsat OLI and derived MicaSense). Sensor columns have their own
wavelength axes; row y limits remain shared. Additional descending quantile
PDF/PNG grids isolate all 1,886 plants for Landsat and MicaSense separately.
MicaSense export labels remain unverified and are explicitly flagged.
These are presentation-only changes; training matrices, fits and held-out
measurements are unchanged. Eighteen targeted tests verify exact sensor grids,
independent columns/ranges, all plant paths, missing samples and checksums.
