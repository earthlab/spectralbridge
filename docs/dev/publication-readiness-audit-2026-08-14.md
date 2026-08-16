# Publication Readiness And Test Coverage Audit

Review date: 2026-08-15
Repository state reviewed: local `main` working tree after report-only footprint and spectral-quality classification

## Decision

SpectralBridge has a credible scientific-software foundation, but it is **not yet ready for a publication-tagged software release**. The restart-safe architecture, public documentation, GPL license, citation file, release workflow, and substantial synthetic test suite are meaningful strengths. Release-blocking work remains in test health, version/citation synchronization, authorship metadata, legal provenance, and DOI ownership.

This is a repository-readiness assessment, not a scientific validation of the correction algorithms or coefficient tables.

## Verification performed

| Check | Result |
| --- | --- |
| Python syntax compilation | Passed: `python3 -m compileall -q src tests scripts` |
| Documentation links | Passed: `python3 scripts/check_docs_links.py` |
| Pytest collection | 225 tests collected in unit mode |
| Unit-mode test run | 218 passed, 7 skipped |
| Coverage | 56.41% statements, 38.55% branches, 52.01% combined |
| Ruff baseline (`E4,E7,E9,F`) | Passed after removing one unused NumPy import from `merge_duckdb.py`; the baseline is now explicit in `pyproject.toml` |
| MkDocs strict build | Passed in a docs-enabled project environment |
| Distribution build | Passed: `uv build` produced the `2.2.0` sdist and wheel |
| Twine metadata check | Passed for both built artifacts |
| Clean wheel install | Passed under Python 3.12.8; package data, version import, and primary CLI help commands were verified |

The current test environment used Python 3.12.8 and pytest 8.4.2. It now
respects the repository's pytest `<9` constraint, but it is not the documented
Python 3.10 baseline. Results must still be confirmed in the declared CI
environment before release.

## Release blockers and material risks

### 1. The suite is green, but scientific validation coverage is incomplete

The two drone-preview fixture failures recorded in the first audit were fixed
and are protected by regression tests. The current unit-mode suite completes
with 218 passing and seven expected skipped tests. The new real-flightline run
also passed every computational stage while honestly returning stage-QA
warnings for known poor-quality bands that remain retained in the products.
Structural bounding-box background and all-band extreme values remain disclosed
but are no longer misclassified as unexpected pipeline failures.

This closes the immediate red test gate, but it does not establish scientific
generality. Multi-site threshold tuning, independent paired-sensor validation,
topographic-only versus BRDF-only attribution, and sensor-network path/cycle
tests still require additional real datasets and persisted artifacts.

### 2. Release metadata is inconsistent

- `pyproject.toml`, `spectralbridge.__version__`, and `CITATION.cff` say `2.2.0`.
- `CHANGELOG.md` begins with `2.3.0`.
- Existing tags documented by the repository do not match the packaged version.

The release workflow builds tags but does not yet enforce synchronization among tag, package version, citation metadata, and changelog.

### 3. Citation authorship is still a placeholder

`CITATION.cff` uses “Earth Lab / SpectralBridge Team” and contains a TODO for the maintainer-approved author list, ORCIDs, and affiliations. A publication release needs an approved author/contributor record and a clear distinction between software authorship, acknowledgements, and associated-paper authorship.

### 4. License and third-party provenance review is incomplete

The repository consistently declares GPL-3.0-or-later, and source comments identify HyTools-derived adaptations. The existing checklist correctly leaves the legal/provenance review open. Maintainers should confirm third-party code and data attribution before publication and should not claim an Apache migration without that review.

### 5. Distribution artifacts work, but packaging metadata needs modernization

The current tree builds an sdist and wheel, both artifacts pass `twine check`, and the wheel installs successfully in a clean Python 3.12 environment. The installed package exposes version `2.2.0`, contains the brightness-coefficient JSON, and its primary pipeline and QA CLI help commands execute. Setuptools nevertheless warns that the TOML-table license field and GPL classifier are deprecated; migrate to an SPDX license expression before the announced February 2027 deadline. Repeat the clean-install smoke on Python 3.10 and the release CI platform before tagging.

### 6. DOI status is explicitly unresolved

The README DOI points to a pre-rename archived record. Repository documentation already warns that it should not be represented as a minted DOI for the current SpectralBridge 2.2.0 metadata. The preferred version DOI/concept DOI strategy must be confirmed before publication.

## Test and coverage audit

### Coverage baseline

Coverage was measured with branch tracking over the installed `spectralbridge` package:

```bash
CSCAL_TEST_MODE=unit pytest --cov=spectralbridge --cov-branch \
  --cov-report=term --cov-report=json
```

| Metric | Covered | Total | Percent |
| --- | ---: | ---: | ---: |
| Statements | 7,127 | 12,634 | 56.41% |
| Branches | 1,592 | 4,130 | 38.55% |
| Combined | — | — | 52.01% |

The new CI command retains JSON and XML coverage artifacts and enforces a conservative 45% combined baseline. That floor prevents immediate regression; it is not a claim of adequate scientific coverage.

### Lowest-covered active modules

| Module | Combined coverage | Assessment |
| --- | ---: | --- |
| `mask_raster.py` | 0% | Untested raster-mask behavior is a publication risk. |
| `standard_resample.py` | 0% | Spectral-resampling coefficient paths need direct contract tests. |
| `brightness.py` | 6% | General percentile/regression correction paths are largely untested. |
| `polygon_extraction.py` | 6% | Full-mode skips leave most extraction behavior uncovered locally. |
| `envi_download.py` | 38% | Authentication/error paths improved, but live network variation still needs campaign evidence. |
| `sensor_panel_plots.py` | 9% | Regression and panel-selection helpers have little direct coverage. |
| `brdf_topo.py` | 12% | Orchestration around scientifically important corrections is thinly covered. |

### Stronger areas

- `qa_metrics.py`, `io/neon_legacy.py`, and several compatibility/protocol modules reached 100%.
- The new stage-QA modules range from 80% to 96%, and `envi_writer.py` now reaches 83% after scale/no-data round-trip regression coverage.
- `sort_core.py` reached 95%.
- `io/neon_schema.py` reached 89%.
- `io/neon.py` reached 78%.
- `pipelines/drone.py` reached 76%.
- `corrections.py` and naming helpers reached about 75%.

The suite has valuable synthetic contracts for HDF5 orientation, ancillary alignment, schema parity, naming, restart behavior, QA metrics, and drone orchestration. Those tests protect scientifically important invariants without requiring the full external dataset.

### Test-system risks

- Six tests were skipped in unit mode, including external/full-mode checks.
- Several test modules install dependency shims or extensive monkeypatches. These are useful for isolation but can diverge from real dependency behavior, as the two current failures demonstrate.
- The audit environment now uses pytest 8.4.2, within the contributor constraint,
  but the suite still needs confirmation in a fresh Python 3.10 environment.
- CI currently uses Python 3.11 even though the README states Python 3.10 is the primary tested baseline.
- There is no maintained coverage trend service or high-value-module threshold. A single global percentage can hide zero-coverage scientific modules.
- The strict documentation build succeeds, but reports 25 Markdown pages outside the configured navigation; maintainers should confirm which are intentionally hidden.
- Ruff's release-blocking baseline now covers import/syntax/undefined-name rules. A broader optional style audit reports substantial legacy cleanup, so expanding the enforced rule set should be incremental and independently reviewed.

## Publication-readiness strengths

- A clear GPL license and package metadata are present.
- `CITATION.cff`, DOI guidance, software-citation policy, changelog, contributing guide, and Code of Conduct exist.
- The pipeline is designed around deterministic files, canonical naming, restart safety, and auditable QA artifacts.
- GitHub Actions cover lint/smoke, unit tests, QA, documentation, and tag-driven release packaging.
- Documentation links and a strict MkDocs build passed locally.
- The repository now publishes a deterministic [AI transparency statement](../ai-transparency.md) generated from its verbatim prompt log.

## Recommended order of work

1. Synchronize version, changelog, citation, and tag metadata; add a release metadata validation gate.
2. Approve the author/ORCID/affiliation list and DOI strategy.
3. Complete the GPL/third-party provenance review.
4. Run a pinned multi-site real-data campaign and scientifically review the provisional QA thresholds.
5. Modernize the PEP 621 license metadata and repeat artifact smoke tests on Python 3.10/Linux.
6. Add direct tests for `standard_resample.py`, `mask_raster.py`, and `brightness.py`.
7. Persist SRF weights and translation-validation artifacts needed for the currently `NOT EVALUATED` checks.
8. Remove or consolidate duplicate documentation deployment workflows and add recurring dependency/security audits.

## AI-transparency audit trail

The generated statement reports aggregate prompt frequency, topics, intents, lengths, AI-system metadata, and model-metadata coverage. It deliberately does not claim line-level AI authorship or reconstruct missing model identities. Reproduce it with:

```bash
python scripts/generate_ai_transparency.py
python scripts/generate_ai_transparency.py --check
```
