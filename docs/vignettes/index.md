# Choose a vignette

Use this section when you want to accomplish a task. Each user-facing module has
one canonical vignette, so you do not have to choose between several tutorials
that appear to cover the same work.

## Start with your situation

| I want to… | Vignette |
| --- | --- |
| Run everything for a NEON flightline | [Run the full pipeline](full-pipeline.md) |
| Continue after a stopped or partial run | [Carry On My Wayward Son](carry-on-wayward-son.md) |
| Work on one part of the workflow | Choose a module below |
| Open a runnable Jupyter notebook | [Runnable notebook vignettes](notebook-vignettes.md) |
| Look up exact arguments, filenames, or algorithms | [Technical reference](../reference/index.md) |

## Module vignettes

The numbered modules follow the order of the main NEON workflow. Drone and
polygon workflows branch from that sequence where noted.

1. [Acquire NEON data](data-acquisition.md) — download or reuse the source HDF5.
2. [Correct NEON reflectance](neon-correction.md) — create raw and
   BRDF/topography-corrected ENVI products.
3. [Harmonize target sensors](sensor-harmonization.md) — translate corrected
   spectra into configured target-sensor bandspaces.
4. [Build analysis tables](analysis-tables.md) — work with per-product and
   merged Parquet outputs.
5. [Review QA outputs](qa-and-analysis.md) — render and interpret the PNG and
   JSON audit artifacts.
6. [Process drone imagery](drone-processing.md) — run the separate local-HDF5
   drone workflow.
7. [Extract polygon spectra](polygon-extraction.md) — build polygon-indexed
   spectral libraries from completed products.

## How to use these pages

Every vignette answers the same four questions:

1. When should I use this module?
2. What is the smallest runnable example?
3. What files prove that it worked?
4. Where are the deeper technical details?

The vignettes teach workflow. The [technical reference](../reference/index.md)
defines contracts and implementation details.

Prefer code you can edit interactively? Every module also has one corresponding
[downloadable notebook](notebook-vignettes.md), including a carefully isolated template
for adding a custom correction between the standard topo/BRDF and convolution
stages.
