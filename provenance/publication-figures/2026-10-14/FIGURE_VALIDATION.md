# Scientific and graphical validation

## Inputs and inherited results

Builder verifies 338 analysis-owned files across the sensor-transfer, empirical PFT-method audit and real-Landsat manifests, plus every sensor-transfer evidence-owned hash. Original library SHA256 remains `cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978`. It is read in place with only original metadata projected; compact empirical summaries are reused. No original pixel table is copied or exported. No canonical input/result is modified.

Published correlation evidence has additional blocked-MicaSense rows/status fields; its tested NEON-vs-OLI subset exactly reproduces the canonical correlation table. The canonical effect table is byte-identical to published evidence. The published signed curves and retention summary are verified against their evidence manifest; selected beta curves also reproduce the original empirical method-audit envelopes. This distinction between enriched evidence and analysis-owned outputs is deliberate.

## Panel checks

| Panel | Numerical validation |
|---|---|
| 1A | All 4,807 polygon/year curves enter five category summaries. Recomputed every exported median/IQR coordinate against the empirical compact arrays. Exactly 360 complete common-support coordinates; excluded domains remain disconnected. Shading is an empirical IQR, not a confidence interval or fitted quantile regression. |
| 1B | Source Parquet metadata: 85,706 pixel records; projected source metadata: 3,639 unique identities, 2,496 with species recorded, 1,143 missing. Compact/source identity sets equal. Three sites/two years/five researcher categories. Polygon/year counts: NIWO 2020 1,631; NIWO 2023 1,168; WREF 2023 947; YELL 2023 1,061. Counts sum to 4,807. |
| 1C | All 4,807 rows retained, no imputation/union-column PCA/clipping. Independent weighted covariance eigenvalues reproduce SVD variance fractions 0.7090049433416605 and 0.2676811105619891; score covariance equals corresponding eigenvalues and exported scores/keys match. Denominator uses full spectral variance. |
| 1D | All five chosen examples are actual paired observations. Independently checked each minimizes weighted distance to its category coordinate-wise median. Synthetic OLI values come from the identical site/year/GlobalID. Exact distance tie behavior tested under reordering. Centers: packaged validated physical metadata, not rounded stored coordinates. |
| 2A | Every plotted comparison/effect/p-value/sample count exactly reproduces canonical effect_retention.csv. All 21 eligible inferred comparisons shown; absent cells reflect insufficient matched support. No p-values recomputed or untested cells inferred. |
| 2B | Exported NIWO 2023 DBS/ECT and DBT/ECT signed curves reproduce verified native evidence. Beta and wavelength arrays match original simultaneous-envelope records exactly within numerical precision; excursion masks copied from that family. Separately reproduced all five previously recorded recurring intervals across their four cohorts. These are maximum-component null excursions, not simultaneous effect confidence bands or exhaustive NPC localization. |
| 2C | Recomputed Pearson 0.95487920511704 and Spearman 0.9818181818181818 from the 21 paired effect points, matching canonical evidence. Verified 16 NEON supported, 15 retained, five unsupported in both, one loss (NIWO 2023 DBS/DBT). Repeated/shared comparisons are dependent descriptive observations. |
| 2D | All seven actual/undarkened matched image arrays exactly reproduce pixel_metrics.parquet on the common mask. Recomputed pooled RMSE 0.014770650851422805 and bandwise correlations; median stored angle matches 2.0891007605071943°. Exactly 3,583 accepted footprints, 56 spatial blocks, one acquisition pair. Same native aspect/extent/EPSG:32613/mask; RGB fixed 0–0.4. No RGB pixels are display-clipped; no valid NIR residual exceeds ±0.15. None excluded from metrics for visual reasons. |

Run independent numerical/export verification:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 \
 .venv/bin/python -m examples.publication_figures.validate_figures
```

Machine-readable checks: `numerical_validation.json`, `pdf_validation.json`, `reproducibility_validation.json`. Four targeted regression contracts cover weighted PCA total variance/sign convention, disconnected support, deterministic observed representative ties, and upstream corruption rejection.

## Export and visual review

- Two main figures: 7.2 × 6.5 inches and 7.2 × 6.65 inches (182.88 mm wide, below 170 mm high); 400 dpi, 2,880 × 2,600 / 2,880 × 2,660 pixels. Combined preview 5,860 × 2,660 pixels at 400 dpi.
- Ten PDFs and ten SVGs: two main plus eight standalone panels. Eleven PNGs include the preview. Thirty-three output files total including captions.
- Editable SVG text inspected via XML and independently rendered with sharp/libvips; PDFs rendered with Poppler and inspected alongside direct PNGs. PDF text/page geometry checks confirm all ten are one page and no characters cross page boundaries. Only dense PCA markers and true imagery are rasterized; axes, curves, annotations and text remain vector.
- Visible standard labels/legends are 6.5–8.5 pt; panel letters 11 pt. Counts are 13 pt emphasis. Mathematical superscripts are naturally smaller. PDF glyph bounding boxes for rotated/math text are not literal font point sizes; style definitions and SVG text retain nominal sizes.
- Inspected all eight standalone PNGs together. Corrected initial crowded hierarchy text, representative legend, pilot strip titles, loss annotation and a standalone heatmap colorbar overflow. Final panel exports pass numerical geometry and visual review.
- Reviewed grayscale previews. Category line styles, site shapes and support symbols preserve secondary encodings; PCA category coloring and signed residual imagery are intended for color publication. Cividis provides monotone heatmap luminance; the diverging residual map is explicitly zero-centered. Fine ecological overlap is retained rather than optimized away.
- All 33 final outputs are byte-identical across consecutive complete builds with fixed authoring metadata and SVG identifiers; checked hashes in reproducibility_validation.json. Upstream scientific results remain untouched.

## Verification outcome

Full repository suite: **616 passed, 8 skipped, 29 warnings**, 122.92 s. Four new targeted contracts pass separately. Focused Ruff, strict MkDocs, local documentation links, AI-transparency regeneration and git whitespace checks pass. Logs are in `checks/`.

## Interpretation / submission limits

The strongest visual finding is retained ordering/magnitude structure of conditional inferred-PFT separation after OLI reduction, with a visible weak/borderline exception. The atlas simultaneously shows substantial overlap and within-category spread. Neither proves classification accuracy, intrinsic PFT mechanisms or mixture recoverability.

The weakest generalization is 2D: one separate R10C next-day pair, not an independent Landsat observation of the library polygons and not multisite validation. Its timestamp lag remains conditional on the legacy NEON UTC assumption. High r coexists with residual differences; no claim of universal interchangeability is warranted.

The largest unresolved manuscript concern is physical library scale: retained metadata does not justify relabeling stored values as 0–1 reflectance. This planned axis was changed to explicit stored units. Source heterogeneity, repeated years, unequal classes and species/acquisition confounding remain; PCA may reflect amplitude/environment/material structure and is descriptive. Before submission recover physical units, review taxonomy and caption length for the chosen journal, archive reproducible inputs, and add independently timed real-flight/site validation for broader claims. No scientific placeholder, invented map or fake scene was used.
