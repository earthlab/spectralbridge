# Gordon, Goldhill and Ruby: full reprocess completed

**Completed and remote-verified on 2026-10-29.** All three flights from the user's figure were rebuilt from the original source data in a new workspace, with correction, four Landsat-like translation products per flight, polygon extraction, QA and a combined three-flight bulk analysis/report. Earlier tests, historical products and original Data Store collections are preserved.

| Flight | Extracted plot-pixel records | Native spectral values checked |
| --- | ---: | ---: |
| Gordon | 31,413 | 314,130 |
| Goldhill | 144,415 | 1,444,150 |
| Ruby | 22,481 | 224,810 |
| **Total** | **198,309** | **1,983,090** |

## Results and verification

- All extracted source-grid locations, polygon memberships, GlobalIDs and labels pass the independent checks. Corrected and translated raster CRS/affine transforms match the original TIFFs. The diagnostic control arithmetic differs by at most 7.51 × 10⁻⁹ pixel at Gordon (floating-point rounding); the other two report zero.
- All **274,811,292** whole-grid translation value/mask checks pass. Existing terrain masking is preserved, with no source NoData filled.
- All **12 translated extraction tables** have the same identities/labels as their native counterparts. All **3,569,562** translated table values match their backing rasters; no partial or missing table records remain.
- Bulk accepts exactly the three requested flights. It creates compact statistics, coefficients, figures and reports without an ordinary pixel-scale bulk cache. Compact result summarization does not reopen source rasters.
- **337 manifested remote files** are present with the expected sizes, with identical SHA-256 manifests. Uploads use GoCommands checksum verification. All three corrected rasters were downloaded back in full and have identical SHA-256 hashes to the local products. Four upload manifests are additional to the 337 manifested files.

## Scientific review remains necessary

Scientific QA is **caution** for all three. Goldhill has a strong visible color boundary in the corrected RGB preview. Its spatial and arithmetic checks pass, but this does not establish physically valid corrected reflectance. `goldhill_source_comparison.png` shows original/corrected displays with separate contrast stretches; it is not a quantitative radiometric comparison. The source H5 reflectance dataset has no scaling attributes, and TIFF band units are unspecified (scale 1, offset 0). No guessed rescaling, seam removal, coefficient changes or smoothing were applied.

The omitted eleventh TIFF channel remains unclassified, and acquisition/terrain provenance still needs review under P149. These are separate from the repaired spatial metadata. This is the full requested three-flight cohort, not the full 2023/2024 campaign and not independent field validation or universal sensor calibration.

## Where the products are

Local full products:
`/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products`

Permanent Data Store run collection:
`i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_20261029_v1`

The collection contains `flight_products`, `bulk_preflight`, `bulk_analysis` and `campaign_state`. For GIS, open each flight's `*__corrected.img` with its adjacent `.hdr`; preserve the pair. The flight folders are:

- `2023_AOP-GORDON-08-14-23-ExportPackage/AOP_GORDON_20230814`
- `2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814`
- `2023_AOP-Ruby-08-14-23-ExportPackage/AOP_Ruby_20230814`

The combined report is under `bulk_analysis/reports/bulk_results/bulk_translation_results.pdf`.

## Evidence and reproducibility

- `three_flight_overview.png` / `.pdf`: corrected imagery with researcher polygons; separate display contrast per flight.
- `validation_summary.json`, each package's `spatial_check` and `full_pixel_checks.json`: independent full records, geometry, values and masks.
- `translated_table_checks.json`, `remote_verification.json`, `*_upload_manifest.json`: complete extraction and transfer checks.
- `cell_execution.json`, `execution_summary.log`, `run_configuration.json`, `completed_run.json`: actual run scope and execution.
- `validated_code_snapshot.json`, `validated_workflow.patch`: ten exact code/input fingerprints and the code patch against the recorded base. Clean-base reconstruction was verified. Apply only to the clean recorded base, not over already recovered edits.
- `reprocess.py`, `verify_remote_outputs.py`, `check_translated_tables.py`, `plot_overview.py`: reproduction/checking scripts. The first performs actual authenticated downloads and separate output uploads.

Runtime fixes were narrowly tested: Gordon/Goldhill terrain headers differ from reflectance by only 1–2 coordinate ULPs, so all four corners now allow eight float64 coordinate ULPs while rejecting real shifts and preserving arrays. Exact spatial QA median/p90 calculations are grouped in bounded pixel blocks, with NumPy parity tests and a real Gordon-window comparison. No correction formula, reflectance scaling, band coefficients, geometry array or scientific assumption was changed. A potentially interrupted Goldhill table was quarantined outside the product tree and fully regenerated. Slow full-source translated-polygon extraction is retained as P155 for separate performance work.

Focused roundoff/notebook/drone, spatial/ENVI and QA regression suites pass, together with Ruff, docs links, whitespace and AI-transparency freshness checks. The run used the local macOS environment against the real Data Store; it does not test fresh Linux container installation. No commit or push was performed.
