# Pipeline Overview & Stages

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Pipeline</p>
    <h1>Pipeline Overview &amp; Stages</h1>
    <p class="sb-doc-lead">SpectralBridge transforms NEON HDF5 directional reflectance into corrected, sensor-harmonized, and analysis-ready outputs through restart-safe, file-based stages.</p>
    <p>The orchestrators <code>process_one_flightline</code> and <code>go_forth_and_multiply</code> validate outputs before skipping them, which makes reruns restart-safe and auditable.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Execution order</p>
    <h2>Stage order and idempotence</h2>
    <ol class="sb-doc-steps">
      <li>Download HDF5 via <code>stage_download_h5</code>.</li>
      <li>Export the raw ENVI cube.</li>
      <li>Build correction JSON.</li>
      <li>Apply BRDF and topographic correction.</li>
      <li>Resample all configured sensors.</li>
      <li>Export Parquet sidecars.</li>
      <li>Merge to <code>_merged_pixel_extraction.parquet</code>.</li>
      <li>Render QA PNG and JSON outputs.</li>
    </ol>
    <p>Each stage checks whether expected outputs exist and validate before deciding to skip or recompute them. Recovery mode exists for raw ENVI exports when corrected products are already present.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>1. Data acquisition</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p>NEON API paths or local HDF5 files.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p>Cached HDF5 tiles stored under the selected <code>--base-folder</code>.</p>
      </article>
    </div>
    <p>Downloads are handled by <code>stage_download_h5</code> and triggered automatically by <code>go_forth_and_multiply</code>.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>2. HDF5 to ENVI export</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p><code>*_directional_reflectance.h5</code> plus per-pixel geometry and metadata.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p><code>*_envi.img/.hdr</code> and the matching parquet sidecar when exported.</p>
      </article>
    </div>
    <p><code>stage_export_envi_from_h5</code> writes the raw ENVI pair using canonical naming in <code>FlightlinePaths</code>, with optional brightness offsets.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>3. Topographic and BRDF correction</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p>Directional or raw ENVI exports, DEM-derived slope and aspect, and solar/view geometry.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p><code>&lt;flight_id&gt;_brdfandtopo_corrected_envi.(img|hdr|json)</code>.</p>
      </article>
    </div>
    <p><code>stage_build_and_write_correction_json</code> writes the parameter JSON, and <code>stage_apply_brdf_and_topo</code> applies the combined correction before downstream resampling.</p>
    <p class="sb-doc-note">The current NEON path writes the corrected cube in fixed non-overlapping spatial chunks. For drone workflows, correction only runs when required ancillary geometry is available for that flight.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>4. Sensor harmonization</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p>BRDF-and-topo-corrected ENVI plus sensor spectral response functions.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p><code>&lt;flight_id&gt;_&lt;sensor&gt;_envi.(img|hdr|parquet)</code>.</p>
      </article>
    </div>
    <p><code>stage_convolve_all_sensors</code> delegates to the configured resample method and iterates through the sensor products registered in <code>FlightlinePaths</code>.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>5. Parquet extraction and merging</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p>Any ENVI cube produced by earlier stages.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p>Per-product parquet files plus <code>&lt;flight_id&gt;_merged_pixel_extraction.parquet</code>.</p>
      </article>
    </div>
    <p><code>_export_parquet_stage</code> builds the per-product sidecars, and <code>merge_flightline</code> uses DuckDB to consolidate them with schema validation before optional QA rendering.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <h2>6. Quality assurance</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Inputs</h3>
        <p>Merged parquet plus supporting ENVI files.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Outputs</h3>
        <p><code>&lt;flight_id&gt;_qa.png</code>, <code>&lt;flight_id&gt;_qa.json</code>, and optional PDF output.</p>
      </article>
    </div>
    <p>QA artefacts come from <code>render_flightline_panel</code> and follow the same canonical stems described in <a href="outputs/">Outputs &amp; File Structure</a>.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Next steps</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <a class="sb-doc-link-card" href="outputs/">
        <strong>Outputs &amp; file structure</strong>
        <span>See the on-disk contract that downstream analyses should rely on.</span>
      </a>
      <a class="sb-doc-link-card" href="qa/">
        <strong>QA panels &amp; metrics</strong>
        <span>Understand the visual and numeric checks generated after processing.</span>
      </a>
    </div>
  </section>
</div>
