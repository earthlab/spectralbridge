# Script Catalog

The core library lives under `src/spectralbridge/`. Files in `scripts/` are
entry points, diagnostics, or repository-maintenance tools; they should call
package functions rather than reimplement scientific processing.

## User-facing runners

| Script | Purpose | Reads | Writes | Safe first command |
| --- | --- | --- | --- | --- |
| `run_pipeline_from_local_h5.py` | Run the normal NEON pipeline when the HDF5 already exists locally | One local `.h5`, optional polygons | Canonical flightline directory | `python scripts/run_pipeline_from_local_h5.py --help` |
| `diagnose_brdf_topo_stage.py` | Investigate correction support, geometry, coefficients, and NoData behavior | Existing HDF5, ENVI, and correction JSON | Console diagnostics | `python scripts/diagnose_brdf_topo_stage.py --help` |
| `run_validation_campaign.py` | Exercise stage contracts with deterministic small synthetic inputs | Generated temporary fixtures | Validation campaign JSON | `python scripts/run_validation_campaign.py --help` |

The most approachable full-download and drone runners live in `examples/`
because they are intended to be copied and edited by users.

## Documentation and publication generators

| Script | Purpose | Normal invocation |
| --- | --- | --- |
| `check_docs_links.py` | Check local Markdown links and optional placeholder markers | `python scripts/check_docs_links.py` |
| `generate_validation_docs.py` | Render website validation pages from machine-readable campaign results | `python scripts/generate_validation_docs.py --check` |
| `generate_ai_transparency.py` | Render the AI transparency statement and figures from `PROMPT_LOG.md` | `python scripts/generate_ai_transparency.py --check` |

These generators are maintainer tools. Generated pages should not be edited by
hand; change their source records or generator instead.

`validation_docs_content.py` is the structured prose catalog used by the
validation generator. It gives every recorded input, diagnostic, and check a
human explanation and maps real R10C figures to the appropriate module and
stage. `tests/test_validation_docs.py` fails if campaign fields or real-stage
check families are added without corresponding documentation.

## Root-level and deprecated utilities

`move_folders_from_instance_to_remote.py`, `remote_to_instance.py`, and
`patch_script_toworkfromcorrectedfiles.py` are site-specific historical or
maintainer utilities with hard-coded infrastructure paths. They are not package
entry points and should not be copied into a new scientific workflow.

Code under `deprecated/` is retained for provenance and migration reference.
New work should import `spectralbridge`, use `examples/`, or follow the current
vignettes.
