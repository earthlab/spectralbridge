# QA Panel

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Pipeline</p>
    <h1>AOP QA panel</h1>
    <p class="sb-doc-lead">The normal NEON/AOP pipeline writes a compact PNG quick-look, a machine-readable JSON sidecar, and a multi-page PDF audit report for each completed flight line.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>PNG preview</h3>
        <p>Fast visual triage with raw ENVI, corrected ENVI, and core correction diagnostics.</p>
      </article>
      <article class="sb-doc-card">
        <h3>JSON metrics</h3>
        <p>Structured validation values for automation, dashboards, and regression checks.</p>
      </article>
      <article class="sb-doc-card">
        <h3>PDF audit</h3>
        <p>A fuller report with ENVI overview, correction diagnostics, QA summaries, and parquet/merge checks.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">PNG layout</p>
    <h2>What the quick-look panel shows</h2>
    <p>The single PNG, <code>&lt;prefix&gt;_qa.png</code>, is intentionally compact. It now uses six panels:</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Original ENVI RGB</h3>
        <p>RGB preview from the raw exported ENVI cube using the selected wavelength targets.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Corrected ENVI RGB</h3>
        <p>The same RGB targets after topographic and BRDF correction.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Pre vs post histograms</h3>
        <p>Raw and corrected sampled reflectance distributions plotted together.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Correction distribution</h3>
        <p>Signed and absolute correction deltas by wavelength.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Convolved vs corrected</h3>
        <p>Sensor harmonization scatter diagnostics when convolved products are available.</p>
      </article>
      <article class="sb-doc-card">
        <h3>QA summary and flags</h3>
        <p>Header, validity, reflectance-bound, and issue summaries for quick interpretation.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">PDF layout</p>
    <h2>What the full report adds</h2>
    <p>The PDF, <code>&lt;prefix&gt;_qa.pdf</code>, remains the deeper audit artifact and currently renders four pages:</p>
    <ol class="sb-doc-list">
      <li><strong>ENVI product overview:</strong> raw, corrected, and resampled ENVI products that exist on disk.</li>
      <li><strong>Topographic and BRDF diagnostics:</strong> histograms, delta-by-wavelength plots, and geometry summaries from the correction JSON.</li>
      <li><strong>Additional QA diagnostics:</strong> wavelength/header integrity, mask and reflectance-bound summaries, brightness coefficients, and issue text.</li>
      <li><strong>Parquet and merge quality:</strong> per-stage parquet inventory, merge status, column summaries, and quality checks.</li>
    </ol>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Interpretation</p>
    <h2>How to use the QA outputs</h2>
    <ul class="sb-doc-list">
      <li>Use the PNG first to see whether raw and corrected imagery agree spatially and whether the correction diagnostics look plausible.</li>
      <li>Use the JSON when you need programmatic thresholds, dashboards, or repeatable comparisons across flight lines.</li>
      <li>Use the PDF when a result needs a human-readable audit trail for review, reporting, or publication support.</li>
    </ul>
    <p class="sb-doc-note">QA outputs are part of the scientific workflow contract. They are meant to preserve transparency, not just make the output folder look tidy.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Related pages</p>
    <h2>Where to go next</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="qa/">
        <strong>QA panels and metrics</strong>
        <span>Higher-level overview of QA artefacts and metric families.</span>
      </a>
      <a class="sb-doc-link-card" href="../reference/validation/">
        <strong>Validation metrics</strong>
        <span>Metric definitions and interpretation guidance.</span>
      </a>
      <a class="sb-doc-link-card" href="outputs/">
        <strong>Outputs and file structure</strong>
        <span>Locate the QA files next to ENVI and parquet products.</span>
      </a>
    </div>
  </section>
</div>
