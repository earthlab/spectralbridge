# Spectral-library analytics audit — 2026-10-14

Human report: `output/pdf/spectral_library_analytics/SpectralBridge_Spectral_Library_Analytics_Report.pdf` (27 pages). Editable report_source.json / report_source.md and the ReportLab builder are retained here. This source-specific experimental audit is not a stable public prediction API or operational MESMA approval.

Read RESULTS, LIMITATIONS and RECOMMENDATIONS with DESIGN and the ten stage files. tables/ has master outputs; figures/ has PNG/PDF/SVG; models/model_index.csv links trusted local fitted models; manifests/ records sources, hashes and report sections. Earlier biological/real-sensor/mixture results are reused.

## Reproduction

Install the optional analytics extra. From repository root:

```bash
python examples/spectral_library_analytics.py Aug_2026_all_polygons_merged_pixel_extraction.parquet --compact artifacts/plant_spectral_atlas/sensor_pft_transfer/compact --output artifacts/plant_spectral_atlas/analytics --stage all --workers 2
python examples/spectral_library_analytics_results.py
python provenance/spectral-library-analytics/2026-10-14/build_explanatory_figures.py
```

The all stage completes secondary diagnostics before sealing the learning ledger, which protects its owned directory. Use a fresh output directory for a changed experiment; do not mutate completed outputs. profile measures proper-training cost; learning --first-pass is explicitly a smoke rather than full inference. extensions, domains and mixtures are separately available. The source-specific result exporter intentionally uses declared audit paths.

With ReportLab/pandas/pypdf:

```bash
python provenance/spectral-library-analytics/2026-10-14/build_report.py
python provenance/spectral-library-analytics/2026-10-14/seal_evidence.py
```

Use --source-json path/to/edited_report_source.json to render edited narrative. Figure/data values remain source-table derived; preserve evidence scope. Native stored-unit library values are not verified unitless Landsat SR.

## Scientific scope

New-plant recognition is strong in this sample. Geographic/temporal scores vary, unknowns are poorly rejected, and mixture inversion remains ambiguous without independent field validation. Three sites cannot establish global uncertainty. No deep model, source-library copy, commit or publication is part of this audit.
