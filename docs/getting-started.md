# Your first SpectralBridge example

Start with a small offline example before downloading flightlines. You will
inspect six invented observations with three wavelengths, count their groups,
and see how the spectral-library workflow checks its input. No remote-sensing
background, credentials or real data are required.

If the terms are new, read [why sensors see the same landscape
differently](concepts/measurements.md) first.

## Verify your installation

Use Python 3.10–3.12. Start from a terminal; these commands create a separate
environment, install the source checkout and run an offline lesson:

```bash
git clone https://github.com/earthlab/spectralbridge.git
cd spectralbridge
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python examples/first_example.py
```

On Windows Command Prompt, replace the activation command with
`.venv\Scripts\activate`. Keep this environment active for the following commands.
The distribution is **earthlab-spectralbridge**; the import is **spectralbridge**.
These instructions install your checkout, not a claimed published RC2 release.
Check it with `python -c "import spectralbridge; print(spectralbridge.__version__)"`.

| Optional task | Install from the checkout |
| --- | --- |
| Separability, recognition and mixture lessons | `python -m pip install -e '.[analytics]'` |
| Jupyter notebooks | `python -m pip install -e '.[notebooks]'` |
| Search for actual Landsat observations | `python -m pip install -e '.[landsat]'` |
| Boosted quantile models | `python -m pip install -e '.[quantile-models]'` |
| Run tests / build documentation | `python -m pip install -e '.[tests,docs]'` |

The base install already includes the raster, vector, Parquet, plotting and
pipeline dependencies. Optional extras enable specific tasks; they are not
needed for the first two offline lessons. See [environment setup](env.md) and
[troubleshooting](troubleshooting.md) if installation fails.

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

## Keep a result you can inspect

```bash
python examples/scientific_workflows_offline.py --output-dir lesson_output
```

This existing offline workflow creates six invented pixel spectra, aggregates
them into two plant identities, projects a flat teaching spectrum into OLI-like
bands and compares identical arrays. It writes:

- `lesson_output/example_summary.json`: two retained plants, OLI values of 0.2
  and identity RMSE of zero, as expected for this constructed example;
- `lesson_output/teaching.parquet`: the tiny source table; and
- `lesson_output/atlas/`: compact plant summaries and their provenance; and
- `lesson_output/library_summary/`: compact group/band summaries, with exact paths
  in the JSON result.

A fresh output directory is required so another run cannot overwrite your result.
Omit `--output-dir` for a temporary lesson that cleans up automatically. Matching
an array to itself checks software use; it does not measure real sensor agreement.
For a short analysis lesson, install `analytics` above and run
`python examples/spectral_library_methods.py`.

## Run your first scientific workflow

| Your inputs / goal | Next step |
| --- | --- |
| NEON airborne flightline | [Run one NEON flightline](vignettes/full-pipeline.md) |
| Supported local drone TIFF/HDF5 | [Process drone observations](vignettes/drone-processing.md) |
| Already completed flightline products | [Run bulk analysis](vignettes/bulk-analysis.md) |
| Imagery plus field polygons | [Create a spectral library](vignettes/polygon-extraction.md) |
| An existing spectral table | [Inspect a spectral library](vignettes/spectral-library.md) |
| Target-sensor bands | [Translate spectral bands](vignettes/sensor-harmonization.md) |
| Spectral differences, recognition or mixture fractions | [Choose an analysis method](api/scientific-analysis.md) |

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

Continue with `python examples/scientific_workflows_offline.py` for invented-data library aggregation, gap-preserving harmonization, synthetic OLI projection and agreement metrics. The [API maturity map](api/scientific-analysis.md) separates these numerical examples from full research analyses.

## Before running real drone imagery

Read [correction eligibility](concepts/correction-eligibility.md) and the
[Gordon/Goldhill/Ruby findings](validation/drone-findings.md). Supply verified
physical calibration, validate source alignment and explicitly choose corrections.
The installation example above remains a synthetic software demonstration.

Last updated: 2026-11-04
