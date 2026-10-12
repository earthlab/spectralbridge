---
hide:
  - toc
---

<div class="sb-home">
  <img class="sb-preload-logo" src="asset/img/spectralbridge_logo.png" alt="SpectralBridge logo" loading="eager">

  <section class="sb-hero">
    <div class="sb-hero__copy">
      <p class="sb-eyebrow">NEON flightlines · drone imagery · bulk analysis</p>
      <h1 id="spectralbridge"><span>Same place.</span><span>Many views.</span></h1>
      <p class="sb-hero__lead">Different sensors see the same landscape differently.</p>
      <p class="sb-hero__body">SpectralBridge prepares observations of reflected light for comparison. Reflectance describes how a surface returns incoming light under stated conditions. The software records processing choices and checks so you can inspect what changed and decide what the observations support.</p>
      <div class="sb-button-row">
        <a class="sb-button sb-button--primary" href="concepts/measurements/">Understand the measurements</a>
        <a class="sb-button sb-button--secondary" href="getting-started/">Run the first example</a>
      </div>
    </div>
    <div class="sb-hero__art">
      <img src="asset/img/spectralbridge_logo.png" alt="SpectralBridge logo">
      <p>Common framework. Sensor-specific treatment.</p>
    </div>
  </section>

  <section class="sb-manifesto">
    <p class="sb-kicker">Why it exists</p>
    <h2>One landscape, different measurements.</h2>
    <p>NEON airborne instruments record reflected light across many narrow wavelength ranges. Drones such as those carrying MicaSense cameras provide fine local observations. Landsat satellites observe wider areas with larger ground footprints. SpectralBridge gives these systems a common framework while treating each according to how it was collected. Configured Landsat-like bands do not prove agreement with Landsat observations; aligning or aggregating ground footprints remains a separate scientific decision.</p>
    <p>SpectralBridge applies configured corrections, constructs sensor-like wavelength bands from NEON observations, and compares completed products. Drone observations follow their own preparation path. The software preserves the meaning of each measurement and records the choices needed to review it.</p>
  </section>

  <section class="sb-section sb-section--routes">
    <div class="sb-section__intro">
      <p class="sb-kicker">Choose your way in</p>
      <h2>Choose the pipeline for your inputs.</h2>
    </div>
    <div class="sb-card-grid sb-card-grid--three">
      <a class="sb-route-card sb-route-card--yellow" href="vignettes/full-pipeline/">
        <span class="sb-route-card__number">01</span>
        <h3>NEON flightlines</h3>
        <p>Prepare detailed airborne spectra, apply configured corrections, construct sensor-like bands, and inspect outputs.</p>
        <strong>Run the NEON vignette →</strong>
      </a>
      <a class="sb-route-card sb-route-card--teal" href="vignettes/drone-processing/">
        <span class="sb-route-card__number">02</span>
        <h3>Drone imagery</h3>
        <p>Prepare supported local imagery while retaining the drone observation’s identity and its own correction path.</p>
        <strong>Run the drone vignette →</strong>
      </a>
      <a class="sb-route-card sb-route-card--paper" href="vignettes/bulk-analysis/">
        <span class="sb-route-card__number">03</span>
        <h3>Bulk analysis</h3>
        <p>Compare completed products across flightlines and sites; inspect how relationships and uncertainties vary.</p>
        <strong>Run the bulk vignette →</strong>
      </a>
    </div>
  </section>

  <details class="sb-advanced-views">
    <summary>Explore the technical figures</summary>
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
        <p>The supplied processing diagram is a conceptual view. In the current package, NEON hyperspectral products use spectral convolution, while drone products use optional post-correction affine translation. Bulk analysis estimates and reviews the relationships from completed products.</p>
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
          <figcaption>The source figure is a conceptual research diagram. Its calibration labels do not certify independent sensor agreement; current drone and NEON processing routes differ.</figcaption>
        </figure>
      </div>
    </article>

    <article class="sb-science-panel">
      <div class="sb-science-panel__copy">
        <span class="sb-science-panel__number">03 / Translation network</span>
        <h3>Use NEON as the hyperspectral anchor.</h3>
        <p>Matched MicaSense and Landsat products generated from the same corrected NEON source support diagnostic regressions. Actual Landsat comparison is a separate, optional validation step; a strong synthetic fit alone does not prove sensor interchangeability.</p>
        <a href="vignettes/sensor-harmonization/">Inspect sensor harmonization →</a>
      </div>
      <div class="sb-science-panel__viewport" tabindex="0" aria-label="Scrollable enlarged sensor-translation figure">
        <figure class="sb-science-panel__figure">
          <a href="images/homepage/spectralbridge-technical-overview.png" aria-label="Open the complete technical overview at full resolution">
            <svg viewBox="1010 140 510 760" role="img" aria-labelledby="sb-network-title sb-network-desc" xmlns:xlink="http://www.w3.org/1999/xlink">
              <title id="sb-network-title">Conceptual comparison network among NEON, MicaSense, and Landsat</title>
              <desc id="sb-network-desc">The supplied technical sensor triangle showing translation relationships among NEON hyperspectral, MicaSense UAS multispectral, and Landsat Collection 2 NBAR observations.</desc>
              <image xlink:href="images/homepage/spectralbridge-technical-overview.png" width="1536" height="1024"></image>
            </svg>
          </a>
          <figcaption>The translation diagram is enlarged without simplifying its pairwise relationships.</figcaption>
        </figure>
      </div>
    </article>

    <ul class="sb-science-principles" aria-label="SpectralBridge workflow principles">
      <li><strong>Deterministic</strong><span>Fixed inputs and configuration</span></li>
      <li><strong>Restartable</strong><span>Reuse validated products</span></li>
      <li><strong>Versioned</strong><span>Record software and parameters</span></li>
      <li><strong>Provenance tracked</strong><span>Inputs, models, and outputs</span></li>
      <li><strong>Open evidence</strong><span>Inspect sources and gaps</span></li>
    </ul>
  </section>

  </details>

  <section class="sb-section sb-section--workflow">
    <div class="sb-section__intro">
      <p class="sb-kicker">The NEON processing path</p>
      <h2>Source observations in. Traceable products out.</h2>
      <p class="sb-subtitle">The five steps below describe the individual-flightline NEON workflow. Drone and bulk follow their own linked vignettes above.</p>
    </div>
    <div class="sb-workflow">
      <div class="sb-workflow__step"><span>01</span>Acquire</div>
      <div class="sb-workflow__step"><span>02</span>Correct</div>
      <div class="sb-workflow__step"><span>03</span>Harmonize</div>
      <div class="sb-workflow__step"><span>04</span>Tabulate</div>
      <div class="sb-workflow__step"><span>05</span>Review QA</div>
    </div>
  </section>

  <section class="sb-evidence">
    <div>
      <p class="sb-kicker">Evidence, not mystery</p>
      <h2>Every transformation should leave a trail.</h2>
    </div>
    <div>
      <p>Validation campaigns record input variation, expected behavior, observed diagnostics, runtime, provenance, and failures. QA panels turn those records into something scientists can inspect.</p>
      <a href="validation/evidence-hierarchy/">Distinguish tests, QA and independent validation →</a>
    </div>
  </section>

  <section class="sb-resume-strip">
    <p class="sb-kicker">Already halfway there?</p>
    <h2>Carry on from the files you have.</h2>
    <p>Individual-flightline processing validates existing artifacts and resumes at the first missing or invalid stage.</p>
    <a class="sb-button sb-button--ink" href="vignettes/carry-on-wayward-son/">Carry On My Wayward Son →</a>
  </section>

  <section class="sb-cta">
    <div>
      <p class="sb-kicker">Ready when you are</p>
      <h2>Translate reflectance across sensors and scales.</h2>
    </div>
    <div class="sb-button-row">
        <a class="sb-button sb-button--primary" href="vignettes/">Choose a pipeline</a>
      <a class="sb-button sb-button--secondary" href="reference/">Read the reference</a>
    </div>
  </section>
</div>
