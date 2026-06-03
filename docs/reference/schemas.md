# JSON Schemas

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Reference</p>
    <h1>JSON schemas and metadata sidecars</h1>
    <p class="sb-doc-lead">SpectralBridge writes structured JSON files next to major processing artefacts so correction choices, wavelengths, QA summaries, and provenance remain inspectable after the raster work is done.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Reproducibility</h3>
        <p>Metadata sidecars record how a product was generated instead of forcing users to infer processing history from filenames alone.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Validation</h3>
        <p>QA JSON files carry machine-readable checks that complement the PNG and PDF artefacts.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Stage transparency</h3>
        <p>Each major stage can leave a structured record of what was assumed, fitted, or applied.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Export metadata</p>
    <h2>ENVI export sidecars</h2>
    <p>The export stage records metadata needed to interpret the ENVI cube and the downstream parquet products derived from it.</p>
    <ul class="sb-doc-list">
      <li>wavelength arrays and band names</li>
      <li>reflectance scaling details</li>
      <li>mask and CRS context</li>
      <li>basic provenance for the exported raster</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Correction metadata</p>
    <h2>Topographic and BRDF sidecars</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Topographic metadata</h3>
        <p>Topographic sidecars summarize the slope, aspect, solar geometry, and correction parameters used for the terrain-sensitive part of the workflow.</p>
      </article>
      <article class="sb-doc-card">
        <h3>BRDF metadata</h3>
        <p>BRDF sidecars preserve coefficient summaries, fit diagnostics, kernel settings, and any NDVI-binning context used while building the correction model.</p>
      </article>
    </div>
    <p>The streamlined BRDF model JSON remains the most direct structured record of the fitted coefficient surfaces and kernel configuration for a flight line.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Harmonization metadata</p>
    <h2>Sensor translation sidecars</h2>
    <p>Convolution and harmonization sidecars document how corrected hyperspectral reflectance was translated into target sensor products.</p>
    <ul class="sb-doc-list">
      <li>sensor response assumptions</li>
      <li>wavelength alignment checks</li>
      <li>brightness adjustment coefficients when used</li>
      <li>bandpass integration context and summary metrics</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">QA metadata</p>
    <h2>QA JSON sidecars</h2>
    <p>Every QA JSON file acts as the machine-readable counterpart to the PNG and optional PDF reports.</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Scene-level summaries</h3>
        <p>Reflectance, masking, correction, geometry, and harmonization summaries live here for dashboards and automated review.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Provenance and workflow context</h3>
        <p>QA payloads also carry package version, created time, and other details that make a run auditable later.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">How to use them</p>
    <h2>Why these files matter downstream</h2>
    <p>These JSON files are useful when you need to:</p>
    <ul class="sb-doc-list">
      <li>reproduce a published processing run</li>
      <li>compare runs across software versions</li>
      <li>debug a suspicious corrected or harmonized output</li>
      <li>drive dashboards or automated quality gates from structured metadata</li>
    </ul>
    <p class="sb-doc-note">The raster and parquet outputs are still the main analysis products, but the JSON sidecars are the best explanation of how those products were created.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="validation/">
        <strong>Validation metrics</strong>
        <span>See the metric families that appear in the QA JSON payloads.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/outputs/">
        <strong>Outputs &amp; file structure</strong>
        <span>Match sidecars to the files they describe.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/qa/">
        <strong>QA panels &amp; metrics</strong>
        <span>See how the structured summaries surface in the visual reports.</span>
      </a>
    </div>
  </section>
</div>
