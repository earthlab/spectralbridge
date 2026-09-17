# Runnable notebook vignettes

These are real Jupyter `.ipynb` files tracked in the SpectralBridge repository.
Each link opens the notebook in GitHub's repository viewer so you can read its
Markdown and code cells on the web. GitHub does not execute the cells; clone or
download the notebook when you are ready to run it locally.

The notebooks mirror the learning modules and call existing SpectralBridge
functions. They contain configuration cells, explanations of inputs and
outputs, and validation checkpoints. Copy a notebook into your own analysis
directory before changing scientific assumptions.

The NEON and drone examples follow the two active root research notebooks.
The local bulk example uses the public API on an already curated file tree. A
separate advanced bulk notebook adapts the supplied production workflow for
CyVerse-hosted collections, including discovery, transfer, duplicate
reconciliation, preflight, compact analysis, reporting, and closeout packaging.
It is an environment-specific recipe, not a prerequisite for using
`run_bulk_pipeline()` on local files.

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
| 09 | [Build a bulk cross-run analysis][notebook-09] | You want canonical catalogs, virtual queries, balanced regressions, and held-out-site validation |
| 10 | [Run a curated CyVerse bulk production job][notebook-10] | You have a CyVerse collection in the completed-flightline format and need transfer, reconciliation, analysis, reports, and closeout gates |

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

The notebooks have valid kernels and no saved outputs. The numbered learning
examples use `RUN = False`; set it to `True` after editing their configuration.
The advanced CyVerse notebook also stops at its configuration guard until you
set `RUN = True`, replace the example `REMOTE_SOURCE`, review VM disk/output
paths, and choose a stage. `RUN_STAGE="all"` may transfer a large archive. An
existing reconciled stage or closeout package is not deleted without separate
explicit flags. Remote upload remains disabled unless `UPLOAD_RESULTS=True`.

The supplied PDF was used for review but is not published as runnable guidance:
its print layout clips wide code cells. Use the tracked notebook to copy or run
code.

[notebook-00]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/00_full_neon_pipeline.ipynb
[notebook-01]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/01_acquire_neon.ipynb
[notebook-02]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/02_correct_neon.ipynb
[notebook-03]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/03_harmonize_to_landsat.ipynb
[notebook-04]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/04_analysis_tables.ipynb
[notebook-05]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/05_qa_and_validation.ipynb
[notebook-06]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/06_drone_pipeline.ipynb
[notebook-07]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/07_polygon_extraction.ipynb
[notebook-08]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/08_custom_correction_hook.ipynb
[notebook-09]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/09_bulk_analysis.ipynb
[notebook-10]: https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/10_bulk_production_cyverse.ipynb
