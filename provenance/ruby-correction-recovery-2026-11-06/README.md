# Ruby original-photo correction experiment (P184)

This is an opt-in research workflow. It does not alter the production drone or NEON orchestrators. Both SCS+C and RossThick/LiDenseR are required; unsupported stages never become identity corrections. Historical products and the source Metashape project remain immutable.

Run from the repository root with its scientific Python environment and the official Metashape Python module available. The current machine uses a temporary module at `/private/tmp/spectralbridge-metashape-api/module`. Read-only access works without an active license; licensed mosaic build/export is unavailable here.

```bash
PYTHONPATH=/private/tmp/spectralbridge-metashape-api/module \
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/private/tmp/spectralbridge-mpl \
.venv/bin/python provenance/ruby-correction-recovery-2026-11-06/run_experiment.py
```

Use `--retrieve` only when an authenticated GoCommands client and remote access are available. The existing fixed selection is in `photo_selection.json`; `retrieve_batches.py` preserves remote-relative paths, verifies each remote MD5, records SHA256 and resumes verified files. No credentials are read or changed. Source-cache location is explicit in the frozen scripts and manifests; change it in a new experiment configuration when moving machines. Temporary source cache is not durable archival storage.

`expand_targets.py` generated the fixed 8 by 8 grid, nearest repeated track within 10 metres, at least four master observations, at most eight chronologically spaced observations, all ten bands. Selection does not optimize angular diversity or radiometric/model success. Tie-point availability still biases the sample toward trackable surfaces. NDVI and elevation strata are descriptive proxies, not independent ecological labels.

Primary response is the calibrated source pixel at the projected tracked point. The 9 by 9 median and local variation are recorded as sensitivity/quality diagnostics. Large patch variability indicates that registration and footprint differences can matter. Camera timestamps are grouped using UTC calendar minutes without assuming an integer datetime storage resolution.

`analyze.py` compares additive target intercepts with a shared linear Ross/Li shape times target-specific amplitudes. Additive angular differences are never used as multiplicative gains. Spatial target folds are fixed geographic quadrants. `matched_workflow.py` refits SCS+C only on training-target means, applies confidence/denominator/support checks, fits BRDF in that topographic space and evaluates held-out targets. Spatial and time-block bootstrap remain conditional on one flight's shared calibration.

```bash
.venv/bin/python provenance/ruby-correction-recovery-2026-11-06/analyze.py \
  --data-root /private/tmp/ruby-median-sensitivity \
  --input-file provenance/ruby-correction-recovery-2026-11-06/expanded_observations.csv \
  --response median
```

Use `--homogeneous-only` as the predeclared local-CV sensitivity (0.25); it is not a universal physical acceptance threshold. Do not select a successful subset and claim full-flight validity.

`src/spectralbridge/drone_original.py` contains reusable explicit radiometry, target-aware model, ray-intersection, temporal-grouping and masked matched-stage export helpers. Its functions are experimental and not imported into the stable top-level API. Tests use independent synthetic signals and file contracts.

`licensed_reconstruct.py` is a prepared interface for a separately licensed environment. Its current status gate refuses reconstruction. The in-memory calibrated-float replacement control was measured separately; no copied project was saved and no orthomosaic regenerated. Future licensed builds must supply complete accepted source images, masks, source binding, reviewed mosaic settings and successful held-out/full-frame checks. They must disable existing radiometric/vignetting adjustments to prevent double calibration while preserving geometric camera calibration.

Final interpretation belongs to `REPORT.md`, `correction_status.json`, the recorded regression checks and the reproducible figures from `make_figures.py`.
