# Quickstart

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Getting started</p>
    <h1>Quickstart</h1>
    <p class="sb-doc-lead">Run SpectralBridge end to end from the command line or from Python using the same restart-safe pipeline.</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>CLI path</h3>
        <p>Best for laptops, servers, containers, and batch jobs.</p>
        <p><code>spectralbridge-pipeline</code></p>
      </article>
      <article class="sb-doc-card">
        <h3>Notebook path</h3>
        <p>Best for exploratory and reproducible Python workflows.</p>
        <p><code>from spectralbridge import go_forth_and_multiply</code></p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Install</p>
    <h2>Install SpectralBridge</h2>
    <p>Install from PyPI:</p>

```bash
pip install spectralbridge
```

    <p>Ray is part of the standard dependency set. The <code>spectralbridge[full]</code> extra remains available as a compatibility alias for existing automation and currently resolves to the same dependency set.</p>
    <p class="sb-doc-note">Legacy imports and CLI aliases still work, but the Quickstart uses the canonical <code>spectralbridge</code> namespace and <code>spectralbridge-*</code> entry points.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">CLI workflow</p>
    <h2>Run a NEON flight line from the terminal</h2>
    <p>Use the CLI when you want a file-based, restart-safe run that works the same way on your laptop, in a container, or on HPC.</p>

```bash
BASE=output_quickstart
mkdir -p "$BASE"

spectralbridge-pipeline \
  --base-folder "$BASE" \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --max-workers 2 \
  --engine thread
```

    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>What it writes</h3>
        <p>Per-flightline ENVI exports, corrected ENVI, sensor-resampled products, Parquet sidecars, a merged parquet, and QA outputs.</p>
      </article>
      <article class="sb-doc-card">
        <h3>What happens on rerun</h3>
        <p>Completed stages are validated and skipped when their outputs are already present and usable.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Why <code>thread</code> here</h3>
        <p>The pipeline defaults to <code>ray</code>, but <code>thread</code> keeps the example deterministic and lightweight for first runs.</p>
      </article>
    </div>

    <p>Typical first-run stages:</p>
    <ul class="sb-doc-list">
      <li>download the NEON HDF5 flightline</li>
      <li>export the raw ENVI cube</li>
      <li>build correction JSON</li>
      <li>apply topographic and BRDF correction</li>
      <li>resample into configured target sensors</li>
      <li>write Parquet sidecars and the merged parquet</li>
      <li>render QA PNG and JSON outputs</li>
    </ul>

    <p>To inspect QA outputs after the run, look inside the flightline subdirectory under <code>$BASE</code> for files such as <code>*_qa.png</code> and <code>*_qa.json</code>. PDF output may also be present when enabled during rendering.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Python workflow</p>
    <h2>Run the same pipeline from Python</h2>
    <p>Use the Python API when you want to stay in a notebook or script while keeping the same on-disk outputs and restart behavior.</p>

```python
from spectralbridge import go_forth_and_multiply

base = "output_quickstart_py"

go_forth_and_multiply(
    base_folder=base,
    site_code="NIWO",
    year_month="2023-08",
    product_code="DP1.30006.001",
    flight_lines=[
        "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance",
    ],
    max_workers=2,
    engine="thread",
)
```

    <p>Preview the merged parquet after the run:</p>

```python
import duckdb
import os

flightline = "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
merged = os.path.join(base, flightline, f"{flightline}_merged_pixel_extraction.parquet")

duckdb.query(f"SELECT * FROM '{merged}' LIMIT 5").df()
```
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Next steps</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <a class="sb-doc-link-card" href="concepts/why-calibration/">
        <strong>Why cross-sensor calibration?</strong>
        <span>Understand the scientific motivation behind the workflow.</span>
      </a>
      <a class="sb-doc-link-card" href="tutorials/neon-to-envi/">
        <strong>Tutorials</strong>
        <span>Walk through a fuller NEON processing example.</span>
      </a>
      <a class="sb-doc-link-card" href="pipeline/stages/">
        <strong>Pipeline stages</strong>
        <span>See what each stage consumes, writes, and validates.</span>
      </a>
      <a class="sb-doc-link-card" href="usage/parquet/">
        <strong>Working with Parquet outputs</strong>
        <span>Use the authoritative analysis-ready outputs directly.</span>
      </a>
    </div>
  </section>
</div>
