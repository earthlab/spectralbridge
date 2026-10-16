# Primary manuscript synthesis figure

One six-panel figure composed from completed canonical analyses, without fitting models or reading the original spectral library. Final exports are in `output/figures/manuscript_synthesis/`: vector PDF/SVG and nominal 600 dpi PNG (4488 × 6210 pixels). Print dimensions: 190 × 262.89 mm. PNG metadata rounds to 599.9988 dpi. DejaVu Sans typography; white/charcoal styling. Both balanced and asymmetric layouts were rendered; the asymmetric layout gives the ten pair labels enough room. Drafts are retained separately.

## Reproduce from repository root

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m examples.manuscript_synthesis.build_figure --reuse-data
.venv/bin/python -m examples.manuscript_synthesis.write_caption
.venv/bin/python -m examples.manuscript_synthesis.validate_data
.venv/bin/python -m examples.manuscript_synthesis.validate_rebuild
pytest -q tests/test_manuscript_synthesis.py
```

`--reuse-data` reads the checksummed figure CSV bundle. Omitting it prepares that bundle from the canonical summary tables; neither path fits models. `figure_data_manifest.json` records source hashes, panel filters, fields, aggregation and units. `CAPTION.md` is the human-facing caption. `packet_manifest.json` seals final outputs, scripts, tests and packet files (excluding exploratory layout drafts and the manifest itself).

## Interpretation and display decisions

A uses annual-observation medians/IQR, not independent-plant confidence intervals; spectral values retain stored units because absolute scaling is unresolved. B is the descriptive median signed effect across four cohorts, first category minus second. Full opacity requires corrected support and consistent sign in all four; fading does not mean zero. The ±2 display range does not truncate the saved effects. Gaps remain disconnected. OLI markers are centers/FWHM, not rectangular response functions or independent satellite observations.

C shows equal-fold means and observed fold/seed ranges, not confidence intervals. Full is 360 wavelengths; no random-360 curve is invented. D uses equal-fold row-normalized confusion percentages (rounding may prevent exact row sums of 100) and aligned class recall. E uses equal held-site fold means at supported synthetic fractions. F averages per-fold macro RMSE and shows observed fold ranges. Ambiguity is specific to the saved candidate library, bins and near-fit tolerance, not exhaustive physical uncertainty.

Cornflower blue (#6495ED) identifies selected spectra in C. Related scalar blues encode signed effects/confusion in B/D. Category hues link A/D/E; charcoal Ridge120 and warm MESMA15 link E/F. Open circles and filled squares distinguish new identities and held sites where shown.

All required scientific panels are supported. Optional OLI classifier reference and tiny whole-spectrum inset were omitted for readability; OLI markers and whole-spectrum support remain documented. Absolute physical reflectance units and independent field abundance validation are unsupported. The exact-15 control changes retained diversity/training bundles and cannot isolate intrinsic algorithm superiority. The global-year prior failure remains in the complete report; this figure follows the requested new-identity/held-site focus. Lower synthetic error does not establish unique inversion.

## Canonical sources

- `provenance/publication-figures/2026-10-14/atlas_summary.csv`
- `provenance/researcher-pft-information/2026-10-15/v1/tables/cohort_wavelength_inference.csv`
- `provenance/researcher-evidence/2026-10-16/v1/tables/whole_spectrum_separability.csv`
- `src/spectralbridge/data/landsat_band_parameters.json`
- `provenance/researcher-evidence/2026-10-16/v1/tables/recognition_control_summary.csv`
- `provenance/researcher-pft-information/2026-10-15/v1/tables/complementary_feature_performance.csv`
- `provenance/researcher-pft-information/2026-10-15/v1/tables/class_specific_transfer.csv`
- `provenance/researcher-pft-information/2026-10-15/v1/tables/confusion_plot_values.csv`
- `provenance/researcher-evidence/2026-10-16/v1/tables/fraction_grid_calibration.csv`
- `provenance/researcher-evidence/2026-10-16/v1/tables/abundance_domain_summary.csv`
- `provenance/researcher-evidence/2026-10-16/v1/tables/same_candidate_ridge.csv`
- `provenance/researcher-pft-information/2026-10-15/v1/tables/abundance_by_ambiguity.csv`
- `output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf`
