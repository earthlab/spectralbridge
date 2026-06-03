# Command-Line Interface (CLI)

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Usage</p>
    <h1>Command-Line Interface</h1>
    <p class="sb-doc-lead">The CLI provides restart-safe entry points for downloading NEON flightlines, running the full pipeline, generating QA outputs, and repairing missing intermediate products.</p>
    <p class="sb-doc-note">Legacy CLI aliases still forward to the same implementation, but the primary command names are <code>spectralbridge-*</code>.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Entry points</p>
    <h2>Available commands</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3><code>spectralbridge-download</code></h3>
        <p>Download NEON HDF5 flightlines into a workspace.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>spectralbridge-pipeline</code></h3>
        <p>Run the full NEON processing pipeline end to end.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>spectralbridge-qa</code></h3>
        <p>Re-render QA PNG/JSON outputs for processed flightlines.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>spectralbridge-recover-raw</code></h3>
        <p>Backfill raw ENVI exports when corrected outputs already exist.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>spectralbridge-qa-summary</code></h3>
        <p>Build a multi-page PDF summary of recursive drone QA PNG outputs.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>spectralbridge-merge-duckdb</code></h3>
        <p>Merge per-product parquet outputs into a flightline-level master table.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-download</code></h2>
    <p>Downloads NEON HDF5 flightlines into a workspace directory using the package download helpers.</p>

```bash
spectralbridge-download SOAP \
  --year-month 2021-06 \
  --flight NEON_D17_SOAP_DP1_L057-1_20210615_directional_reflectance \
  --output data
```

    <ul class="sb-doc-list">
      <li>Required: positional <code>site</code>, <code>--year-month</code>, and one or more <code>--flight</code> values</li>
      <li>Optional: <code>--product</code> defaults to <code>DP1.30006.001</code></li>
      <li>Optional: <code>--output</code> defaults to <code>data</code>, with downloads written under <code>&lt;output&gt;/&lt;site&gt;/</code></li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-pipeline</code></h2>
    <p>Runs the main NEON pipeline and writes all canonical outputs for each flightline.</p>

```bash
spectralbridge-pipeline \
  --base-folder output_demo \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --engine thread \
  --max-workers 2
```

    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Required options</h3>
        <p><code>--base-folder</code>, <code>--site-code</code>, <code>--year-month</code>, <code>--product-code</code>, and <code>--flight-lines</code>.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Parallel defaults</h3>
        <p>The pipeline defaults to <code>--engine ray</code> and <code>--max-workers 8</code>.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Resampling controls</h3>
        <p><code>--resample-method</code> accepts <code>convolution</code>, <code>legacy</code>, or <code>resample</code>.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Merge controls</h3>
        <p>Use <code>--merge-memory-limit</code>, <code>--merge-threads</code>, <code>--merge-row-group-size</code>, and <code>--merge-temp-directory</code> to tune DuckDB merging.</p>
      </article>
    </div>

    <p>Outputs include raw ENVI exports when available, corrected ENVI, sensor-resampled products, per-product parquet sidecars, <code>_merged_pixel_extraction.parquet</code>, and QA files. See <a href="../pipeline/outputs/">Outputs &amp; File Structure</a> for the full contract.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-qa</code></h2>
    <p>Recomputes QA PNG and JSON outputs for existing flightline folders.</p>

```bash
spectralbridge-qa --base-folder output_demo --quick
```

    <ul class="sb-doc-list">
      <li><code>--base-folder</code> is required</li>
      <li><code>--quick</code> uses the deterministic 25k-pixel path; <code>--full</code> disables that subsampling shortcut</li>
      <li><code>--n-sample</code> defaults to <code>100000</code></li>
      <li><code>--rgb-bands</code> accepts values such as <code>660,560,490</code> or symbolic <code>R,G,B</code></li>
      <li><code>--save-json / --no-save-json</code> controls whether <code>_qa.json</code> is written alongside the PNG</li>
      <li><code>--out-dir</code> copies the generated QA files elsewhere after rendering</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-recover-raw</code></h2>
    <p>Scans a base folder for HDF5 plus corrected ENVI outputs and backfills missing raw ENVI exports so restart-safe downstream stages can continue cleanly.</p>

```bash
spectralbridge-recover-raw \
  --base-folder output_demo \
  --brightness-offset 0.0
```
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-qa-summary</code></h2>
    <p>Builds a multi-page PDF summary by recursively finding drone QA PNG files.</p>

```bash
spectralbridge-qa-summary drone_outputs --output-pdf drone_outputs/qa_summary.pdf
```

    <ul class="sb-doc-list">
      <li>Required: positional <code>base_dir</code></li>
      <li>Optional: <code>--output-pdf</code> to override the default output path</li>
      <li>Optional: <code>--pattern</code> defaults to <code>*__qa.png</code></li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2><code>spectralbridge-merge-duckdb</code></h2>
    <p>Merges per-product parquet tables into a master parquet and can optionally render QA alongside the merge output.</p>

```bash
spectralbridge-merge-duckdb --help
```

    <p>Use this command when you need direct control over parquet merging outside the main pipeline orchestration.</p>
  </section>
</div>
