# P185 Ruby topographic recovery

The experimental workflow compares native/1/3/10m Gaussian terrain scales, explicit finite-radius shadows, descriptive/field-labelled populations, spatial OLS/balanced/Huber fits, SCS+C/C-correction/Minnaert, synthetic identifiability, matched original-photo BRDF and full 10cm factor/support diagnostics. Both correction stages remain required. Unsupported observations remain missing; no source data or P183/P184 evidence is overwritten.

Run from the repository root:

```bash
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/private/tmp/spectralbridge-mpl \
.venv/bin/python provenance/ruby-topographic-recovery-2026-11-06/run.py
```

Inputs are the verified P184 calibrated 10cm TIFF, recovered absolute viewing DEM and ground DTM, original-photo observation table, P183 metadata and existing half-diameter field polygons. No new raw-photo downloads or licensed Metashape operations are required. Actual paths/checksums are recorded in `source_manifest.json`; moving machines requires rehydrating those sources and using a distinct configured run. Temporary source-cache paths are not archival storage.

Each stage hashes inputs, relevant implementation and outputs. An unchanged completed stage is reused; changed completed experiments require a distinct run, preserving previous evidence. Progress reports stage and bounded full-frame row counts. The runner does not publish or upload anything.

`REPORT.md` is the human-readable interpretation, `decision.json` the production decision, `models.json` the candidate/uncertainty evidence and `spatial_holdouts.csv` the spatial comparison. `matched_common_support.csv` compares methods on identical original-target support. `full_frame_support.csv` reports all ten bands; diagnostic red factor/parameter-bound/support TIFFs are under `archive/local/ruby-topographic-recovery-2026-11-06/`. They are not corrected reflectance products.

The reusable opt-in helpers live in `spectralbridge.drone_topography`; they are not production defaults or top-level stable API exports. The P184 negative-branch diagnostic issue is audited without modifying historical files. Experimental numerator and denominator intervals must stay positive; negative C itself is not prohibited. No gains are clipped.

Shadow rays cover a declared 100m radius at 0.5m steps. Unknown coverage is distinct from sunlit. Original-photo context uses the common grid; full-frame diagnostics repeat visibility at 10cm source locations. Spectral darkness and inferred ecological strata are separate diagnostic variables; existing field labels do not establish ground reflectance.

`final_checks.json` records tests, source preservation, restart reuse and figure review. The full package/release suite is not claimed green. No corrected Ruby orthomosaic is approved merely because a subset has numerically supported factors.
