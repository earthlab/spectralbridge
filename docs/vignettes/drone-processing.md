# Module vignette 6: process drone imagery

Use this module for local drone HDF5 inputs. It is separate from the NEON
download workflow and preserves provenance from the original drone filenames.

## Prepare the inputs

Place valid drone HDF5 files under one input directory. Discovery is recursive,
so campaign or flight subdirectories are allowed.

```text
drone_inputs/
├── flight_a/
│   └── flight_a.h5
└── flight_b/
    └── flight_b.h5
```

Reflectance and ancillary arrays in each HDF5 must already share the expected
spatial orientation and footprint. Corrections require the relevant terrain,
view, and solar geometry.

## Run it

```python
from spectralbridge import run_drone_pipeline

results = run_drone_pipeline(
    input_h5_dir="drone_inputs",
    output_dir="drone_outputs",
    polygon_path=None,
    apply_topo=True,
    apply_brdf=True,
    require_solar_geometry=True,
)

print(results["processed"])
print(results["failed"])
print(results["qa_summary"])
```

Set `polygon_path` to a supported vector file only when polygon extraction is
part of the same run.

## Confirm the result

Each discovered flight gets a separate output directory with drone-native
stems. Depending on available inputs and requested modules, expect corrected
ENVI, Parquet, QA PNG, and QA JSON outputs plus a run-level QA summary.

Read each QA JSON before assuming a requested correction was applied. It records
whether correction ran, was skipped because geometry was unavailable, or fell
back after a quality check.

## Continue

- [Review QA outputs](qa-and-analysis.md)
- [Extract polygon spectra](polygon-extraction.md)
- Technical details: [outputs and naming](../pipeline/outputs.md) and [package
  architecture](../dev/architecture.md)
