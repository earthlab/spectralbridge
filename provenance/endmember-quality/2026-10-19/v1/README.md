# Selected undarkened OLI endmembers — 19 October 2026

Open **ENDMEMBER_QUALITY_REPORT.html** for the portable, self-contained illustrated
report. Markdown and separate PNG/SVG figures are also supplied.

The user confirmed zero-based spectral indices, class codes 1–5, and selection
from the whole library. The three supplied files are read in place. Numeric class
codes remain separate from spectral column indices; the supplied label array stores
names. The initial input_audit.json predates that clarification. summary.json and
user_confirmation.json describe the confirmed analysis.

The 603 selected spectra originate from 367 polygon IDs. Internal targets exclude
all those IDs, but they are not selection-blind: selection used the whole archive.
Thirty random controls match exact selected counts per polygon; another thirty
also match flightline. Tests cover category coverage/agreement, full-library
cross-category convex-hull certificates, and screened synthetic MESMA with oracle,
random, dense prior and sparsity-matched prior controls. Screening sensitivity is
explicitly exploratory; full 16.9-million-model MESMA was not run.

## Reproduce

From the repository root with its scientific/analytics environment:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python provenance/endmember-quality/2026-10-19/v1/run_analysis.py
    MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python provenance/endmember-quality/2026-10-19/v1/build_report.py
    OPENBLAS_NUM_THREADS=1 .venv/bin/python provenance/endmember-quality/2026-10-19/v1/validate_results.py
    .venv/bin/python -m pytest -ra tests/test_selected_endmember_quality.py tests/test_mixtures.py

Original inputs must remain available at their recorded paths. No original array
or Parquet was copied into this packet. Compact tables retain candidate identity,
model membership, predictions and certificate weights. Selected-reference values
are an intentional traceable selected-library export, not a full input cache.

See VALIDATION.md, numerical_validation.json, figure_manifest.json and
packet_manifest.json. Reproduction after changing code, inputs or protocol should
be versioned separately rather than silently replacing a shared sealed packet.
No earlier scientific result, production implementation, coefficient or formal
proof was modified.
