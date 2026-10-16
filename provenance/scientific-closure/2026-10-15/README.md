# Final scientific closure — 15 October 2026

Start with FINAL_SCIENTIFIC_SYNTHESIS.md, FINAL_ANALYSIS_AUDIT.md,
tables/FINAL_READINESS_MATRIX.csv and NEXT_DATA_NEEDED.md. Convenient links with
those names are also at repository root. The polished human report is:

`output/pdf/scientific_closure/What_Can_We_Reliably_Learn_from_the_SpectralBridge_Spectral_Library.pdf`

The final evidence consists of five synthesis figures (PDF/SVG/PNG), figure
captions, editable report JSON/Markdown, tidy tables, exact model/membership
references and validation manifests. No independent field abundance truth or
new actual sensor observations were invented.

## Decision

Broad woody leaf-habit associations are the strongest transferable result within
the assigned source-label population. Species/narrow PFT transfer is more fragile;
species closed-set target coverage can be low. Labels recorded in 2023/2024 are
reused across image years, so temporal tests are retrospective recognition of
labelled footprints rather than annual biological field verification. Median
polygon/acquisition support is two native 1 m pixels. Synthetic OLI changes
spectral response, not spatial mixing to 30 m. Mixture abundance and dependable
physical unknown rejection remain unvalidated.

## Reproduce without duplicating previous analyses

Use the optional analytics environment and supplied original Parquet **in place**,
with verified canonical paired compact products. All scripts run from repo root:

```bash
python provenance/scientific-closure/2026-10-15/run_closure.py
python provenance/scientific-closure/2026-10-15/synthesize.py
python provenance/scientific-closure/2026-10-15/audit_metadata.py
python provenance/scientific-closure/2026-10-15/finalize_tables.py
python provenance/scientific-closure/2026-10-15/build_figures.py
```

The gap run is 156 fixed fits, with a documented 16-fit broad amplitude/shape
clarification. P118–P126 model/permutation/mixture/real-sensor analyses are reused.
Completed per-fit hashes protect restart. A modified execution configuration
requires a fresh output directory; never replace a completed evidence ledger to
hide scientific changes. Development output was superseded before final sealing
and is not the final scientific evidence.

With a Python containing ReportLab/pandas/pypdf (the desktop bundled document
runtime was used here):

```bash
python provenance/scientific-closure/2026-10-15/build_report.py
```

Report/figures rebuild from tidy tables, without reopening rasters or fitting
models. Source-specific code keeps paths explicit. Numerical validation needs
trusted local model caches and the original/compact inputs:

```bash
python provenance/scientific-closure/2026-10-15/validate_closure.py
python scripts/generate_scientific_docs.py
```

The raw archive retains all valid observations, identity/year/site/acquisition
and annotation dates. Prototypes/summaries are separate derived products. An
identity-balanced sampling policy is a recommendation for the stated inferential
target, not an untested change to production defaults. Earliest-observation
sensitivity changes both representation and weights and cannot isolate weighting.

Review thresholds are use-specific scenarios, not universal scientific approval
rules. Conditional identity-bootstrap intervals do not represent unobserved
geographic populations. See DESIGN and VALIDATION before interpreting a score.

Final QA: see VALIDATION.md, checks/, manifests/numerical_validation.json and
manifests/rebuild_validation.json. Run validate_rebuild.py with the report runtime
to verify byte-identical publication artifacts, then seal_evidence.py to refresh
the final checksum ledger after an intentional revision. The ledger includes
packaged crosswalk/band definitions and references existing evidence in place.
