# A curated visual story for the lab group

The shareable standalone PDF is
`output/pdf/lab_story/SpectralBridge_The_Visual_Scientific_Story.pdf`.
It contains 29 pages and 23 figure-led explanations. Every selected visual is
embedded; recipients do not need repository access. Pages use a landscape
14 × 10.5 inch canvas for readable figures; print using fit-to-page if needed.

## Editorial choices

The narrative follows the scientific questions rather than the order of files:
sampling structure; exploratory traces and processing; quantile signatures and
failure diagnostics; site support; the distinction between inferred woody PFTs
and researcher categories; matched curve tests; synthetic spectral reduction;
one independent real-Landsat pilot; grouped model validation; biological and
spectral resolution; representative libraries; mixture recovery and ambiguity;
unknowns/uncertainty; paired temporal recognition; use-specific readiness and
future observations.

Every figure page explains how to read its marks, the conclusion to draw, and
what the experiment does not establish. Representative failures are retained.
Large exploratory atlases and exhaustive tables are deliberately not reproduced
at unreadable size. Earlier panel letters remain local to their source figure.
Early ordinary matching accuracy, later balanced classification accuracy and
fraction RMSE are explicitly separated; they do not measure one interchangeable
quantity. The final closure interpretation controls historical-label, spatial
support, unit, MicaSense and readiness caveats throughout.

## Reproduce and edit

- `report_source.json`: editable titles, questions, figure choices and captions.
- `report_source.md`: a figure-by-figure Markdown companion.
- `figure_inventory.csv`: report page numbers and exact source paths.
- `evidence_manifest.json`: selected source/output hashes and full inventory.
- `validation.json`: numerical, hash, PDF geometry and rebuild checks.
- `curate.py`: restore the authored default JSON (overwrites manual JSON edits).
- `build_figures.py`: four readable descriptive redraws from compact saved
  products; no model fits or original merged-table copy.
- `build_report.py`: generate the PDF and companion from the current JSON.
- `validate_report.py`: check claims against saved results, selected legacy
  seals, all source hashes, figure/page contracts, text bounds and byte-identical
  reconstruction.

Run from repository root. The analysis environment needs pandas, NumPy,
Matplotlib and the installed source package; the report environment needs
ReportLab, pandas, Pillow, pypdf and pdfplumber. The desktop bundled document
runtime provided the latter here. Arial fonts use macOS system paths.

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl python provenance/lab-story/2026-10-15/build_figures.py
python provenance/lab-story/2026-10-15/curate.py
python provenance/lab-story/2026-10-15/build_report.py
python provenance/lab-story/2026-10-15/validate_report.py
```

Build figures before the report; validate after it finishes. To edit the story,
change JSON and run the report builder directly, without restoring defaults.
This is an editorial synthesis of existing scientific evidence, not a new
statistical experiment or a change to production processing.
