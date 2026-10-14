# Report validation - 2026-10-13

- Final PDF: 33 pages, approximately 3.8 MiB; all figure families covered.
- Original inventory: 46 PDFs, 421 pages including aliases; original files remain separate.
- PDF SHA-256: `57f741cf1463031d1053009650503326856aa28670208ed35aba6141adfbc11c`.
- Evidence extraction verified 16,455 manifest-covered output entries (including checkpoint pairs and aliases, not independent data).
- Final contracts verified 19 source hashes, 16 Wilson intervals, matching counts/accuracies, exact attachment bytes, page count and text bounds.
- Embedded attachments: report_evidence.json, accuracy_intervals.csv, figure_inventory.json.
- Render review: all page layouts reviewed; coverage, descending-cell excerpts and year/site labels inspected at larger size after repairs. No clipped text, overlapped labels or neighboring-cell crop contamination remained.
- Focused Ruff and documentation-link checks passed.
- No production models, source Parquet or analytical fits changed. New calculations are descriptive correction summaries and fixed-holdout conditional binomial intervals.
- Limitations include shared acquisition dependence, poor tail fitting, weak identification, unverified MicaSense coordinates and nonpaired yearly cohorts. They are explicit throughout the report.

Authoring sources and report integrity receipt are recorded in the ignored output folder. A complete checksum pass can be slow on cloud-backed storage; wait for analyze_report.py before running build_report.py.
