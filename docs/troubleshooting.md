# Troubleshooting Guide

This page lists common problems encountered when running SpectralBridge, along
with likely causes and recommended responses. The pipeline is restart-safe, so
the first recovery step is usually to rerun the same command and let validated
stages skip.

---

## General issues

### The pipeline crashes or stops mid-run

Likely causes:

- out-of-memory errors
- temporary directory filling up
- unexpected NEON file structure
- interrupted network access during download

Recommended responses:

- reduce `--max-workers`
- lower `--parquet-chunk-size`
- set `CSCAL_TMPDIR` to a larger scratch disk
- rerun the same `spectralbridge-pipeline` command so completed stages are reused

---

## Download and HDF5 access issues

### Missing or corrupted HDF5 files

Likely causes:

- NEON paths changed or the requested flight line is unavailable
- cloud or shared-storage sessions timed out
- a prior download was interrupted

Recommended responses:

- verify the site, year-month, product code, and flight line identifier
- rerun the pipeline; downloads are validated before reuse
- use a fresh working directory if a partial file keeps failing validation

---

## HDF5 -> ENVI export issues

### ENVI header not recognized or wavelengths missing

Likely causes:

- malformed or incomplete HDF5 metadata
- older NEON files with different metadata layout
- an interrupted ENVI export

Recommended responses:

- confirm the HDF5 product is `DP1.30006.001`
- confirm the filename includes `directional_reflectance`
- remove or archive the invalid output pair, then rerun the same pipeline command

ENVI export is I/O intensive. For single-flightline debugging, use a
conservative worker count:

```bash
spectralbridge-pipeline ... --engine thread --max-workers 1
```

---

## Topographic and BRDF correction issues

### Dark or clipped areas after correction

Likely causes:

- deep shadows
- DEM mismatch
- slope/aspect irregularities
- unstable geometry values

Recommended responses:

- inspect slope/aspect and solar/view geometry metadata
- review correction diagnostics in the QA JSON
- compare the raw and corrected ENVI products in the QA panel
- flag persistent concerns for domain review before changing correction logic

### BRDF correction produces NaNs or extreme values

Likely causes:

- unstable coefficient fitting
- low-SNR or noisy bands
- invalid view/solar geometry

Recommended responses:

- inspect BRDF coefficients in the correction JSON and QA JSON
- rerun with the same inputs to rule out an interrupted write
- preserve the failing artifacts for review rather than changing coefficients silently

---

## Sensor harmonization issues

### Landsat-style reflectance looks wrong

Likely causes:

- wavelength metadata mismatch
- incomplete sensor response definitions
- bright or dark artifacts propagated from correction stages

Recommended responses:

- inspect the matching ENVI header for wavelengths and FWHM values
- compare sensor Parquet summaries by `wavelength_nm`
- review QA plots before downstream modeling

### Brightness coefficients are unusually large

This can indicate poor alignment between corrected spectra and the target
sensor response frame.

Check:

- reflectance scaling
- BRDF coefficient stability
- QA brightness plots and JSON metrics

---

## Parquet extraction and merge issues

### Memory errors during extraction or merge

Recommended responses:

- reduce `--max-workers`
- lower `--parquet-chunk-size`
- set `--merge-memory-limit` to a value appropriate for the machine
- set `--merge-temp-directory` to a large local scratch disk
- use DuckDB for summaries instead of loading large Parquet files into pandas

### Corrupted Parquet sidecars

If a Parquet sidecar is empty or unreadable, rerun the same pipeline command.
The export stage validates Parquet schemas and rebuilds invalid sidecars from
the ENVI source.

---

## QA issues

### QA PNG, PDF, or JSON missing

Likely causes:

- pipeline interrupted before QA rendering
- missing merged Parquet output
- insufficient write permissions in the output directory

Recommended responses:

- rerun the pipeline for the same flight line
- or rerender QA only:

```bash
spectralbridge-qa --base-folder output_demo
```

---

## When to reach out for help

Persistent issues are easier to diagnose when you preserve:

- the exact command and environment
- the flight line identifier
- the QA PNG/PDF/JSON
- the correction JSON
- a small metadata snippet from the relevant ENVI header

---

## Next steps

- [Pipeline stages](pipeline/stages.md)
- [QA metrics](pipeline/qa.md)
- [Working with Parquet](usage/parquet.md)
