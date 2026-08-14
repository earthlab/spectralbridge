# Runnable notebook vignettes

These are real Jupyter `.ipynb` files tracked in the SpectralBridge repository.
Each link opens the notebook in GitHub's repository viewer so you can read its
Markdown and code cells on the web. GitHub does not execute the cells; clone or
download the notebook when you are ready to run it locally.

The notebooks mirror the learning modules and call existing SpectralBridge
functions. They contain configuration cells, explanations of inputs and
outputs, and validation checkpoints. Copy a notebook into your own analysis
directory before changing scientific assumptions.

| Order | Notebook | Use it when |
| --- | --- | --- |
| 00 | [Full NEON pipeline][notebook-00] | You want download through QA in one restart-safe call |
| 01 | [Acquire NEON HDF5][notebook-01] | You only want to obtain or reuse the source HDF5 |
| 02 | [Correct NEON reflectance][notebook-02] | You want raw ENVI plus standard topo/BRDF outputs |
| 03 | [Harmonize to Landsat][notebook-03] | You already have corrected hyperspectral ENVI and want target-sensor products |
| 04 | [Build and inspect analysis tables][notebook-04] | You want Parquet/CSV inspection and output checks |
| 05 | [Review QA and validation][notebook-05] | You want to render QA and inspect machine-readable diagnostics |
| 06 | [Process drone imagery][notebook-06] | You have local drone HDF5 inputs |
| 07 | [Extract polygon spectra][notebook-07] | You want polygon-indexed spectra from a completed flightline |
| 08 | [Insert a custom correction][notebook-08] | You are developing a reviewed correction after topo/BRDF and before convolution |

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

[notebook-00]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/00_full_neon_pipeline.ipynb
[notebook-01]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/01_acquire_neon.ipynb
[notebook-02]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/02_correct_neon.ipynb
[notebook-03]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/03_harmonize_to_landsat.ipynb
[notebook-04]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/04_analysis_tables.ipynb
[notebook-05]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/05_qa_and_validation.ipynb
[notebook-06]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/06_drone_pipeline.ipynb
[notebook-07]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/07_polygon_extraction.ipynb
[notebook-08]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/08_custom_correction_hook.ipynb
