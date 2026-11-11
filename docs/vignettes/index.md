# Choose a vignette

SpectralBridge has three separate pipelines. Choose the one that matches the
data you have; the bulk pipeline analyzes completed flightline products and
does not run NEON or drone processing for you.

| Pipeline | Start here | Runnable notebook | What it does |
| --- | --- | --- | --- |
| NEON flightlines | [Full NEON vignette](full-pipeline.md) | [NEON notebook][neon-notebook] | Download or read NEON HDF5; correct, convolve, extract, and review QA for individual flightlines. |
| Drone imagery | [Drone vignette](drone-processing.md) | [Drone notebook][drone-notebook] | Read local TIFF/HDF5; correct native MicaSense; optionally apply packaged affine coefficients, extract, and review QA. No convolution. |
| Bulk analysis | [Bulk vignette](bulk-analysis.md) | [Local bulk notebook][bulk-notebook] | Read already completed, immutable flightline products; fit population relationships and interpret compact outputs. |

Remote drone production is a campaign wrapper around the drone and bulk workflows,
not a fourth processing pipeline. Use the [production vignette](drone-production.md)
and [CyVerse notebook][bulk-production-notebook] to inventory ExportPackages,
enforce per-year completeness and optionally upload a verified compact closeout.

The bulk coefficient evidence comes from synthetic matched products of the
same corrected NEON source. It is diagnostic, not universal empirical sensor
calibration. Drone use of those coefficients remains an explicit opt-in with
band-level cautions and a corrected-value scale check.

## Capability map

Three pipelines support six researcher tasks. Start with the guide rather than
assembling low-level transforms yourself. A supported callable does not certify
the scientific validity of arbitrary inputs.

| Task / primary user | Expected inputs → useful outputs | Primary Python entry point | CLI / simplest example | Support |
| --- | --- | --- | --- | --- |
| NEON processing / airborne researcher | NEON directional-reflectance H5 + site/date → corrected ENVI, target bands, optional tables, QA | `spectralbridge.go_forth_and_multiply`; `process_one_flightline` for one flight | `spectralbridge-pipeline`; `python examples/run_neon_pipeline.py --check` before the [NEON guide](full-pipeline.md) | Core; real downloads require credentials and storage |
| Drone processing / UAS researcher | Supported local TIFF/H5 + verified radiometry and aligned geometry → native/corrected ENVI, optional translated bands, QA | `spectralbridge.run_drone_pipeline` | JSON runner: `python examples/run_drone_pipeline.py --check`; [drone guide](drone-processing.md) | Core orchestration; inferred viewing reconstruction remains experimental |
| Sensor translation / cross-sensor researcher | Corrected hyperspectral data and target responses, or drone data and reviewed coefficients → separately named target-band products | Existing NEON pipeline for convolution; `run_drone_pipeline(..., apply_translation=True)` for drone affine translation | Included in the producer workflows; [sensor guide](sensor-harmonization.md) | Supported configured transforms; synthetic comparisons do not establish empirical calibration |
| Library creation / field collaborator | Completed products + overlapping researcher polygons → pixel index and labeled spectral Parquet | `spectralbridge.polygons.run_polygon_pipeline_for_flightline` | Python / [polygon example](polygon-extraction.md) | Core extraction; labels and polygon definitions come from the researcher |
| Library inspection and analysis / ecologist | Existing spectral Parquet, or same-unit arrays with labels/identities → compact summaries, separability/recognition metrics, mixture diagnostics | `inspect_spectral_library_preflight`, `run_spectral_library_analysis`; explicit `spectralbridge.library_analysis` methods | `python examples/scientific_workflows_offline.py`; analysis lesson: `python examples/spectral_library_methods.py` | Core reporting; numerical analysis contracts have explicit assumptions; field abundance mapping is experimental |
| Bulk analysis / collection manager | Completed immutable flightline outputs → compact pooled/balanced/held-out statistics and reports | `spectralbridge.run_bulk_pipeline`, then `summarize_bulk_results` | `spectralbridge-bulk SOURCE --output-dir NEW_DIR --preflight-only`; [bulk guide](bulk-analysis.md) | Core; ordinary analysis does not copy all pixels |

The first two offline lessons need no credentials. The analysis lesson needs the
`analytics` extra. A configuration `--check` confirms JSON structure and options;
it does not verify a missing dataset, geometry or scientific eligibility.

[Installation and offline results](../getting-started.md) ·
[Scientific method assumptions](../api/scientific-analysis.md) ·
[Which outputs to open first](../pipeline/outputs.md)

## Start with your situation

| I want to… | Vignette |
| --- | --- |
| Run everything for a NEON flightline | [Run the full pipeline](full-pipeline.md) |
| Continue after a stopped or partial run | [Carry On My Wayward Son](carry-on-wayward-son.md) |
| Catalog many completed runs and analyze a sensor population | [Build a bulk cross-run analysis](bulk-analysis.md) |
| Process CyVerse drone ExportPackages and produce a bulk closeout package | [Remote drone production](drone-production.md) |
| Work on one part of the workflow | Choose a module below |
| Inspect labeled polygon/species spectra | [Spectral-library preflight and reporting](spectral-library.md) |
| Open a runnable Jupyter notebook | [Runnable notebook vignettes](notebook-vignettes.md) |
| Look up exact arguments, filenames, or algorithms | [Technical reference](../reference/index.md) |

## Module vignettes

The numbered modules follow the order of the main NEON workflow. Drone and
polygon workflows branch from that sequence where noted.

1. [Acquire NEON data](data-acquisition.md) — download or reuse the source HDF5.
2. [Correct NEON reflectance](neon-correction.md) — create raw and
   BRDF/topography-corrected ENVI products.
3. [Harmonize target sensors](sensor-harmonization.md) — translate corrected
   spectra into configured target-sensor bandspaces.
4. [Build analysis tables](analysis-tables.md) — work with per-product and
   merged Parquet outputs for an individual run.
5. [Review QA outputs](qa-and-analysis.md) — render and interpret the PNG and
   JSON audit artifacts.
6. [Process drone imagery](drone-processing.md) — run the separate local-HDF5
   drone workflow.
7. [Extract polygon spectra](polygon-extraction.md) — build polygon-indexed
   spectral libraries from completed products.
8. [Build a bulk cross-run analysis](bulk-analysis.md) — catalog canonical
   flightlines, derive narrow observations from persisted target-sensor ENVI,
   and fit pooled, balanced, and held-out-site synthetic translations without
   modifying individual runs. Prebuilt merged Parquets remain supported.

## How to use these pages

Every vignette answers the same four questions:

1. When should I use this module?
2. What is the smallest runnable example?
3. What files prove that it worked?
4. Where are the deeper technical details?

The vignettes teach workflow. The [technical reference](../reference/index.md)
defines contracts and implementation details.

Prefer code you can edit interactively? Every module also has one corresponding
[downloadable notebook](notebook-vignettes.md), including a carefully isolated template
for adding a custom correction between the standard topo/BRDF and convolution
stages.

[neon-notebook]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/00_full_neon_pipeline.ipynb
[drone-notebook]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/06_drone_pipeline.ipynb
[bulk-notebook]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/09_bulk_analysis.ipynb
[bulk-production-notebook]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/10_bulk_production_cyverse.ipynb
