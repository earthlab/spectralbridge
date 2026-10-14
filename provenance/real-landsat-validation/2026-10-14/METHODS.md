# Methods: what is being tested

## Physical comparison and units

The unit is one actual NEON flight, R10C L002-1, 2021-09-15. Archived real H5 dimensions are 1,115 x 5,351 x 426 at 1 m, EPSG:32613; it is not a synthetic fixture. The canonical pipeline exported the raw cube, fit scene-wide BRDF/topographic correction and generated Gaussian OLI-like channels at 443, 482, 561.4, 654.6, 864.7, 1608.9 and 2200.7 nm. Runtime processing strips were 32 rows; scientific scene fits were unchanged. This is a simulation using implemented Gaussian responses, not an exact measurement of every Landsat relative spectral response or PSF.

`olioli_undarkened` means corrected NEON convolved to OLI-like bands without the packaged multiplicative brightness gains. `olioli` applies those existing band-specific gains. Both are derived from the same corrected NEON data. Neither is a Landsat observation. Source scale divisor 10,000 was inherited explicitly from H5 and ENVI metadata. Landsat SR uses official DN * 0.0000275 - 0.2; fill 0 and DN outside 1..65,455 are missing. Finite negative or >1 reflectance is not silently clipped. Analysis is in unitless reflectance, not percent.

The brightness file describes synthetic sensor differences. It does not identify empirical Landsat training scene IDs. No evidence of fitting to this scene was found, but the complete independence of historical gain training cannot be established without those IDs. No gains, offset, calibration or response definitions were fitted or changed here. Undarkened is the cleanest primary independent real-observation test.

## QA and actual pixel support

QA_PIXEL bits 0..5 reject fill, dilated cloud, cirrus, cloud, shadow and snow. QA_RADSAT rejects saturation in B1..7 and terrain occlusion bit 11. Water remains a valid physical surface, with its flag preserved. The QA figure distinguishes these causes. Cloud-distance values are conservative distances to flagged cloud/shadow/unknown halo boundaries, not proof of aerosol-free skies.

Actual Landsat 30 m cell boundaries define the observation. Exact source-cell intersection areas weight the 1 m NEON means and within-cell population variances; neither upsampling nor nearest-point matching creates replicates. The primary gate is valid NEON intersection area / FULL Landsat cell area >=0.90, using joint all-seven-band support of both variants. Geometric coverage, fraction valid within covered area, full-cell valid coverage and number of intersecting valid source pixels are distinct saved fields. Partial intersections contribute area weights, not whole-pixel counts. All variants use identical source and Landsat support. Cross-CRS fallback intersects transformed source-cell corner polygons in the destination projected CRS; it approximates curved cell edges and is slower. Registration offsets currently require matching projected CRS and are refused otherwise.

## Agreement statistics and regression

x is real Landsat; y is aggregated synthetic OLI. Residual y-x is positive when SpectralBridge is brighter. N counts matched actual footprints, not independent ecological samples. Mean and median bias describe offset; MAE is typical absolute discrepancy; RMSE weights large discrepancies more strongly. RMSE / observed Landsat IQR is a dimensionless range-normalized diagnostic, not a universal accuracy percentage. Pearson describes linear co-variation, Spearman rank co-variation. Correlation squared is explicitly distinct from identity R-squared, 1-SSE(y-x)/SST(x), which can be negative. None proves agreement by itself.

Both axes contain error. Descriptive Deming regression uses error-variance ratio lambda = Var(error_y)/Var(error_x) = 1; sensitivity ratios 0.25 and 4 remain in tables. This is equal-error orthogonal regression, not a justified estimate of the actual sensor error ratio. Major-axis regression imposes a different variance-based slope assumption; OLS treats x as error-free. Deming with disclosed lambda is preferable here as a descriptive agreement slope, while bias/RMSE against the 1:1 line remain primary. Slope 1 and intercept 0 describe identity. No regression is used to correct the validation data.

Bland-Altman plots put difference against pair mean. Mean +/-1.96 residual SD is a descriptive normal-reference spread, not a confidence interval or guaranteed 95% coverage under heteroscedasticity. Empirical 2.5/97.5 residual percentiles and Spearman(abs residual, brightness) supplement it. Residual spatial structure can remain even with small average bias.

## Uncertainty and replication

Fixed 10x10 Landsat-cell blocks (300 m) are resampled 499 times with seed 20261014; 56 occupied blocks contribute. Percentile 95% intervals summarize within-flight spatial uncertainty conditional on this block size, scene, masks and alignment. They do not account for unknown atmosphere/calibration error, prove blocks independent, or substitute for flight/site replication. No independent-pixel p-values are reported. Both products share bootstrap draws; adjusted-minus-undarkened differences are paired. CIs are descriptive, not multiplicity-adjusted bandwise significance tests. Across-flight summaries equally weight flight metrics; n=1 is explicitly marked insufficient for cross-flight inference.

## Shape, images, sensitivity and failures

Seven-band spectral angle is the arccosine of normalized vector dot product in degrees; zero vectors return missing. Angle measures shape but ignores pure amplitude scaling. Per-pixel multiband RMSE and pooled seven-band RMSE retain amplitude discrepancy; mean per-pixel RMSE is a different statistic and is named separately. Normalized cross-correlation adds little beyond band Pearson, and SSIM depends on a chosen stretch/window/dynamic range and missing-data treatment; neither is used as a primary reflectance endpoint. Fixed RGB stretch 0..0.4 is identical for both images, grid, extent and mask. Scatterplots retain every accepted outlier. Map color saturation is disclosed and never alters statistics.

Nine declared source offsets (-30,0,+30 m east/north) are evaluated on the intersection of all eligible shifted supports. The original alignment remains primary; the lowest sensitivity error is disclosed without fitting/applying a shift. Low/high heterogeneity tertiles use RMS of the seven NEON within-footprint SDs. Coverage >=99%, conservative cloud distance >=90 m and same-day gold subsets are reported without removing difficult cases from the primary set. These overlapping descriptive subsets confound cover/brightness and do not causally isolate error sources. Same-day gold has N=0. View, sun angle, time, year, site and flight each have one selected-scene value: their independent effects and temporal decay cannot be estimated. No independent land-cover labels were supplied; QA water is descriptive, not a cover map.

Full corrected NEON includes BRDF/topographic normalization whereas Landsat LaSRC SR remains directional under its observation geometry. Different atmosphere, view/solar geometry, PSF, registration, surface change and spectral response approximation can all contribute. Residuals are cross-product discrepancies, not pure algorithm error.

## Reproduce

From the repository root, prepare the archived full flight with `python provenance/real-landsat-validation/2026-10-14/prepare_pilot.py`, then run `python examples/real_landsat_validation.py artifacts/real_landsat_validation/flight_input.json --cached-search provenance/real-landsat-validation/2026-10-14/search_items.json --output artifacts/real_landsat_validation/R10C_20210915`. Public asset access requires network and optional cloud dependencies. Omitting --cached-search makes a fresh declared-window search. Then run `python provenance/real-landsat-validation/2026-10-14/finalize_pilot.py`. Full raw/corrected source cubes are not copied into provenance or Git. Cache/results are checksum-reused only for matching source/configuration/code identity. Compact provenance evidence is intentional, not a general pixel cache.

## Primary references

- USGS Collection 2 Level-2 SR and official scaling: https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products
- USGS QA bit definitions: https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
- Planetary Computer STAC: https://planetarycomputer.microsoft.com/docs/reference/stac/
- NEON general data/time conventions: https://www.neonscience.org/data-samples/data-management/data-formats-conventions
- Errors-in-variables / orthogonal distance rationale: https://docs.scipy.org/doc/scipy/reference/odr.html (analytic Deming used; no deprecated ODR dependency).
