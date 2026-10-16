# SpectralBridge

SpectralBridge is scientific Python software for preparing and comparing
observations of reflected light across airborne, drone and satellite sensor
representations. It processes NEON flightlines and supported local drone imagery
through separate, restart-safe workflows, then analyzes completed products with
an independent bulk workflow. Named files, recorded parameters and QA outputs
make each processing step inspectable.

**Common framework, sensor-specific treatment.** Sensors observe different
wavelength ranges, ground footprints and acquisition geometries. SpectralBridge
can weight NEON spectra into configured sensor-like bands; drone observations
have their own preparation/correction path. A Landsat-like representation does
not prove agreement with Landsat, and spectral weighting does not solve spatial
alignment or footprint differences. [Start with the measurement concepts](https://earthlab.github.io/spectralbridge/concepts/measurements/).

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://earthlab.github.io/spectralbridge/)
[![PyPI](https://img.shields.io/pypi/v/earthlab-spectralbridge)](https://pypi.org/project/earthlab-spectralbridge/)

Explore the [spectral library](https://earthlab.github.io/spectralbridge/spectral-library/)
and its ecological variation, paired synthetic OLI analysis and
[separate real-Landsat pilot](https://earthlab.github.io/spectralbridge/validation/landsat-pilot/).
Experimental mixture-readiness diagnostics do not establish operational abundance
mapping. [Scientific tests and evidence levels](https://earthlab.github.io/spectralbridge/dev/scientific-testing/)
explain what has been checked and what still needs independent observations.

## Install

Python 3.10–3.12 is the tested baseline. The distribution and import names differ:

```bash
python -m pip install earthlab-spectralbridge
python -c "import spectralbridge; print(spectralbridge.__version__)"
```

Repository examples describe the checked-out version. Candidate metadata is not
proof that the same candidate has been published; see [release status and gates](https://earthlab.github.io/spectralbridge/dev/releasing/).

## Verify your installation

From a clone in a virtual environment:

```bash
python -m pip install -e .
python examples/first_example.py
```

This runs the public spectral-library preflight on six invented observations,
without downloads or credentials. It checks groups and report scope; it does not
calibrate sensors or establish scientific validity. [Read the result and continue](https://earthlab.github.io/spectralbridge/getting-started/).

## Choose a workflow

| Your inputs | Guide |
| --- | --- |
| NEON airborne flightlines | [NEON processing](https://earthlab.github.io/spectralbridge/vignettes/full-pipeline/) |
| Supported local drone TIFF/HDF5 | [Drone processing](https://earthlab.github.io/spectralbridge/vignettes/drone-processing/) |
| Completed flightline products | [Bulk analysis](https://earthlab.github.io/spectralbridge/vignettes/bulk-analysis/) |
| Existing polygon spectral library | [Library preflight and reporting](https://earthlab.github.io/spectralbridge/vignettes/spectral-library/) |

The three workflows also support downstream products: polygon-level pixel
extraction, labeled spectral libraries, species/population summaries and compact
cross-flight evidence. These are products and analysis modules, not extra
processing pipelines. [Read the data model before combining flights](https://earthlab.github.io/spectralbridge/usage/parquet/): wide wavelength columns can represent different native grids.

Use [the documentation](https://earthlab.github.io/spectralbridge/) for outputs,
configuration, QA, resume behavior, remote production and APIs. Distinguish
[execution, artifact completion, internal QA and independent agreement](https://earthlab.github.io/spectralbridge/validation/evidence-hierarchy/).

## Cite and contribute

Cite the software version used, relevant scientific methods and any associated
publication. [CITATION.cff](https://github.com/earthlab/spectralbridge/blob/main/CITATION.cff) and [citation guidance](https://earthlab.github.io/spectralbridge/dev/software-citation/)
record the current citation/archival status. The manuscript and supplement have
canonical sources in [paper/](https://github.com/earthlab/spectralbridge/blob/main/paper/README.md).

SpectralBridge is licensed GPL-3.0-or-later; see [LICENSE](https://github.com/earthlab/spectralbridge/blob/main/LICENSE), [NOTICE](https://github.com/earthlab/spectralbridge/blob/main/NOTICE)
and [HyTools source/method provenance](https://github.com/earthlab/spectralbridge/blob/main/HYTOOLS_PROVENANCE.md). HyTools-derived
implementation credit is distinct from the scientific-method citations and
current runtime dependency.

See [CONTRIBUTING.md](https://github.com/earthlab/spectralbridge/blob/main/CONTRIBUTING.md), the [repository map](https://earthlab.github.io/spectralbridge/reference/repository-map/)
and [developer workflow](https://earthlab.github.io/spectralbridge/dev/contributing/). Research history is preserved
under `archive/` and `provenance/`; installed code lives in `src/spectralbridge/`.


## Current researcher-category scientific analysis

The recorded `cover_category` field is the sole primary biological grouping:
Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, and Woody shrub.
The [three-question validation report](provenance/researcher-evidence/2026-10-16/v1/README.md)
is the current primary synthesis: **separability → identifiability → abundance**,
with field abundance a separate unestablished evidence level. The audit adds matched
random-subset and temporal recognition controls and a same-candidate ridge control.
The latter removes ridge's original NEON advantage when reduced to MESMA's 15
retained parents; do not interpret the larger-library result as intrinsic method
superiority. All earlier reports and numerical evidence remain preserved.

The [preceding numerical companion](provenance/researcher-pft-information/2026-10-15/v1/README.md)
contains the wavelength-information atlas, nested complementary-feature tests,
class-specific transfer, common synthetic abundance benchmark and human PDF.
Supervised regression improves known synthetic fraction recovery under the
stated validation design; independent field-cover validation remains missing.

[Scientific synthesis](FINAL_SCIENTIFIC_SYNTHESIS.md),
[readiness matrix](FINAL_READINESS_MATRIX.csv),
[label/analysis audit](FINAL_ANALYSIS_AUDIT.md) and
[next data needed](NEXT_DATA_NEEDED.md) identify the current final interpretation.
Earlier species-derived analyses and the
[earlier lab-story report](provenance/lab-story/2026-10-15/README.md)
are preserved as historical/exploratory records. Their grouping system is not
used in the current primary results.
