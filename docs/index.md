---
hide:
  - toc
---

<div class="sb-home">
  <img class="sb-preload-logo" src="asset/img/spectralbridge_logo.png" alt="SpectralBridge logo" loading="eager">

  <section class="sb-hero">
    <div class="sb-hero__copy">
      <p class="sb-eyebrow">Drone hyperspectral → Landsat reflectance</p>
      <h1 id="spectralbridge"><span>Drone to</span><span>Landsat</span></h1>
      <p class="sb-hero__lead">Make hyperspectral reflectance comparable across scales.</p>
      <p class="sb-hero__body">SpectralBridge carries drone and airborne observations through correction, spectral convolution, tabular extraction, and QA—while keeping every scientific decision inspectable and reproducible.</p>
      <div class="sb-button-row">
        <a class="sb-button sb-button--primary" href="vignettes/">Learn by doing</a>
        <a class="sb-button sb-button--secondary" href="vignettes/full-pipeline/">Run the full pipeline</a>
      </div>
    </div>
    <div class="sb-hero__art">
      <img src="asset/img/spectralbridge_logo.png" alt="SpectralBridge connects drone, airborne, and satellite observations across a reflectance spectrum">
      <p>Drone <span>→</span> airborne <span>→</span> Landsat</p>
    </div>
  </section>

  <section class="sb-manifesto">
    <p class="sb-kicker">Why it exists</p>
    <h2>One spectral workflow. Three observing scales.</h2>
    <p>Move from fine-resolution hyperspectral measurements to Landsat-compatible bands without hiding the corrections, response functions, provenance, or quality evidence along the way.</p>
  </section>

  <section class="sb-section sb-section--routes">
    <div class="sb-section__intro">
      <p class="sb-kicker">Choose your way in</p>
      <h2>Start with what you need today.</h2>
    </div>
    <div class="sb-card-grid sb-card-grid--three">
      <a class="sb-route-card sb-route-card--yellow" href="vignettes/">
        <span class="sb-route-card__number">01</span>
        <h3>Learn</h3>
        <p>Follow one focused vignette for each module—or run the complete workflow.</p>
        <strong>Browse the vignettes →</strong>
      </a>
      <a class="sb-route-card sb-route-card--teal" href="validation/">
        <span class="sb-route-card__number">02</span>
        <h3>Validate</h3>
        <p>See the input variations, explicit checks, and diagnostics behind reliability claims.</p>
        <strong>Inspect the evidence →</strong>
      </a>
      <a class="sb-route-card sb-route-card--paper" href="reference/">
        <span class="sb-route-card__number">03</span>
        <h3>Reference</h3>
        <p>Look up stage contracts, filenames, configuration, schemas, algorithms, and APIs.</p>
        <strong>Open technical details →</strong>
      </a>
    </div>
  </section>

  <section class="sb-section sb-section--workflow">
    <div class="sb-section__intro">
      <p class="sb-kicker">The scientific story</p>
      <h2>Raw signal in. Comparable evidence out.</h2>
      <p class="sb-subtitle">Each stage writes validated files that the next stage can understand—and a future rerun can safely reuse.</p>
    </div>
    <div class="sb-workflow">
      <div class="sb-workflow__step"><span>01</span>Acquire</div>
      <div class="sb-workflow__step"><span>02</span>Correct</div>
      <div class="sb-workflow__step"><span>03</span>Harmonize</div>
      <div class="sb-workflow__step"><span>04</span>Tabulate</div>
      <div class="sb-workflow__step"><span>05</span>Validate</div>
    </div>
  </section>

  <section class="sb-evidence">
    <div>
      <p class="sb-kicker">Evidence, not mystery</p>
      <h2>Every transformation should leave a trail.</h2>
    </div>
    <div>
      <p>Validation campaigns record input variation, expected behavior, observed diagnostics, runtime, provenance, and failures. QA panels turn those records into something scientists can inspect.</p>
      <a href="validation/">See how SpectralBridge is validated →</a>
    </div>
  </section>

  <section class="sb-resume-strip">
    <p class="sb-kicker">Already halfway there?</p>
    <h2>Carry on from the files you have.</h2>
    <p>The pipeline validates existing artifacts and resumes at the first missing or invalid stage.</p>
    <a class="sb-button sb-button--ink" href="vignettes/carry-on-wayward-son/">Carry On My Wayward Son →</a>
  </section>

  <section class="sb-cta">
    <div>
      <p class="sb-kicker">Ready when you are</p>
      <h2>Translate reflectance across sensors and scales.</h2>
    </div>
    <div class="sb-button-row">
      <a class="sb-button sb-button--primary" href="vignettes/full-pipeline/">Run end to end</a>
      <a class="sb-button sb-button--secondary" href="reference/">Read the reference</a>
    </div>
  </section>
</div>
