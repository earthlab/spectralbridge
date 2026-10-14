# Human-readable PFT report

Deliverable: `output/pdf/researcher_pft_distinguishability_report.pdf`.

The report explains the five executed statistics (maximum, integrated,
synchronized max/integrated NPC, energy and FPCA), permutation design,
simultaneous null envelopes and multiplicity. It includes the complete 40
matched numerical results, effects, descriptive spectra/spreads, limitations,
methodological references and the distinction between group differentiation
and unknown-polygon classification. It does not run new scientific tests.

## Reproduce

Use Python with numpy, pandas, pyarrow, matplotlib and reportlab installed:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 \
  python provenance/researcher-pft/2026-10-14/build_report.py
```

Requires the checksum-verified P118 generated analysis and interpretation outputs
in `artifacts/plant_spectral_atlas/researcher_pft_statistics/`. The builder verifies
both manifests and the compact input-table copies before authoring. Scientific
inputs and analysis outputs are read-only. Figures intermediate to the report
are generated in `tmp/pdfs/researcher_pft/`.

The local build used the repository Python environment for scientific packages
and the Codex bundled reportlab package through an appended Python module search
path; no dependencies were installed or changed. Poppler rendered all 15 pages;
contact sheets and detailed pages were visually reviewed. `REPORT_VERIFICATION.json`
records input/source/output hashes and final PDF checks. PDF timestamps can
change on regeneration; input checksums preserve scientific provenance.
