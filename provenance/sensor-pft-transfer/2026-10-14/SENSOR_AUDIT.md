# Sensor provenance and coordinate audit

## Source inventory

The supplied merged library has 85,706 pixel records and 3,639 unique GlobalIDs.
`source_columns.json` enumerates exact columns, including 1,140-column union
schemas each for `raw` and `corr`, six TM, six ETM+, seven OLI and ten MicaSense
channels, with darkened/undarkened counterparts. Metadata identifies corrected
BRDF/topographic NEON imagery as the reference. These are synthetic spectral
representations on the same NEON pixel locations, not independent satellite or
drone observations. `raw` is pre-BRDF/topographic native NEON; `corr` is corrected
native NEON. The pipeline consumes corrected ENVI to create all sensor products;
its inline Gaussian/convolution and straight/legacy routes are distinct. Exact
historical runtime and source headers are not supplied, so no byte-identical
historical SRF claim is made.

## OLI gate: admitted as synthetic OLI-like representation

Exact stored centers: 443, 482, 561, 655, 865, 1609, 2201 nm. These match the
exporter's seven-channel OLI definition and rounded packaged Landsat 8 OLI
centers (443,482,561.4,654.6,864.7,1608.9,2200.7); physical identities are coastal,
blue, green, red, NIR, SWIR1, SWIR2. Packaged FWHMs are
16,60,57.3,37.5,28.3,84.7,186.7 nm. These are Gaussian band approximations, not a
manufacturer-measured response-curve validation.

The source audit samples two pixels per source table and compares the stored
undarkened OLI values with Gaussian and nearest-channel reductions of the native
raw and corrected spectra. Corrected Gaussian relative RMSE median 0.001012,
maximum 0.002509, versus raw Gaussian median 0.010924, maximum 0.149501, and
corrected nearest-channel maximum 0.114181. Rounded native coordinates and
unknown historical kernels prevent exact reconstruction. This strong numerical
consistency plus naming and code lineage supports corrected-derived OLI-like
interpretation, not independent empirical validation. Full per-source diagnostics
are in generation_consistency.csv. All 85,706 rows have seven finite OLI bands;
there is no multispectral representation loss at pixel/identity level.

`olioli_undarkened` is the primary reduction; `olioli` additionally applies
brightness factors. Code saves undarkened values before Landsat-specific
multiplicative adjustment. brightness_audit.csv verifies per-band stored ratios.
Positive common per-band gains cancel in beta/pooled-SD effects, including median
aggregation; verify this numerically. TM/ETM+ families are analogous synthetic
six-band products, inventoried but outside the requested OLI experiment.

## MicaSense gate: BLOCKED for biological inference

Stored coordinates in both ten-band families:
475,560,668,717,840,841,842,843,844,845 nm.

Packaged intended ten-band coordinates:
444,475,531,560,650,668,705,717,740,842 nm, with FWHMs
28,32,14,27,16,14,10,12,18,57 nm.

The exporter fallback instead supplies FIVE centers 475,560,668,717,840. Both
polygon_extraction.py and parquet_export.py extend missing centers by 1-nm steps,
which exactly explains the suspicious five padded coordinates. The original
source .hdr files are absent in the repository; recorded paths point to an
unavailable /home/jovyan archive. The merged Parquet has no Arrow schema metadata
and no populated fwhm_nm. The intended configuration alone cannot establish
which physical response generated each stored value or rule out export sorting.
No relabeling based on ten-band count/order is authorized as a validation.

All ten MicaSense values are finite for all rows, and darkened/undarkened values
can be paired by identity, but availability does not validate physical identity.
No MicaSense PFT p-values, effect ratios, direction, ranking or ecological claims
are computed. Tables and figures mark this branch blocked rather than interpreting
its erroneous coordinates. Supply original product headers plus generation/SRF
provenance (or regenerate a separately named verified product from immutable
source spectra) before opening this branch. The pipeline does not generally
apply the Landsat-only adjustment to MicaSense; stored paired values, rather than
the suffix alone, determine whether they differ.

## Evidence files and code

- source_family_support.csv: band completeness by family.
- source_columns.json: every exact field name.
- brightness_audit.csv: actual stored darkened/undarkened ratios.
- generation_consistency.csv: bounded sampled numerical lineage audit.
- audit_source.py: reproducible projected, batched audit; no pixel cache.
- Source code: pipelines/pipeline.py (_build_sensor_srfs, convolution and
  brightness stages), standard_resample.py, resample.py,
  exports/schema_utils.py, polygon_extraction.py, parquet_export.py,
  sensor_pairs.py, data/landsat_band_parameters.json.

## Structural missingness and historical-label caveats

`raw` and `corr` each have 426 finite native bands at every pixel, with no blank
pixels. Their 1,140-column merged union has structural NaNs because three native
grids differ; these NaNs are not missing plants or 62.6% loss of a physical
spectrum. Native grid counts are in native_family_support.csv. Corrected compact
spectra have complete support at all 360 admitted test wavelengths after the
specified atmospheric exclusions. Every discrete product is finite in every
source row. Thus neither OLI sample loss nor native-grid union sparsity explains
the observed retention differences.

In this dataset every MicaSense value is exactly equal to its undarkened
counterpart; a legacy plot title containing "darkened" does not establish an
applied adjustment. OLI gains match the packaged brightness percentages within
float32 precision, and all are positive. Repeated prefixes such as `olioli`,
`tmtm` and `etm+etm+` are stored family names, not evidence of two sequential
sensor convolutions. The actual reduction graph supported by code/data is
corrected NEON -> separate synthetic OLI and MicaSense branches, with OLI
brightness adjustment downstream. There is no demonstrated NEON -> MicaSense ->
OLI cascade and no physical MicaSense inference while its mapping is blocked.
