# Why cross-sensor calibration?

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Concepts</p>
    <h1>Why cross-sensor calibration?</h1>
    <p class="sb-doc-lead">SpectralBridge exists because airborne, drone, and satellite sensors do not observe the same landscape in directly comparable ways, even on the same day.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Different spectra</h3>
        <p>Band centers, widths, and response functions vary across sensors.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Different geometry</h3>
        <p>Solar and view angles change the reflectance signal seen by each platform.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Different scale</h3>
        <p>Ground sampling distance and aggregation change what a pixel represents ecologically.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">The problem</p>
    <h2>Why raw reflectance is not enough</h2>
    <p>Integrating information from NEON imaging spectroscopy, drone systems such as MicaSense, and moderate-resolution satellites such as Landsat or Sentinel requires more than putting the files in one folder. Each platform encodes a different mix of spectral response, illumination geometry, viewing geometry, scaling, masking, and spatial support.</p>
    <p>Those differences matter when you want to:</p>
    <ul class="sb-doc-list">
      <li>validate satellite products using airborne data</li>
      <li>relate drone measurements to NEON or Landsat observations</li>
      <li>build cross-scale ecological models</li>
      <li>interpret reflectance change through time or across terrain</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Two operations</p>
    <h2>Correcting and harmonizing are different steps</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Physical corrections</h3>
        <p>SpectralBridge applies topographic and BRDF correction to reduce variation caused by terrain, illumination, and viewing geometry.</p>
        <p>The result is a reflectance product that is more comparable across acquisition conditions.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Sensor harmonization</h3>
        <p>SpectralBridge then integrates corrected hyperspectral spectra against published sensor response functions to translate the data into another sensor's bandspace.</p>
        <p>Optional brightness adjustments are documented in the QA outputs rather than applied opaquely.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Why NEON</p>
    <h2>Why NEON is the core airborne foundation</h2>
    <p>NEON AOP directional reflectance products provide the ingredients the workflow needs to stay explicit and reproducible:</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Rich spectral detail</h3>
        <p>NEON provides dense hyperspectral sampling with wavelength metadata that can be translated into target sensor bandspaces.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Per-pixel ancillary context</h3>
        <p>Solar geometry, sensor geometry, slope, and aspect travel with the reflectance cube, which is essential for correction and QA.</p>
      </article>
      <article class="sb-doc-card">
        <h3>File-based reproducibility</h3>
        <p>The pipeline turns each flight line into restart-safe ENVI, parquet, JSON, and QA outputs that can be audited later.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Cross-scale bridge</h3>
        <p>NEON serves as an intermediary between fine-scale field or drone measurements and coarser satellite observations.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Caveats</p>
    <h2>What still requires scientific judgment</h2>
    <p>SpectralBridge improves comparability, but it does not remove every source of uncertainty. Even after correction and harmonization, you still need to think carefully about:</p>
    <ul class="sb-doc-list">
      <li>residual BRDF effects and unstable coefficients in low-signal regions</li>
      <li>atmospheric differences between sensors and acquisitions</li>
      <li>snow, smoke, water, shadows, and other masking edge cases</li>
      <li>scale mismatch between airborne, drone, and satellite footprints</li>
      <li>the quality flags and masking conventions used downstream</li>
    </ul>
    <p class="sb-doc-note">The package favors transparency over hidden convenience. Major steps write sidecars and QA artifacts so assumptions remain reviewable.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Continue into the workflow</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="../pipeline/stages/">
        <strong>Pipeline stages</strong>
        <span>See what each stage consumes, writes, and validates.</span>
      </a>
      <a class="sb-doc-link-card" href="../tutorials/neon-to-envi/">
        <strong>NEON to corrected ENVI</strong>
        <span>Follow a stepwise workflow from HDF5 to corrected outputs.</span>
      </a>
      <a class="sb-doc-link-card" href="../pipeline/qa/">
        <strong>QA panels and metrics</strong>
        <span>Review the artifacts that document each flight line.</span>
      </a>
    </div>
  </section>
</div>
