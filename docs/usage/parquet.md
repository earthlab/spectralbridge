<div class="sb-doc-page" markdown="1">
<section class="sb-doc-hero" markdown="1">
<p class="sb-kicker">Usage</p>
<h1>Working with parquet outputs</h1>
<p class="sb-doc-lead">Read the row model, source identity and native wavelength grid before combining spectral tables.</p>
</section>

<section class="sb-doc-section" markdown="1">

## Table families and rows

Current raster exports are **wide tables: one row per retained pixel**, with
one reflectance column per band. They are not long pixel–band tables.

| Product | Row represents | Spectral fields and provenance |
| --- | --- | --- |
| Per-product ENVI sidecar | One retained pixel from one raster product | Stage-prefixed band columns, such as `corr_b001_wl0382nm`; `row`, `col`, `pixel_id`, `source_image` and coordinate/CRS fields where available |
| Per-flightline merged table | One pixel with available stages joined | Raw, corrected and resampled columns; stage availability depends on supplied products |
| Polygon extraction / merged polygon table | One retained pixel linked to polygon attributes | Polygon/source identifiers and labels alongside spectral columns; **not** one median spectrum per plant |
| Cross-flight concatenation | Rows from several source tables | May contain a sparse union of different native wavelength grids; retain original table/flightline identity |
| Spectral-library input | Supplied spectra with grouping labels; row meaning must be declared | One compatible wavelength-bearing grid; polygon, plant, species and source fields where supplied; preflight reports counts, not biological independence |
| Normal bulk analysis | Compact sufficient statistics, coefficients and diagnostics | Not an ordinary pixel cache; explicit `build_harmonized_dataset()` is a separate row-materialization workflow |

The merge reader also accepts legacy long inputs with wavelength and reflectance
fields and pivots them. This compatibility does not make `wavelength_nm` and
`reflectance` universal columns in current exports. Inspect the actual schema.
Stage prefixes vary with product names; do not assume a column contains the
word `landsat` simply because it is an OLI product.

`pixel_id` is derived from raster row/column and width. It is local to a raster,
not a globally unique plant or pixel identifier. Preserve source table/flightline
identity and use it with `pixel_id` for cross-flight joins. Check polygon IDs and
repeated observations separately before counting independent plants.

Per-product exports exclude pixels with nodata or nonfinite bands. Finite negative
corrected reflectance is not automatically nodata. Stored values are not guaranteed
to be unit-interval reflectance: verify source scaling and units before plotting
or comparing products. Column wavelength labels are
rounded to integer nanometres; missing or short header wavelengths can trigger
fallback labels. Verify physical wavelengths against source headers and sensor
configuration before treating labels as a calibrated spectral axis.

## Native grids are not a common spectral axis

!!! warning "A merged schema can contain several native grids"
    Cross-flight unioning can retain multiple wavelength-bearing columns for the
    same band index. A row may populate only its source grid, leaving the other
    grids null. Sorting every `corr_*` column by wavelength can therefore create
    a false spectrum, duplicate bands and artificial gaps. A low fraction of
    finite cells across the union schema alone does not establish data loss.

Reconstruct each source grid from its original schema/header and provenance.
Select the verified band columns for that source, keep values paired with their
wavelengths, then inspect missingness **within that grid**. Preserve the source
identity and wavelength mapping with any derived table. If a common grid is
needed, document the interpolation/convolution method, overlap, gap handling and
excluded wavelengths explicitly; concatenation is not harmonization.

The [spectral-library adapter](../vignettes/spectral-library.md) expects one
compatible physical grid. Selecting `spectral_stage="corr"` does not reconstruct
multiple source grids or repair a sparse union schema.

## Inspect before collecting data

DuckDB can inspect the schema and a bounded sample without loading a whole cube:

```python
import duckdb

source = "flight_merged_pixel_extraction.parquet"  # your existing output
relation = duckdb.read_parquet(source)
print(list(zip(relation.columns, relation.types)))
print(relation.limit(5).df())
```

After checking that this is one source grid, select a verified spectral column
from that schema. This example summarizes one band, not an entire spectrum:

```python
band = "corr_b001_wl0382nm"  # replace with a verified column in your file
if band not in relation.columns:
    raise ValueError(f"Band not in supplied schema: {band}")
quoted_band = '"' + band.replace('"', '""') + '"'
print(relation.aggregate(f"count(*) AS pixels, avg({quoted_band}) AS mean_reflectance").df())
```

For a union table, filter by the retained source identifier and select that
source's verified native column list **before** collecting into pandas. Do not
fill structural nulls with zero or infer a plant's grid from species name.
Use ENVI `.img/.hdr` for spatial cube access, orientation and authoritative raster
metadata. Parquet is useful for bounded filtering, grouping and joining; it does
not replace the raster contract.

## From pixels to biological summaries

Polygon pixels are spatially correlated subsamples. First define a per-polygon
summary, then identify repeat observations of the same plant, and only then
summarize independent plants within species or PFT. Report pixel, polygon,
plant, flightline, site and year counts separately where those identifiers exist.
Species labels alone do not establish independence or trait accuracy.
A source table name can supply a site/year only when its naming contract has
been checked; retain the original name and expose unresolved identifiers.

Synthetic Landsat or MicaSense products convolved from NEON are derived views
of the same observations. Their agreement is a diagnostic, not independent
satellite/drone validation. See the [evidence hierarchy](../validation/evidence-hierarchy.md).

## Related pages

- [Output files and naming](../pipeline/outputs.md)
- [Polygon extraction](../pipeline/polygons.md)
- [Spectral-library preflight and reports](../vignettes/spectral-library.md)
- [Bulk analysis](../vignettes/bulk-analysis.md)

</section>
</div>
