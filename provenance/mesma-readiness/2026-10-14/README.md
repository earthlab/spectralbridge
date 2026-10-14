# MESMA readiness assessment - 2026-10-14

Start with RESULTS.md for the twenty scientific questions and final readiness matrix; MATERIAL_CLASS_AUDIT.md and RECOMMENDATIONS.md explain the data gates. DESIGN.md fixes constraints/thresholds before mixture benchmarks. REPOSITORY_AUDIT.md and LITERATURE_METHODS.md identify reused evidence and primary definitions. Other named reports separate QC, coverage, selection, geometry, controlled mixtures, sensor transfer, grouped transfer and uncertainty. Tables and six PDF/PNG/SVG figure families carry exact counts and memberships.

This is not an operational MESMA implementation or abundance product. No physical unit scale, pure material identity or field fraction was invented. The physical and real-abundance branches stopped at their data gates; explicitly conditional common-scale synthetic diagnostics were still run.

Reproduce from the repository root using the existing compact P120 input summaries:

```bash
python provenance/mesma-readiness/2026-10-14/audit_source.py
python examples/mesma_readiness.py Aug_2026_all_polygons_merged_pixel_extraction.parquet --compact artifacts/plant_spectral_atlas/sensor_pft_transfer/compact --output artifacts/plant_spectral_atlas/mesma_readiness_first_pass --first-pass
python examples/mesma_readiness.py Aug_2026_all_polygons_merged_pixel_extraction.parquet --compact artifacts/plant_spectral_atlas/sensor_pft_transfer/compact --output artifacts/plant_spectral_atlas/mesma_readiness
python provenance/mesma-readiness/2026-10-14/analyze_results.py
python provenance/mesma-readiness/2026-10-14/additional_sensitivity.py
python provenance/mesma-readiness/2026-10-14/ambiguity_sensitivity.py
python provenance/mesma-readiness/2026-10-14/write_report.py
```

The compact products must already be verified against this SAME immutable source; this workflow does not regenerate upstream inputs. This audit checks P120 origin and all owned output hashes before interpretation. For the optional human PDF run build_report.py with reportlab and pypdf available.

Use `.venv/bin/python`, `MPLCONFIGDIR=/tmp/spectralbridge-mpl`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` on the validated local environment. The first pass precedes the expanded audit. Grouped fold checkpoints include source/configuration/code identities and checksums; restarts reuse valid folds. Source Parquet and prior ecological/sensor results are immutable. Candidate pools, not a pixel-scale source copy, bound the combinatorics. See VALIDATION.md for full-suite, exact optimizer, identity leakage, actual-flight target and evidence checks.
