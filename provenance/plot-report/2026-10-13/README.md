# Plot methods and robustness report

User-directed detailed PDF review of all plant spectral plot families.

- `analyze_report.py`: run from repo root with the repository environment. Reads
  verified compact outputs, writes evidence, inventory and reader-sized figures.
  Does not refit or alter production models. Full checksum review can take time
  on cloud-backed storage because it checks thousands of checkpoint files.
- `build_report.py`: run with ReportLab, Pillow and pypdf (bundled PDF runtime).
  Produces the illustrated report and embeds compact evidence as attachments.
- `verify_report.py`: run with pypdf and pdfplumber. Checks source hashes, numeric
  consistency, Wilson intervals, attachment bytes, page count and text bounds.

Outputs are ignored under `output/pdf/plant_spectral_review/`. Rebuild in this
order, waiting for each step to complete. Do not run analysis and authoring
concurrently: authoring consumes the generated evidence and figures.

The report is descriptive, not independent empirical validation. Recorded
performance and counts belong to this supplied dataset. No source Parquet,
production fit, empirical baseline or year-specific model was changed. The
exact authoring-source and report hashes are saved in `report_validation.json`.
