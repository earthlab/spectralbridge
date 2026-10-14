# Verification record - 2026-10-14

- Full repository suite: `MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/pytest`: **612 passed, 8 skipped, 29 warnings**, 125.43 seconds. Existing warnings remain visible in checks/full-suite.txt.
- Focused `tests/test_mixtures.py tests/test_mixtures_readiness.py`: **15 passed**, including independent constrained optimization, known/boundary/near-collinear cases, zero-fraction composition handling, EAR/MASA/CoB/IES determinism, missing-class ambiguity, grouped identity purity, actual-flight replacement and nested exposure decoding.
- Focused Ruff over both new package modules, the example, tests and all provenance scripts: **passed**.
- Documentation links: **all valid**. Strict MkDocs build: **passed**, navigation unchanged.
- AI transparency: **six artifacts verified** after the complete verbatim request was logged.
- Whitespace check: **passed**, preserving verbatim pasted prompt whitespace.
- Valid completed-run restart: **3,643 files/cache ledgers retain identical mtimes**, and the manifest returns without rerunning analysis.
- Full executed analysis: **3,642 owned output checksums verified**, 360 supported scheme/fold tests, 369,048 fitted mixture rows and 1,282,485 membership rows. Every simulated parent is in held-out membership and absent from all training acquisitions; all recorded fraction-negative/sum violations are zero.
- Same-source lineage verified against P120's original source SHA256. All **170 P120**, **181 researcher-PFT**, and **53 real-Landsat** owned outputs remain byte-identical. The original 255,546,633-byte source Parquet remains read-only/unchanged.
- Large result tables use compressed Parquet exports; table_exports.json records original CSV hashes, destination hashes and row counts. No file in this provenance package exceeds GitHub's individual-file size limit, and no source pixel table was copied.
- Human report: **22 pages**, all rendered with Poppler and visually reviewed; six primary figure families plus one coverage supplement retain PDF/PNG/SVG formats. Numeric table coordinates and page layout were checked; headings keep their following content, atmospheric gaps remain gaps, and undefined low-residual rates retain n=0 disclosure.

Raw checks are in checks/. Exact source and code identities, executed design and memberships are in manifests/ and tables/. No commit, push, publication, coefficient refit, correction change, operational raster MESMA run or fabricated field reference was performed. Scientific data gates are in VALIDATION.md and are distinct from passing software tests.
