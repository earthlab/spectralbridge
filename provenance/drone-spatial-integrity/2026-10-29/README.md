# Drone spatial investigation evidence

See [the investigation report](../../../docs/dev/drone-spatial-integrity-investigation.md).

The strongest evidence is the paired production-source audit:

- `production_source_comparison.json` and `production_verified_footprints.*`
  compare all ten retained bands of the actual Gordon, Goldhill and Ruby TIFF/H5
  pairs, and independently replay polygon membership from saved output geometry.
- `ruby_before/` and `legacy_ruby_export_replay.json` reproduce the old export
  behavior from original Ruby H5. Missing historical later stages remain explicit.
- `ruby_after/`, `ruby_full_pixel_validation.json`, `ruby_recovery_result.json`
  and `ruby_restart.json` record the real Ruby recovery, retained-row validation,
  four translation equations/masks, and unchanged-run reuse.
- `synthetic/` and tiny `synthetic_inputs/` remain separate asymmetric controls.
  The synthetic illustration uses pass-through correction and translation +1;
  real Ruby recovery enables the existing correction and all four existing plans.

`production_metadata_evidence.json` and its figure are the earlier metadata-only
comparison; their blue hypothesis is superseded by the authoritative paired
source audit. `unassigned_h5/` concerns a separate unidentified local H5, not a
substitute for the three named pairs. `remote_access.json` records successful
authentication/retrieval after the initial missing-login attempt.
`remote_downloads.json` and the source audit retain paths, sizes and hashes.
`downloaded_parquet_inventory.json` explains why an unrelated local MRS1 table
cannot establish historical impact. `validation.json` records final checks.

Original production files and recovered products stay in separate temporary
workspaces; no production raster or pixel library is copied into this packet.
The report contains exact source retrieval and real recovery/diagnostic commands.
The explicit first-ten-band recovery derivative is an investigation choice, not
auto-trimming in the package. Band 11, acquisition-date discrepancy and missing
terrain remain scientific-promotion gates.

From the repository root, regenerate the saved-metadata figure using the
fingerprinted files (the QA download must be present):

```bash
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python \
  provenance/drone-spatial-integrity/2026-10-29/build_evidence.py \
  --summary /Users/tuff/Downloads/drone_qa_summary.json \
  --polygons Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg \
  --output provenance/drone-spatial-integrity/2026-10-29
```

Regenerate the synthetic products:

```bash
MPLCONFIGDIR=/private/tmp/spectralbridge-mpl .venv/bin/python \
  provenance/drone-spatial-integrity/2026-10-29/build_synthetic_evidence.py \
  --output provenance/drone-spatial-integrity/2026-10-29/synthetic_inputs
```

Then pass the retained synthetic TIFF/H5/native/corrected/translated products and
polygons to `scripts/diagnose_drone_spatial_integrity.py --synthetic`, with
`--parquet` pointing at `synthetic_inputs/spectra.parquet` and `--output` pointing
at `synthetic/`. The script's `--help` describes the explicit stage inputs. The
report contains the corresponding real-production commands.

Memory scales with bounded source row windows, thumbnail dimensions, four cached
raster rows and two bounded reference-index chunks for record comparisons, polygon metadata and a bounded Parquet batch.
Exact lossless comparisons make an additional sequential source pass per supplied
lossless stage. No production raster or full pixel table is copied into this
packet. Duplicate checks use DuckDB's bounded memory setting and may spill to
local temporary storage on large inputs. Progress is emitted by stage and during
long Parquet scans. No recovery command uploads or publishes anything.
