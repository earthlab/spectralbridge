# Extending

Use this page when adding a target sensor, a QA output, or a new writer that
feeds the canonical pipeline outputs. SpectralBridge does not currently have a
runtime sensor registry; supported sensors are defined through package data,
path helpers, and pipeline functions.

## Adding a target sensor

1. Add the sensor band centers and FWHM values to
   `src/spectralbridge/data/landsat_band_parameters.json`.
2. Add a canonical output suffix to `FlightlinePaths.sensor_products` in
   `src/spectralbridge/paths.py`.
3. Mirror the same suffix in `spectralbridge.utils.naming.get_flight_paths` if
   the legacy dictionary path helper needs to resolve the product.
4. Check sensor-name aliases in
   `spectralbridge.pipelines.pipeline._safe_resolve_sensor_entry`.
5. Add or update tests near `tests/test_pipeline_convolution.py`,
   `tests/test_paths.py`, and `tests/test_file_sort.py`.
6. Update [Naming conventions](../naming-conventions.md) and
   [Outputs](../pipeline/outputs.md) so docs match the new filenames.

## Adding brightness coefficients

Brightness coefficients live under `src/spectralbridge/data/brightness/` and
are loaded with `spectralbridge.brightness_config.load_brightness_coefficients`.
Add tests near `tests/test_brightness_coefficients.py` when introducing or
renaming a coefficient table.

## Adding QA or export outputs

QA artifacts are part of the public output contract. Preserve these names unless
the change is explicitly coordinated across code, tests, and docs:

- `<flight_id>_qa.png`
- `<flight_id>_qa.json`
- optional `<flight_id>_qa.pdf`
- `<flight_id>_merged_pixel_extraction.parquet`

Update [QA panels & metrics](../pipeline/qa.md), [Outputs](../pipeline/outputs.md),
and tests under `tests/test_qa/` when adding metrics or changing payload
structure.

## Quick verification

Run focused tests first:

```bash
pytest -q tests/test_pipeline_convolution.py tests/test_paths.py tests/test_file_sort.py
pytest -q tests/test_qa
```

Then run the public API smoke matrix:

```bash
pytest -q tests/test_public_api_smoke.py
```

## Pitfalls

- Do not construct output filenames ad hoc; use the path helpers.
- Keep Parquet as the authoritative tabular output.
- Do not change BRDF, topographic correction, spectral response definitions, or
  brightness coefficients without a scientific review.
- Update docs and tests in the same change whenever output names or public
  payloads change.
