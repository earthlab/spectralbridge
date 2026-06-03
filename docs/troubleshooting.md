# Troubleshooting Guide

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Troubleshooting</p>
    <h1>Troubleshooting guide</h1>
    <p class="sb-doc-lead">SpectralBridge is designed to be restart-safe, so the first recovery step is usually to rerun the same command and let validated stages skip instead of starting over manually.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Preserve artifacts</h3>
        <p>Keep QA outputs, correction JSON, and the exact command so failures stay diagnosable.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Reduce pressure</h3>
        <p>Lower worker counts and chunk sizes before assuming the workflow logic is wrong.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Prefer reruns</h3>
        <p>Completed outputs are validated and reused when they are still good.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">General failures</p>
    <h2>When the pipeline stops mid-run</h2>
    <p>Common causes include out-of-memory conditions, full temporary directories, unexpected NEON file structure, or interrupted network access during download.</p>
    <p>Recommended responses:</p>
    <ul class="sb-doc-list">
      <li>reduce <code>--max-workers</code></li>
      <li>lower <code>--parquet-chunk-size</code></li>
      <li>set <code>CSCAL_TMPDIR</code> to a larger scratch disk</li>
      <li>rerun the same <code>spectralbridge-pipeline</code> command so completed stages can be reused</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Input issues</p>
    <h2>Download and HDF5 access problems</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Missing or corrupted HDF5 files</h3>
        <p>Verify the site, year-month, product code, and flight line identifier. If a prior download was interrupted, rerun the pipeline so the download stage can validate and rebuild the file if needed.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Repeated validation failure</h3>
        <p>If the same partial file keeps failing, move it aside or start from a fresh working directory rather than editing the file in place.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Export stage</p>
    <h2>HDF5 to ENVI export issues</h2>
    <p>ENVI header recognition problems or missing wavelengths usually point to malformed metadata, older NEON metadata layout differences, or interrupted writes.</p>
    <p>Recommended responses:</p>
    <ul class="sb-doc-list">
      <li>confirm the HDF5 product is <code>DP1.30006.001</code></li>
      <li>confirm the filename includes <code>directional_reflectance</code></li>
      <li>remove or archive the invalid output pair, then rerun the same pipeline command</li>
    </ul>
    <p>For single-flightline debugging, keep the execution path simple:</p>

```bash
spectralbridge-pipeline ... --engine thread --max-workers 1
```
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Correction stage</p>
    <h2>Topographic and BRDF correction problems</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Dark or clipped areas after correction</h3>
        <p>Check for deep shadows, DEM mismatch, unstable slope or aspect values, or unusual solar and view geometry. Compare the raw and corrected products in the QA outputs before changing logic.</p>
      </article>
      <article class="sb-doc-card">
        <h3>NaNs or extreme BRDF values</h3>
        <p>Inspect correction JSON and QA JSON diagnostics. Low-SNR bands or unstable geometry can make coefficient fitting noisy. Preserve the failing artifacts for review rather than silently changing coefficients.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Harmonization stage</p>
    <h2>Sensor translation issues</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Landsat-style reflectance looks wrong</h3>
        <p>Check wavelength metadata, FWHM values, and QA diagnostics before assuming the sensor response definitions are wrong. Problems often propagate from earlier correction stages.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Brightness coefficients are unusually large</h3>
        <p>This can indicate poor alignment between corrected spectra and the target sensor response frame. Review reflectance scaling, BRDF stability, and the brightness plots in QA.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Parquet and QA</p>
    <h2>Output and reporting problems</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Memory errors during extraction or merge</h3>
        <p>Reduce <code>--max-workers</code>, lower <code>--parquet-chunk-size</code>, tune <code>--merge-memory-limit</code>, and point <code>--merge-temp-directory</code> at a large local scratch disk.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Corrupted parquet sidecars</h3>
        <p>Rerun the same pipeline command. Export stages validate parquet outputs and rebuild invalid sidecars from ENVI sources when needed.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Missing QA PNG, PDF, or JSON</h3>
        <p>The run may have stopped before QA rendering or before the merged parquet was available. Rerun the pipeline for the same flight line first.</p>
      </article>
      <article class="sb-doc-card" markdown="1">
        <h3>QA-only rerender</h3>
        <p>If the upstream products are already present, rerender QA directly:</p>

```bash
spectralbridge-qa --base-folder output_demo
```
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Escalation</p>
    <h2>What to preserve when asking for help</h2>
    <p>Persistent issues are much easier to diagnose when you keep:</p>
    <ul class="sb-doc-list">
      <li>the exact command and environment details</li>
      <li>the flight line identifier</li>
      <li>the QA PNG, PDF, and JSON artifacts</li>
      <li>the correction JSON</li>
      <li>a small metadata snippet from the relevant ENVI header</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="pipeline/stages/">
        <strong>Pipeline stages</strong>
        <span>Review the ordered workflow and its restart-safe stages.</span>
      </a>
      <a class="sb-doc-link-card" href="pipeline/qa/">
        <strong>QA panels and metrics</strong>
        <span>Use the QA artifacts to interpret unusual outputs.</span>
      </a>
      <a class="sb-doc-link-card" href="usage/parquet/">
        <strong>Working with parquet outputs</strong>
        <span>Inspect tabular outputs without loading full scenes into memory.</span>
      </a>
    </div>
  </section>
</div>
