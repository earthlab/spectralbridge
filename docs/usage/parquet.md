# Working with Parquet Outputs

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Usage</p>
    <h1>Working with parquet outputs</h1>
    <p class="sb-doc-lead">Parquet sidecars and merged parquet tables are the main analysis-ready outputs for tabular workflows in SpectralBridge.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Authoritative tables</h3>
        <p>They are the intended interface for DuckDB, pandas, and other columnar tools.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Restart-safe exports</h3>
        <p>The pipeline validates and reuses good parquet outputs instead of recomputing them blindly.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Large-scene friendly</h3>
        <p>They support filtering and aggregation without loading a whole raster cube into memory.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Why parquet</p>
    <h2>Why the pipeline writes columnar outputs</h2>
    <p>ENVI remains the raster authority for image-style access, but parquet is the practical entry point for most analysis, validation, and merge workflows. It compresses well, reads efficiently by column, and works cleanly with DuckDB and pandas.</p>
    <p>That makes parquet especially useful when you want to summarize reflectance, inspect metadata, or join outputs across stages without materializing the full scene in Python memory.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">File contract</p>
    <h2>What files you should expect</h2>
    <p>Typical per-product sidecars and merged outputs include names such as:</p>

```text
*_envi.parquet
*_brdfandtopo_corrected_envi.parquet
*_landsat_oli_envi.parquet
*_merged_pixel_extraction.parquet
```

    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Per-product parquet sidecars</h3>
        <p>These sit beside the corresponding ENVI products and store one row per pixel-band observation for that product.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Merged parquet</h3>
        <p>This combines raw, corrected, and sensor-resampled products into the per-flightline table named <code>&lt;flight_id&gt;_merged_pixel_extraction.parquet</code>.</p>
      </article>
    </div>

    <p>Common columns include:</p>
    <ul class="sb-doc-list">
      <li><code>flightline_id</code></li>
      <li><code>row</code>, <code>col</code>, <code>x</code>, <code>y</code></li>
      <li><code>band</code></li>
      <li><code>wavelength_nm</code></li>
      <li><code>fwhm_nm</code></li>
      <li><code>reflectance</code></li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">DuckDB</p>
    <h2>Inspect outputs without loading everything</h2>
    <p>DuckDB is usually the best first tool for large flight lines because it can query parquet lazily.</p>

```python
import duckdb

duckdb.query("""
    SELECT *
    FROM '..._brdfandtopo_corrected_envi.parquet'
    LIMIT 5
""").df()
```

    <p>Check the size of a product:</p>

```python
duckdb.query("""
    SELECT COUNT(*) AS nrows
    FROM '..._landsat_oli_envi.parquet'
""").df()
```

    <p>Summarize reflectance by wavelength:</p>

```python
duckdb.query("""
    SELECT wavelength_nm, AVG(reflectance) AS mean_reflectance
    FROM '..._landsat_oli_envi.parquet'
    GROUP BY wavelength_nm
    ORDER BY wavelength_nm
""").df()
```
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Python access</p>
    <h2>Use pandas carefully and keep ENVI for raster-style work</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card" markdown="1">
        <h3>Pandas</h3>
        <p>Pandas works well once you have narrowed the data down to a manageable size.</p>

```python
import pandas as pd

df = pd.read_parquet("..._merged_pixel_extraction.parquet")
df.head()
```
      </article>
      <article class="sb-doc-card">
        <h3>Raster and cube views</h3>
        <p>If you need full spatial cube behavior, the ENVI <code>.img/.hdr</code> outputs are still the better interface. Parquet-to-xarray workflows usually work best after pivoting or aggregation.</p>
      </article>
    </div>
    <p class="sb-doc-note">For big flight lines, prefer DuckDB for filtering and aggregation first, then collect smaller results into pandas.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="cli/">
        <strong>CLI usage</strong>
        <span>See how the parquet outputs are produced from the command line.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/outputs/">
        <strong>Pipeline outputs</strong>
        <span>Review the file layout and naming conventions around parquet sidecars.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/qa/">
        <strong>QA panels and metrics</strong>
        <span>Connect parquet summaries back to the QA artifacts written for each flight line.</span>
      </a>
    </div>
  </section>
</div>
