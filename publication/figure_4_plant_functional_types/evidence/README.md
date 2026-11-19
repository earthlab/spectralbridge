# Evidence index for current Figure 4

## Current primary HLS analysis

- `landsat_hls_primary_reference_observations.csv`: 496 cells, 24 spatial patches,
  nominal 30 m cover >=95%; reference bases and support flags retained.
- `landsat_hls_figure_table_summary.csv`: current per-PFT table values.
- `landsat_exploratory_patch_separability.csv`: current exact NPC tests and statuses.
- `landsat_exploratory_held_out_predictions.csv`: current whole-patch/region and
  secondary pixel predictions; use unit=patch, scheme=leave_one_patch_out for B.
- `landsat_exploratory_patch_median_spectra.csv`: 24 direct-reflectance patch medians.
- `landsat_hls_pairwise_*`: secondary balanced-accuracy diagnostic and predictions.
- `landsat_hls_methods_and_results.md`: current methods, values and limitations.
- HLS analysis/reference manifests, expansion provenance and additional review
  policy identify the exact current inputs and cover-only added references.

## Current full-source-area sensitivity

`landsat_hls_expanded_source_support_reference_observations.csv` contains 161 cells
in 13 patches. `landsat_hls_expanded_source_support_sensitivity_*` holds its
separate analyses. Do not combine these records with the primary cohort: they
are a selected subset, not another sample.

## Retained historical evidence

`landsat_hls_strict_reference_observations.csv` is the **previous 114-cell** strict
cohort, not the current 161-cell sensitivity. `landsat_hls_previous_strict_*`,
`landsat_hls_nominal_sensitivity_*` (previous 382-cell cohort), all C2, normalized,
photo-screened, matched-test and geography-audit files are earlier stages retained
for audit. They are not current Figure 4 HLS inputs. NEON and drone evidence is
unchanged. The numeric source table and companion caption govern current display.

## Spectral Panel A now uses the same HLS cohort

`data/spectral_observations_by_footprint.csv` and its summary contain HLS L30
NBAR as the real-Landsat sensor. Current input counts are77/110/99/165/45 in
plot order. `historical_c2_spectral_observations.csv` and its historical summary
retain the old276-cell Niwot curves only for audit; they are never renderer
inputs. `update_hls_spectral_inputs.py` rebuilds A from the same local primary
HLS observations whose hash is recorded in the current statistical manifest.
