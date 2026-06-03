# Configuration

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Reference</p>
    <h1>Configuration</h1>
    <p class="sb-doc-lead">Most users can rely on the default pipeline behavior, but SpectralBridge does expose a small set of runtime controls for execution engine, restart-safe extraction, merge tuning, and Ray diagnostics.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>CLI first</h3>
        <p>Most configuration is surfaced through <code>spectralbridge-pipeline</code> flags rather than through large external config files.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Restart-safe defaults</h3>
        <p>The pipeline validates outputs and skips good artifacts by default, so reruns are part of the intended workflow.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Ray is optional</h3>
        <p>The default engine is Ray, but thread and process execution remain available for constrained or debugging environments.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Control surface</p>
    <h2>Where configuration comes from</h2>
    <ol class="sb-doc-list">
      <li>CLI arguments and Python function parameters</li>
      <li>A small set of environment variables used mainly for Ray behavior</li>
      <li>Package defaults in the pipeline and merge helpers</li>
    </ol>
    <p>There is not currently a project-wide YAML or TOML runtime configuration file for the main processing workflow.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Core runtime options</p>
    <h2>Common pipeline controls</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3><code>--base-folder</code></h3>
        <p>Root location for downloaded HDF5 inputs, ENVI products, parquet outputs, merged tables, and QA artefacts.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>--engine</code></h3>
        <p>Execution backend: <code>ray</code>, <code>thread</code>, or <code>process</code>. Ray remains the default in the NEON CLI path.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>--max-workers</code></h3>
        <p>Upper bound for concurrent work. Higher values can improve throughput but also increase memory pressure.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>--parquet-chunk-size</code></h3>
        <p>Controls chunk size for ENVI-to-parquet extraction and is one of the safest tuning knobs when memory is limited.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>--merge-memory-limit</code></h3>
        <p>Tunes the DuckDB merge stage when parquet joins become memory-heavy.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>--merge-temp-directory</code></h3>
        <p>Lets the merge stage spill to a specific scratch location instead of relying on the default temp directory.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Environment variables</p>
    <h2>Supported environment knobs</h2>
    <p>The current codebase uses a relatively small set of environment variables directly:</p>
    <table>
      <thead>
        <tr><th>Variable</th><th>Purpose</th></tr>
      </thead>
      <tbody>
        <tr><td><code>CSC_RAY_NUM_CPUS</code></td><td>Override Ray helper CPU selection when you want a different cap than <code>--max-workers</code>.</td></tr>
        <tr><td><code>CSC_RAY_DEBUG</code></td><td>Enable extra Ray diagnostics for troubleshooting initialization and dispatch behavior.</td></tr>
        <tr><td><code>RAY_DISABLE_DASHBOARD</code></td><td>Can override the default suppression of the Ray dashboard if you intentionally want Ray’s dashboard behavior changed.</td></tr>
      </tbody>
    </table>
    <p class="sb-doc-note">Older documentation sometimes referenced <code>CSCAL_TMPDIR</code>, <code>CSCAL_LOGLEVEL</code>, or <code>CSCAL_RAY_ADDRESS</code>. Those are not current first-class runtime controls in the present package code.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Sensor and workflow configuration</p>
    <h2>What is built into the package?</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Sensor outputs</h3>
        <p>Canonical sensor products are defined through path helpers and data tables, including Landsat TM, ETM+, OLI, OLI-2, and the current MicaSense-related products.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Spectral data tables</h3>
        <p>Band centers, FWHM values, and brightness coefficient tables live under <code>src/spectralbridge/data/</code> and are part of the package contract.</p>
      </article>
    </div>
    <p>If you change sensor support or brightness tables, update the code, tests, and naming/output documentation together.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Operational guidance</p>
    <h2>How to tune safely</h2>
    <ul class="sb-doc-list">
      <li>Prefer lowering <code>--max-workers</code> before assuming a scientific stage is broken.</li>
      <li>Lower <code>--parquet-chunk-size</code> if parquet extraction or polygon workflows are memory-bound.</li>
      <li>Point <code>--merge-temp-directory</code> at a fast local scratch disk for large merges.</li>
      <li>Use <code>thread</code> for reproducible first-pass debugging and <code>ray</code> for larger production runs.</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related references</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="../usage/cli/">
        <strong>CLI reference</strong>
        <span>See the concrete command patterns for the main entry points.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/stages/">
        <strong>Pipeline stages</strong>
        <span>Understand which stages consume each setting.</span>
      </a>
      <a class="sb-doc-link-card" href="validation/">
        <strong>Validation metrics</strong>
        <span>Review the QA and output checks that make reruns safe.</span>
      </a>
    </div>
  </section>
</div>
