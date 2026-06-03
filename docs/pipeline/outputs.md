# Outputs & File Structure

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Pipeline</p>
    <h1>Outputs &amp; File Structure</h1>
    <p class="sb-doc-lead">Outputs on disk are the primary interface of SpectralBridge. Downstream analysis should rely on these files rather than return values from the Python API.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Canonical outputs</p>
    <h2>Per-flightline contract</h2>
    <p>Naming stems come from <code>spectralbridge.paths.FlightlinePaths</code> and <code>spectralbridge.utils.naming.get_flightline_products</code>. Sensor-specific stems come from <code>SensorProductPaths</code>.</p>

| Output type | Canonical filename pattern | Description | Notes / guarantees |
| --- | --- | --- | --- |
| Raw ENVI (when available) | `<flight_id>_envi.(img|hdr|parquet)` | Direct export of the NEON HDF5 reflectance cube. | Used when present to seed later stages; parquet sidecar is written when exported. |
| BRDF model JSON | `<flight_id>_brdf_model.json` | Scene-level BRDF coefficient tables written before BRDF application. | Includes `iso`/`vol`/`geo`, kernel settings, `ndvi_binning_enabled`, and `ndvi_edges`. |
| BRDF + topographic corrected ENVI | `<flight_id>_brdfandtopo_corrected_envi.(img|hdr|json|parquet)` | Physics-informed normalization and correction JSON produced before sensor resampling. | One corrected set per flightline; parquet mirrors the corrected ENVI cube. |
| Sensor-resampled ENVI + Parquet | `<flight_id>_<sensor>_envi.(img|hdr|parquet)` | Reflectance cubes resampled into the configured target sensor frame. | Sensor stems match `FlightlinePaths.sensor_products`. |
| Merged Parquet | `<flight_id>_merged_pixel_extraction.parquet` | Master table that merges Parquet sidecars across stages into one analysis-ready spectral library. | Exactly one per flightline and treated as the primary success signal. |
| QA artefacts | `<flight_id>_qa.png`, `<flight_id>_qa.json`, optional `<flight_id>_qa.pdf` | Visual and numeric QA summaries aligned to the merged outputs. | PNG and JSON are expected for completed runs; PDF is optional. |
| QA metrics parquet | `<flight_id>_qa_metrics.parquet` | Structured QA metrics by band and sensor. | Emitted alongside QA outputs when QA calculation runs. |
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Success criteria</p>
    <h2>What a successful run looks like</h2>
    <ul class="sb-doc-list">
      <li>The merged parquet exists and is readable: <code>&lt;flight_id&gt;_merged_pixel_extraction.parquet</code>.</li>
      <li>The QA PNG renders with its matching JSON: <code>&lt;flight_id&gt;_qa.png</code> and <code>&lt;flight_id&gt;_qa.json</code>.</li>
      <li>Sensor-specific ENVI and parquet products exist as configured; absence can reflect configuration rather than failure.</li>
      <li>If the merged parquet and QA outputs are present, the flightline completed successfully.</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Restart safety</p>
    <h2>Idempotence and validation</h2>
    <p><code>process_one_flightline</code> and <code>go_forth_and_multiply</code> skip stages whose outputs already exist and validate, so re-running the pipeline does not recompute completed products unless outputs are missing or invalid.</p>
    <p class="sb-doc-note">Drone polygon workflows also attempt to write CSV sidecars next to parquet outputs for portability. The parquet files remain the authoritative outputs.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">How to use these files</p>
    <h2>Recommended downstream usage</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Load parquet first</h3>
        <p>Use merged parquet outputs directly for most analysis tasks.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Inspect QA before modeling</h3>
        <p>Review QA PNG and JSON outputs to confirm spectral health and calibration quality.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Treat ENVI as diagnostic</h3>
        <p>Intermediate ENVI products remain useful for inspection, but many workflows only need parquet and QA outputs.</p>
      </article>
    </div>
  </section>
</div>
