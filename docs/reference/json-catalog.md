# JSON file catalog

SpectralBridge uses JSON for three different jobs: installed scientific
parameters, run-specific correction/QA records, and validation or governance
evidence. They should not be edited or interpreted in the same way.

This catalog documents active JSON files without inserting new keys into
runtime schemas that existing loaders may not recognize.

## Packaged scientific parameters

Installed code reads these files from `src/spectralbridge/data/`. This location
is authoritative.

| File | What it controls | Units and structure | Loaded by | How to validate a change |
| --- | --- | --- | --- | --- |
| `src/spectralbridge/data/landsat_band_parameters.json` | Target sensor band centers and Gaussian full widths at half maximum used for convolution/resampling | Nanometers; every sensor entry has equal-length `wavelengths` and `fwhms` arrays | `standard_resample.py`, pipeline convolution, sensor-panel plots | Run resampling/convolution tests; inspect output band count, wavelengths, support, and QA |
| `src/spectralbridge/data/hyperspectral_bands.json` | Reference hyperspectral wavelength axis for sensor-panel visualization | Nanometers in one ordered `bands` array | `sensor_panel_plots.py` | Confirm ordering, numeric values, and expected panel wavelength range |
| `src/spectralbridge/data/brightness/landsat_to_micasense.json` | Percent brightness adjustment coefficients for the general Landsat-to-MicaSense comparison | `system_pair`, human-readable `description`, `unit: percent`, and string band indices | `brightness_config.py` | Run `tests/test_brightness_coefficients.py`; inspect the convolution stage's `brightness*.png` fitted-versus-configured coefficient profiles |
| `src/spectralbridge/data/brightness/landsat_tm_etm_to_micasense.json` | Percent coefficients for the TM/ETM+-specific comparison | Wavelength-aligned Landsat-like order; not native Landsat numbering | `brightness_config.py` | Run coefficient tests and the Python `brightness_correction_metrics`/`render_brightness_diagnostics` workflow before accepting scientific changes |

The same band-definition filenames under repository-root `data/` are
example/notebook copies. Installed package code does **not** load those copies.
If a scientifically reviewed value changes, update both locations deliberately
and keep the packaged file authoritative.

## Example run configurations

These are intentionally self-documenting and are consumed only by the wrappers
in `examples/`. Their `about` blocks are explanatory metadata; the wrappers pass
only the nested `pipeline` object to SpectralBridge.

| File | Purpose | Run safely |
| --- | --- | --- |
| `examples/config/neon_pipeline.example.json` | Complete NEON download-through-QA run | `python examples/run_neon_pipeline.py --check` |
| `examples/config/drone_pipeline.example.json` | Local drone HDF5 correction/extraction/QA run | `python examples/run_drone_pipeline.py --check` |

Copy an example before adapting it for a study. Record the copy with the output
or analysis repository so parameters remain reproducible.

## Validation and transparency records

| File | Meaning | Edit policy |
| --- | --- | --- |
| `validation/campaigns/neon-live-100.example.json` | A proposed live campaign specification and resource checklist | Populate deliberately before a live campaign; it is not evidence that runs occurred |
| `validation/results/offline-contract.json` | Generated observations from deterministic offline function contracts | Treat as generated evidence; regenerate with `scripts/run_validation_campaign.py` |
| `docs/ai-transparency.json` | Generated machine-readable summary of `PROMPT_LOG.md` | Do not hand edit; regenerate with `scripts/generate_ai_transparency.py` |

## JSON produced by a pipeline run

These files normally do not live in the repository because they belong to one
flightline or run.

| Filename pattern | Meaning | Consumer / check |
| --- | --- | --- |
| `*_brdfandtopo_corrected_envi.json` | Run-specific geometry, masks, paths, and correction parameters used to create the corrected ENVI pair | `stage_apply_brdf_topo_correction`; must parse and match the flightline |
| `*_brdf_model.json` | Fitted BRDF coefficient model for the scene | Correction implementation and `diagnose_brdf_topo_stage.py` |
| `*_qa.json` | Machine-readable diagnostic summary paired with the QA PNG | Users, tests, publication/validation review |
| `drone_qa_summary.json` | Batch-level drone provenance, status counts, paths, and failure details | Drone users and QA review |
| `qa_plots/*__MS_vs_Landsat_FIXED.json` | Per-flightline sampled synthetic MicaSense/Landsat regression diagnostic | QA inspection only; not a pooled coefficient source |
| `synthetic_translation_coefficients.json` | Exact pooled regression records written by the independent bulk pipeline | Bulk analysis and reviewed downstream translation work |
| `bulk_manifest.json` | Bulk source inventory signature, settings, counts, and output names | Restart validation for `run_bulk_pipeline` |

Run-specific JSON is evidence. Keep it next to the artifacts it describes and
do not reuse it for a different flightline merely because the filename looks
similar.

## Before changing any coefficient or band definition

1. Identify the authoritative packaged JSON and the Python loader above.
2. Record where the proposed value came from and its units.
3. Confirm band indices are wavelength-aligned rather than assumed native
   sensor numbers.
4. Add or update a focused test.
5. Run the related convolution or coefficient plot and inspect the QA output.
6. Keep the old and new values traceable in version control.

Changing scientific JSON is a scientific-method change, not a formatting task.
