# QA Panels & Metrics

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Pipeline</p>
    <h1>QA panels and metrics</h1>
    <p class="sb-doc-lead">Each completed flight line writes visual and machine-readable QA artifacts so correction, harmonization, and export decisions remain inspectable after the run.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>QA PNG</h3>
        <p>Fast visual triage for reflectance, masks, brightness shifts, and sensor diagnostics.</p>
      </article>
      <article class="sb-doc-card">
        <h3>QA PDF</h3>
        <p>A longer-form audit record when multi-page reporting is enabled for the workflow.</p>
      </article>
      <article class="sb-doc-card">
        <h3>QA JSON</h3>
        <p>Machine-readable metrics and metadata for automation, validation, and reproducible review.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Visual QA</p>
    <h2>What the QA PNG is for</h2>
    <p>The PNG is the fastest way to spot unusual behavior in a flight line without loading the raster products manually. Typical panels summarize:</p>
    <ul class="sb-doc-list">
      <li>reflectance distributions for representative wavelengths</li>
      <li>spatial mask coverage and invalid-pixel structure</li>
      <li>before and after brightness behavior</li>
      <li>BRDF correction diagnostics</li>
      <li>wavelength and target-sensor alignment checks</li>
    </ul>
    <p>Use the PNG for quick triage before deciding whether deeper inspection is necessary.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Audit outputs</p>
    <h2>What the PDF and JSON capture</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>QA PDF</h3>
        <p>The PDF expands the visual report into a flight-line-level audit artifact with extended diagnostics, tables, optional per-band summaries, and correction details.</p>
        <p>Think of it as the human-readable record you keep with a processing run.</p>
      </article>
      <article class="sb-doc-card">
        <h3>QA JSON</h3>
        <p>The JSON carries the same run into a machine-readable form for dashboards, automation, and regression checks.</p>
        <p>It is the better interface when you need to compare runs systematically.</p>
      </article>
    </div>

    <p>Common QA JSON categories include:</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Reflectance and masks</h3>
        <p>Bandwise min, max, median, saturated or masked fractions, and cloud, snow, shadow, water, or invalid summaries.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Correction diagnostics</h3>
        <p>BRDF coefficients, reconstruction error summaries, and brightness differences across correction stages.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Sensor harmonization</h3>
        <p>Brightness coefficients, spectral alignment checks, and regression-based metrics when that path is active.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Geometry context</h3>
        <p>Solar and view angles plus terrain summaries that help explain unusual correction behavior.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Interpretation</p>
    <h2>What to watch for</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Reflectance above expected bounds</h3>
        <p>Values well above 1 can point to correction instability, geometry problems, or DEM issues that deserve review.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Large brightness shifts</h3>
        <p>Substantial step changes between raw, corrected, and harmonized products usually warrant a closer look at the relevant stage outputs.</p>
      </article>
      <article class="sb-doc-card">
        <h3>High invalid or shadow fractions</h3>
        <p>These can dominate downstream summaries, especially for difficult illumination conditions or partial-scene coverage.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Noisy coefficients</h3>
        <p>Unstable BRDF or harmonization coefficients often indicate low-SNR regions or other conditions that reduce correction reliability.</p>
      </article>
    </div>
    <p class="sb-doc-note">QA outputs are part of the workflow contract, not optional polish. They are meant to preserve transparency when a downstream analysis needs to explain how a product was generated.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="stages/">
        <strong>Pipeline stages</strong>
        <span>See how QA fits into the full ordered workflow.</span>
      </a>
      <a class="sb-doc-link-card" href="outputs/">
        <strong>Outputs and file structure</strong>
        <span>Find the flight-line files that sit next to the QA artifacts.</span>
      </a>
      <a class="sb-doc-link-card" href="../troubleshooting/">
        <strong>Troubleshooting</strong>
        <span>Use the QA outputs to diagnose common pipeline problems.</span>
      </a>
    </div>
  </section>
</div>
