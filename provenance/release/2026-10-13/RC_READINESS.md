# SpectralBridge RC readiness audit

Release candidate: **v2.3.0rc1**. Audit date: 2026-10-13.
Baseline: `d4ebb04ac139840e18ac19a2be17e60807fc51d2` on `main`, initially clean.
This report concerns the final release preparation changes described below.
No tag, remote push, GitHub release, PyPI publication, or deployment was performed.

## Scope and identities

Reviewed packaging metadata, package exports and runtime resources, source/test
contracts for NEON, drone, bulk, correction, conversion, extraction and QA,
README, novice/workflow documentation, notebook/example references, citation,
license/provenance, and all GitHub workflows. The implementation remains frozen
except for the small validator compatibility fix. No algorithm, coefficient,
scientific convention, output filename, table schema or public API was changed.

Identities agree: distribution `earthlab-spectralbridge`, import `spectralbridge`,
software SpectralBridge, repository `earthlab/spectralbridge`, version `2.3.0rc1`.
`pyproject.toml`, `__init__.py`, both citation versions, first changelog heading
and the local package lock entry agree. Python requires >=3.10; the tested matrix
is 3.10–3.12. Required dependencies and optional tests/docs/dev/notebooks/Landsat
extras retain their established scope; no speculative dependency slimming.
README badges and project URLs point to the canonical distribution/repository.
Changelog already summarizes the NEON, drone, bulk, compact results, library,
translation registry and QA functionality represented by RC1.

GPL-3.0-or-later metadata agrees with LICENSE, NOTICE, README and CITATION.
[GPL version 3 is OSI approved](https://opensource.org/license/gpl-3.0).
HyTools-derived implementation attribution remains explicit; removal of a runtime
dependency is not claimed to erase lineage. Both artifacts contain license/notice
bytes; the sdist additionally contains the provenance narrative and manifest.
This audit does not certify rights to every historical research artifact.

## Release gates

All commands below were run locally against the final source/docs or the exact
final artifacts. Python executables are in clean temporary environments; logs
and machine-readable results are retained beside this report.

| Gate | Result | Command / evidence |
| --- | --- | --- |
| Clean source install | PASS | `uv venv --python 3.11 /private/tmp/spectralbridge-rc-source`; `uv pip install --python .../bin/python '.[tests,docs]' ruff build twine`; 144 compatible packages; `source-environment.txt` |
| Full final tests + CI coverage | PASS | `CSCAL_TEST_MODE=unit python -m pytest -q -o addopts= --cov=spectralbridge --cov-branch --cov-report=term --cov-report=json:...`; **502 passed, 7 skipped**, 66.08% against 45%; `tests.log` |
| Ruff supported CI lint | PASS | `ruff check src tests scripts` (broader than release CI slice) |
| Format/type checks | NOT TESTED | No formatter or type checker gate is configured in supported CI |
| Metadata/tag contract | PASS | `python scripts/check_release_metadata.py --tag v2.3.0rc1` |
| Generated AI evidence | PASS | `python scripts/generate_ai_transparency.py --check` |
| Validation documentation | PASS | `python scripts/generate_validation_docs.py --check` |
| Complete supplement | PASS | `python scripts/generate_supplement_docs.py --check` |
| JOSS source format | PASS | `python scripts/check_joss_submission.py`; author declarations remain separate |
| Source docs links | PASS | `python scripts/check_docs_links.py` |
| Strict final docs build | PASS | `mkdocs build --strict --site-dir /private/tmp/spectralbridge-rc-final-site` |
| Rendered links/anchors/assets | PASS | `python scripts/check_built_site.py /private/tmp/spectralbridge-rc-final-site`; zero errors; `site-check.log` |
| Final browser documentation smoke | PASS | local HTTP server + `SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:18766 python -m pytest -q -o addopts= tests/test_docs_playwright.py`; 1 passed; `browser.log` |
| Isolated final wheel + sdist build | PASS | `python -m build --outdir /private/tmp/spectralbridge-rc-final-dist`; `build.log` |
| Distribution metadata/renderability | PASS | `python -m twine check /private/tmp/spectralbridge-rc-final-dist/*` |
| Archive inspection and package data | PASS | ZIP/tar inspection; all 6 JSON/CSV runtime inputs byte-match source; license/notice bytes match; final validator and release docs match source; no prompt log/research archive shipped; `artifacts.json` |
| Clean wheel, Python 3.10.16 | PASS | fresh environment + exact local wheel + `uv pip check` + offline installed smoke outside checkout; `wheel310-*.log` |
| Clean wheel, Python 3.11.11 | PASS | same final wheel; `wheel311-*.log` |
| Clean wheel, Python 3.12.8 | PASS | same final wheel; `wheel312-*.log` |
| Clean sdist, Python 3.10.16 | PASS | exact local sdist built/installed in fresh environment; `sdist310-*.log` |
| Import, expected RC version, resources, APIs, console scripts | PASS | all four `check_installed_artifact.py --expected-version 2.3.0rc1` runs; `installed-artifact-results.json` |
| Installed TIFF/translation/validator regressions | PASS | copied existing test modules into temporary directory, no source conftest; 9 passed / 84 deselected; `installed-regressions.log` |
| Novice example | PASS | `python examples/first_example.py` outside checkout with installed package; six invented observations and no PDFs |
| Workflow consistency | PASS | static review + release-workflow/metadata regression tests in full suite; exact-candidate publication ordering verified |
| GitHub-hosted Linux jobs / PyPI settings / actual publication | NOT TESTED | no remote execution or irreversible release action authorized/performed |
| Live acquisition / new production real-data run | NOT TESTED | synthetic and retained historical evidence only |
| Final whitespace check | PASS | `git diff --check` |

The seven skips are retained conditional environment/browser/external-data tests,
not failures; the dedicated browser gate runs separately. Final artifact smokes
block outbound network and exercise normal/drone/bulk/library production paths.
Diagnostic pre-fix distributions were kept separate from the final candidate and
are not release artifacts. The final candidate was built once; every final matrix
job consumed those exact wheel/sdist bytes. `artifacts.json` records SHA-256.
The report/work queue/logs live under excluded provenance paths and do not change
those tested distribution bytes.

## Findings

### Blockers

None found. All required local source, documentation and installed-artifact
gates pass. External publisher/environment configuration remains an explicit
owner prerequisite before the irreversible tag trigger.

### RC fixes completed

The installed Parquet validator previously rejected established merged aliases
such as `raw_wl500` and `orig_wl0500nm`, because it required a band index and `nm`
suffix. The merge implementation emits these aliases. Validation now accepts
both forms while preserving per-stage monotonic wavelength checks and rejection
of malformed wavelengths. Two regressions cover mixed/interleaved naming,
malformed names and descending order; existing hard/soft and JSON fixture tests
remain intact. `docs/dev/releasing.md` documents the accepted contract.
The fix changes only validation, not stored values, column names or ordering.
Prompt logging and all six generated transparency artifacts were refreshed.

### Post-RC issues

- Installed NEON smoke still emits a merged-Parquet validation warning. Schema
  inspection isolates non-monotonic physical column order and duplicate sensor
  aliases with DuckDB suffixes (for example `olioli_b006_wl1609nm_1`), separate
  from the fixed wavelength-only naming acceptance. Outputs remain readable and
  pipeline/restart/QA tests pass; no value corruption was demonstrated. Review
  merged schema identity/ordering during RC testing. Do not use positional column
  order to infer wavelengths or silently rename existing output contracts.
  `schema-investigation.log` retains the exact column/diagnostic evidence.
- Citation author metadata still contains the existing maintainer-approved-list
  placeholder. Confirm preferred software author identities before final release;
  do not invent author/ORCID metadata during a release freeze.
- JOSS author-only AI review, funding and conflict declarations remain incomplete.
  The submission format gate passes; this is not a JOSS submission-ready claim
  and these declarations are not package-installation blockers.
- Real production validation records predate these exact candidate artifacts.
  External RC testing should record independent data, production memory/disk and
  cross-site transferability evidence separately from synthetic smoke results.
- Established merged-table filtering counts negative non-null reflectance toward
  the >90% invalid-row threshold, while library visualization can retain finite
  negative corrected reflectance. Tests/documentation preserve the distinct
  policies. Domain review of that boundary is deferred rather than changing
  scientific conventions during RC preparation.
- Existing deprecation warnings and small-fixture numerical/plotting warnings
  are retained for review; software gate success is not numerical validation of
  degenerate synthetic fits. Review collection/literature rights independently
  before externalizing the historical publication archive.

### Future improvements

Existing work-queue items for logger ownership, output-discovery consolidation,
naming authority, citation/Zenodo metadata and governance remain deferred.
No refactor, sensor definition change or scientific feature was added.

## Scientific evidence boundaries

**Software correctness:** regression and contract tests exercise storage scaling,
unitless conversion, nodata and masks, HDF5 layout/orientation and ancillary
alignment, geospatial metadata, band/wavelength mapping, correction controls,
convolution connectivity, Parquet/merge/QA, and restart safety. Bulk tests cover
stable merge/subtract moments, weighting families and LOSO, source immutability,
bounded processing and compact summaries without reopening rasters.

**Synthetic validation:** installed smokes use tiny deterministic NEON and drone
HDF5 fixtures, real production correction/convolution/extraction/QA functions,
three completed bulk fixture flightlines, translation/LOSO and compact reports.
Outbound network is blocked and output is bounded. Additional copied regression
modules run against the installed wheel outside the checkout, without repository
conftest path injection, covering TIFF conversion, correction/translation/polygon
QA, wavelength mismatch, exact affine values, nodata and restart reuse.

**Real-data validation:** no new production archive or live acquisition was run.
Retained evidence is described in `docs/dev/production-validation-record.md`:
a historical NEON flightline and operator-reported streaming bulk campaign.
These records do not prove the exact RC bytes ran those archives or establish
universal empirical sensor calibration. Acquisition APIs are covered by fixtures
and existing tests; credentials, external services and live downloads were not
exercised. Notebooks were reviewed as examples, not executed with production data.

**Assumptions intentionally unchanged:** reflectance/wavelength conventions,
BRDF/topographic kernels and fits, interpolation/convolution and brightness,
masking/nodata policies, sensor metadata, affine coefficient provenance and
weighting choices, geospatial alignment, schemas and filenames. High R² and
synthetic shared-reference comparisons do not establish sensor interchangeability.

## Release workflow and irreversible steps

Static workflow review and release contract tests confirm source/docs/metadata
checks precede a single build; wheel installs on Python 3.10/3.11/3.12 and sdist
install on 3.10 precede release creation and publication. Downstream jobs download
the same candidate, GitHub prerelease status derives from PEP 440, and publication
uses OIDC trusted publishing through the `pypi` environment. No stored PyPI token.
Supported CI has Ruff and branch coverage; no formatter/type gate is configured.

GitHub-hosted Linux execution, protected-environment settings and the PyPI trusted
publisher were **NOT TESTED** locally. An owner must verify the existing setup in
`docs/dev/releasing.md`; never dispatch `release.yml` merely to test configuration,
since successful dispatch can publish. Local matrix results are macOS ARM64.

After review of the preparation commit, verify the trusted publisher and `pypi`
environment, then push main and wait for branch CI. Only on that exact successful
commit, execute:

```bash
git status --porcelain  # must be empty
git push origin main
# Wait for branch CI to pass before the following irreversible release trigger.
git tag -a v2.3.0rc1 -m "SpectralBridge 2.3.0rc1"
git push origin v2.3.0rc1
```

Approve the protected `pypi` job after artifact gates pass. The workflow builds
one candidate for that run and publishes those same tested bytes. The locally
retained audit artifacts are identified in `artifacts.json`; do not mix them with
CI-built artifacts or manually publish a rebuild of either. A failed publication
should rerun the failed job against the retained candidate, not rebuild it.

The preparation contains one small validator fix, its regressions/documentation,
and required prompt/transparency/audit evidence. No scientific feature expansion.
Review the preparation commit, confirm external publication setup and await
successful branch CI before triggering the release workflow.

READY TO TAG v2.3.0rc1
