# Validation Metrics

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Reference</p>
    <h1>Validation metrics</h1>
    <p class="sb-doc-lead">SpectralBridge writes QA metrics so reflectance, correction, harmonization, and masking decisions remain reviewable after a run instead of being hidden behind a single success flag.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Visual QA</h3>
        <p>PNG and optional PDF outputs summarize the same behavior in human-readable form.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Machine-readable QA</h3>
        <p>JSON sidecars preserve the numeric summaries for dashboards, regression tests, and automated checks.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Restart-safe review</h3>
        <p>Validation is part of the workflow contract, not just post-hoc reporting.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Reflectance</p>
    <h2>What the core spectral metrics capture</h2>
    <ul class="sb-doc-list">
      <li>bandwise minimum, maximum, and median reflectance</li>
      <li>negative reflectance fractions</li>
      <li>high-reflectance fractions above the QA warning thresholds</li>
      <li>distribution summaries used in the QA PNG and PDF panels</li>
    </ul>
    <p>These metrics help detect correction instability, unexpected scaling, or masking problems before the data moves into downstream ecological analysis.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Masks and coverage</p>
    <h2>How valid-pixel availability is tracked</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Mask coverage</h3>
        <p>Mask and invalid-pixel summaries show how much of a scene remains usable after filtering clouds, shadows, water, snow, or no-data regions.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Sampling support</h3>
        <p>Drone QA also records sampled-support diagnostics so spectral summaries can be interpreted in light of how many valid pixels actually contributed.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Correction metrics</p>
    <h2>How pre and post correction are compared</h2>
    <p>Correction QA focuses on how much the BRDF and topographic stages changed the data and whether those changes look plausible.</p>
    <ul class="sb-doc-list">
      <li>signed reflectance delta summaries</li>
      <li>median absolute change summaries</li>
      <li>distribution spreads by wavelength</li>
      <li>spatial summaries of where corrections were strongest</li>
      <li>flags that distinguish no-op behavior from meaningful change</li>
    </ul>
    <p>Large changes are not automatically wrong, but they should be interpretable in the context of scene geometry, terrain, and QA overlays.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Harmonization metrics</p>
    <h2>How translated sensor products are checked</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Brightness adjustments</h3>
        <p>When brightness normalization is active, the applied coefficients are recorded so downstream users can see that the translated product was not just a raw convolution.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Spectral alignment</h3>
        <p>Convolution and harmonization diagnostics track how corrected reflectance relates to the target sensor bandpass assumptions and whether the resulting products look internally consistent.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Geometry and context</p>
    <h2>What helps explain unusual scenes</h2>
    <p>Geometry and ancillary summaries make the QA outputs interpretable instead of leaving users with unexplained deltas.</p>
    <ul class="sb-doc-list">
      <li>solar zenith and azimuth context</li>
      <li>view geometry summaries</li>
      <li>slope and aspect context where relevant</li>
      <li>drone correction status and overlap diagnostics</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Using the metrics</p>
    <h2>When a flight line deserves closer review</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>Common red flags</h3>
        <p>Large brightness shifts, high invalid fractions, unstable correction summaries, or severe out-of-range reflectance all deserve a second look.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Best follow-up step</h3>
        <p>Open the QA PNG or PDF and compare it with the JSON sidecar rather than changing coefficients or masks blindly.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="../pipeline/qa/">
        <strong>QA panels &amp; metrics</strong>
        <span>See how the visual QA pages present these summaries.</span>
      </a>
      <a class="sb-doc-link-card" href="schemas/">
        <strong>JSON schemas</strong>
        <span>Review the structured files that carry these metrics.</span>
      </a>
      <a class="sb-doc-link-card" href="../troubleshooting/">
        <strong>Troubleshooting</strong>
        <span>Use QA outputs to diagnose failed or questionable runs.</span>
      </a>
    </div>
  </section>
</div>
