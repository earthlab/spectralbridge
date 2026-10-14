# What do the tests establish?

| Layer | Question | Typical fixtures / checks |
|---|---|---|
| Unit | Does the calculation agree with known mathematics? | Flat/linear spectra, QA bits, exact fractions, known geometry |
| Scientific invariant | Is the required scientific behavior preserved? | Pixel replication, atmospheric gaps, scaling, paired membership, global identity holdouts |
| Regression | Have important audited summaries changed? | Small frozen derived pilot/contrast fixtures with explicit source hashes |
| Integration | Do components work together? | Tiny Parquet/raster pipelines, cached restart and figure composition |
| Network | Do live external services work? | Explicitly requested STAC/CyVerse checks with credentials where needed |
| Scientific validation | Does evidence support the target application? | Large recorded real-data analyses with design/uncertainty/limitations |

Normal tests require **no downloads, credentials or large scientific archive**.
Existing `lite` identifies tiny synthetic smoke checks; `full` retains legacy
external-data opt-in behavior. New `scientific`, `regression`, `integration` and
`network` markers identify purpose without changing old semantics. Browser tests
use `playwright` and an explicitly configured local built site.

## Run the checks

```bash
python -m pip install -e '.[tests,docs]' ruff
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 \
  pytest -m 'not full and not network and not playwright' --cov=spectralbridge \
  --cov-branch --cov-report=term --cov-report=json:coverage.json
pytest -m scientific
python examples/scientific_workflows_offline.py
ruff check src tests
python scripts/generate_scientific_docs.py --check
python scripts/generate_ai_transparency.py --check
python scripts/check_docs_links.py
mkdocs build --strict
python scripts/check_built_site.py site
```

For local browser checks, serve `site/` and set `SPECTRALBRIDGE_DOCS_SITE`:

```bash
python -m http.server 8000 --directory site
# In another terminal after installing Playwright Chromium:
SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:8000 pytest -m playwright
```

Run legacy external-data tests separately using `CSCAL_TEST_MODE=full pytest -m full`
and any test-specific opt-in environment variables. Supply genuine source data;
skips are not validation passes. Live service checks are distinct from offline
mocked transport. The full scientific figure validator needs local original and
compact artifacts; it is not a JOSS installation requirement:

```bash
python -m examples.publication_figures.build_spectral_library_figures
python -m examples.publication_figures.validate_figures
```

## Scientifically important protections

- Native grids and structural NaNs remain distinct. Finite negative values are
  preserved; unsupported gaps are never interpolated across.
- Duplicating a whole within-plant pixel sample preserves the plant median and
  cannot increase biological N. A selectively duplicated subset can change its
  empirical median; this is not extra plant replication.
- Conditional tests retain complete curves/blocks; synchronized NPC calibrates
  its combination. Positive common scaling leaves standardized statistics fixed.
- Sensor pairing, band identity/order, discrete channel weights and whole-ID
  bootstrap coupling are explicit. Gaussian diagnostics do not impersonate real
  Landsat observations.
- Coverage is relative to full actual footprints. QA/scaling and spectral-angle,
  bias/error metrics have independent analytic checks.
- FCLS fractions obey constraints; ambiguous and degenerate systems remain
  ambiguous. Endmember selection stays inside identity-purged folds.
- Residual adequacy is never validated unknown-material membership. Fraction
  detection uses explicit thresholds and reports undefined denominators as NaN.

Frozen derived fixtures record provenance and measured tolerances; they are not
package constants. Changing a canonical result requires scientific review before
updating the fixture. Row/ID renaming invariants apply to deterministic algebra;
seeded stochastic procedures promise repeatability for a fixed ordered input,
not bitwise equality under every reordering. Hypothesis is not currently an
installed dependency; seeded parameterized mathematical checks avoid adding it
solely for these tests.

Coverage measures exercised code, not scientific validity. Use per-module branch
reports to identify missing rejection/edge paths, rather than chasing 100%.
The [integration test matrix](https://github.com/earthlab/spectralbridge/blob/main/provenance/docs-integration/2026-10-14/TEST_MATRIX.md)
and [validation hierarchy](../validation/scientific-validation.md) separate
mathematical confidence from missing empirical evidence.
