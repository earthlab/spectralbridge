# Run a remote drone campaign through bulk production

Use this workflow when the authoritative drone ExportPackages live in a remote
collection and the goal is one complete, restartable campaign plus compact bulk
results. SpectralBridge owns remote inventory, H5 staging, per-flight producer
checkpoints, producer-to-bulk validation, population analysis, interpretation,
closeout packaging, and optional verified upload.

The default CyVerse adapter uses the existing `gocmd` configuration. Install and
authenticate `gocmd` before starting; SpectralBridge does not collect passwords
or run interactive credential setup inside scientific functions.

## Production call

```python
from spectralbridge import run_drone_bulk_production

result = run_drone_bulk_production(
    source=(
        "i:/iplant/home/shared/earthlab/macrosystems/field-data/output/"
        "summer-2023-10cm-10k"
    ),
    years=[2023, 2024],
    work_dir="/home/jovyan/data-store/SpectralBridge_Drone_2023_2024",
    upload_results=True,
)

result.summary()
```

Inventory alone does not download an H5:

```python
from spectralbridge import inspect_drone_collection

inventory = inspect_drone_collection(
    "i:/iplant/home/shared/earthlab/macrosystems/field-data/output/"
    "summer-2023-10cm-10k",
    years=[2023, 2024],
    inventory_output_dir="campaign_state",
)
print(inventory.to_dict()["counts"])
```

The inventory recursively identifies ExportPackages, requires one source H5 per
package, preserves the package path, derives the producer flight stem, resolves
the bundled field manifest with separator-tolerant identifiers such as `SPR-1`,
`SPR1`, and `SPR_1`, and records local/bulk readiness. Arbitrary outer batch
directory names never become scientific identity.

## Producer-to-bulk gate

After each `run_drone_pipeline()` call, the campaign invokes
`validate_bulk_ready_flightline()`. That function calls the same
`discover_completed_flightlines()` implementation used by `run_bulk_pipeline()`.
The flight is complete only when discovery finds exactly one canonical identity,
classifies it as accepted, finds a requested translation pair, and marks that
pair regression-eligible. Missing `spectralbridge_flightline.json`, invalid
products, duplicate identity, incompatible bands, and incomplete pairs fail at
the producer boundary rather than hours later in population analysis.

The default completeness policy is strict. SpectralBridge inventories the
eligible population before processing and stops before bulk when any expected
flight is failed, blocked, or not bulk-ready. Set
`require_complete_campaign=False` only for a deliberately partial analysis.

## Restart and disk behavior

Each remote package has an independently persisted state under `work_dir/state`.
On restart, a flight that still passes the canonical bulk gate is reused. A
failed flight is retried from its valid staged H5 and any restart-safe producer
stages. No duplicate canonical flight is created.

By default the runner stages one H5, validates its remote size (and checksum when
available), processes it, proves the completed flight is bulk-ready, and removes
only that exact staged source H5. Its canonical output retains the restartable
working H5 and scientific products. Failed flights keep their staged source for
diagnosis and retry. Use `DroneCampaignConfig(cleanup_inputs=False)` for local
raw retention.

## Bulk and result semantics

The normal campaign calls `run_bulk_pipeline()` with no spectral library and
with spectral-library plotting disabled. It then calls
`summarize_bulk_results(..., config=BulkResultsConfig(), make_figures=True,
make_report=True)` for normal compact bulk interpretation. The similarly named
`make_summary_plots` bulk argument belongs only to the optional polygon
spectral-library workflow.

Drone Landsat-like products remain same-source coefficient applications. Their
fits and LOSO artifacts are application-verification diagnostics, not independent
empirical calibration, and must not be fed back into the production registry.

After local analysis succeeds, `work_dir/results/` receives a deterministic,
versioned closeout directory. It contains campaign inventory/status, package and
Git provenance, bulk catalogs, census, sufficient statistics, coefficients,
per-flight/per-site/balanced/LOSO results, figures, reports, and a SHA-256
manifest. It excludes downloaded H5s, temporary data, DuckDB scratch/cache data,
and diagnostic pixel samples. With `upload_results=True`, that one directory is
uploaded beneath the source collection. Existing remote destinations are never
overwritten; an equivalent package is verified and reused, while a mismatch
fails closed.

## Command line

```bash
spectralbridge-drone-production inventory \
  i:/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023-10cm-10k \
  --years 2023 2024 --output-dir campaign_state

spectralbridge-drone-production bulk \
  i:/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023-10cm-10k \
  --years 2023 2024 \
  --work-dir /home/jovyan/data-store/SpectralBridge_Drone_2023_2024 \
  --upload-results
```

Use `campaign` instead of `bulk` to stop after canonical per-flight production.
`--keep-inputs` retains staged H5s and `--allow-partial` explicitly opts into a
partial population.
