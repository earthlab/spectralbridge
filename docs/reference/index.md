# Technical reference map

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


## Publication evidence

For the historical manuscript evidence and complete SI, use the
[technical supplement](../validation/supplement.md). Current instructions and
contracts remain in the workflow/reference pages.

## Reviewer and publication paths

- [Scientific need and measurement differences](../concepts/measurements.md)
- [Installation and bounded example](../getting-started.md)
- [Tests, contribution and development checks](../dev/contributing.md)
- [Evidence hierarchy and limitations](../validation/evidence-hierarchy.md)
- [Citation and paper status](../dev/software-citation.md)
- [Release and reproducibility gates](../dev/releasing.md)
- [License and provenance](https://github.com/earthlab/spectralbridge/blob/main/LICENSE)
  and [attribution](https://github.com/earthlab/spectralbridge/blob/main/NOTICE)
- [JOSS author checklist](https://github.com/earthlab/spectralbridge/blob/main/paper/SUBMISSION_CHECKLIST.md)

Historical audits remain under [development history](../dev/history.md); their
counts and blockers describe their recorded revisions, not the current checkout.
