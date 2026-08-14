# Start Here

SpectralBridge relates drone reflectance to Landsat bandspace through NEON
airborne hyperspectral observations. In this scientific bridge—**Drone → NEON
→ Landsat**—NEON is the translating reference, not just another interchangeable
input. The processing workflows are restart-safe and file-based: each stage
writes a named artifact that the next stage validates and consumes.

The drone and NEON entry points remain separate in the software. The drone
workflow preserves drone-native products, while the NEON workflow produces the
corrected and Landsat-compatible reference products used for cross-scale
comparison. “Drone to Landsat” therefore does not mean a hidden, direct
one-step conversion.

If the repository feels large, start with one row in this table and ignore the
rest until you need it.

| Your goal | Start here | What you run |
| --- | --- | --- |
| Run a complete NEON-to-Landsat workflow | [`examples/run_neon_pipeline.py`](examples/run_neon_pipeline.py) | `python examples/run_neon_pipeline.py --check`, then rerun without `--check` |
| Run from a local NEON HDF5 file | [`scripts/run_pipeline_from_local_h5.py`](scripts/run_pipeline_from_local_h5.py) | `python scripts/run_pipeline_from_local_h5.py --help` |
| Work interactively | [`docs/vignettes/notebooks/README.md`](docs/vignettes/notebooks/README.md) | Open the notebook matching your task |
| Process drone HDF5 data | [`examples/run_drone_pipeline.py`](examples/run_drone_pipeline.py) | Edit its JSON config and run it |
| Resume a partial run | [`docs/vignettes/carry-on-wayward-son.md`](docs/vignettes/carry-on-wayward-son.md) | Rerun the normal entry point against the same output folder |
| Add a correction after topo/BRDF | [`docs/reference/custom-correction-hook.md`](docs/reference/custom-correction-hook.md) | Preserve the canonical product and write a separately named ENVI pair |
| Understand a JSON file | [`docs/reference/json-catalog.md`](docs/reference/json-catalog.md) | Find its owner, units, consumer, and validation rule |
| Check whether outputs are trustworthy | [`docs/validation/index.md`](docs/validation/index.md) | Inspect module evidence and QA artifacts |

## The repository in six folders

| Folder | Audience | Purpose | Safe to edit? |
| --- | --- | --- | --- |
| `src/spectralbridge/` | Package users and developers | Installed runtime code and authoritative packaged data | Only with tests; filenames and scientific assumptions are contracts |
| `examples/` | New users | Small, editable Python entry scripts and self-documenting example configs | Yes—copy these into your own project |
| `docs/vignettes/notebooks/` | Scientists working interactively | Ordered, runnable and website-downloadable notebooks for full and partial workflows | Yes—copy before adapting to a study |
| `docs/` | All users | Educational vignettes, validation evidence, and technical reference | Yes; these sources build the website |
| `scripts/` | Users and maintainers | Operational runners, diagnostics, and documentation/validation generators | Read [`scripts/README.md`](scripts/README.md) before choosing one |
| `validation/` | Reviewers and maintainers | Campaign specifications and machine-readable evidence | Specs are editable; generated results should be treated as evidence |

The `deprecated/` directory is retained for provenance. It is not a place to
start new work. Root-level transfer scripts are site-specific maintainer tools,
not package entry points. The large root `Drone_processing.ipynb` and
`Raster_processing.ipynb` remain active research notebooks, but new users should
start with the smaller ordered notebook vignettes.

## The workflow in one sentence per stage

1. **Acquire:** place a canonical NEON `.h5` in the run root.
2. **Export:** convert HDF5 reflectance to raw ENVI `.img/.hdr`.
3. **Describe corrections:** calculate and save correction parameters as JSON.
4. **Correct:** apply topographic and BRDF corrections to a canonical ENVI pair.
5. **Harmonize:** convolve corrected spectra into Landsat and other configured sensors.
6. **Tabulate:** export and merge Parquet tables, with optional polygon extraction.
7. **Validate:** write QA PNG/JSON artifacts and reuse valid products on restart.

The authoritative stage order and filenames are documented in
[`docs/pipeline/stages.md`](docs/pipeline/stages.md) and
[`docs/naming-conventions.md`](docs/naming-conventions.md).

## A container-friendly first run

From the repository root inside a container or virtual environment:

```bash
python -m pip install -e .
python examples/run_neon_pipeline.py --check
```

The check command validates the example configuration without downloading or
processing data. Edit `examples/config/neon_pipeline.example.json`, then run:

```bash
python examples/run_neon_pipeline.py \
  --config examples/config/neon_pipeline.example.json
```

Use `engine: "thread"` and `max_workers: 1` for the most portable first run.
Increase parallelism only after confirming the memory available for a full
hyperspectral cube.

## How to validate your own run

A run is not complete merely because a Python call returned. Confirm the
expected ENVI pairs, Parquet outputs, and QA JSON/PNG artifacts exist inside the
flightline directory. Then compare them with the contracts in
[`docs/pipeline/outputs.md`](docs/pipeline/outputs.md) and the module diagnostics
in [`docs/validation/`](docs/validation/index.md).
