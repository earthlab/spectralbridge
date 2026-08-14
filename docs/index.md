---
hide:
  - toc
---

<div class="sb-home">
  <img class="sb-preload-logo" src="asset/img/spectralbridge_logo.png" alt="SpectralBridge logo" loading="eager">

  <section class="sb-hero">
    <div class="sb-hero__copy">
      <p class="sb-eyebrow">Drone hyperspectral → NEON reference → Landsat reflectance</p>
      <h1 id="spectralbridge"><span>Drone to Landsat</span><span>through NEON</span></h1>
      <p class="sb-hero__lead">Make hyperspectral reflectance comparable across scales.</p>
      <p class="sb-hero__body">SpectralBridge uses NEON airborne hyperspectral observations as the translating reference between fine-scale drone measurements and Landsat bandspace. Its correction, spectral convolution, tabular extraction, and QA steps keep every scientific decision inspectable and reproducible.</p>
      <div class="sb-button-row">
        <a class="sb-button sb-button--primary" href="vignettes/">Learn by doing</a>
        <a class="sb-button sb-button--secondary" href="vignettes/full-pipeline/">Run the full pipeline</a>
      </div>
    </div>
    <div class="sb-hero__art">
      <img src="asset/img/spectralbridge_logo.png" alt="SpectralBridge uses NEON airborne observations to connect drone and Landsat reflectance">
      <p>Drone <span>→</span> NEON <span>→</span> Landsat</p>
    </div>
  </section>

  <section class="sb-manifesto">
    <p class="sb-kicker">Why it exists</p>
    <h2>One NEON-mediated bridge. Three observing scales.</h2>
    <p>Relate fine-resolution drone measurements to Landsat-compatible bands through NEON's airborne hyperspectral reference without hiding the corrections, response functions, provenance, or quality evidence along the way.</p>
  </section>

  <section class="sb-science-story" aria-labelledby="sb-science-story-title">
    <div class="sb-science-story__intro">
      <p class="sb-kicker">The system at a glance</p>
      <h2 id="sb-science-story-title">Three technical views. Read them one at a time.</h2>
      <p>The original scientific figure is separated into enlarged panels here. The plots, wavelength ranges, processing stages, and translation relationships remain unchanged; the surrounding text provides a readable path through them.</p>
    </div>

    <article class="sb-science-panel">
      <div class="sb-science-panel__copy">
        <span class="sb-science-panel__number">01 / Observing systems</span>
        <h3>Measure at three scales.</h3>
        <p>NEON airborne imaging spectroscopy, MicaSense UAS observations, and Landsat Collection 2 NBAR each sample reflectance differently. The first panel keeps their spectral ranges and sampling patterns visible together.</p>
        <a href="concepts/why-calibration/">Why cross-sensor calibration matters →</a>
      </div>
      <div class="sb-science-panel__viewport" tabindex="0" aria-label="Scrollable enlarged sensor-platform figure">
        <figure class="sb-science-panel__figure">
          <a href="images/homepage/spectralbridge-technical-overview.png" aria-label="Open the complete technical overview at full resolution">
            <svg viewBox="15 140 460 760" role="img" aria-labelledby="sb-sensors-title sb-sensors-desc" xmlns:xlink="http://www.w3.org/1999/xlink">
              <title id="sb-sensors-title">NEON, MicaSense, and Landsat observing systems</title>
              <desc id="sb-sensors-desc">The supplied technical panel comparing an airborne hyperspectral sensor, a multispectral research drone, and Landsat Collection 2 with their wavelength ranges and schematic reflectance plots.</desc>
              <image xlink:href="images/homepage/spectralbridge-technical-overview.png" width="1536" height="1024"></image>
            </svg>
          </a>
          <figcaption>Enlarged from the supplied technical figure. Open for the full-resolution overview.</figcaption>
        </figure>
      </div>
    </article>

    <article class="sb-science-panel sb-science-panel--reverse">
      <div class="sb-science-panel__copy">
        <span class="sb-science-panel__number">02 / Processing chain</span>
        <h3>Correct before you compare.</h3>
        <p>The processing panel follows input reflectance through topographic correction, BRDF correction, spectral convolution, and empirical calibration. Keeping these operations explicit is what makes the translation inspectable.</p>
        <a href="vignettes/full-pipeline/">Walk through the full pipeline →</a>
      </div>
      <div class="sb-science-panel__viewport" tabindex="0" aria-label="Scrollable enlarged processing-pipeline figure">
        <figure class="sb-science-panel__figure">
          <a href="images/homepage/spectralbridge-technical-overview.png" aria-label="Open the complete technical overview at full resolution">
            <svg viewBox="490 140 506 760" role="img" aria-labelledby="sb-pipeline-title sb-pipeline-desc" xmlns:xlink="http://www.w3.org/1999/xlink">
              <title id="sb-pipeline-title">SpectralBridge processing and calibration pipeline</title>
              <desc id="sb-pipeline-desc">The supplied technical panel showing input reflectance, topographic correction, BRDF correction, spectral convolution with sensor response functions, and empirical calibration.</desc>
              <image xlink:href="images/homepage/spectralbridge-technical-overview.png" width="1536" height="1024"></image>
            </svg>
          </a>
          <figcaption>Each correction and calibration step remains visible at its original technical detail.</figcaption>
        </figure>
      </div>
    </article>

    <article class="sb-science-panel">
      <div class="sb-science-panel__copy">
        <span class="sb-science-panel__number">03 / Translation network</span>
        <h3>Use NEON as the hyperspectral anchor.</h3>
        <p>Paired synthetic and observed measurements define empirical translations among the three sensor spaces. NEON's dense airborne spectrum supplies the central reference for relating drone-scale measurements to Landsat.</p>
        <a href="vignettes/sensor-harmonization/">Inspect sensor harmonization →</a>
      </div>
      <div class="sb-science-panel__viewport" tabindex="0" aria-label="Scrollable enlarged sensor-translation figure">
        <figure class="sb-science-panel__figure">
          <a href="images/homepage/spectralbridge-technical-overview.png" aria-label="Open the complete technical overview at full resolution">
            <svg viewBox="1010 140 510 760" role="img" aria-labelledby="sb-network-title sb-network-desc" xmlns:xlink="http://www.w3.org/1999/xlink">
              <title id="sb-network-title">Empirical translation network among NEON, MicaSense, and Landsat</title>
              <desc id="sb-network-desc">The supplied technical sensor triangle showing translation relationships among NEON hyperspectral, MicaSense UAS multispectral, and Landsat Collection 2 NBAR observations.</desc>
              <image xlink:href="images/homepage/spectralbridge-technical-overview.png" width="1536" height="1024"></image>
            </svg>
          </a>
          <figcaption>The translation diagram is enlarged without simplifying its pairwise relationships.</figcaption>
        </figure>
      </div>
    </article>

    <ul class="sb-science-principles" aria-label="SpectralBridge workflow principles">
      <li><strong>Deterministic</strong><span>Same input, same output</span></li>
      <li><strong>Restartable</strong><span>Resume from any stage</span></li>
      <li><strong>Versioned</strong><span>Code, parameters, and data tracked</span></li>
      <li><strong>Provenance tracked</strong><span>Inputs, models, and outputs</span></li>
      <li><strong>Open and reproducible</strong><span>Transparent and extensible</span></li>
    </ul>
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
