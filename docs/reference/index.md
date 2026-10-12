# Technical reference map

## Complete manuscript supplementary material

The [complete SI](../validation/supplement.md) contains the supplied processing contracts, scientific
transformations, drone campaign accounting, R10C and WREF QA evidence, bulk
analysis definitions and results, reproducibility records, software lineage,
neighboring-software comparisons, and prospective QA/resource protocols.
All 23 tables, both figures, equations, appendices and references are included,
with downloadable source and editing copies. Historical evidence retains its
original revision boundaries and limitations.


Use this section for exact behavior: stage order, filenames, interfaces, data
formats, validation, algorithms, and internals. If you want a guided task,
return to the [educational vignettes](../vignettes/index.md).

## Pipeline contracts

- [Stage order and restart behavior](../pipeline/stages.md)
- [Outputs and file structure](../pipeline/outputs.md)
- [Naming conventions](../naming-conventions.md)

## Interfaces

- [Command-line interface](../usage/cli.md)
- [Configuration](configuration.md)
- [Python API](../api/index.md)

## Data and validation

- [Working with Parquet](../usage/parquet.md)
- [JSON schemas](schemas.md)
- [QA panels and metrics](../pipeline/qa.md)
- [Validation metrics](validation.md)

## Algorithms and extension

- [BRDF and topographic correction](../brdf_topo_algorithm.md)
- [Extending SpectralBridge](extending.md)

## Runtime and internals

- [Environment](../env.md)
- [Package architecture](../dev/architecture.md)
- [Container and remote helpers](../dev/container-workflows.md)
