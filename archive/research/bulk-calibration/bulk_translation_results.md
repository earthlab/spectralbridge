# SpectralBridge bulk translation results

Analysis run: `4710c6434c2bef864df516fce0dd024b1f71a345b742fdf573db193e88f9a989`

This report was calculated only from completed compact bulk-result tables. It
did not reopen source rasters, regenerate sufficient statistics, or create a
pixel-level cache.

## Collection and result counts

- Accepted flightlines: 12
- Sites (3): NIWO, WREF, YELL
- Selected observation rows represented by compact statistics: 96,016,835
- Failed or excluded source candidates: 0
- Translation pair-band combinations: 18
- Candidate coefficient rows: 54
- Successful candidate coefficient rows: 54
- Per-flightline fits: 216
- Per-site fits: 54
- Leave-one-site-out evaluations: 54

## Population overview

- Candidate slope median and range: 0.9757 (0.8881 to 1.0007)
- Candidate R-squared median and range: 0.9960 (0.5800 to 0.9999)
- Candidate RMSE median and range: 20.4358 (2.3858 to 267.0201)
- Median absolute fitted correction at each pair-band's common representative source value: 7.52%
- Largest absolute fitted correction at a representative source value: 114.27%
- Pair-bands requiring review: 12 of 18

High R-squared indicates a strong fitted relationship; it does not establish
sensor interchangeability. Compare weighting choices, per-flightline and
per-site distributions, and leave-one-site-out performance before promoting a
coefficient. Corrections are evaluated at one common source value per pair-band
(the pixel-pooled source mean unless explicitly configured), so weighting
differences are compared at the same reflectance.

Band numbers are local to each sensor. Every built-in pair is matched by shared
spectral identity and packaged center wavelength/passband; the report keeps the
separate source and target band indices visible. For example, TM blue band 1 is
the same spectral identity as OLI blue band 2, not OLI coastal-aerosol band 1.

## Pair-band screening summary

| Spectral match | Candidate slope range | Minimum candidate R-squared | Maximum absolute correction (%) | Weighting slope spread | Flightline slope IQR | Site slope range | Worst LOSO R-squared | Screening status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Coastal Aerosol: MicaSense_to-match_OLI_and_OLI-2 B1 (444 nm) → Landsat_9_OLI-2 B1 (442.8 nm) | 0.9613 to 0.9615 | 0.9998 | 3.63 | 0.0002 | 0.0022 | 0.0029 | 0.9995 | no_configured_warning_triggered |
| Coastal Aerosol: MicaSense_to-match_OLI_and_OLI-2 B1 (444 nm) → Landsat_8_OLI B1 (443 nm) | 0.9616 to 0.9617 | 0.9998 | 3.66 | 0.0001 | 0.0019 | 0.0027 | 0.9996 | no_configured_warning_triggered |
| Blue: MicaSense_to-match_OLI_and_OLI-2 B2 (475 nm) → Landsat_9_OLI-2 B2 (481.9 nm) | 0.9983 to 0.9986 | 0.9983 | 3.77 | 0.0003 | 0.0409 | 0.0516 | 0.9926 | review_required |
| Blue: MicaSense_to-match_OLI_and_OLI-2 B2 (475 nm) → Landsat_8_OLI B2 (482 nm) | 0.9986 to 0.9989 | 0.9983 | 3.83 | 0.0003 | 0.0413 | 0.0522 | 0.9925 | review_required |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_7_ETM+ B1 (482.5 nm) | 0.9798 to 0.9801 | 0.9973 | 3.07 | 0.0004 | 0.0514 | 0.0643 | 0.9881 | review_required |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_5_TM B1 (485 nm) | 0.9985 to 1.0007 | 0.9782 | 17.34 | 0.0022 | 0.1613 | 0.1971 | 0.9047 | review_required |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_9_OLI-2 B3 (561 nm) | 0.9522 to 0.9537 | 0.9955 | 7.68 | 0.0015 | 0.0629 | 0.0722 | 0.9860 | review_required |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_8_OLI B3 (561.4 nm) | 0.9521 to 0.9536 | 0.9952 | 7.81 | 0.0015 | 0.0650 | 0.0746 | 0.9849 | review_required |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_7_ETM+ B2 (565 nm) | 0.9283 to 0.9310 | 0.9853 | 12.37 | 0.0027 | 0.1086 | 0.1253 | 0.9511 | review_required |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_5_TM B2 (575 nm) | 0.9121 to 0.9167 | 0.9659 | 15.58 | 0.0045 | 0.1577 | 0.1870 | 0.8745 | review_required |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_9_OLI-2 B4 (654.3 nm) | 0.9886 to 0.9896 | 0.9935 | 9.14 | 0.0010 | 0.0575 | 0.0766 | 0.9678 | review_required |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_8_OLI B4 (654.6 nm) | 0.9890 to 0.9900 | 0.9936 | 9.14 | 0.0010 | 0.0574 | 0.0765 | 0.9681 | review_required |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | 0.9119 to 0.9228 | 0.5800 | 114.27 | 0.0109 | 0.4782 | 0.6979 | 0.1880 | review_required |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_7_ETM+ B3 (660 nm) | 0.9732 to 0.9749 | 0.9778 | 18.46 | 0.0017 | 0.1045 | 0.1518 | 0.9029 | review_required |
| Near Infrared: MicaSense_to-match_TM_and_ETM+ B4 (842 nm) → Landsat_5_TM B4 (837.5 nm) | 0.8881 to 0.8897 | 0.9962 | 9.71 | 0.0016 | 0.0076 | 0.0118 | 0.9862 | no_configured_warning_triggered |
| Near Infrared: MicaSense_to-match_TM_and_ETM+ B4 (842 nm) → Landsat_7_ETM+ B4 (837.5 nm) | 0.9766 to 0.9770 | 0.9997 | 2.16 | 0.0004 | 0.0021 | 0.0039 | 0.9991 | no_configured_warning_triggered |
| Near Infrared: MicaSense_to-match_OLI_and_OLI-2 B5 (842 nm) → Landsat_9_OLI-2 B5 (864.6 nm) | 0.9956 to 0.9958 | 0.9998 | 0.25 | 0.0002 | 0.0014 | 0.0041 | 0.9995 | no_configured_warning_triggered |
| Near Infrared: MicaSense_to-match_OLI_and_OLI-2 B5 (842 nm) → Landsat_8_OLI B5 (864.7 nm) | 0.9957 to 0.9959 | 0.9998 | 0.27 | 0.0002 | 0.0014 | 0.0042 | 0.9995 | no_configured_warning_triggered |

## Attention flags

| Spectral match | Flag | Scope | Observed | Review rule | Detail |
| --- | --- | --- | ---: | --- | --- |
| Blue: MicaSense_to-match_OLI_and_OLI-2 B2 (475 nm) → Landsat_8_OLI B2 (482 nm) | site_dependence | per_site | 0.0522 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_8_OLI B3 (561.4 nm) | flightline_heterogeneity | per_flightline | 0.0650 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_8_OLI B3 (561.4 nm) | site_dependence | per_site | 0.0746 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_8_OLI B4 (654.6 nm) | flightline_heterogeneity | per_flightline | 0.0574 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_8_OLI B4 (654.6 nm) | site_dependence | per_site | 0.0765 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Blue: MicaSense_to-match_OLI_and_OLI-2 B2 (475 nm) → Landsat_9_OLI-2 B2 (481.9 nm) | site_dependence | per_site | 0.0516 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_9_OLI-2 B3 (561 nm) | flightline_heterogeneity | per_flightline | 0.0629 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Green: MicaSense_to-match_OLI_and_OLI-2 B3 (560 nm) → Landsat_9_OLI-2 B3 (561 nm) | site_dependence | per_site | 0.0722 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_9_OLI-2 B4 (654.3 nm) | flightline_heterogeneity | per_flightline | 0.0575 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Red: MicaSense_to-match_OLI_and_OLI-2 B4 (668 nm) → Landsat_9_OLI-2 B4 (654.3 nm) | site_dependence | per_site | 0.0766 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_5_TM B1 (485 nm) | flightline_heterogeneity | per_flightline | 0.1613 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_5_TM B1 (485 nm) | site_dependence | per_site | 0.1971 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_5_TM B2 (575 nm) | flightline_heterogeneity | per_flightline | 0.1577 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_5_TM B2 (575 nm) | site_dependence | per_site | 0.1870 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | flightline_heterogeneity | per_flightline | 0.4782 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | large_fitted_correction | candidate_weightings | 114.2739 | above 20.0000 | At least one weighting implies a large fitted correction at the common representative source value. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | site_dependence | per_site | 0.6979 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | weak_flightline_fit | per_flightline | 0.4771 | below 0.9000 | Weakest flightline: NEON_D16_WREF_DP1_L030-1_20230624_directional_reflectance. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | weak_global_fit | candidate_weightings | 0.5800 | below 0.9000 | At least one global weighting has R-squared below the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | weak_loso_transferability | leave_one_site_out | 0.1880 | below 0.8000 | Weakest held-out site: WREF. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_5_TM B3 (660 nm) | weak_site_fit | per_site | 0.5015 | below 0.9000 | Weakest site: WREF. |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_7_ETM+ B1 (482.5 nm) | flightline_heterogeneity | per_flightline | 0.0514 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Blue: MicaSense_to-match_TM_and_ETM+ B1 (475 nm) → Landsat_7_ETM+ B1 (482.5 nm) | site_dependence | per_site | 0.0643 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_7_ETM+ B2 (565 nm) | flightline_heterogeneity | per_flightline | 0.1086 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Green: MicaSense_to-match_TM_and_ETM+ B2 (560 nm) → Landsat_7_ETM+ B2 (565 nm) | site_dependence | per_site | 0.1253 | above 0.0500 | Per-site slopes span more than the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_7_ETM+ B3 (660 nm) | flightline_heterogeneity | per_flightline | 0.1045 | above 0.0500 | The middle half of per-flightline slopes spans more than the configured review threshold. |
| Red: MicaSense_to-match_TM_and_ETM+ B3 (668 nm) → Landsat_7_ETM+ B3 (660 nm) | site_dependence | per_site | 0.1518 | above 0.0500 | Per-site slopes span more than the configured review threshold. |

## Interpretation boundary

The thresholds below are configurable screening aids, not universal scientific
acceptance criteria. `no_configured_warning_triggered` means only that these
rules did not fire. It does not approve empirical calibration, extrapolation to
an unseen reflectance domain, or transfer to a site unlike those evaluated.

```json
{
  "absolute_correction_review_threshold_pct": 20.0,
  "correction_denominator_floor": 1e-08,
  "figure_dpi": 150,
  "flightline_slope_iqr_review_threshold": 0.05,
  "loso_r2_review_threshold": 0.8,
  "r2_review_threshold": 0.9,
  "representative_source_value": null,
  "site_slope_range_review_threshold": 0.05,
  "weighting_slope_spread_review_threshold": 0.05
}
```

## Figures

![translation_coefficients_and_fit](../../figures/bulk_results/diagnostics/translation_coefficients_and_fit.png)

![fitted_correction_magnitude](../../figures/bulk_results/diagnostics/fitted_correction_magnitude.png)

![stability_and_transferability](../../figures/bulk_results/diagnostics/stability_and_transferability.png)
