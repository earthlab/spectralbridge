# FAQ

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Help</p>
    <h1>Frequently asked questions</h1>
    <p class="sb-doc-lead">Short answers to the questions that come up most often when running SpectralBridge, reading its outputs, or deciding which products to trust.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Outputs are the API</h3>
        <p>The merged parquet and QA artefacts are the main interface for downstream analysis.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Reruns are expected</h3>
        <p>The NEON pipeline is designed to validate and reuse good outputs instead of recomputing everything.</p>
      </article>
      <article class="sb-doc-card">
        <h3>QA is part of the contract</h3>
        <p>PNG, JSON, and optional PDF summaries exist so reflectance changes remain inspectable after processing.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Concepts</p>
    <h2>What problem is SpectralBridge solving?</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Cross-sensor comparability</h3>
        <p>SpectralBridge helps make reflectance from NEON, drones, and target sensor frames more comparable by correcting geometry-driven artifacts and standardizing downstream outputs.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Analysis-ready structure</h3>
        <p>The workflow is built to produce stable ENVI, parquet, merged parquet, and QA products that can be reused across notebooks, scripts, and batch runs.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Inputs</p>
    <h2>What inputs do I need?</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>NEON pipeline</h3>
        <p>The canonical NEON path starts from NEON <code>.h5</code> directional reflectance files and can download them for you.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Drone pipeline</h3>
        <p>The drone workflow accepts either existing HDF5 inputs or supported TIFF-backed packages that are bridged into the working HDF5 contract before QA and polygon extraction continue.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Common questions</p>
    <h2>Why do some values look surprising?</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Why does NEON use scaled reflectance?</h3>
        <p>NEON HDF5 products store scaled values for compactness. SpectralBridge converts them back to floating-point reflectance during export.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Why do some pixels exceed 1.0 reflectance?</h3>
        <p>Topographic or BRDF correction can amplify noisy regions or difficult geometry. QA outputs flag these conditions so they can be reviewed rather than silently hidden.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Why do some bands look noisy?</h3>
        <p>Low-SNR wavelength regions, edge effects, clouds, shadow, or unstable correction support can all increase visible noise in specific bands.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Do I need both topo and BRDF correction?</h3>
        <p>Usually yes for the NEON workflow. They address different sources of reflectance variability and are treated as a coupled correction stage in the main pipeline.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Performance</p>
    <h2>Why can the pipeline take a long time?</h2>
    <p>NEON and drone products are large, and several stages are intentionally chunked and restart-safe instead of optimized around whole-scene shortcuts.</p>
    <ul class="sb-doc-list">
      <li>ENVI export and correction touch large raster volumes</li>
      <li>sensor translation and parquet extraction are designed to preserve provenance and chunking</li>
      <li>merge and QA stages validate outputs rather than assuming they are always good</li>
    </ul>
    <p class="sb-doc-note">If you need a lighter first run, reduce worker counts and prefer the <code>thread</code> engine while validating a workflow.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Outputs</p>
    <h2>Can I analyze results without reopening ENVI cubes?</h2>
    <p>Yes. In most cases, the merged parquet is the intended downstream analysis surface.</p>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Use merged parquet</h3>
        <p>For NEON runs, start with <code>&lt;flight_id&gt;_merged_pixel_extraction.parquet</code>. It is the authoritative tabular product for analysis.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Use polygon parquet</h3>
        <p>For polygon workflows, use the polygon-specific extracted and merged parquets instead of re-reading the rasters.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Support</p>
    <h2>Where should I look next?</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="troubleshooting/">
        <strong>Troubleshooting</strong>
        <span>Recovery steps for failed or partial runs.</span>
      </a>
      <a class="sb-doc-link-card" href="pipeline/outputs/">
        <strong>Outputs &amp; file structure</strong>
        <span>Understand what each stage writes and reuses.</span>
      </a>
      <a class="sb-doc-link-card" href="pipeline/qa/">
        <strong>QA panels and metrics</strong>
        <span>Interpret the visual and machine-readable audit outputs.</span>
      </a>
    </div>
  </section>
</div>
