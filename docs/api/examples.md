# API examples and data requirements

The reference contains executable docstring examples for the composable spectral
methods, brightness adjustment, QA metrics and packaged resources. All spectra in
those examples are **invented teaching data**. Numerical success is not ecological
validation or independent sensor calibration.

Run the checked offline examples from an installed checkout:

```bash
python examples/first_example.py
python examples/scientific_workflows_offline.py
python examples/spectral_library_methods.py
```

The first two need the normal package dependencies; the third also needs the
`analytics` extra. They create their own tiny inputs or temporary files. They
require neither NEON downloads nor the production polygon library.

For producer orchestration, filenames alone are not sufficient input fixtures.
NEON and drone workflows need real supported rasters, companion metadata,
geometry and spectral support. Their source docstring examples use variables
such as `source_dir` supplied by the caller, and are marked `doctest: +SKIP`.
These calls are signature-checked, not claimed as executed scientific runs.

- [NEON workflow](../vignettes/full-pipeline.md) and [orchestrator contracts](generated/pipelines-pipeline.md).
- [Drone workflow](../vignettes/drone-processing.md) and [local producer contract](generated/pipelines-drone.md).
- [Remote drone production](generated/drone_production.md) requires an authorized backend and a manifest defining the expected population.
- [Bulk workflow](../vignettes/bulk-analysis.md) starts from completed immutable products and writes outputs outside the source tree.
- [Scientific API maturity](scientific-analysis.md) distinguishes reusable numerical methods from source-specific research.

Executable docstring checks and source-signature checks run with:

```bash
pytest -q tests/test_api_reference.py
```

See the [function glossary](index.md) to select the entry point for your task.
