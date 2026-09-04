# Repository map

Use this page to decide which file to read or modify. The repository contains
runtime code, educational material, generated evidence, and historical files;
their presence in the same checkout does not give them the same role.

## Sources of truth

When documentation and an old exploratory file disagree, use this order:

1. `src/spectralbridge/` — current installed behavior;
2. `tests/` — executable contracts and regression cases;
3. `docs/` — current user and developer documentation;
4. `examples/` and `docs/vignettes/notebooks/` — editable adapters over the
   current package;
5. `deprecated/` and site-specific root scripts — provenance only.

## Where to begin

| You want to understand… | Read first | Then inspect |
| --- | --- | --- |
| Complete NEON orchestration | `examples/run_neon_pipeline.py` | `src/spectralbridge/pipelines/pipeline.py` |
| Drone orchestration | `examples/run_drone_pipeline.py` | `src/spectralbridge/pipelines/drone.py` |
| Cross-run bulk analysis | The [bulk-analysis vignette](../vignettes/bulk-analysis.md) | `src/spectralbridge/bulk/` and `src/spectralbridge/pipelines/bulk.py` |
| Canonical filenames | `docs/naming-conventions.md` | `src/spectralbridge/paths.py` and `src/spectralbridge/utils/naming.py` |
| Topographic/BRDF correction | `docs/brdf_topo_algorithm.md` | `src/spectralbridge/corrections.py` and `src/spectralbridge/brdf_topo.py` |
| Sensor convolution | The harmonization vignette | `src/spectralbridge/standard_resample.py` and packaged band JSON |
| Parquet and polygon products | The analysis-table and polygon vignettes | `src/spectralbridge/parquet_export.py`, `merge_duckdb.py`, and `polygons.py` |
| QA evidence | The QA vignette and validation pages | `qa_plots.py`, `qa_metrics.py`, and QA tests |
| JSON parameters | The [JSON catalog](json-catalog.md) | The loader named in that catalog |
| A custom correction | The [custom-correction hook](custom-correction-hook.md) | Stage functions in `pipelines/pipeline.py` |

## What each top-level area means

| Area | Label | Guidance |
| --- | --- | --- |
| `src/spectralbridge/` | Runtime | Installed package; changes require focused tests |
| `tests/` | Contracts | Best place to verify what the package promises |
| `examples/` | Copyable runners | Small scripts and JSON configs for local or container use |
| `docs/vignettes/notebooks/` | Interactive runners | Current ordered notebook set, including independent bulk analysis, with processing disabled until configured |
| `scripts/` | Operations and maintenance | Read `scripts/README.md`; not every script is a user entry point |
| `validation/` | Evidence | Separates campaign plans from generated observations |
| `data/` | Example/local data | Installed code uses `src/spectralbridge/data/`, not this directory |
| `deprecated/` | Provenance | Do not use as the basis for new code |

The root `Drone_processing.ipynb` and `Raster_processing.ipynb` are retained
active research notebooks. New users should begin with the smaller ordered
[notebook vignettes](../vignettes/notebook-vignettes.md), which expose the same current
entry points with clearer stage boundaries.

## How to verify code yourself

Start narrow and expand only when the change crosses contracts:

```bash
python examples/run_neon_pipeline.py --check
pytest -q tests/test_example_entrypoints.py
pytest -q tests/test_pipeline_convolution.py
python scripts/check_docs_links.py
```

For scientific parameter changes, also run the coefficient, correction, or
convolution tests named in the [JSON catalog](json-catalog.md) and inspect the
resulting QA, not only the test exit status.
