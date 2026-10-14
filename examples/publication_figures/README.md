# Two manuscript figures (local, source-specific example)

From the repository root, with the existing development environment:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m examples.publication_figures.build_spectral_library_figures
```

Required inputs are the original merged polygon library **in place** and the
completed canonical sensor-PFT-transfer, PFT-method-audit and real-Landsat pilot
outputs under `artifacts/`. These are local scientific inputs, not bundled data.
The builder checks upstream owned-file manifests before reading analytical data;
it fails on missing/changed inputs. It never regenerates previous inference or
copies the source library. No external downloads are performed.

`figure_data.py` verifies inputs and calculates only the new descriptive weighted
PCA and median-nearest representative selection. `figure_panels.py` supplies eight
reusable plot functions. The builder composes/exports the two figures, eight
standalone panels (each PDF/PNG/SVG), 400 dpi combined preview, captions, compact
analytical tables, and per-panel file/hash manifest. Running it again overwrites
only these new figure outputs; canonical analytical products are immutable.

Outputs: `output/pdf/publication_figures/`.
Evidence: `provenance/publication-figures/2026-10-14/`.

Read FIGURE_SOURCE_AUDIT.md and FIGURE_VALIDATION.md before interpreting them.
The unresolved physical scale of library values is explicit; a 0–1 reflectance
axis must wait for recovered source-unit provenance. The separate real-Landsat
pilot has verified SR scaling, but is one next-day acquisition pair and does not
validate the exact library polygons. The PFT results are sampled-mixture,
acquisition-conditioned associations, not causal mechanisms or classification
accuracy. The figures deliberately do not imply successful fraction recovery.

Four regression tests cover the only new scientific calculations, gap handling
and upstream checksum rejection. Full-suite results and visual QA are retained
in the evidence directory. No production pipeline or stable package API changes.
