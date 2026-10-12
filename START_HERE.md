# Start here

SpectralBridge prepares observations of reflected light for comparison across
sensors. Different sensors see different wavelength ranges, ground footprints
and viewing conditions. The software gives these observations a common framework
while processing each according to how it was collected.

Start with [the basic concepts](docs/concepts/measurements.md), then run
[the small offline example](docs/getting-started.md). These are the canonical
beginner path; technical details remain available when needed.

| What you have | Workflow |
| --- | --- |
| NEON airborne observations | [NEON flightlines](docs/vignettes/full-pipeline.md) |
| Supported drone TIFF/HDF5 | [Drone processing](docs/vignettes/drone-processing.md) |
| Completed flightline products | [Bulk analysis](docs/vignettes/bulk-analysis.md) |
| An existing spectral library | [Library preflight and reports](docs/vignettes/spectral-library.md) |

A configured Landsat-like product is a representation, not proof of agreement
with Landsat. Spectral weighting does not resolve spatial-footprint differences.
After processing, distinguish [execution, output completion, QA and independent
validation](docs/validation/evidence-hierarchy.md).

Developers: use the [repository map](docs/reference/repository-map.md).
Publication reviewers: start with [paper/README.md](paper/README.md), then the
[publication evidence](docs/validation/supplement.md).
