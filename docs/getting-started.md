# Your first SpectralBridge example

Start with a small offline example before downloading flightlines. You will
inspect six invented observations with three wavelengths, count their groups,
and see how the spectral-library workflow checks its input. No remote-sensing
background, credentials or real data are required.

If the terms are new, read [why sensors see the same landscape
differently](concepts/measurements.md) first.

## Verify your installation

Use Python 3.10–3.12 in a virtual environment. From a cloned repository:

```bash
python -m pip install -e .
python examples/first_example.py
```

For a release installation use `python -m pip install earthlab-spectralbridge`.
The installed distribution is `earthlab-spectralbridge`; the Python import is
`spectralbridge`. Repository examples describe the checked-out source version;
verify that your installed release includes the API you intend to use.

## Read the result

The example should report six source rows and valid spectra, two example plant
groups, two polygons, one flightline and one site. It records wavelengths of
450, 550 and 700 nm, and `pdfs_generated: false`. The temporary table is removed
when the script exits; your data are untouched.

This runs the public `inspect_spectral_library_preflight()` API, rather than
merely checking installation. It inspects a Parquet table (a structured columnar
data file) and estimates report scope before expensive plotting. The values are
invented teaching data, so this verifies software use without claiming scientific
validation or representing sensor performance.

The [complete example source](https://github.com/earthlab/spectralbridge/blob/main/examples/first_example.py)
is short enough to adapt. For a real spectral library, run the same preflight on
your supplied table, then choose compact summaries or explicit full reports in
[the spectral-library guide](vignettes/spectral-library.md).

## Run your first scientific workflow

| Your inputs / goal | Next step |
| --- | --- |
| NEON airborne flightline | [Run one NEON flightline](vignettes/full-pipeline.md) |
| Supported local drone TIFF/HDF5 | [Process drone observations](vignettes/drone-processing.md) |
| Already completed flightline products | [Run bulk analysis](vignettes/bulk-analysis.md) |
| An existing spectral table | [Inspect a spectral library](vignettes/spectral-library.md) |

No small, complete real reflectance dataset with verified redistribution terms
is bundled for this quick start. The retained GPKGs are research vector inputs,
not a runnable spectral dataset. Supply a real flightline or supported local drone
input through the guides above; do not interpret the invented example as a
scientific benchmark. To inspect an existing real run without downloading its
large inputs, read the [R10C walkthrough and QA](validation/real-data-example.md).

For the NEON example, first run `python examples/run_neon_pipeline.py --check`
to validate configuration without downloading. Choose real site/month/flightline
identifiers and storage before processing; the full input and output can be large.
A preflight check is not a completed scientific run.

When processing stops, [resume against existing valid files](vignettes/carry-on-wayward-son.md).
After it finishes, inspect [required outputs](pipeline/outputs.md) and
[QA evidence](validation/evidence-hierarchy.md) before drawing scientific conclusions.
