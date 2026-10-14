# Results: independent real-observation pilot

One R10C flight and one real Landsat 8 scene; 3,583 matched 30 m footprints, 56 spatial bootstrap blocks. The selected observation is next-day (+22.368 h conditional on the legacy timestamp's UTC basis), not same-day gold. No other flight or site was validated in this experiment. No new coefficient was fitted.

## 1. How similar are they?

The broad spectral signal is preserved: per-band Pearson r=0.810..0.945 and undarkened median seven-band angle=2.089 degrees. Pooled seven-band RMSE=0.014771 reflectance (1.477 reflectance percentage points); adjusted=0.014587. Mean per-pixel RMSE is 0.011845/0.011753 and is not the pooled RMSE. Good co-variation coexists with systematic contrast disagreement. Figure H is the paper overview; A provides both brightness variants with the actual image and residual maps.

## 2. Best and worst bands

Undarkened blue has lowest absolute RMSE (0.008893), while SWIR1 is largest (0.020364), followed by NIR (0.019565). Coastal has the weakest r (0.810); SWIR2 has the strongest (0.945) but still RMSE 0.017438 and negative bias -0.007968. Thus absolute magnitude accuracy and correlation produce different rankings. Adjusted coastal is best in absolute RMSE (0.008592); adjusted SWIR1 remains worst (0.020669). Band range and radiometric uncertainty differ, so this is not a universal ranking of sensor quality.

| Band | Bias undarkened | RMSE undarkened | r | Deming slope | RMSE adjusted |
|---|---:|---:|---:|---:|---:|
| coastal | +0.00168 | 0.00920 | 0.810 | 1.538 | 0.00859 |
| blue | -0.00125 | 0.00889 | 0.868 | 1.401 | 0.00894 |
| green | +0.00083 | 0.01028 | 0.908 | 1.424 | 0.00999 |
| red | +0.00237 | 0.01250 | 0.933 | 1.257 | 0.01281 |
| nir08 | +0.00960 | 0.01957 | 0.917 | 1.109 | 0.01686 |
| swir16 | -0.00187 | 0.02036 | 0.914 | 1.139 | 0.02067 |
| swir22 | -0.00797 | 0.01744 | 0.945 | 1.122 | 0.01898 |

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
