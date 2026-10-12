# Research and historical archive

These files preserve historical research and development; they are not installed
package code or recommended first examples. No scientific file was discarded.
The checksummed move ledger is `provenance/cleanup/2026-10-12/moves.json`.

| Area | Role | Execution / editing policy |
| --- | --- | --- |
| `notebooks/campaigns/` | Named campaign and exploratory notebooks | Cells and outputs preserved byte-for-byte. Historical paths/dependencies may need the original environment; run from repository root, not the notebook directory. |
| `research/bulk-calibration/` | Author-supplied compact bulk evidence bundle | Immutable snapshot; retain incomplete run/source provenance stated in the SI. |
| `research/polygons/` | Research polygon layers | Root compatibility symlinks preserve existing notebook inputs. Provenance and sharing permissions need maintainer review before external hosting. |
| `scripts/` | Historical monkeypatch experiment | Retained for inspection, not a supported correction or resume workflow. |
| `literature/` | Local third-party reading collection | Ignored PDFs, outside website/package builds. Do not redistribute without reviewing the applicable license/rights evidence. |
| `local/` | Preserved local binaries, test artifacts and downloaded inputs | Ignored; not reproducible package fixtures. Original input filenames and checksums retained in the move ledger. |

`deprecated/` and `vendor/` remain at their original paths because pinned source
history and HyTools attribution refer to them. They are not alternate public APIs.
Active `Drone_processing.ipynb` and `Raster_processing.ipynb` remain at root because
current vignette contract tests and outside notebook users reference them. Prefer
`docs/vignettes/notebooks/` for new studies.
