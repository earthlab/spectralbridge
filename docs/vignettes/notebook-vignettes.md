# Runnable notebook vignettes

These notebooks mirror the learning modules and call existing SpectralBridge
functions. They contain configuration cells, explanations of inputs and
outputs, and validation checkpoints. Copy a notebook into your own analysis
directory before changing scientific assumptions.

| Order | Notebook | Use it when |
| --- | --- | --- |
| 00 | [Full NEON pipeline](notebooks/00_full_neon_pipeline.ipynb) | You want download through QA in one restart-safe call |
| 01 | [Acquire NEON HDF5](notebooks/01_acquire_neon.ipynb) | You only want to obtain or reuse the source HDF5 |
| 02 | [Correct NEON reflectance](notebooks/02_correct_neon.ipynb) | You want raw ENVI plus standard topo/BRDF outputs |
| 03 | [Harmonize to Landsat](notebooks/03_harmonize_to_landsat.ipynb) | You already have corrected hyperspectral ENVI and want target-sensor products |
| 04 | [Build and inspect analysis tables](notebooks/04_analysis_tables.ipynb) | You want Parquet/CSV inspection and output checks |
| 05 | [Review QA and validation](notebooks/05_qa_and_validation.ipynb) | You want to render QA and inspect machine-readable diagnostics |
| 06 | [Process drone imagery](notebooks/06_drone_pipeline.ipynb) | You have local drone HDF5 inputs |
| 07 | [Extract polygon spectra](notebooks/07_polygon_extraction.ipynb) | You want polygon-indexed spectra from a completed flightline |
| 08 | [Insert a custom correction](notebooks/08_custom_correction_hook.ipynb) | You are developing a reviewed correction after topo/BRDF and before convolution |

## Opening them

From a clone:

```bash
python -m pip install -e ".[notebooks]"
jupyter lab docs/vignettes/notebooks/
```

The notebooks use repository-relative paths and begin with an editable
configuration cell. Large runs can take substantial memory and storage. Start
with one flightline, `engine="thread"`, and `max_workers=1`.

## What “runnable” means

The notebooks have valid kernels, importable code, and no saved outputs. Data
processing cells are guarded by `RUN = False` so opening or running all cells
does not unexpectedly download tens of gigabytes. Set `RUN = True` only after
editing the paths and identifiers in the configuration cell.

