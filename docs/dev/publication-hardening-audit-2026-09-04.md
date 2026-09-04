# PyPI Publication-Hardening Audit

Review date: 2026-09-04  
Repository: `earthlab/spectralbridge`  
Reviewed commit: `d98b2f5` on `main`  
Distribution version built: `2.2.0`  
Decision: **NOT READY FOR PYPI PUBLICATION**

This document supersedes the 2026-08-14 publication-readiness audit for the
specific question of whether the built package is ready for PyPI. It reports
what was demonstrated from the actual wheel and source distribution, not what
the source tree appears capable of doing.

## Executive verdict

The package builds, passes `twine check`, clean-installs, exposes the three
canonical Python APIs, ships the five runtime data files currently located by
the code, and passes a meaningful installed-package smoke test outside the
repository. The bulk pipeline was exercised through its complete small-data
analysis path. The drone pipeline was exercised through HDF5 discovery,
conversion, orchestration, output creation, and QA with corrections disabled.
The normal pipeline was exercised only through HDF5-to-ENVI conversion.

That evidence is encouraging but does **not** satisfy the release-blocking
contract:

> A wheel installed into a clean environment must run the normal NEON, drone,
> and bulk pipelines without access to a repository checkout.

The complete normal workflow and the drone correction plus full/polygon
extraction variants have not yet been demonstrated from an installed artifact.
The tag workflow also neither runs such a gate nor publishes to PyPI, version
history is inconsistent, and maintainer/legal review is still needed for
citation and bundled-data provenance. Publication should wait until every
BLOCKER below is closed or explicitly resolved by maintainers.

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

The smoke fixtures are synthetic and offline. They do not validate scientific
agreement with full production flightlines, remote NEON download, distributed
Ray execution, or every combination of corrections and polygon inputs. Those
limits must remain explicit.

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
| Normal NEON | `from spectralbridge import go_forth_and_multiply` | `spectralbridge-pipeline` | `go_forth_and_multiply(base_folder=..., sites=[...], years=[...])` | API/import/help passed; only offline H5-to-ENVI was run from the artifact |
| Drone | `from spectralbridge import run_drone_pipeline` | None | `run_drone_pipeline(input_h5_dir=..., output_dir=...)` | API and abbreviated orchestration passed; corrections and extraction were not exercised |
| Bulk | `from spectralbridge import run_bulk_pipeline` | `spectralbridge-bulk` | `run_bulk_pipeline(input_path, output_dir)` | Full tiny catalog/database/census/translation/LOSO smoke passed |
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

| Environment | Artifact | Import outside checkout | `pip check` | Installed smoke |
| --- | --- | --- | --- | --- |
| Python 3.10.16 | wheel | Passed | Passed | Passed |
| Python 3.11.11 | wheel | Passed | Passed | Passed |
| Python 3.12.8 | wheel | Passed | Passed | Passed |
| Python 3.14.3 | wheel | Passed | Passed | Passed |
| Python 3.10.16 | sdist-built install | Passed | Passed | Passed |

The reusable `scripts/check_installed_artifact.py` check verifies that the
imported module is outside the checkout, verifies the canonical APIs and
runtime resources, generates tiny inputs, and runs the three abbreviated paths.
It must be invoked with the Python executable belonging to the clean environment
where the artifact was installed.

Pipeline-level results:

- **Normal NEON:** import, configuration/resource lookup, public API, CLI help,
  and real synthetic NEON HDF5-to-ENVI conversion passed. The complete
  correction, convolution, extraction, merge, and QA orchestration did not run.
- **Drone:** real `run_drone_pipeline` orchestration discovered one HDF5,
  converted it, produced raw/corrected reuse outputs and QA, and reported
  `success_qa_only_no_polygons`. Topographic/BRDF corrections were disabled;
  full and polygon extraction were not run.
- **Bulk:** real `run_bulk_pipeline` discovered three synthetic flightlines and
  twelve rows, built its catalog and DuckDB database, and ran census, sensor
  translation, coefficient export, and leave-one-site-out analysis.

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

One repository-relative behavior remains: normal pipeline validation looks for
`bin/validate_parquets` above the source module and silently skips it when the
script is absent. The script is not installed. This does not currently crash
the pipeline, but a documented package feature cannot depend on that path.
Move the implementation into the package or explicitly label it as a
repository-only maintainer check.

## 4. Dependency audit

The base installation declares `numpy`, `scipy`, `pandas`, `pyarrow`, `pyproj`,
`h5py`, `requests`, `tqdm`, `matplotlib`, `rasterio`, `shapely`, `geopandas`,
`spectral>=0.23`, `ray[default]>=2.2`, and `duckdb>=1.0.0`.

| Category | Dependencies |
| --- | --- |
| Normal NEON runtime | NumPy, SciPy, pandas, PyArrow, pyproj, h5py, requests, tqdm, matplotlib, rasterio, shapely, GeoPandas, Spectral Python, Ray, DuckDB |
| Drone runtime | NumPy, SciPy for correction paths, pandas, PyArrow, pyproj, h5py, tqdm, matplotlib, rasterio, shapely, GeoPandas, DuckDB |
| Bulk runtime | pandas/PyArrow and DuckDB; standard library for catalog/provenance support |
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

The release must define a finite tested matrix. A reasonable minimum is 3.10,
3.11, and 3.12 in Linux CI, followed by an explicit maintainer choice about
3.13/3.14. Update classifiers, README, and `requires-python` consistently. Do
not describe untested future Python versions as supported merely because the
metadata permits installation.

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

The release workflow correctly checks out the requested tag, builds both
artifacts, and runs `twine check`. It does not provide a safe PyPI release path:

- it installs the project editable before building;
- it force-reinstalls the wheel into that same checkout-backed environment,
  which is not a clean artifact test;
- it does not run lint, tests, docs, transparency, version sync, package-data
  validation, or the three-pipeline smoke;
- tag pushes do not trigger the main CI workflow;
- it creates a GitHub release but contains no PyPI or TestPyPI publication step;
- it has no PyPI trusted-publishing/OIDC permission or environment protection;
- manual tag input is not format/version validated.

The normal CI workflow installs the checkout editable and tests only Python
3.11. Its path filters can skip CI for changes to `README.md`, `MANIFEST.in`,
`CITATION.cff`, `CHANGELOG.md`, `LICENSE`, most docs, and release-support files.
It does not build distributions or test their installed contents.

Before publishing, CI should have separate source/unit and artifact jobs. The
artifact job must build once, inspect/package-check once, then install that
exact wheel into clean supported-version environments and run
`check_installed_artifact.py` after it has been expanded to meet the complete
pipeline contract. The release workflow should consume artifacts from a
required successful release-candidate workflow rather than rebuild an
untested variant.

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

#### B1. The three-pipeline installed-wheel contract is not fully demonstrated

- **Problem:** the normal end-to-end path and drone correction/extraction paths
  are absent from the installed-artifact gate.
- **Evidence:** normal stopped after synthetic H5-to-ENVI; drone disabled topo
  and BRDF and had no polygons; only bulk completed all requested analyses.
- **Affected:** normal and drone.
- **Impact:** a PyPI user may encounter missing resources or repository
  assumptions only after starting real processing.
- **Fix:** create tiny scientifically valid fixtures and run normal correction,
  convolution, full or polygon extraction, merge, and QA; run drone correction,
  translation, and both full/polygon extraction selection. Execute from the
  clean wheel environment with the checkout inaccessible.
- **Owner:** Codex can implement the gate; maintainers must approve what counts
  as a scientifically representative minimum.

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

#### H1. CI does not exercise artifacts or the declared Python range

- **Evidence:** one Python 3.11 editable-install job; broad path-filter gaps.
- **Affected:** all pipelines.
- **Impact:** packaging and compatibility regressions can merge without CI.
- **Fix:** add supported-version build/install smoke matrix and broaden/remove
  release-critical path filters.
- **Owner:** Codex.

#### H2. Normal validation invokes an uninstalled repository script

- **Evidence:** normal orchestration searches above its module for
  `bin/validate_parquets`; that file is not in the wheel.
- **Affected:** normal pipeline validation/QA.
- **Impact:** installed behavior silently omits a documented check.
- **Fix:** package the implementation or document it as maintainer-only and use
  installed validation APIs in user docs.
- **Owner:** Codex; maintainer confirms desired public contract.

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
4. Decide the supported Python versions and dependency policy; add that clean
   Linux CI matrix and align public documentation.
5. Expand `check_installed_artifact.py` with tiny representative fixtures for
   the complete normal correction/convolution/extraction/merge/QA path and the
   drone correction/translation plus full-or-polygon extraction behavior.
6. **Mandatory artifact gate:** build the wheel once, install it with
   dependencies into clean environments with no repository checkout on import
   paths, and successfully run the normal NEON, drone, and bulk pipelines. Fail
   the release if any package data or code is obtained from the checkout.
7. Build and install the sdist in at least the lowest supported Python version;
   run metadata, import, resource, and smoke checks.
8. Make CI run Ruff, unit/integration tests, docs build/link checks, AI
   transparency, validation evidence checks, version synchronization, package
   data inventory, `twine check`, and the artifact gate for every
   release-relevant change.
9. Replace the repository-relative Parquet validator behavior with an installed
   API or clearly remove it from the public installed workflow.
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
  scripts/check_installed_artifact.py

.venv/bin/python -m compileall -q src/spectralbridge scripts/check_installed_artifact.py
.venv/bin/pytest -q tests/test_drone_pipeline.py
.venv/bin/pytest -q tests/test_bulk_pipeline.py
.venv/bin/pytest -q tests/test_qa
.venv/bin/pytest -q
.venv/bin/python scripts/check_docs_links.py
.venv/bin/mkdocs build --strict --site-dir /tmp/spectralbridge-pypi-audit-site
.venv/bin/python scripts/generate_ai_transparency.py --check
git diff --check
```

All commands in this section passed. The full suite had six skips and existing
deprecation/all-NaN warnings; focused results and the remaining build notices
are recorded in `FEATURE_REQUESTS.md`. The commands above do not imply that the
abbreviated artifact smoke satisfies blocker B1.
