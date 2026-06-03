# Tutorial: Cloud & HPC Workflows

<div class="sb-doc-page" markdown="1">
  <section class="sb-doc-hero" markdown="1">
    <p class="sb-kicker">Tutorial</p>
    <h1>Cloud and HPC workflows</h1>
    <p class="sb-doc-lead">SpectralBridge is designed for large flight lines and restart-safe reruns, which makes it a good fit for scratch-based cloud, JupyterHub, and cluster environments where compute and storage policies matter as much as the code itself.</p>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3>Stage data in</h3>
        <p>Bring only the HDF5 inputs you need into fast local or scratch storage for the current job.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Process locally</h3>
        <p>Write ENVI, parquet, merge, and QA artefacts into the working directory where chunked stages can spill safely.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Archive outputs</h3>
        <p>Move final products back to persistent storage once the restart-safe run is complete.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Storage pattern</p>
    <h2>Recommended working model</h2>
    <ol class="sb-doc-list">
      <li>Stage a small batch of NEON HDF5 inputs into scratch or fast local storage.</li>
      <li>Run the pipeline there so correction, parquet extraction, merge, and QA all share the same fast workspace.</li>
      <li>Copy the completed outputs you care about back to object storage or shared research storage.</li>
      <li>Clean intermediate scratch only after the outputs are validated.</li>
    </ol>
    <p>This pattern keeps failures isolated and works well with the package’s skip-aware rerun behavior.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Engine choice</p>
    <h2>When to use Ray, thread, or process execution</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <article class="sb-doc-card">
        <h3><code>ray</code></h3>
        <p>Best for larger multi-flightline or managed compute environments. This remains the default execution backend for the NEON CLI.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>thread</code></h3>
        <p>Best for first-pass debugging, lightweight runs, or situations where you want to avoid Ray initialization entirely.</p>
      </article>
      <article class="sb-doc-card">
        <h3><code>process</code></h3>
        <p>Useful when you want local multi-process execution without the Ray runtime.</p>
      </article>
    </div>

```bash
spectralbridge-pipeline ... --engine ray --max-workers 8
spectralbridge-pipeline ... --engine thread --max-workers 1
spectralbridge-pipeline ... --engine process --max-workers 2
```
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Memory and temp space</p>
    <h2>How to reduce pressure safely</h2>
    <ul class="sb-doc-list">
      <li>lower <code>--max-workers</code> before changing scientific settings</li>
      <li>lower <code>--parquet-chunk-size</code> when extraction or polygon filtering is memory-bound</li>
      <li>set <code>--merge-temp-directory</code> to local scratch for large parquet merges</li>
      <li>avoid keeping many scenes or notebooks open against the same working directory</li>
      <li>treat reruns as normal; the pipeline is built to skip validated outputs</li>
    </ul>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Batch pattern</p>
    <h2>Recommended scheduler workflow</h2>
    <div class="sb-doc-grid sb-doc-grid--two">
      <article class="sb-doc-card">
        <h3>One job per flight line</h3>
        <p>This is the safest default because failed jobs stay isolated and completed jobs can be rerun without recomputing validated outputs.</p>
      </article>
      <article class="sb-doc-card">
        <h3>Shared post-processing</h3>
        <p>Use downstream DuckDB, pandas, or QA summary tools once the per-flightline artefacts are already on disk.</p>
      </article>
    </div>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Example</p>
    <h2>Minimal SLURM job script</h2>

```bash
#!/bin/bash
#SBATCH --job-name=spectralbridge
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

module load python

BASE=$SCRATCH/spectralbridge_${SLURM_JOB_ID}
mkdir -p "$BASE"

spectralbridge-pipeline \
  --base-folder "$BASE" \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --engine ray \
  --max-workers 8
```

    <p>Adapt the worker count and memory request to the size of the scene and the storage available on the cluster.</p>
  </section>

  <section class="sb-doc-section" markdown="1">
    <p class="sb-kicker">Where to go next</p>
    <h2>Related pages</h2>
    <div class="sb-doc-grid sb-doc-grid--three">
      <a class="sb-doc-link-card" href="../pipeline/stages/">
        <strong>Pipeline stages</strong>
        <span>See which stages dominate runtime and disk usage.</span>
      </a>
      <a class="sb-doc-link-card" href="../usage/parquet/">
        <strong>Working with parquet outputs</strong>
        <span>Use the authoritative tabular products downstream.</span>
      </a>
      <a class="sb-doc-link-card" href="../troubleshooting/">
        <strong>Troubleshooting</strong>
        <span>Recover safely from partial jobs or cluster interruptions.</span>
      </a>
    </div>
  </section>
</div>
