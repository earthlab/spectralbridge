# PyPI Publication-Hardening Audit

Review date: 2026-09-04  
Repository: `earthlab/spectralbridge`  
Reviewed repository state: `main` at `f7e7ddd` plus the recorded audit changes
Distribution version built: `2.2.0`  
Decision: **NOT READY FOR PYPI PUBLICATION**

This document supersedes the 2026-08-14 publication-readiness audit for the
specific question of whether the built package is ready for PyPI. It reports
what was demonstrated from the actual wheel and source distribution, not what
the source tree appears capable of doing.

## Executive verdict

The package builds, passes `twine check`, clean-installs, exposes the three
canonical Python APIs, and ships its required runtime data. The release
criterion is explicitly bounded: a production flightline can require roughly
250 GB of RAM, so GitHub Actions must not attempt to reproduce a production
execution.

The release-blocking artifact contract is instead:

> The exact built wheel must execute every major public stage of the normal
> NEON, drone, and bulk pipelines on deliberately tiny, deterministic fixtures
> outside the repository checkout, with no network or repository-relative
> runtime dependency.

The stage-complete smoke framework and a Python 3.10/3.11/3.12 release matrix
now encode that contract. Scale reduction is acceptable only because the same
production orchestration and scientific algorithms execute; no fake-science
branch replaces them. Separate large-VM evidence remains required for
production scientific and operational validation. Publication is still
blocked by unresolved version history, citation/DOI identity, bundled-data
provenance, and PyPI publishing ownership described below.

## Evidence scope and limits

The audit built the repository with `uv build`, producing:

| Artifact | Size | Members |
| --- | ---: | ---: |
| `spectralbridge-2.2.0-py3-none-any.whl` | about 360 KiB | 99 |
| `spectralbridge-2.2.0.tar.gz` | about 15 MiB | 319 |

Artifact hashes belong in the external release evidence rather than inside this
file: this audit is itself included in the sdist, so editing a hash here changes
the sdist hash. The final audit-build hashes were reported with the completed
work and must be regenerated for the eventual tagged release.

Both passed `twine check`. Clean wheel installs passed dependency checks and
installed-package smoke checks on local macOS using Python 3.10.16, 3.11.11,
3.12.8, and 3.14.3. A Python 3.10.16 installation built from the sdist also
passed. These are local compatibility observations, not a declaration of
support for every version or operating system.

Validation has two non-interchangeable tiers:

- **Tier A — installed-artifact CI smoke:** tiny, deterministic, offline, and
  stage-complete. It proves packaging integrity, resource availability,
  orchestration, stage connectivity, readable outputs, and restart behavior.
- **Tier B — production scientific validation:** selected real flightlines on
  an appropriately sized large-memory machine. It records scientific QA,
  cross-site behavior, empirical calibration evidence, and production
  performance.

Tier A does not validate scientific accuracy on real landscapes, performance
at production scale, stability across sites, or empirical calibration
validity. Tier B does not replace exact-wheel packaging validation. The
maintainer evidence contract and existing R10C record are documented in
`docs/dev/production-validation-record.md`.

## 1. Actual package and public workflows

### Distribution and namespaces

- Distribution name: `spectralbridge`
- `pyproject.toml` version: `2.2.0`
- `spectralbridge.__version__`: `2.2.0`
- Primary package namespace: `spectralbridge`
- Compatibility namespace: `cross_sensor_cal`
- Installed subpackages include `bulk`, `bulk.analyses`, `cli`, `io`,
  `pipelines`, `qa`, and `utils`.
- Canonical top-level workflow exports are `go_forth_and_multiply`,
  `run_drone_pipeline`, and `run_bulk_pipeline`.
- Other intentionally exposed top-level functions include
  `process_one_flightline`, `apply_brightness_correction`, and
  `load_brightness_coefficients`, plus plotting functions when their imports
  are available.

### Invocation inventory

| Workflow | Canonical Python invocation | Canonical CLI | Smallest documented package-first call | Audit result |
| --- | --- | --- | --- | --- |
| Normal NEON | `from spectralbridge import go_forth_and_multiply` | `spectralbridge-pipeline` | `go_forth_and_multiply(base_folder=..., sites=[...], years=[...])` | Stage-complete 8 × 8 × 32 artifact smoke implemented |
| Drone | `from spectralbridge import run_drone_pipeline` | None | `run_drone_pipeline(input_h5_dir=..., output_dir=...)` | Corrections, QA, and full plus polygon 8 × 8 × 10 extraction artifact smoke implemented |
| Bulk | `from spectralbridge import run_bulk_pipeline` | `spectralbridge-bulk` | `run_bulk_pipeline(completed_archive, output_dir)` | Direct normal-output discovery/cache/database/census/translation/LOSO/materialization artifact smoke implemented |
| QA | module-specific Python functions | `spectralbridge-qa`, `spectralbridge-qa-summary`, `spectralbridge-qa-dashboard`, `spectralbridge-stage-qa` | See QA documentation | All installed command help paths passed |

The drone Python API is clear and installable. A drone CLI is not required for
the initial release merely for symmetry; it can remain a post-release usability
feature if maintainers confirm Python is the supported interface.

### Console scripts

All 15 installed commands returned exit code 0 for `--help`:

- Canonical: `spectralbridge-download`, `spectralbridge-pipeline`,
  `spectralbridge-qa`, `spectralbridge-qa-summary`,
  `spectralbridge-recover-raw`, `spectralbridge-qa-dashboard`,
  `spectralbridge-stage-qa`, `spectralbridge-merge-duckdb`, and
  `spectralbridge-bulk`.
- Compatibility aliases: `cscal-download`, `cscal-pipeline`, `cscal-qa`,
  `cscal-recover-raw`, `cscal-qa-dashboard`, and `csc-merge-duckdb`.

The `cscal-*` commands correctly emit deprecation warnings pointing users to
canonical names. The `cross_sensor_cal` compatibility imports also work and
emit a deprecation warning. Keep these paths for the first publication unless a
separate compatibility decision is made.

## 2. Built artifact and clean-install results

| Environment | Artifact | Import outside checkout | Installed smoke | Scope |
| --- | --- | --- | --- | --- |
| Python 3.10.16 | wheel | Passed | Passed | Stage-complete Tier A |
| Python 3.11.11 | wheel | Passed | Passed | Stage-complete Tier A |
| Python 3.12.8 | wheel | Passed | Passed | Stage-complete Tier A |
| Python 3.10.16 | sdist-built install | Passed | Passed | Stage-complete Tier A |
| Python 3.14.3 | wheel | Passed | Passed | Earlier abbreviated compatibility observation; outside the declared release matrix |

The stage-complete wheel runs produced 12,223,911, 12,465,986, and 12,465,763
bytes on Python 3.10, 3.11, and 3.12 and completed in 28.350, 30.329, and
28.228 seconds respectively. The Python 3.10 sdist-built run produced
12,225,300 bytes in 27.694 seconds. These are local macOS observations; the
release workflow is the authority for the Linux matrix.

The reusable `scripts/check_installed_artifact.py` check verifies that the
imported module is outside the checkout, verifies the canonical APIs and
runtime resources, generates bounded inputs, blocks outbound socket access,
and runs all three stage-complete tiny workflows. It must be invoked with the
Python executable belonging to the clean environment where the artifact was
installed.

Pipeline-level results:

- **Normal NEON (8 × 8 × 32):** reads a canonical synthetic HDF5, exports raw
  ENVI, prepares and applies topographic/BRDF correction, convolves all seven
  target products through the production resampler, exports Parquet, merges,
  emits stage and legacy QA, and reruns to assert that valid heavy artifacts
  are reused.
- **Drone (two 8 × 8 × 10 fixtures):** recursively discovers HDF5 input,
  exports ENVI, runs topographic and BRDF correction, deliberately records that
  convolution is not applicable, and separately runs full-pixel and
  intersecting-polygon extraction, merge, and QA.
- **Bulk (three completed flightline folders, twelve rows):** traverses
  arbitrary worker/storage folders, recovers identity from canonical inner
  NEON directories, validates corrected and wavelength-matched target ENVI
  products without scanning pixels during preflight, then performs bounded
  target-product extraction into restartable caches. It builds the catalog and
  DuckDB database, runs census, sensor translation, coefficient export and
  leave-one-site-out analysis, materializes the optional observation
  super-Parquet, and verifies restart reuse. Prebuilt merged Parquet remains a
  compatibility path, not the primary production contract.

No local scientific stage is omitted. Remote NEON acquisition is intentionally
outside this offline artifact check, and upstream drone TIFF-to-HDF5 conversion
is outside the current drone HDF5 input contract. Those external boundaries are
covered by interface/unit checks and production evidence rather than networked
or vendor-specific CI fixtures.

The smoke hard-codes one worker, one merge thread, eight-row Parquet chunks,
small fixture-dimension ceilings, a 2 MiB per-HDF5 fixture ceiling, a 128 MiB
total temporary-tree ceiling, no symlinks, and all discovery/output paths below
one temporary root. It records elapsed time, fixture dimensions, and total
output bytes. These are resource-escalation guardrails, not changes to
production defaults.

No repository path was on `PYTHONPATH`, and the import resolved from each clean
environment's `site-packages` directory.

## 3. Runtime package-data inventory

| Repository path | Installed destination | Consumer | Wheel | Sdist | Locator |
| --- | --- | --- | :---: | :---: | --- |
| `src/spectralbridge/data/hyperspectral_bands.json` | `spectralbridge/data/hyperspectral_bands.json` | spectral/convolution utilities | Yes | Yes | package-relative `get_package_data_path` |
| `src/spectralbridge/data/landsat_band_parameters.json` | `spectralbridge/data/landsat_band_parameters.json` | normal sensor convolution | Yes | Yes | package-relative `get_package_data_path` |
| `src/spectralbridge/data/drone_field_manifest.csv` | `spectralbridge/data/drone_field_manifest.csv` | drone metadata/orchestration | Yes | Yes | package-relative `get_package_data_path` |
| `src/spectralbridge/data/brightness/landsat_to_micasense.json` | same relative package path | OLI/OLI-2 to MicaSense brightness adjustment | Yes | Yes | `importlib.resources` |
| `src/spectralbridge/data/brightness/landsat_tm_etm_to_micasense.json` | same relative package path | TM/ETM+ to MicaSense brightness adjustment | Yes | Yes | `importlib.resources` |

`src/spectralbridge/data/README.md` is in neither artifact. It is not required
at runtime, but its scientific provenance/context should be packaged or moved
to durable public documentation. The Landsat JSON contains centers and FWHM
values, not full spectral-response curves; public wording should not imply more
than the packaged resource provides.

The former repository-relative Parquet validator has been moved to
`spectralbridge.parquet_validation`. Normal orchestration calls the installed
module directly and the installed `spectralbridge-validate-parquets` console
script exposes the same check. `bin/validate_parquets` is now only a compatible
repository wrapper; installed runtime behavior no longer searches for it.

## 4. Dependency audit

The base installation declares `numpy`, `scipy`, `pandas`, `pyarrow`, `pyproj`,
`h5py`, `requests`, `tqdm`, `matplotlib`, `rasterio`, `shapely`, `geopandas`,
`spectral>=0.23`, `ray[default]>=2.2`, and `duckdb>=1.0.0`.

| Category | Dependencies |
| --- | --- |
| Normal NEON runtime | NumPy, SciPy, pandas, PyArrow, pyproj, h5py, requests, tqdm, matplotlib, rasterio, shapely, GeoPandas, Spectral Python, Ray, DuckDB |
| Drone runtime | NumPy, SciPy for correction paths, pandas, PyArrow, pyproj, h5py, tqdm, matplotlib, rasterio, shapely, GeoPandas, DuckDB |
| Bulk runtime | Rasterio and PyProj for bounded target-ENVI extraction; pandas/PyArrow and DuckDB for compact caches, federation, and analysis; standard library for catalog/provenance support |
| Tests only | pytest, pytest-xdist, pytest-cov |
| Docs only | MkDocs and the declared MkDocs/Playwright plugins |
| Notebook/development | JupyterLab; dev aggregates tests/docs/Ruff/build/Twine |

No missing runtime dependency was observed in clean installs. For the stated
contract, keeping all three pipelines' requirements in the base installation
is correct. The `full` extra currently repeats Spectral Python and Ray even
though they are already core dependencies.

Most runtime requirements have no upper bound and several have no lower bound.
The clean environments therefore resolved substantially newer scientific
stacks than the repository's developer lock. `uv.lock` is useful for local
development but does not constrain `pip install spectralbridge`. Before
publication, test a supported dependency matrix and either add evidence-based
bounds or publish a constraints/reproducibility policy. At minimum, outputs
should record dependency versions so an analysis can be reconstructed.

## 5. Python support

- Metadata declares `requires-python = ">=3.10"` with no upper bound.
- Ruff targets Python 3.10 syntax.
- README language claims Python 3.10 and 3.11 CI coverage.
- Actual CI tests only Python 3.11.
- This local clean-artifact audit passed on 3.10, 3.11, 3.12, and 3.14, but did
  not establish full-pipeline or Linux support on all four.

The release artifact gate now defines Python 3.10, 3.11, and 3.12 as its finite
Linux matrix. Python 3.13/3.14 remain compatibility observations only unless
maintainers explicitly add and support them. Metadata and public support
wording still need to be aligned with that decision; an unconstrained
`>=3.10` declaration alone is not evidence of support.

## 6. Version, citation, DOI, and authorship

| Source | Current value/status |
| --- | --- |
| `pyproject.toml` | `2.2.0` |
| `spectralbridge.__version__` | `2.2.0` |
| wheel/sdist metadata | `2.2.0` |
| `CITATION.cff` and preferred citation | `2.2.0` |
| first changelog heading | `2.3.0`; an `Unreleased` section occurs later |
| repository tags | `0.1`, `v1.0.0`; no 2.2.0 or 2.3.0 tag |

The intended first PyPI version cannot be inferred safely from this history.
Maintainers must decide whether 2.2.0 is an unpublished current release or
whether the next version should incorporate the recorded 2.3.0 work. Then make
`pyproject.toml` the authoritative release value, derive runtime version using
installed distribution metadata, and add an automated gate comparing package,
tag, citation, and changelog values.

`CITATION.cff` still contains the placeholder “Earth Lab / SpectralBridge Team”
and TODO comments for the approved author list, ORCIDs, and affiliations. Do not
publish that as final metadata without maintainer input.

The README DOI `10.5281/zenodo.11167877` is documented as a historical
pre-rename `cross-sensor-cal` v1.0.0 record, not evidence of a current
SpectralBridge 2.2.0 release. Maintainers must confirm the Zenodo integration,
the current project identity, author metadata, and whether README/CITATION use a
concept DOI or a release DOI. This audit did not invent or externally verify
those facts.

## 7. Release workflow and CI

The release workflow now resolves and validates the requested tag, runs source
tests plus docs/link/transparency/evidence gates, builds the wheel and sdist
once, runs `twine check`, uploads that exact candidate, and installs the exact
wheel in checkout-free Python 3.10, 3.11, and 3.12 jobs. A Python 3.10 job also
builds/installs the exact sdist. Every clean job runs the offline,
stage-complete three-pipeline smoke, including installed package-data checks,
before the GitHub release job can attach the artifacts.

The workflow still intentionally contains no PyPI or TestPyPI publishing step,
trusted-publishing permission, or protected PyPI environment. Those require a
separate maintainer decision and configuration. The metadata synchronization
gate also correctly prevents the currently inconsistent 2.2.0/2.3.0 history
from being tagged without resolution.

The normal CI workflow installs the checkout editable and tests only Python
3.11. Its path filters can skip CI for changes to `README.md`, `MANIFEST.in`,
`CITATION.cff`, `CHANGELOG.md`, `LICENSE`, most docs, and release-support files.
It does not build distributions or test their installed contents.

Normal branch CI remains a source/editable test system. The tag workflow now
provides the separate exact-artifact gate; release-critical path filters in the
branch workflow include the smoke and metadata gate scripts. A later PyPI
publishing job must consume these tested bytes and must not rebuild them.

## 8. Public API and compatibility

The smallest stable publication surface should be:

- `spectralbridge.go_forth_and_multiply`
- `spectralbridge.process_one_flightline`
- `spectralbridge.run_drone_pipeline`
- `spectralbridge.run_bulk_pipeline`
- documented brightness/config and QA APIs that are already public
- the nine canonical `spectralbridge-*` commands listed above.

Keep `cross_sensor_cal` and `cscal-*` as deprecated compatibility paths for the
initial release. Do not add more top-level names merely because internal
modules are importable. Mark bulk-analysis modules whose schemas are still
evolving as such, and document a compatibility policy before promising semantic
versioning guarantees for every internal function.

## 9. Documentation and PyPI landing page

The README communicates the overall purpose, normal and bulk workflows, QA,
documentation, citation, license, and support links. It is not yet a clean-room
PyPI landing page:

- many links and images are repository-relative and will not resolve on PyPI;
- Mermaid source may render as text rather than a diagram;
- the first Conda option creates an environment but does not install the
  package;
- several instructions assume `pip install .`, a clone, repository scripts,
  notebooks, or execution from the repository root;
- there is no minimal drone Python call in the README;
- the Python support/CI statement is inaccurate;
- `bin/validate_parquets` is documented but absent from installed artifacts;
- stable, experimental, and maintainer-only workflows are not consistently
  distinguished.

`START_HERE.md` is primarily repository-oriented. The normal, drone, and bulk
docs contain useful package APIs, but package-first quickstarts should be the
first path a PyPI reader sees. Convert public asset/doc links to absolute GitHub
or documentation-site URLs, include one minimal invocation for each pipeline,
and move clone/notebook instructions under explicit contributor or advanced
example sections.

## 10. Scientific configuration reproducibility

The release includes band-center/FWHM parameters, two brightness-coefficient
sets, a drone field manifest, correction defaults in Python/config outputs, QA
thresholds in code, bulk schema version 2, and translation-pair definitions.
The installed resources are versioned indirectly by the package release, but
reproducibility metadata is uneven:

- coefficient and band files do not consistently state source dataset,
  derivation method, license, resource schema version, and immutable checksum;
- QA provenance records the installed package version and input hashes, but a
  Git commit is normally unavailable from a wheel;
- the bulk manifest records run/schema/config/source catalog information but
  not the installed package and dependency versions or resource checksums;
- unbounded dependencies allow numerical environments to drift under the same
  SpectralBridge version.

Add a shared provenance record containing distribution version, Python and key
dependency versions, pipeline/config schema versions, and SHA-256 values for
scientific resources. Version coefficient schemas explicitly; never alter a
released coefficient file in place.

## 11. License, provenance, and repository hygiene

The repository contains the GPLv3 license text and the classifier says GPLv3,
while `CITATION.cff` says `GPL-3.0-or-later`. Those are not precise substitutes:
maintainers must confirm whether the intended grant is GPL-3.0-only or
GPL-3.0-or-later and align notices and metadata. Adapted HyTools-related modules
retain author/GPL notices, which is compatible at a high level, but this is not
a legal determination. The build emits deprecation warnings for the table-form
`project.license` field and the license classifier; migrate to an approved SPDX
license expression and `license-files` before the packaging-tool deadline.

Maintainer/legal review is required for:

- provenance and redistribution terms of the band-parameter JSON files;
- source data/method/license of both brightness-coefficient JSON files;
- consent, privacy, and redistribution of collaborator names and operational
  notes in `drone_field_manifest.csv`;
- the exact GPL-3.0-only versus GPL-3.0-or-later grant;
- logos and validation images included in the 15 MiB sdist, including the NSF,
  CU/CIRES, ESIIL, and project assets.

The wheel is compact, but the sdist includes documentation images up to several
megabytes and validation JSON containing absolute `/Users/...` source paths.
Reduce the sdist to source, tests needed for verification, essential docs, and
cleared assets; sanitize local paths in published validation evidence.

Large tracked deprecated rasters, a large executable, root outputs, notebooks,
and site-specific scripts make the repository heavy, but `MANIFEST.in` excludes
most of them from the distribution. They are repository-hygiene work rather
than wheel blockers. No obvious credential or token was found by the audit's
text search. Hard-coded `/home/jovyan` paths remain in repository-only helper
scripts and should stay clearly outside the installed interface.

## 12. Prioritized findings

### BLOCKER — must be resolved before PyPI

#### RESOLVED B1. Bounded three-pipeline installed-wheel contract

- **Resolution:** the exact-artifact runner now executes every major normal,
  drone, and bulk stage using the bounded fixtures described in section 2.
- **Boundary:** this is packaging and stage-connectivity evidence, not a claim
  that a tiny fixture is scientifically representative.
- **Production follow-up:** maintainers retain selected large-VM records under
  the separate Tier B contract.

#### B2. No guarded PyPI publication path exists

- **Problem:** release automation creates a GitHub release only and does not
  require source tests or clean artifact tests.
- **Evidence:** `.github/workflows/release.yml` has no PyPI step and tests the
  wheel in an environment already containing an editable checkout.
- **Affected:** all pipelines and every release.
- **Impact:** a tag can distribute an artifact that never passed the release
  contract, while no reproducible trusted-publishing path exists.
- **Fix:** add a protected release-candidate workflow, clean artifact matrix,
  required checks, PyPI trusted publishing, and an optional explicit TestPyPI
  rehearsal. Publish only the already-tested artifacts.
- **Owner:** Codex can implement workflow code; a maintainer must configure
  GitHub environments and PyPI trusted-publisher ownership.

#### B3. Publication version and history are unresolved

- **Problem:** code/artifacts/citation say 2.2.0, the changelog leads with 2.3.0,
  and tags end at v1.0.0.
- **Evidence:** version table in section 6.
- **Affected:** package identity, citation, release workflow.
- **Impact:** users cannot unambiguously map an artifact to release notes and a
  source tag.
- **Fix:** maintainer chooses the publication version and history treatment;
  then add and enforce a version/tag/changelog/CFF synchronization check.
- **Owner:** maintainer decision first; Codex can implement synchronization.

#### B4. Citation identity and DOI are not publication-ready

- **Problem:** authors are placeholders and the linked DOI describes a historic
  pre-rename release.
- **Evidence:** TODOs in `CITATION.cff` and the DOI note identifying the existing
  record as `cross-sensor-cal` v1.0.0.
- **Affected:** all published software and scientific citations.
- **Impact:** PyPI/Zenodo metadata could misattribute authors or point to the
  wrong software identity/version.
- **Fix:** approve author order, names, ORCIDs, affiliations, preferred
  citation, Zenodo project/linkage, and concept-versus-version DOI policy.
- **Owner:** maintainer input required; Codex can apply approved metadata.

#### B5. Redistribution/provenance approval is incomplete for bundled data

- **Problem:** scientific lookup/coefficient files and the drone manifest lack
  complete source/license/privacy records; sdist logos/assets lack an explicit
  distribution inventory.
- **Evidence:** section 11 and package-data files themselves.
- **Affected:** normal and drone; source distribution.
- **Impact:** scientific provenance is insufficient and publication could
  redistribute data, names, or marks without documented approval.
- **Fix:** establish a data/asset manifest with source, author, method, version,
  license/permission, and privacy approval; remove or replace anything not
  approved.
- **Owner:** maintainer/legal/data-owner input required; Codex can encode the
  resulting manifest and packaging exclusions.

#### B6. PyPI instructions do not yet support all three clean-room workflows

- **Problem:** README links/assets are not PyPI-safe and the package-first drone
  path is missing, while some steps require repository files.
- **Evidence:** section 9.
- **Affected:** all workflows, especially drone.
- **Impact:** even functional APIs are not discoverable/runnable by a user who
  only installed from PyPI.
- **Fix:** add concise package-first quickstarts for all three pipelines, repair
  URLs and installation wording, and separate installed, notebook, and
  maintainer workflows.
- **Owner:** Codex can implement; maintainers should approve stability labels.

### HIGH PRIORITY — resolve before publication unless explicitly accepted

#### RESOLVED H1. Release CI exact-artifact matrix

- The tag workflow builds once and gates the exact wheel on Linux Python 3.10,
  3.11, and 3.12, plus the sdist on Python 3.10. Branch CI remains Python 3.11
  source validation.

#### RESOLVED H2. Parquet validation is package-local

- `spectralbridge.parquet_validation` is installed, normal orchestration calls
  it directly, and the public console entry point is
  `spectralbridge-validate-parquets`.

#### H3. Dependency reproducibility is weak

- **Evidence:** mostly unbounded requirements; developer lock does not constrain
  PyPI installs; output provenance omits dependency versions.
- **Affected:** all scientific results.
- **Impact:** the same package release may resolve materially different stacks.
- **Fix:** test supported ranges, add evidence-based constraints, and record
  resolved versions in outputs.
- **Owner:** Codex can implement tests/provenance; maintainers approve bounds.

#### H4. Supported-Python statements are inconsistent

- **Evidence:** metadata says all Python >=3.10, README claims 3.10/3.11 CI,
  CI runs only 3.11.
- **Affected:** installation and support.
- **Impact:** users cannot tell which environments maintainers will support.
- **Fix:** decide and enforce a finite CI matrix, then align metadata,
  classifiers, docs, and release checks.
- **Owner:** maintainer decision plus Codex implementation.

#### H5. Scientific provenance records are incomplete

- **Evidence:** coefficient/resource checksums, schemas, dependency versions,
  and package version are not uniformly stored, especially by bulk outputs.
- **Affected:** all pipelines and bulk-derived coefficients.
- **Impact:** outputs cannot always be reconstructed from release identity.
- **Fix:** add a common immutable provenance block and version resource schemas.
- **Owner:** Codex; scientific metadata requires maintainer confirmation.

#### H6. Sdist is unnecessarily large and leaks local validation paths

- **Evidence:** about 15 MiB versus a 360 KiB wheel; multi-megabyte docs images
  and `/Users/...` paths are included.
- **Affected:** sdist consumers and public source metadata.
- **Impact:** larger downloads, irrelevant assets, and local-path disclosure.
- **Fix:** narrow `MANIFEST.in`, sanitize generated validation records, rebuild,
  and compare inventories in CI.
- **Owner:** Codex; asset removals require provenance decision from B5.

### MEDIUM — reasonable immediately after the initial release

- Add a drone CLI only if user research shows it improves real workflows;
  Python API availability is already sufficient.
- Remove or redefine the redundant `full` extra.
- Package or prominently publish `src/spectralbridge/data/README.md` so runtime
  resources retain nearby context.
- Add explicit Python-version classifiers after the support matrix is settled.
- Formalize which internal bulk analysis functions are stable public API.
- Reduce repository-only large/deprecated files in a separate, non-destructive
  history/hygiene project.

### NON-BLOCKING — cleanup and future improvements

- First-import Matplotlib/fontconfig cache warnings in restricted home
  directories are environmental; the release smoke now redirects its caches.
- Legacy `cross_sensor_cal` and `cscal-*` paths work and can remain deprecated.
- Large tracked files excluded from both artifacts do not prevent PyPI
  installation, though they still affect repository clones.
- Migrate deprecated packaging license syntax before the February 2027 tooling
  deadline even if current builders still accept it.

## 13. Ordered PyPI release checklist

1. Maintainers choose the intended publication version and reconcile changelog,
   tags/history, `pyproject.toml`, runtime version, and `CITATION.cff`.
2. Maintainers approve the final author/ORCID/affiliation list and Zenodo
   concept/release DOI policy.
3. Complete the scientific data and asset provenance/license/privacy inventory;
   remove unapproved files and sanitize local paths.
4. Keep Python 3.10, 3.11, and 3.12 as the finite release-gate matrix; decide
   the dependency-bounds policy and align all public support wording.
5. Maintain the bounded stage-complete fixtures without replacing production
   algorithms with test-only numerical shortcuts.
6. **Mandatory artifact gate:** build the wheel once, install it with
   dependencies into clean environments with no repository checkout on import
   paths, and successfully run the normal NEON, drone, and bulk pipelines. Fail
   the release if any package data or code is obtained from the checkout.
7. Build and install the sdist in at least the lowest supported Python version;
   run metadata, import, resource, and smoke checks.
8. Keep the release workflow's Ruff, unit/integration, docs/link, AI
   transparency, validation-evidence, version synchronization, package-data,
   `twine check`, and exact-artifact gates required before GitHub release.
9. Keep Parquet validation package-local; do not reintroduce repository path
   discovery into installed runtime behavior.
10. Rewrite the README/PyPI landing page with absolute links, accurate Python
    support, and minimal package-first normal, drone, bulk, and QA examples.
11. Rebuild wheel/sdist from a clean tagged commit; record artifact checksums,
    inspect contents, run `twine check`, and rerun the exact artifact gate on
    those final bytes.
12. Configure protected GitHub release environments and PyPI trusted publishing;
    optionally rehearse with TestPyPI without treating it as production.
13. Create the signed/approved `vX.Y.Z` tag only after all required checks pass;
    publish the already-tested artifacts, verify the PyPI page and clean
    installation, create the Zenodo record, and update the release DOI.
14. Archive the release evidence: workflow URLs, hashes, environment versions,
    smoke output, citation metadata, and maintainer approvals.

## 14. Commands and checks actually run

The following checks were run during this audit. Temporary directory names are
shown to distinguish artifact testing from source-tree testing.

```text
uv build --out-dir /tmp/spectralbridge-pypi-final-audit-20260904/dist
uvx twine check /tmp/spectralbridge-pypi-final-audit-20260904/dist/*
unzip -Z1 /tmp/spectralbridge-pypi-final-audit-20260904/dist/*.whl
tar -tzf /tmp/spectralbridge-pypi-final-audit-20260904/dist/*.tar.gz

# Clean environments created with uv, then the wheel was installed in each.
/tmp/spectralbridge-pypi-audit.kPz2oj/venv310/bin/python /Users/tuff/Library/CloudStorage/OneDrive-UCB-O365/Documents/github/spectralbridge/scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-pypi-audit.kPz2oj/venv311/bin/python /Users/tuff/Library/CloudStorage/OneDrive-UCB-O365/Documents/github/spectralbridge/scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-pypi-audit.kPz2oj/venv312/bin/python /Users/tuff/Library/CloudStorage/OneDrive-UCB-O365/Documents/github/spectralbridge/scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-pypi-audit.kPz2oj/venv314/bin/python /Users/tuff/Library/CloudStorage/OneDrive-UCB-O365/Documents/github/spectralbridge/scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-pypi-final-audit-20260904/venv310-sdist/bin/python /Users/tuff/Library/CloudStorage/OneDrive-UCB-O365/Documents/github/spectralbridge/scripts/check_installed_artifact.py --expected-version 2.2.0

uv pip check --python /tmp/spectralbridge-pypi-audit.kPz2oj/venv310/bin/python
uv pip check --python /tmp/spectralbridge-pypi-audit.kPz2oj/venv311/bin/python
uv pip check --python /tmp/spectralbridge-pypi-audit.kPz2oj/venv312/bin/python
uv pip check --python /tmp/spectralbridge-pypi-audit.kPz2oj/venv314/bin/python
uv pip check --python /tmp/spectralbridge-pypi-audit.kPz2oj/venv310-sdist/bin/python

# Every installed console script listed in section 1 was run with --help.

uvx ruff check src tests scripts/generate_ai_transparency.py \
  scripts/generate_validation_docs.py scripts/run_validation_campaign.py \
  scripts/check_installed_artifact.py scripts/check_release_metadata.py

.venv/bin/python -m compileall -q src/spectralbridge scripts/check_installed_artifact.py
.venv/bin/pytest -q tests/test_drone_pipeline.py
.venv/bin/pytest -q tests/test_bulk_pipeline.py
.venv/bin/pytest -q tests/test_qa
.venv/bin/pytest -q
.venv/bin/python scripts/check_docs_links.py
.venv/bin/mkdocs build --strict --site-dir /tmp/spectralbridge-pypi-audit-site
.venv/bin/python scripts/generate_ai_transparency.py --check
git diff --check

# Stage-complete follow-up: exact wheel installed into each clean environment.
/tmp/spectralbridge-stage-complete-20260904/venv310/bin/python scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-stage-complete-20260904/venv311/bin/python scripts/check_installed_artifact.py --expected-version 2.2.0
/tmp/spectralbridge-stage-complete-20260904/venv312/bin/python scripts/check_installed_artifact.py --expected-version 2.2.0

# Exact sdist-built Python 3.10 environment.
/tmp/spectralbridge-stage-complete-20260904/venv310-sdist/bin/python scripts/check_installed_artifact.py --expected-version 2.2.0
```

The stage-complete artifact runs and focused tests passed. The final full-suite,
generated-document, link, and strict-site checks are recorded in
`FEATURE_REQUESTS.md`. Existing deprecation/all-NaN warnings remain, and the
normal pipeline's warning-only Parquet validation reported its existing
spectral-column ordering warning for the synthetic merged output. This
follow-up closes artifact-contract blocker B1 locally; Linux confirmation is
pending the release workflow.

The later direct-flightline-archive bulk contract was verified by focused and
full source-tree tests, including the installed-smoke fixture's bulk path. A
fresh wheel rebuild for repeating the exact-artifact run was attempted but was
blocked when the execution approval service reached its usage limit. Therefore
the historical exact-wheel results above apply to the prior merged-Parquet
bulk fixture; exact-wheel confirmation of the newer direct target-ENVI fixture
remains pending and is not claimed here.
