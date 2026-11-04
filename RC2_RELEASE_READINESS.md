# SpectralBridge 2.3.0rc2 release readiness

Review date: **2026-11-04**  
Preparation branch: **`codex/prepare-2.3.0rc2`**  
Baseline HEAD: **`bb3da46bea0a4295ca3152a9f607ed17140575f1`**  
Decision: **Engineering preparation complete; publication awaits maintainer decisions and explicit approval.**

No release tag was created or pushed, no merge was performed, and nothing was
published to PyPI or GitHub Releases. RC2 preparation changes remain uncommitted
on the dedicated local branch for review. Existing scientific limitations are
not classified as unfinished drone software work.

## Subsequent P177 integration changes

The three-site integration work adds source-intake, verified-transfer and original
orthomosaic preparation helpers after the exact RC2 artifacts below were frozen.
Those archived artifact hashes and their test results remain valid for those
bytes, but do not certify the new working tree. Rebuild and repeat the exact
artifact gates for a replacement candidate before publication. See
[the three-site integration report](DRONE_THREE_SITE_INTEGRATION_REPORT.md) for
available-stage evidence and deferred inputs. No replacement was published.

## A. Release summary

RC2 stabilizes the completed experimental drone workflow: spatial integrity,
affine radiometric units and offsets, BRDF filtering and shared kernel math,
reconstructed viewing geometry, spatial fitting controls and conditioned SCS+C.
Combined topographic and BRDF processing remains available with explicit
provenance and acceptance status. It also includes post-RC1 spectral-library,
PFT/sensor-transfer and MESMA diagnostics and their supporting documentation.

The RC1 comparison baseline is **`eb202c230478c62de17c111e68bdc73de4bcfcb4`**,
13 October 2026, “Prepare and audit SpectralBridge 2.3.0rc1 release candidate.”
There are **23 subsequent commits** through the initial RC2 baseline. This is a
preparation revision, not a verified RC1 release tag. Local tags are `v1.0.0`
and `0.1`; the connected [GitHub Releases listing](https://github.com/earthlab/spectralbridge/releases)
also returned only those releases on the review date. The old `0.1` is marked
prerelease; no published `2.3.0rc1` was found. The failed sandboxed `git ls-remote`
DNS attempt was not treated as proof of remote state.

The source working tree was initially clean. Only `main` existed locally; cached
remote development branches were inspected and were not silently merged. The
commit inventory and changed-file history are retained in
[release evidence](provenance/release-rc2/2026-11-04/).

## B. Repository integration and stabilization

All November drone work requested for RC2 was already committed in the initial
`bb3da46` baseline. Reports were compared with actual modules and regression
coverage; no missing calibration, true contributors or automatic production
strategy was invented to match a report.

| Capability | Actual implementation / coverage | RC2 status |
| --- | --- | --- |
| TIFF/H5 spatial metadata, orientation, ancillary alignment | `pipelines/drone.py`, `neon_cube.py`, spatial-integrity tests | Committed and retained |
| Scalar/per-band affine scaling, offsets, alpha/NoData, numerical encoding | `radiometry.py`, I/O, radiometric tests | Committed and retained |
| Physical-unit BRDF eligibility, shared kernels and fitting/application guards | `corrections.py`, `brdf_topo.py`, mathematics/reliability tests | Committed and retained |
| Experimental rays, true-north angles, footprint assignment and kernel mixtures | `drone_view_geometry.py`, nine geometry tests | Committed; explicitly inferred |
| Spatial fitting masks, fitting provenance and cluster covariance | `corrections.py`, conditioned-topography tests | Committed; opt-in research capability |
| Conditioned SCS+C and combined application | `topographic.py`, `apply_drone_corrections()` | Committed; unsupported cells explicit |
| ENVI scientific status and approved-library gate | `envi_writer.py`, `radiometry.py`, contract tests | Committed; experimental outputs stay blocked |

The advanced options are available through their documented module APIs. They
are not automatically selected by `run_drone_pipeline`, and no new incompatible
BRDF formulation or broad architectural refactor was introduced.

### Release-preparation fixes

1. **Per-band topographic NoData:** one missing wavelength previously erased valid
   wavelengths at the same ground cell. Application now respects each band's
   quality mask. The real AOP/drone entry-point regression preserves a NoData-only
   band without claiming a fit or discarding the observed band. Both real NEON
   regression modes remain exactly unchanged.
2. **Convolution header contract:** JSON affine calibration was wrapped as an ENVI
   list when its provenance contained whitespace. Its commas were then parsed as
   separate values, blocking downstream Parquet extraction. JSON contracts are
   now serialized as scalars; a dedicated round-trip regression and complete
   normal-pipeline smoke cover the integration.
3. **Canonical polygon imports:** polygon extraction no longer imports its chunk
   helpers through the legacy namespace. This removes import-order-dependent
   binding and keeps the existing extraction API and metadata assertions.
4. **Test isolation and fixtures:** contain a frozen research adapter's generic
   `common` import; avoid installing fake HDF5/plotting modules merely because a
   real dependency has not yet been imported. Synthetic QA, bulk and extraction
   fixtures declare their known units. The validation campaign fits a supported
   isotropic synthetic BRDF rather than injecting unvalidated coefficients.
   Checkpoint assertions reflect algorithm version 4. Notebook status cells were
   appended without deleting existing cells.
5. **Release metadata gate:** preferred-citation and lockfile versions are now
   checked in addition to project, package, citation and changelog versions, with
   regression tests for drift.

No scientific thresholds, kernel equations, reference geometry, radiometric
calibration constants or production defaults were changed to make tests pass.
**3,220 existing tracked research-provenance files match the baseline byte for
byte**; only the authorized prompt/work-queue logs are excepted. Original
experimental rasters, publications and source data were preserved.

## C. Test results

Primary source environment: macOS ARM64, **CPython 3.12.8**, project `.venv`,
`MPLCONFIGDIR=/private/tmp/spectralbridge-mpl`, `OPENBLAS_NUM_THREADS=1`.

| Check | Result |
| --- | --- |
| Full source suite, `CSCAL_TEST_MODE=unit` | **946 passed, 9 skipped, 0 failed**; 955 recorded cases, 144.80 s |
| Additional full-mode polygon module | **4 passed** |
| Website Chromium regression tests | **2 passed** |
| Fresh deterministic offline campaign | **40 passed, 0 failed, 0 skipped** |
| Installed wheel with analytics/quantile extras, copied regression tests outside checkout | **40 passed, 0 skipped** |
| Real NEON BRDF-only control | **3,600,000 values exactly equal**, including NoData placement |
| Real NEON combined control | **3,600,000 values exactly equal**, including NoData placement |
| Ruff source/tests/release scripts | Pass |
| Metadata, API/evidence freshness, AI transparency and docs links | Pass |
| Repository whitespace/diff check | Pass |

The first broad run had 13 failures (929 passed, 9 skipped). They were resolved,
not suppressed. A subsequent run caught an inadvertently modified test pinned by
historical evidence; that test was restored byte-for-byte and the import leak was
fixed at its source. Focused test order exposed the fake-module import bug.
An initial installed-extra run lacked copied fixture/example files; restoring
that layout outside the checkout yielded the passing 40-case result without
weakening assertions. A cold CLI import exceeded an initial 45-second harness
budget; all eleven help commands passed with warm caches and a 120-second budget.

### Exact source and real-data commands

```bash
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 \
  CSCAL_TEST_MODE=unit .venv/bin/python -m pytest \
  --junitxml=/private/tmp/rc2-source-final.xml
CSCAL_TEST_MODE=full .venv/bin/python -m pytest -q tests/test_polygon_extraction.py
SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:8765/ \
  .venv/bin/python -m pytest -q tests/test_docs_playwright.py
.venv/bin/python scripts/run_validation_campaign.py --iterations-per-module 5 \
  --output provenance/release-rc2/2026-11-04/offline-campaign.json
.venv/bin/python provenance/release-rc2/2026-11-04/neon_control.py --phase after
ruff check src tests scripts/check_installed_artifact.py \
  scripts/check_release_metadata.py scripts/generate_ai_transparency.py \
  scripts/generate_api_reference.py scripts/check_api_reference.py \
  scripts/generate_validation_docs.py scripts/run_validation_campaign.py
```

The real NEON control uses the existing D10 R10C 2021-09-15 source, fixed
120-by-3000 window and ten channels. New RC2 evidence/scratch paths preserve the
older P175 record. `neon-regression.json` records zero maximum absolute difference
for each mode. This proves regression preservation, not empirical drone calibration.

### Exceptions and limits

The unit-run skips are explicitly retained in `source-test-summary.json`:

- Two browser cases require a served site; both were subsequently run and passed.
- The polygon extraction module is full-mode-only; its four cases subsequently passed.
- Four legacy HyTools full-mode/preflight cases require the optional pinned legacy
  environment. HyTools is not a required runtime dependency; these were not run.
- One optional real Landsat-window test had no configured cached-window fixture.
- One perceptual-hash test requires the undeclared optional `imagehash` dependency,
  unavailable in the source environment. PNG/JSON and browser checks did run.

No source-suite tests were deselected or assertions weakened to obtain the result.
Deprecation/NoData warnings are preserved in the logs. Full source suites were
not repeated on 3.10/3.11 locally; the exact wheel stage smokes passed on both,
and CI retains the three-version unit matrix.

## D. Documentation and website

Updated README/version guidance, getting-started, drone processing, correction
eligibility, current drone findings, release instructions and RC2 release notes.
Removed outdated claims that `Radiometry` is scalar-only or that all current
Goldhill experiments are rank-one. Practical guides now distinguish the original
zero-view inputs from conditional rank-three reconstructions and supported
SCS+C domains without granting physical approval.

Regenerated the import-free API inventory, including `drone_view_geometry` and
`topographic`, and documented new advanced parameters/returns, units, masks and
status. Existing NEON, bulk, cross-sensor and spectral-library workflows were
reviewed through their source tests and installed stage-complete smoke; no
unnecessary parallel guide or navigation reorganization was introduced.

Fixed 127 out-of-site provenance links plus one test-reference link. Images and
evidence links target immutable baseline `bb3da46`, preserving the underlying
research reports rather than copying or rewriting them.

```bash
python scripts/generate_api_reference.py --check
python scripts/generate_ai_transparency.py --check
python scripts/generate_validation_docs.py --check
python scripts/generate_supplement_docs.py --check
python scripts/check_joss_submission.py
python scripts/check_docs_links.py
mkdocs build --strict
python scripts/check_built_site.py site
python scripts/check_api_reference.py site
```

**Strict build passes; rendered internal links/anchors/assets: 0 errors; rendered
API signatures: 393 checked, 0 errors.** Both browser tests pass. The JOSS checker
passes structural/citation checks while explicitly retaining author declarations
for AI review, funding and conflicts. The dated paper's historical RC1/evidence
statements were not relabeled as newly executed RC2 science.

## E. Packaging validation

Version **2.3.0rc2** is synchronized across project/package, both CFF version
fields, lockfile, first changelog heading, current README and release docs.
`earthlab-spectralbridge` remains the distribution; `spectralbridge` remains the
import; the software/repository names remain SpectralBridge/earthlab/spectralbridge.

The runtime wheel was built once and its exact bytes were reused for all tests.
The final wheel and sdist contain **143 byte-identical runtime files**.
A final version sweep found an RC1 default in the release-smoke example and RC1
commands in the release guide. The first sdist was retired, preserved under
`archive/local/release-rc2/2026-11-04/retired-candidate-1/`, and replaced after
those corrections. The replacement sdist is the final candidate and is installed
and retested independently; the wheel was not rebuilt. No selected artifact is
rebuilt between its final validation and publication. The candidate revision and
both checksum sets are recorded explicitly.

Build commands (initial combined build, then the corrected sdist only):

```bash
SOURCE_DATE_EPOCH=1793823029 .venv/bin/python -m build --no-isolation \
  --outdir archive/local/release-rc2/2026-11-04/dist
SOURCE_DATE_EPOCH=1793823029 .venv/bin/python -m build --sdist --no-isolation \
  --outdir archive/local/release-rc2/2026-11-04/dist
.venv/bin/python -m twine check archive/local/release-rc2/2026-11-04/dist/*
.venv/bin/python provenance/release-rc2/2026-11-04/audit_distributions.py
```

Build tooling: build 1.5.0, setuptools 84.0.0, wheel 0.48.0, twine 7.0.0.
The wheel was built from the initial generated sdist; the final sdist changes
only the helper/version documentation and test coverage, with identical runtime
source. Both final distributions pass Twine and the payload audit.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `earthlab_spectralbridge-2.3.0rc2-py3-none-any.whl` | 748,827 | `9af4c09411a00ee95635ca693cb25c207811fbff3798bb6215060438ba3bfb3c` |
| `earthlab_spectralbridge-2.3.0rc2.tar.gz` | 25,463,752 | `e817dc3839c9b2e278a6694a0668f4eb5f7f739a89f00eeab8fbe1e41dbf7fd9` |

They are retained in `archive/local/release-rc2/2026-11-04/dist/` and are Git-ignored.
`SHA256SUMS`, `distribution-audit.json` and source/environment manifests are in
`provenance/release-rc2/2026-11-04/`.

| Installation | Environment | Offline stage-complete smoke |
| --- | --- | --- |
| Exact wheel | Clean CPython 3.10.16 | Pass |
| Same wheel bytes | Clean CPython 3.11.11 | Pass |
| Same wheel bytes | Clean CPython 3.12.8 | Pass |
| Exact sdist, installed with local build tooling | Separate clean CPython 3.10.16 | Pass |

Runtime dependencies were installed into fresh temporary environments; the
project checkout was not on their import path. Base smokes completed **before**
installing analytics/quantile extras. Dependency checks pass in all four
environments. The later 3.12 extras run verifies scikit-learn 1.9.1 and XGBoost
3.4.1 with 40 existing tests outside the checkout; no production science is claimed.

For each environment, the exact smoke command was:

```bash
cd /private/tmp
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 \
  /private/tmp/rc2-wheel312/bin/python /ABSOLUTE/REPOSITORY/scripts/check_installed_artifact.py \
  --expected-version 2.3.0rc2
```

Substitute `rc2-wheel310`, `rc2-wheel311` or `rc2-sdist310` for the environment.
The runner blocks outbound connections, exercises normal/drone/bulk/compact
results/library stages and restart reuse, and checks API imports, eleven console
scripts and runtime data. Output stays below its 128 MiB limit (about 22-24 MB).
All eleven actual `--help` invocations also pass. The release-smoke helper
extracted from the final sdist also passes with its default version argument. The installed introductory
`examples/first_example.py` reports six valid spectra, two species/two polygons,
one flightline/site and no generated PDFs, as documented.

Research-test provenance is intentionally retained in the checkout rather than
shipped in full; the installed smoke does not claim that every source/research
test can run from the sdist alone.

Payload audit finds **0 issues**: required runtime data and new modules are
included; GPL-3.0-or-later metadata, LICENSE and NOTICE are present; no rasters,
HDF5/Parquet research outputs, notebooks, credential directories, prompt logs,
private archives or accidental machine-specific paths are shipped. The sdist
contains the intended documentation, hence its larger size. Two historical
machine-specific investigation narratives are excluded from installation payloads
while remaining unchanged as scientific records in the repository.

## F. Scientific scope limitations

Goldhill physical DN/32768 calibration, real orthomosaic contributors, vertical
and pose conventions, within-target directional response and independently
improved ecological performance remain unverified. Spatial confounding controls
are adverse evidence, not another invitation to keep altering the RC2 methods.
Experimental products are labeled accordingly and excluded from approved libraries.
These are **documented research limitations, not release-blocking software defects**.

## G. Remaining issues and maintainer decisions

| Class | Issue | Required action |
| --- | --- | --- |
| **BLOCKER for publication** | CFF canonical and preferred authors still use provisional “Earth Lab / SpectralBridge Team” with TODOs | Maintainer must approve the software author list/order, affiliations and any supplied ORCIDs, or explicitly approve the existing organizational form. Paper authorship is not automatically software authorship. No names/IDs were invented. |
| **BLOCKER for publication** | No approval to publish, tag, push a release tag or merge | Review the preparation branch and give explicit authorization for the selected publication steps. |
| **BLOCKER for automated publication until confirmed** | Actual PyPI trusted publisher and protected GitHub `pypi` environment/reviewers were not inspectable from local files | Repository owner confirms `earthlab/spectralbridge`, `release.yml`, environment `pypi`, OIDC and reviewer protections. No credentials/secrets were changed. |
| **IMPORTANT** | Preparation edits are uncommitted; remote CI has not run for the final reviewed commit | Review and commit the intended changes, then run hosted gates before authorizing a tag. Preserve candidate identity and hashes. |
| **IMPORTANT** | Full source suites on 3.10/3.11 and the documented optional skips remain outside local coverage | Require the existing hosted matrix; retain local exact-wheel and sdist results as scoped evidence. |
| **DEFER** | JOSS author declarations for funding/conflicts/AI review | Resolve for paper submission; do not invent declarations or conflate paper approval with software packaging. |
| **DEFER** | Independent drone physical/directional/ecological validation and Gordon/Ruby source extension | Future research scope; current experimental software release is not contingent on another investigation. |

No known failing required local software gate remains.

## H. Final release checklist

- [x] Dedicated preparation branch and reproducible RC1/current integration baseline.
- [x] Completed drone work integrated; focused stabilization fixes and regression tests.
- [x] Full source suite, offline campaign, real NEON parity and additional browser/polygon checks.
- [x] Strict docs, rendered links, API signatures, release notes and synchronized RC2 metadata.
- [x] Wheel/sdist built once; exact bytes audited and installed/tested on the required local matrix.
- [x] CI review: existing three-version matrix retained, metadata path triggers added,
  API freshness/rendered signature gates added, deterministic build timestamp and
  checksum verification before downstream install/release/publication added.
- [ ] Maintainer resolves/approves citation metadata and confirms publication protections.
- [ ] Review and commit RC2 changes; run hosted CI on the final commit.
- [ ] Obtain explicit approval before merge, tag creation/push, release or publication.
- [ ] After approval, use strict PEP 440 `v2.3.0rc2`, never `v2.3.0-rc2`.
- [ ] Run the existing protected release workflow on the approved ref. Its build
  job creates **one authoritative hosted candidate**, validates it, and all wheel
  3.10/3.11/3.12 and sdist 3.10 jobs test those same uploaded bytes. It then creates
  a GitHub **prerelease** and publishes those exact tested artifacts through OIDC.
  Do not dispatch this publishing workflow merely to preview readiness.
- [ ] Keep local and hosted candidate checksums distinct. The local artifacts here
  are tested preparation evidence, not automatically promoted by the hosted
  workflow. A maintainer metadata/source edit requires a fresh candidate and all
  relevant gates; never publish an untested rebuild or rebuild between testing
  and publication of the selected candidate.

The repository is prepared for RC2 review. Publication and citation decisions
remain human-controlled; no new drone investigation is required to finish this
release scope.
