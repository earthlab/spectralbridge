"""Freeze compact pilot evidence and generate source-specific human interpretation.

Run after the reusable one-flight CLI completes. Does not modify analytical data.
"""

from pathlib import Path
import hashlib
import json
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "artifacts/real_landsat_validation/R10C_20210915"


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


manifest = json.loads((RUN / "statistics_manifest.json").read_text())
assert manifest["status"] == "complete_single_flight"
assert all(sha(RUN / n) == h for n, h in manifest["outputs"].items())
for path in RUN.glob("*"):
    if path.is_file() and (path.suffix in [".csv", ".parquet", ".json"]):
        shutil.copy2(path, OUT / path.name)
shutil.copytree(RUN / "figures", OUT / "figures", dirs_exist_ok=True)
for name in ["flight_input.json", "pilot_products.json"]:
    shutil.copy2(RUN.parent / name, OUT / name)

bands = pd.read_csv(RUN / "band_metrics.csv")
flights = pd.read_csv(RUN / "flight_metrics.csv")
subsets = pd.read_csv(RUN / "subset_metrics.csv")
brightness = pd.read_csv(RUN / "brightness_comparison.csv")
pixels = pd.read_parquet(RUN / "pixel_metrics.parquet")
registration = pd.read_csv(RUN / "registration_sensitivity.csv")
assert (
    len(pixels) == 3583
    and not pixels.duplicated(["landsat_product_id", "row", "col"]).any()
)
assert pixels.valid_coverage_fraction.min() >= 0.9
assert bands.N.nunique() == 1 and bands.N.iloc[0] == len(pixels)
assert registration.N.nunique() == 1

search = """# Landsat search and selection

Source: Planetary Computer STAC, collection `landsat-c2-l2`. Saved unsigned `search_items.json` contains all eight returned items and asset metadata. Search covered the flight footprint and calendar dates 2021-08-30 through 2021-10-01 (exclusive end 2021-10-02); individual exact-hour window indicators remain in `scene_candidates.csv`. Calendar boundary scenes can fall slightly beyond 16 x 24 hours.

Three candidates are Landsat 8 OLI Collection 2 Level-2: September 16, September 7, August 31. Five ETM+ candidates remain in the ledger but cannot validate the seven OLI channels, including coastal. The same-day September 15 ETM+ scene is explicitly excluded for sensor incompatibility, not poor agreement.

The selected product is **LC08_L2SP_033032_20210916_20210925_02_T1**, STAC item LC08_L2SP_033032_20210916_02_T1. Actual timestamp: 2021-09-16 17:37:35.213645 UTC; cloud cover 0.19%; sun elevation 48.4929 degrees; sun azimuth 151.4204 degrees. Footprints/platform/sensor/collection/level and every candidate are machine-readable. September 16 had 3,583 usable pixels out of 3,600 with sufficient NEON coverage (99.5278%). Older compatible candidates each had 3,600; the next-day scene won by the predeclared temporal-first ranking, not better agreement.

For this **one** flight: compatible same-day availability 0/1; <=1, <=3 and <=7 days each 1/1 under the stated UTC interpretation. Across-flight availability rates cannot be estimated. Same-day any-sensor availability is 1/1, but ETM+ cannot be substituted for OLI.

The legacy H5 timestamp is `2021-09-15, 191530 [Computer Time in sec]`, without an explicit timezone. UTC is an interpretation based on NEON's general convention, not independently verified for this legacy field. The +22.3681 h time difference and <=1-day classification are conditional on that basis. The September 16 versus September 15 calendar-day distinction is clear; no near-simultaneous gold-standard claim is made.

Only selected seven-band SR and candidate QA crops were read. Ephemeral signed access tokens are not evidence; saved item URLs are unsigned. The raster-window cache is ignored by Git, identified by checksums in the original run manifest. No full Landsat scene was downloaded.
"""
(OUT / "LANDSAT_SEARCH.md").write_text(search)
methods = """# Methods: what is being tested

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
"""
(OUT / "METHODS.md").write_text(methods)
rows = [
    "| Band | Bias undarkened | RMSE undarkened | r | Deming slope | RMSE adjusted |",
    "|---|---:|---:|---:|---:|---:|",
]
for _, r in bands[bands.variant.eq("undarkened")].iterrows():
    a = bands[(bands.variant.eq("adjusted")) & bands.band.eq(r.band)].iloc[0]
    rows.append(
        f"| {r.band} | {r.mean_bias:+.5f} | {r.RMSE:.5f} | {r.Pearson_r:.3f} | {r.deming_slope:.3f} | {a.RMSE:.5f} |"
    )
results = (
    """# Results: independent real-observation pilot

One R10C flight and one real Landsat 8 scene; 3,583 matched 30 m footprints, 56 spatial bootstrap blocks. The selected observation is next-day (+22.368 h conditional on the legacy timestamp's UTC basis), not same-day gold. No other flight or site was validated in this experiment. No new coefficient was fitted.

## 1. How similar are they?

The broad spectral signal is preserved: per-band Pearson r=0.810..0.945 and undarkened median seven-band angle=2.089 degrees. Pooled seven-band RMSE=0.014771 reflectance (1.477 reflectance percentage points); adjusted=0.014587. Mean per-pixel RMSE is 0.011845/0.011753 and is not the pooled RMSE. Good co-variation coexists with systematic contrast disagreement. Figure H is the paper overview; A provides both brightness variants with the actual image and residual maps.

## 2. Best and worst bands

Undarkened blue has lowest absolute RMSE (0.008893), while SWIR1 is largest (0.020364), followed by NIR (0.019565). Coastal has the weakest r (0.810); SWIR2 has the strongest (0.945) but still RMSE 0.017438 and negative bias -0.007968. Thus absolute magnitude accuracy and correlation produce different rankings. Adjusted coastal is best in absolute RMSE (0.008592); adjusted SWIR1 remains worst (0.020669). Band range and radiometric uncertainty differ, so this is not a universal ranking of sensor quality.

"""
    + "\n".join(rows)
    + """

All values are unitless SR; full spatial-block uncertainty, lambda sensitivity, empirical residual spread and identity R-squared are in band_metrics.csv.

## 3. What explains disagreement?

Small bias does not remove discrepancy: all seven undarkened Deming slopes exceed 1 (1.109..1.538); their conditional 95% intervals also exceed 1, indicating contrast mismatch under equal-error assumptions. Absolute errors vary with brightness (Bland-Altman panels). Error and NEON heterogeneity have descriptive Spearman rho=0.544 undarkened / 0.529 adjusted. Homogeneous and heterogeneous thirds each contain 1,195 footprints; pooled undarkened RMSE is 0.010324 versus 0.018992. This is consistent with mixed spatial support contributing, but does not separate land cover, PSF, correction artifacts or temporal effects. One date pair cannot isolate temporal mismatch or atmosphere. Cloud-distance rho is positive (0.341), so proximity alone does not explain this pilot's dominant residuals; the proxy and cover confounding prevent a causal cloud conclusion.

## 4. Does the brightness adjustment help?

NIR RMSE improves 0.019565 -> 0.016857; paired difference -0.002709 (95% spatial-block interval -0.003342..-0.002084). Coastal and green RMSE also decrease. Red worsens 0.012501 -> 0.012813 and SWIR2 worsens 0.017438 -> 0.018980; SWIR2 difference +0.001542 (0.001267..0.001867). Blue and SWIR1 point estimates worsen, but their paired RMSE intervals span zero. Gains leave Pearson effectively unchanged, as expected from positive bandwise scaling.

Pooled RMSE changes -0.000184, approximately 1.24% lower, but its paired 95% interval is -0.000440..+0.000041. Median angle changes -0.0224 degrees with interval -0.0377..+0.0187. Neither overall interval excludes zero. In the homogeneous third, adjusted RMSE (0.010559) is slightly worse than undarkened (0.010324). This is mixed, scene-conditional evidence; it does not validate a universal adjustment or justify choosing it solely by intent.

## 5. Variation among flights/sites?

Not estimable: n=1 flight, n=1 site, n=1 selected acquisition pair. across_flight_metrics.csv provides the requested schema with number_of_flights=1 and explicit single-flight status; min/max equality is not evidence of low between-flight variability. Thousands of pixels cannot substitute for acquisition replication.

## 6. Same-day, homogeneous, well-aligned pixels?

Same-day gold N=0. Homogeneity improves descriptive RMSE substantially, as above. Original alignment is lowest among the nine declared offsets: median per-band undarkened RMSE=0.012346 on their shared support; one-pixel east/west shifts give 0.020101/0.020525 and all nonzero shifts are worse (range 0.020101..0.026856). This supports retaining original alignment but does not rule out subpixel offsets or spatially varying geolocation. No shift was applied. Coverage >=99% gives undarkened pooled RMSE=0.014723 (N=3,507), close to primary 0.014771, so residual error is not confined to partial edges.

## 7. Failure modes?

Worst accepted per-pixel seven-band RMSE is 0.104708 with angle about 11 degrees, full coverage and heterogeneity 0.2354. Other worst pixels form a local cluster near native rows 4661..4662, cols 914..918 with RMSE 0.066..0.086 despite full coverage and clear QA. Figure F exposes actual paired patches, not just a favorable example. These failures survive snow/cloud/shadow/saturation exclusion; QA is not perfect atmospheric truth. Some are heterogeneous, while others are not, so heterogeneity alone cannot explain all failures. Brightness/contrast differences, local processing or sensor/geolocation/PSF differences remain hypotheses; no unobserved cause is asserted. Worst pixels remain in all primary statistics.

## 8. Accurate enough for scientific comparison?

Enough to justify a qualified, acquisition-matched spectral comparison and continued validation, not sensor interchangeability, subtle change detection, independent PFT classification performance or universal calibrated reflectance. A use-specific tolerance/error budget must precede an adequacy decision. The one-flight RMSE and band biases must be propagated or considered for any effect of comparable size. Same-day/site replication, true response/PSF evaluation and timestamp verification remain necessary.

## 9. Defensible manuscript claim

"For one R10C NEON flight compared with a next-day Landsat 8 Collection 2 Level-2 surface-reflectance observation, area-weighted aggregation to 3,583 actual Landsat footprints preserved broad spectral co-variation (bandwise r=0.81-0.95; median seven-band angle 2.09 degrees), with pooled undarkened RMSE 0.0148 reflectance and persistent band-dependent contrast discrepancies. Existing brightness gains had mixed bandwise effects and no clear overall improvement under within-flight spatial-block bootstrap uncertainty. These findings establish a real-observation pilot, not cross-flight or cross-site sensor interchangeability." State the conditional legacy UTC basis alongside exact time difference if reporting it.

## 10. What should change?

Retain both products and expose the mixed adjustment outcome; do not refit global gains from this pilot. Keep strict full-cell coverage, joint masks and real Landsat scale/QA as the validation contract. Fix physical wavelength metadata at its production source (tracked separately) rather than infer it from headers containing band_01 strings. Before bulk validation, verify legacy timestamp timezone and historical brightness-training IDs, add genuinely independent flight/site/date pairs including same-day OLI, examine finer subpixel registration and response/PSF differences, and check spatial-block-size sensitivity. Current 300 m/499-draw intervals are conditional pilot uncertainty. Do not scale to all flights automatically based on favorable r. The existing synthetic ecological transfer evidence remains a different validation level.
"""
)
(OUT / "RESULTS.md").write_text(results)
# Preserve original cache-aware manifest; add a separate portable evidence ledger.
(OUT / "evidence_manifest.json").write_text(
    json.dumps(
        {
            "analysis_manifest_sha256": sha(RUN / "statistics_manifest.json"),
            "run_root": str(RUN),
            "copied_files": {
                str(p.relative_to(OUT)): sha(p)
                for p in OUT.rglob("*")
                if p.is_file() and p.name != "evidence_manifest.json"
            },
        },
        indent=2,
    )
    + "\n"
)
print("Verified compact evidence, reports and 30 figure files frozen.")
