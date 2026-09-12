# SpectralBridge

SpectralBridge translates, validates, and compares reflectance across sensors
and scales. It provides restart-safe scientific workflows for individual NEON
flightlines, local drone products, production-scale cross-sensor analysis, and
spectral-library reporting.

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://earthlab.github.io/spectralbridge/)
[![PyPI](https://img.shields.io/pypi/v/earthlab-spectralbridge)](https://pypi.org/project/earthlab-spectralbridge/)
[![Python](https://img.shields.io/pypi/pyversions/earthlab-spectralbridge)](https://pypi.org/project/earthlab-spectralbridge/)

## Install

SpectralBridge supports Python 3.10, 3.11, and 3.12.

```bash
python -m pip install earthlab-spectralbridge
```

To evaluate the 2.3.0 release candidate explicitly:

```bash
python -m pip install --pre "earthlab-spectralbridge==2.3.0rc1"
python -c "import spectralbridge; print(spectralbridge.__version__)"
```

Contributor, documentation, and notebook dependencies are available as extras:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[notebooks]"
```

## Workflows

### Individual NEON flightlines

`go_forth_and_multiply()` is the canonical file-based NEON workflow. It can
download inputs, export ENVI, build and apply topographic and BRDF corrections,
convolve corrected reflectance to target sensors, extract full-scene or polygon
tables, merge Parquet outputs, and create QA artifacts.

```python
from spectralbridge import go_forth_and_multiply

go_forth_and_multiply(
    base_folder="/data/niwo",
    site_code="NIWO",
    year_month="2023-08",
    flight_lines=["NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"],
    extraction_mode="full",  # or "polygon"
    polygon_path=None,
)
```

Pipeline stages communicate through validated files. A restarted run reuses
valid outputs instead of recomputing them:

```text
NEON HDF5
  -> raw ENVI
  -> correction model + corrected ENVI
  -> target-sensor ENVI products
  -> full or polygon Parquet tables
  -> merged tables + QA
```

### Drone processing

The drone workflow is intentionally separate from NEON acquisition. It searches
local TIFF/HDF5 inputs recursively, preserves source provenance, applies the
requested corrections, and retains corrected native MicaSense. An optional,
wavelength-aware affine stage consumes a versioned, reviewed coefficient
registry to create distinct Landsat-like translated products and spectral
libraries. Translation is `L = a + bM` after correction; it neither fits at
runtime nor performs convolution. Convolution belongs to the NEON hyperspectral
branch.

```python
from spectralbridge import run_drone_pipeline

result = run_drone_pipeline(
    "/data/drone_exports",
    output_dir="/data/drone_processed",
    apply_topo=True,
    apply_brdf=True,
    extraction_mode="polygon",
    polygon_path="/data/plots.geojson",
    apply_translation=True,
    translation_coefficients="/data/drone_translation_coefficients_v1.json",
    translation_strict=False,
)
```

Production policy fixes weighting to `site_balanced`. If the reviewed registry
is packaged, omit `translation_coefficients`; an explicit path is useful while
reviewing a newly generated registry. This source revision intentionally does
not invent a registry from summary statistics: if the exact compact bulk
artifacts have not yet been imported, the default raises an actionable error.
See the [drone translation tutorial](docs/tutorials/micasense-to-landsat.md) for
the import command, wavelength mapping, confidence states, and evidence limits.

Standalone translation QA needs no NEON or network access. Set
`landsat_qa=True` to search Microsoft Planetary Computer for an overlapping
Landsat Collection 2 Level 2 scene; install that optional support with
`python -m pip install "earthlab-spectralbridge[landsat]"`. Alternatively pass
an analysis-ready stacked raster or a previously cached observation manifest as
`landsat_product`. Pass `comparison_neon_product` only when an existing
NEON-convolved product should join the common-Landsat-grid comparison.
The run also writes a one-page dashboard, a self-contained PDF report, and
separate publication-ready PNG/PDF translation panels. Expensive stage reuse
is based on matching source/configuration
fingerprints plus output validation, not file existence alone.

### Production bulk translation analysis

`run_bulk_pipeline()` analyzes a tree of immutable, completed-flightline
products. Normal bulk analysis never creates an ordinary row-level pixel cache.
It reads source rasters in bounded windows and reduces observations immediately
to mergeable sufficient statistics.

```text
immutable completed-flightline ENVI products
  -> discovery, identity, QA, and eligibility catalog
  -> bounded raster windows
  -> one compact sufficient-statistics checkpoint per flightline
  -> pooled, flightline-balanced, and site-balanced translations
  -> per-flightline and per-site fits
  -> leave-one-site-out validation
  -> candidate coefficients + compact DuckDB/Parquet/JSON outputs
```

```python
from spectralbridge import run_bulk_pipeline

result = run_bulk_pipeline(
    "/data/completed_flightlines",
    "/data/bulk_analysis",
    threads=4,
    memory_limit="8GB",
)
```

The workflow is restart-safe: completed per-flightline statistics checkpoints
are reused. Source observations stay in their immutable products, so the compact
bulk output can be retained independently of the large staging archive.
Persistent analysis storage grows mainly with flightline checkpoints and models,
not with the total number of selected source pixels.

### Results and interpretation

`summarize_bulk_results()` operates only on compact outputs from a completed
bulk run. It does not reopen source rasters or regenerate sufficient statistics.

```python
from spectralbridge import summarize_bulk_results

summary = summarize_bulk_results(
    "/data/bulk_analysis",
    make_figures=True,
    make_report=True,
)
```

The report compares pooled and balanced fits, coefficient distributions,
site dependence, leave-one-site-out transferability, and correction magnitude.
High R² alone is not treated as evidence that sensors are interchangeable;
weak, unstable, or unusually large corrections are surfaced explicitly.
Outputs are separated into a one-page summary, detailed diagnostics, three
manuscript-width publication figures, and Markdown/PDF reports. All are
regenerable from the completed compact result tables without the raster archive.

### Spectral-library reporting

Spectral-library analysis reads a supplied Parquet library in place and writes
compact summaries and optional reports. Run the inexpensive preflight before a
full report to inspect schema, group counts, and estimated rendering work.

```python
from spectralbridge import inspect_spectral_library_preflight

preflight = inspect_spectral_library_preflight(
    "/data/polygon_spectral_library.parquet"
)
```

The most convenient production route is to provide the spectral library to
`run_bulk_pipeline()`. Advanced callers can use both public spectral-library
surfaces directly:

```python
from spectralbridge import (
    inspect_spectral_library_preflight,
    run_spectral_library_analysis,
)
```

The outputs include species summaries, quantiles, low-alpha spectral ensembles,
robust and full-range views, hierarchical variability, bounded traceable
extreme-spectrum diagnostics, and optional multipage PDFs. Plot bounds do not
alter analytical summaries, and the workflow does not make a second copy of the
input library. `run_spectral_library_analysis()` accepts a DuckDB connection and
`BulkAnalysisPaths` for direct control.

### Explicit row-level materialization

Most analyses should use the streaming statistics path. If a row-level
harmonized dataset is genuinely required, request it explicitly:

```python
from spectralbridge import build_harmonized_dataset

result = build_harmonized_dataset(
    "/data/completed_flightlines",
    "/data/harmonized_dataset",
)
```

This is an explicit build/export workflow and can be much larger than the
normal compact bulk output.

## Outputs and QA

On-disk outputs and naming contracts are part of the public API. Depending on
the workflow, outputs include paired ENVI `.img`/`.hdr` products, Parquet tables,
DuckDB catalogs, correction models, coefficient tables, stage QA JSON, figures,
and reports. See the [outputs contract](https://earthlab.github.io/spectralbridge/pipeline/outputs/)
and [schema reference](https://earthlab.github.io/spectralbridge/reference/schemas/).

QA is evidence, not decoration. Stage reports record pass/warn/fail status and
provenance; plots help diagnose corrections, convolution, masks, extraction,
weighting dependence, coefficient heterogeneity, and transferability.

## Command-line tools

The installed package provides focused commands including:

```text
spectralbridge-download
spectralbridge-pipeline
spectralbridge-bulk
spectralbridge-qa
spectralbridge-qa-summary
spectralbridge-stage-qa
spectralbridge-qa-dashboard
spectralbridge-merge-duckdb
spectralbridge-validate-parquets
spectralbridge-recover-raw
```

Use `COMMAND --help` for current options. Historical `cscal-*` aliases remain
available for compatibility.

## Release-candidate validation

After installing the exact candidate in a fresh environment, external testers
can download and run the small installation check without cloning the repository:

```bash
python -m pip install --pre "earthlab-spectralbridge==2.3.0rc1"
curl -O https://raw.githubusercontent.com/earthlab/spectralbridge/v2.3.0rc1/examples/release_candidate_smoke.py
python release_candidate_smoke.py --expected-version 2.3.0rc1
```

This checks the installed version, public imports, and primary console scripts;
it is not a scientific validation. Maintainers also run a bounded exact-artifact
smoke that executes the normal, drone, bulk, results, and spectral-library paths.

## Documentation and examples

- [Documentation home](https://earthlab.github.io/spectralbridge/)
- [Start here](https://github.com/earthlab/spectralbridge/blob/main/START_HERE.md)
- [Bulk analysis vignette](https://earthlab.github.io/spectralbridge/vignettes/bulk-analysis/)
- [Architecture](https://earthlab.github.io/spectralbridge/dev/architecture/)
- [Notebook vignettes](https://earthlab.github.io/spectralbridge/vignettes/notebook-vignettes/)
- [Changelog](https://github.com/earthlab/spectralbridge/blob/main/CHANGELOG.md)

## Development

```bash
git clone https://github.com/earthlab/spectralbridge.git
cd spectralbridge
python -m pip install -e ".[dev]"
ruff check src tests scripts
pytest -q
mkdocs build --strict
```

Contributions should preserve scientific assumptions, deterministic outputs,
restart safety, bounded processing, and public filename contracts. See
[CONTRIBUTING.md](https://github.com/earthlab/spectralbridge/blob/main/CONTRIBUTING.md).

## Citation and license

Please cite the software using
[CITATION.cff](https://github.com/earthlab/spectralbridge/blob/main/CITATION.cff).
SpectralBridge is licensed under
[GPL-3.0-or-later](https://github.com/earthlab/spectralbridge/blob/main/LICENSE).
