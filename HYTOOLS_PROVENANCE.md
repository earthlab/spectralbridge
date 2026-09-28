# SpectralBridge and HyTools Code Provenance

## Purpose

SpectralBridge historically used HyTools and later replaced HyTools as a
required runtime dependency in its supported pipeline. That runtime change did
not erase implementation lineage. This document records the relationship
between the projects so releases and publications can distinguish copied or
adapted source, shared scientific methods, compatibility code, and independently
developed SpectralBridge systems.

This is a best-effort repository and source-provenance audit, not a legal
opinion. It deliberately preserves uncertain classifications and does not use
cosmetic rewrites to reduce source similarity.

## Audited versions

Audit date: **2026-09-26**

| Project | Repository | Audited revision | Detected project license |
| --- | --- | --- | --- |
| SpectralBridge | <https://github.com/earthlab/spectralbridge> | `30344404bf7787b135ed00424e624af43d42c6ab` (before this audit's prompt-log, documentation, notice, manifest, and guardrail changes) | `GPL-3.0-or-later` in `pyproject.toml`; GPLv3 text in `LICENSE` |
| HyTools | <https://github.com/EnSpec/hytools> | `31286d64541791a9815d29443a33726fa4d54031` | `GPL-3.0-only` in `pyproject.toml`; GPLv3 text in `LICENSE.txt` |

The HyTools source notices relevant to the identified matches state
`Copyright (C) 2021 University of Wisconsin` and name Adam Chlus, Zhiwei Ye,
and Philip Townsend. The audited HyTools package metadata additionally names
Ting Zheng, Natalie Queally, and Evan Greenberg as project authors. This audit
does not infer ownership beyond those repository statements.

## Classification scheme

1. **Verbatim/vendored HyTools code** — substantially identical source.
2. **Adapted HyTools code** — implementation lineage is established, with
   meaningful SpectralBridge modifications.
3. **Shared scientific algorithm** — both projects implement a published
   method, but source derivation was not established.
4. **Interoperability/compatibility** — code calls HyTools or supports its API
   and file conventions without incorporating its implementation.
5. **Independent SpectralBridge code** — no material HyTools implementation
   lineage was detected by this audit.
6. **Uncertain** — available evidence does not support a stronger conclusion.

The machine-readable record is in `provenance/hytools.json`.

## Component provenance table

| SpectralBridge component | File/function | HyTools counterpart | Class | Nature of relationship | Scientific reference | Attribution before audit | Action taken |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| Legacy resampler application | `src/spectralbridge/standard_resample.py::apply_resampler` | `src/hytools/transform/resampling.py::apply_resampler` | 1 | Same implementation after removal of comments/docstrings; canonical AST is identical. SpectralBridge history traces it to the initial `Resampling/resampling_demo.py`. | Gaussian/interpolation resampling; no specific paper established from the repositories | Missing file-level HyTools copyright, repository, and revision | Added a complete file-level provenance notice and this record |
| Incidence geometry | `src/spectralbridge/corrections.py::calc_cosine_i` | `src/hytools/topo/topo.py::calc_cosine_i` | 2 | Entered in an explicitly HyTools-adapted module; expanded validation, typing, dtype, and safeguards materially changed the implementation | Standard sloped-surface solar-incidence geometry | HyTools and authors named, but no copyright, URL, or fixed revision | Added a consolidated source notice and retained the function-level adaptation statement |
| Ross-Thick volume kernel | `src/spectralbridge/corrections.py::calc_volume_kernel` | `src/hytools/brdf/kernels.py::calc_volume_kernel` | 2 | Historical adaptation is explicit; the current code supports a narrower interface plus SpectralBridge validation/guards | Wanner et al. (1995), DOI `10.1029/95JD02371` | Partial | Added upstream/copyright/revision notice and scientific citation |
| Li reciprocal geometric kernels | `src/spectralbridge/corrections.py::calc_geom_kernel` | `src/hytools/brdf/kernels.py::calc_geom_kernel` | 2 | Historical adaptation is explicit; supported names, parameters, guards, and current `LiDenseR` handling have diverged | Wanner et al. (1995); Lucht et al. (2000), DOI `10.1109/36.841980` | Partial | Added upstream/copyright/revision notice and scientific citations |
| BRDF coefficient fitting/application | `fit_and_save_brdf_model`, `apply_brdf_correct`, NDVI bin helpers | HyTools `brdf/flex.py` and `brdf/universal.py` | 2 | Same Ross/Li kernel-regression and reference/pixel ratio family; Git history calls the change a FlexBRDF ratio inside a module already recorded as adapted. Current masking, persistence, binning, neutral fallbacks, and streamed use are materially different; no exact function match was found. | Wanner et al. (1995); Lucht et al. (2000) and the additional kernel references listed below | Only broad file-level credit | Clarified component-level provenance; no numerical code changed |
| SCS+C fitting and application | `fit_scs_c_coefficients`, SCS+C branch of `apply_topo_correct` | `src/hytools/topo/scsc.py` | 3 | Both implement `rho = a cos(i) + b`, `C=b/a`, and the SCS+C factor. Current SpectralBridge functions were added later and have no material text or AST match to HyTools. The separately used `calc_cosine_i` remains Category 2. | Soenen, Peddle, and Coburn (2005), DOI `10.1109/TGRS.2005.852480` | Algorithm described but original paper not cited | Added original scientific citation and classification |
| NEON cube facade and ancillary ENVI reader | `src/spectralbridge/neon_cube.py` | `src/hytools/io/neon.py::open_neon`; parts of `io/envi.py` | 2 | File entered with an explicit adapted/vendor lineage statement. It now delegates to SpectralBridge schema readers and adds slicing, scale handling, ancillary alignment, and restart-oriented behavior. No exact current function match was found. | Not applicable | HyTools and three authors named; wording overstated current vendoring | Replaced “vendors” with precise adaptation language and added copyright/URL/revision |
| Authoritative NEON HDF5 reader | `src/spectralbridge/io/neon.py` | `src/hytools/io/neon.py::open_neon` | 2 | Factored from the adapted `NeonCube` path, then expanded for old/new layouts, canonical schema resolution, orientation, scaling, and bounded windows | Not applicable | No source-level HyTools notice | Added source-level provenance notice |
| ENVI header and writer | `src/spectralbridge/envi_writer.py` | `src/hytools/io/envi.py::{write_envi_header,envi_header_from_neon,WriteENVI}` | 2 | Explicitly adapted and narrowed to SpectralBridge's float32 BSQ contract; no exact current function match was found | ENVI format convention, not a claimed scientific algorithm | HyTools and authors named; no copyright/URL/revision | Added consolidated source notice |
| HyTools imports across releases | `src/spectralbridge/hytools_compat.py` | HyTools module layouts and public classes | 4 | Dynamic import discovery only | Not applicable | Clear | Retained; recorded in manifest |
| Packaged legacy workflow | `src/spectralbridge/deprecated/hytools.py` and `topo_and_brdf_correction.py` | HyTools runtime APIs | 4 | Optional legacy adapter and SpectralBridge re-export shim. It imports an external HyTools installation only when invoked. | Not applicable | Clear | Retained for compatibility; documented that it ships |
| Historical HyTools base source | `deprecated/code/base.py` | `src/hytools/base.py` | 1 | Historical copy with many exact and near-exact functions and the full upstream GPL notice | Not applicable | Original copyright/authors/GPL notice intact | Retained in Git; confirmed excluded from wheel and sdist by package layout and `MANIFEST.in` |
| Other root historical workflows | `deprecated/bin`, `deprecated/code` other than `base.py`, `deprecated/docs`, notebooks, and legacy tests | HyTools APIs and historical documentation | 4 | Runtime calls, examples, tests, and references. The systematic Python comparison did not find another materially copied file. | Varies | Mixed historical references | Retained in Git and excluded from release artifacts |
| Legacy coefficient fallback and adapter object | `standard_resample.py::{calc_resample_coeffs fallback,resampler_hy_obj}` | HyTools coefficient routine and resampler contract | 6 | The fallback does not match HyTools text or AST, but it was created inside a HyTools-backed module and emulates the surrounding object contract. Evidence is insufficient to call the whole section independent. | General Gaussian spectral-response modeling | HyTools mentioned only around the fallback import | Recorded as uncertain; no code rewrite |
| Current convolution engine | `src/spectralbridge/resample.py` | No material counterpart detected | 5 | SpectralBridge SRF loading, validation, and chunked convolution did not match HyTools source | Sensor response convolution conventions | Not needed | Recorded as independent finding |

## High-risk component review

### Topographic correction

HyTools' `calc_cosine_i` and the original SpectralBridge helper use the same
incidence equation. Git history is decisive here: SpectralBridge introduced the
helper in a module explicitly described as adapted from HyTools. The current
helper is therefore Category 2 even though the equation itself is standard.

The present SCS+C code arrived later. It fits each band using `rho = a*cos(i) +
b`, derives `C=b/a`, and applies `(cos(theta_s)*cos(slope)+C)/(cos(i)+C)`.
HyTools implements the same published method, but its coefficient storage,
actor workflow, masks, and correction dispatch differ. SpectralBridge adds
streamed scene sufficient statistics, optional tile fits, storage-scale
conversion, finite/no-data masks, singular-fit handling, and a small-denominator
neutral fallback. No material function-level source match was found. This part
is Category 3 and should cite Soenen et al. (2005); the adapted incidence helper
inside it remains Category 2.

### BRDF kernels and fitting

The Ross-Thick and Li kernel helpers were explicitly adapted from HyTools and
are Category 2. Their equations are also published methods. Relevant references
already listed by HyTools include:

- Wanner, Li, and Strahler (1995), DOI `10.1029/95JD02371`.
- Lucht, Schaaf, and Strahler (2000), DOI `10.1109/36.841980`.
- Roujean, Leroy, and Deschamps (1992), DOI `10.1029/92JD01411`.
- Maignan, Bréon, and Lacaze (2004), DOI `10.1016/j.rse.2003.12.006`.
- Schläpfer, Richter, and Feingersh (2015), DOI
  `10.1109/TGRS.2014.2349946`.
- Colgan et al. (2012), DOI `10.3390/rs4113462`.

SpectralBridge's fitting and correction path retains the HyTools/FlexBRDF
conceptual lineage: NDVI stratification, per-band Ross/Li linear fits, and a
reference-geometry to pixel-geometry ratio. It has materially diverged in
configuration, bin handling, persistence, masking, coefficient fallbacks,
chunking, and scale conversion. Because repository history explicitly connects
the work to FlexBRDF, those routines are recorded as adapted rather than
independent even though the current mechanical comparison finds no exact
function match.

### NEON HDF5 reading

HyTools `open_neon` uses the NEON reflectance group, wavelength/FWHM arrays,
coordinate metadata, scale and no-data attributes, and ancillary observation
geometry. SpectralBridge began from that data contract and an explicitly
adapted NEON reader. The current implementation additionally resolves multiple
historical layouts, normalizes array orientation and vector units, supports
line/sample windows, shifts map origins, distinguishes storage scaling from
physical reflectance, and exposes canonical metadata. These are substantial
modifications, but history supports Category 2 rather than independent creation.

### ENVI writing

Both projects serialize ENVI header fields and use NumPy memory maps for
interleave-aware binary output. SpectralBridge's writer is restricted to its
float32 BSQ output contract, performs explicit validation, and writes spatial
chunks using its own pipeline interfaces. Its file and function documentation
have always described the HyTools `WriteENVI` and header helpers as the source
of the adaptation. It is Category 2.

### Resampling and convolution

`standard_resample.apply_resampler` is the clearest active Category 1 result.
At both audited commits, the bodies are identical after removing docstrings and
comments and produce identical canonical ASTs. The surrounding fallback
coefficient implementation is not the HyTools algorithm, but its provenance is
uncertain because it was introduced to emulate a HyTools-backed module.

The supported pipeline's separate `spectralbridge.resample` SRF convolution
engine did not produce a material HyTools match and is Category 5 for this
audit. This does not turn the legacy `standard_resample` module into independent
code.

## Direct-reference inventory

The case-insensitive repository search included `HyTools`, the named authors,
University of Wisconsin, GPL/adaptation/vendor terms, NEON/ENVI API names, and
the BRDF/topographic algorithm vocabulary requested for the audit. The
following file-level inventory classifies every tracked file containing a
direct HyTools/name/license reference at the pre-audit revision; algorithm-only
occurrences were manually reviewed in the high-risk areas above.

| Role | Files |
| --- | --- |
| Active adapted source | `src/spectralbridge/corrections.py`, `neon_cube.py`, `io/neon.py` through its history from `NeonCube`, `envi_writer.py`, `standard_resample.py` |
| Runtime compatibility | `src/spectralbridge/hytools_compat.py`, `src/spectralbridge/deprecated/__init__.py`, `src/spectralbridge/deprecated/hytools.py`, `src/spectralbridge/topo_and_brdf_correction.py` |
| Active orchestration/diagnostics mentioning behavior or settings | `src/spectralbridge/brdf_topo.py`, `neon_to_envi.py`, `paths.py`, `pipelines/drone.py`, `pipelines/pipeline.py`, `qa/thresholds.py`, `scripts/diagnose_brdf_topo_stage.py`, `run_validation_campaign.py`, `validation_docs_content.py` |
| Tests/validation references | `tests/conftest.py`, `test_brdf_scale.py`, `test_brdf_topo_streamlined.py`, `test_hytools_compat.py`, `test_hytools_preflight.py`, `test_legacy_hytools_module.py`, `test_parquet_export.py`, `test_pipeline_convolution.py`, `test_stage_export.py` |
| Current documentation/governance | `CHANGELOG.md`, `FEATURE_REQUESTS.md`, `docs/brdf_topo_algorithm.md`, `docs/refactor_notes.md`, `docs/validation/h5_to_envi.md`, `docs/dev/publication-hardening-audit-2026-09-04.md`, `docs/dev/publication-readiness-audit-2026-08-14.md`, `publication_checklist.md` |
| Historical code/docs/tests | `deprecated/README.md`, `deprecated/bin/neon_to_envi.py`, `deprecated/code/base.py`, `deprecated/code/pipeline.py`, `deprecated/code/spectral_unmixing_tools_original.py`, `deprecated/docs/BRDF-Topo-HyTools/README.md`, `deprecated/docs/stage-01-raster-processing.md`, `deprecated/tests_legacy/test_convolution_resample_utils.py`, `deprecated/tests_legacy/test_roi_spectral_comparison.py`, and five tracked deprecated notebooks |
| Audit-log/generated context, not implementation evidence | `PROMPT_LOG.md` and HyTools terms processed by `scripts/generate_ai_transparency.py` |

New references added by this audit occur in this document, `NOTICE`, the
manifest, the guardrail and its tests, manuscript guidance, and navigation or
release documentation that links to them.

## Mechanical comparison

The complete tracked trees were inventoried, not only files mentioning
HyTools. The SpectralBridge baseline contained 585 tracked files, including 222
Python files and 62 notebooks. The HyTools baseline contained 166 tracked
files, including 73 Python files and one notebook. Python comparison covered
2,228 SpectralBridge function definitions and 333 HyTools definitions across
`src`, scripts/bin, tests, examples, deprecated/history paths, and other tracked
locations.

The local comparison normalized and compared:

1. raw and whitespace-normalized source;
2. source with comments and docstrings removed;
3. canonical Python AST structure with identifiers normalized;
4. function-level token and AST similarity;
5. exact windows of at least six nonblank lines; and
6. comments and docstrings.

Results requiring manual triage were 19 exact function/mode records, 26 near
function candidates, 590 exact six-line windows, 32 matching
comment/docstring records, and one file pair with normalized whole-file
similarity at or above 0.30. Most exact windows were repeated GPL notice text,
not separate implementation matches. The material results were:

- `deprecated/code/base.py` versus HyTools `src/hytools/base.py`: normalized
  whole-file ratio `0.7106`, 320 exact six-line windows, at least 17 exact
  whitespace-normalized function records, and additional near matches.
- `standard_resample.apply_resampler` versus HyTools
  `transform/resampling.apply_resampler`: `1.0` stripped-source and canonical
  AST match; token similarity `0.9478`; 13 exact six-line windows.
- `io/neon._as_str` versus HyTools `io/netcdf.get_attr_string`: a four/five-line
  generic bytes-to-string helper (`0.8402` AST candidate), rejected as
  non-distinctive boilerplate rather than evidence of copying.

No similarity score was used as the sole classification criterion. Source
headers, Git history, API purpose, scientific equations, and manual side-by-side
review determined the categories.

## Git-history evidence

- Commit `94ef270354dc6550aa66ee9e256a2b1e7d29f610` (2025-04-23) introduced
  `Resampling/resampling_demo.py` with the HyTools `apply_resampler` body.
- Commit `44a26ea7c428881fdc057e749b511d4cd37aed49` (2025-06-18) moved that
  function into the source resampling module. Later namespace moves preserved
  it.
- HyTools history attributes `apply_resampler` to commit
  `827eeda410239fe843dd756cb309d48ca5e873a5` (2021-01-22) and its GPL source
  notice to `2fd2dc388fb30396472f65bdda192478247e626b` (2021-03-26).
- Commit `b5969f5b7fa55bba8a365c1b6a8f82497b1eba61` (2025-10-27) introduced
  `corrections.py` with explicit HyTools-adaptation statements on incidence,
  Ross/Li kernels, topographic application, BRDF application, and the glint
  placeholder.
- Commits `fc370c477f4fd20039fd2138b92235b1f51e0059` and
  `fa0235a087acae4f09216b728e0784de3e0ab215` (2025-10-27) introduced the
  explicitly adapted NEON cube and ENVI writer.
- Commit `4a4df5e560f9ab02f843d26b3e9eeae333dd8f1b` (2025-12-10) added the
  current SCS+C and FlexBRDF-style path. Its code is materially different from
  HyTools, but its commit and documentation context establish method parity and
  continued implementation influence.
- Commit `91fdf107af3c986abbed9ceb8ad78ec2de9466e9` (2025-10-28) quarantined the
  root historical workflows under `deprecated/`; commit
  `52ef50fec028c7b29a41d8f990d6d6d16704163a` later moved active code into the
  `spectralbridge` namespace.

No Git history was rewritten.

## Licensing and attribution assessment

### Clearly established

- Both audited repositories distribute under GPLv3-family terms according to
  their checked-in metadata and license files.
- The historical `deprecated/code/base.py` retains the upstream copyright,
  named authors, GPL grant, warranty disclaimer, and license pointer.
- The root `deprecated/` archive is pruned by `MANIFEST.in` and is outside the
  package directory used to build wheels.
- HyTools is absent from SpectralBridge's declared runtime dependencies. It is
  pinned only in the CI constraints/preflight environment and loaded by legacy
  compatibility code when explicitly requested.

### Needed improvement at the audited baseline

- The active, substantially identical `standard_resample.apply_resampler`
  lacked an upstream copyright/source/revision notice. This was the principal
  attribution concern.
- Adapted correction, NEON, and ENVI modules named HyTools and three authors but
  omitted the upstream copyright holder, repository URL, and reproducible
  revision.
- The authoritative `io/neon.py` had inherited adapted lineage through
  refactoring but no source-level notice.
- “HyTools-free” wording could be read as denying source lineage when the
  intended claim was only that the supported path does not import HyTools at
  runtime.
- The wheel carried adapted/verbatim code without a concise third-party notice.

This audit adds source notices, `NOTICE`, this provenance record, a manifest,
and an offline guard. Those changes materially improve clarity. Maintainers
should still obtain human/legal review of notice sufficiency and copyright
holder completeness before any license change or final public-release decision.

## Deprecated historical code and release artifacts

`deprecated/code/base.py` is a historical HyTools source copy and is not needed
by the supported package. No active Python import points to it; the root
`deprecated/` directory is pruned from the source distribution, and wheels
discover packages only under `src/`. Keeping the file in Git retains historical
evidence without placing it in release artifacts, so this audit does not delete
it.

`src/spectralbridge/deprecated/hytools.py` is different: it is a SpectralBridge
legacy adapter inside the installable package. It ships intentionally to keep
old configuration workflows importable, but an external HyTools installation
is required to execute the HyTools-backed correction path. The active pipeline
does not call it.

The active Category 1 `standard_resample.apply_resampler` and Category 2
correction, NEON, and ENVI modules do ship in both wheel and source
distribution. `NOTICE` is configured as a packaged license file; this document
and the manifest are included in the source distribution.

## Runtime dependency

The precise statement is:

> The supported SpectralBridge pipeline does not require HyTools as a runtime
> dependency. SpectralBridge nevertheless contains source adapted from HyTools,
> one active substantially identical HyTools function, and optional legacy
> interoperability code. Those relationships remain attributed.

“SpectralBridge contains no HyTools-derived code” is not supported by this
audit.

## Independent SpectralBridge components

The full-tree comparison and history review detected no material HyTools
implementation lineage in the current drone pipeline, bulk-analysis and compact
statistics system, QA metrics/dashboards/reports, polygon extraction,
restart-safe product registry and naming architecture, DuckDB merge stage,
translation evidence chain, or the current `spectralbridge.resample` convolution
engine. They are Category 5 for this audit.

This classification means “no lineage detected using the recorded evidence,”
not mathematical proof of independent creation. Standard library patterns,
generic NumPy operations, file-format conventions, and short boilerplate were
not treated as copying.

## Automated guardrail

Run the offline repository check with:

```bash
python scripts/audit_upstream_provenance.py
```

If a local checkout of HyTools is available at the pinned revision, also
re-check the revision and Category 1 function matches without network access:

```bash
python scripts/audit_upstream_provenance.py --hytools-root /path/to/hytools
```

The guard verifies the manifest, required source markers, repository notice,
and provenance document. It intentionally does not fetch upstream source.

## Limitations and recommended review

- Similarity analysis cannot prove independent creation or identify influence
  that left no repository evidence.
- Notebooks were included in reference searches where practical, but their
  embedded outputs and binary assets were not treated as executable-source
  matches.
- A current fixed HyTools revision makes the audit reproducible; it may not be
  byte-identical to the revision developers consulted in 2025. Git history was
  used to bridge that limitation where possible.
- The Category 6 fallback resampler should remain explicitly uncertain unless
  a maintainer can provide contemporaneous design evidence.
- Legal review is advisable for notice sufficiency, copyright ownership, and
  any future move away from GPLv3-family distribution. This document makes no
  conclusion about legal compliance.

