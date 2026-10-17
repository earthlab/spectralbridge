# Formal verification explained

Start with SpectralBridge_Formal_Verification_Explained.pdf (28 pages). The Markdown companion contains the same narrative. Fifteen coded illustrations are available independently in figures/ as PDF, SVG and PNG. Compact tables, figure_manifest.json and source_manifest.json connect illustrations and claims to their evidence.

The central result is conditional: fixed transformations can preserve mixture weights while losing the information needed to recover them. Mathematical specifications, implementation checks, observed performance and independent field validity remain distinct.

## Reproduce

Run from repository root. Existing scientific environment (numpy, pandas, matplotlib):

    .venv/bin/python formal/check.py
    .venv/bin/python -m pytest -q formal/tests/test_conformance.py
    MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 .venv/bin/python formal/report/build_figures.py

For document generation use Python with reportlab, pypdf, pdfplumber, numpy, pandas and Pillow:

    python formal/report/build_report.py
    python formal/report/validate_report.py

The local PDF build used the bundled Codex Python runtime. No source spectra are copied, no scientific models refitted and no new theorems introduced. Proof reruns refresh operational logs; audit checksum changes explicitly. See VALIDATION.md and checks/. The report has a separate packet_manifest.json.
