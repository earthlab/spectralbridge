# New endmember collaborator report

Eight-page PDF with seven figures curated from the completed P145 IES comparison.
No new fits, raw-data reads or changes to prior analytical packets. The report
separates selection effects, category effects, synthetic fraction error and field
validation. It explicitly explains RMSE versus classification accuracy.

Output: `output/pdf/ies_endmember_update/SpectralBridge_New_Endmember_Analysis.pdf`

Reproduce from repository root with a Python environment containing ReportLab,
Pillow and pypdf; fonts are read from the existing analysis venv's Matplotlib data:

```sh
python provenance/ies-coworker-report/2026-10-22/v1/build_report.py
python provenance/ies-coworker-report/2026-10-22/v1/validate_report.py
```

`report_manifest.json` fingerprints the exact inputs and PDF and records text
bounds. `validation.json` records completeness and source/figure hash checks.
All eight rendered final pages were individually visually reviewed at 1000-pixel
height, including figure labels and footers. Temporary renders are under
`tmp/pdfs/ies_endmember_update/`. Numerical claims reuse the previously verified
comparison packet; this report does not independently revalidate field accuracy.
