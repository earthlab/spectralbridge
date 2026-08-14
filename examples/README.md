# Runnable Examples

This directory contains intentionally small Python entry points for scientists
who want to run SpectralBridge without learning the internal package layout.
They call the existing public pipeline APIs; they do not duplicate processing
logic.

## Choose an entry point

| Script | Use it when | Configuration |
| --- | --- | --- |
| `run_neon_pipeline.py` | NEON should be downloaded and processed end to end | `config/neon_pipeline.example.json` |
| `run_drone_pipeline.py` | Local drone HDF5 files should be corrected, extracted, and QA'd | `config/drone_pipeline.example.json` |

Run `--check` first. It parses and validates configuration but does not contact
the network or process imagery:

```bash
python examples/run_neon_pipeline.py --check
python examples/run_drone_pipeline.py --check
```

Relative paths are resolved from the repository root so the same configuration
works from a cloned repository, an editable install, or a container whose
working directory is the repository.

For a local NEON HDF5 source, use the existing documented runner:

```bash
python scripts/run_pipeline_from_local_h5.py --help
```

For interactive or stage-focused use, open a notebook under
[`docs/vignettes/notebooks/`](../docs/vignettes/notebooks/README.md).
