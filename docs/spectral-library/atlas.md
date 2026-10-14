# How should I inspect spectra across plants, sites and years?

Start with [preflight](../vignettes/spectral-library.md) to inspect schema, group
sizes and report cost. Request compact summaries first; full trace PDFs are an
explicit choice. The atlas works on empirical observations, whereas boosted
quantile curves are fitted descriptive models.

## A union of grids is not a universal spectrum

The supplied merged library has 1,140 corrected wavelength columns because
three native 426-band grids contribute different column names. Each pixel has
its own native support. Structural NaNs in other grids' columns are not missing
plants, and filling them with zeros would invent spectral shape. Applying PCA
to the raw union or dropping every row with any NaN would be scientifically wrong.

`harmonize_spectrum` interpolates only between adjacent finite native samples
within a declared maximum gap (8 nm in the atlas). It neither extrapolates nor
bridges missing native samples or excluded atmospheric intervals. Exact isolated
samples can remain; they provide no interval area. Common-support analyses then
select wavelengths finite across the eligible spectra. The publication analysis
uses 360 coordinates, with 1340–1450 and 1790–2000 nm excluded.

## Sampling units and weighting

1. Pixel median within GlobalID / flight / source image / polygon.
2. Equal-observation median for each GlobalID, or separately each GlobalID/year.
3. Equal plant or polygon/year weighting for category summaries.

An image with more extracted pixels does not automatically dominate a plant
with fewer pixels. Repeating all pixel records does not create new plant
replicates. Duplicating only a subset can change its pixel median; that is a
changed within-polygon empirical distribution, not extra biological replication.
Finite negative corrected values are not automatically nodata; declared nodata
sentinels, nonfinite values and physical units require separate checks.

## Run the module-level atlas

```python
from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas

audit = run_plant_spectral_atlas(
    "my_polygons.parquet", "atlas",
    spectral_stage="corr", species_field="cover_category",
    min_plants_per_species=10, make_figures=False,
)
```

The source needs the identity/flight/source/polygon/label fields and detectable
wavelength names; see [contracts](../api/scientific-analysis.md). Compact outputs
include plant/flight native and harmonized spectra, per-group medians, counts,
coverage, extreme-value records and manifests. Existing valid atlas outputs are
reused; failed reruns preserve completed outputs. The existing
[full atlas vignette](../vignettes/plant-spectral-atlas.md) documents advanced panels.

## Quantiles and regional comparisons

The optional `quantile-models` extra supplies XGBoost. The research workflows fit
99 curves at percentiles 1–99, separately for species and individual identities.
A fitted curve is not an additional plant or independent endmember. Tail support
and limited flights can make extreme quantiles unstable; matching experiments
have not established a validated unknown-species classifier.

Year/site panels refit the specified cohorts using acquisition dates and retain
shared identities. They describe regional samples, not an experiment isolating
climate, site or year effects. Species and acquisition composition may differ.
[Quantile validation](https://github.com/earthlab/spectralbridge/blob/main/provenance/quantile-models/2026-10-13/VALIDATION.md)
records the fitted models and baseline matching performance.
