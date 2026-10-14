---
search:
  exclude: true
---

# Recipes: Notebook Patterns

!!! note "Canonical learning path"
    These older recipes are retained for stable links. Use the [vignette
    map](../vignettes/index.md) to choose the single canonical workflow for each
    module.

These short recipes start from files on disk after the pipeline has run. Copy the cells into your notebook to repeat common workflows and stay aligned with the outputs-and-naming contract.

---

## Recipe 1: Run a single flightline (recap)

Use this when you want the canonical, restart-safe run for one flightline,
including download. See the [Start Here notebook workflow](notebook-example.md)
for the full walkthrough.

```python
from pathlib import Path
from spectralbridge import go_forth_and_multiply

base_folder = Path("csc_output")
site_code = "NIWO"
year_month = "2023-08"
flightline_id = "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"

go_forth_and_multiply(
    base_folder=base_folder,
    site_code=site_code,
    year_month=year_month,
    product_code="DP1.30006.001",
    flight_lines=[flightline_id],
    max_workers=1,
    engine="thread",
)
```

Expect to see `{flightline_id}_merged_pixel_extraction.parquet` plus `{flightline_id}_qa.png`/`{flightline_id}_qa.json` in `base_folder / flightline_id` when it finishes.

---

## Recipe 2: Batch process multiple flightlines

`go_forth_and_multiply` applies the same pipeline to many flightlines and skips work that already succeeded. Safe to re-run if a notebook or kernel restarts mid-way.

```python
from pathlib import Path
from spectralbridge import go_forth_and_multiply

base_folder = Path("csc_output")
flightline_ids = [
    "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance",
    "NEON_D13_NIWO_DP1_L020-2_20230815_directional_reflectance",
]

go_forth_and_multiply(
    base_folder=base_folder,
    site_code="NIWO",
    year_month="2023-08",
    product_code="DP1.30006.001",
    flight_lines=flightline_ids,
    max_workers=2,
    engine="ray",
)
```

Restarting this cell later will fast-forward past any flightlines that already have merged Parquet and QA artefacts.

---

## Recipe 3: Re-run QA on existing outputs

Generate fresh QA artefacts from completed flightlines without recomputing the pipeline.

```python
from pathlib import Path
from spectralbridge.qa_plots import render_flightline_panel

flight_dir = Path("csc_output") / "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"

png_path, metrics = render_flightline_panel(
    flightline_dir=flight_dir,
    quick=True,  # deterministic sampling
    save_json=True,
)
print("QA PNG →", png_path)
print("Issues:", metrics.get("issues", []))
```

This operates on existing ENVI and Parquet products in `flight_dir` and rewrites `{flight_id}_qa.png` and `{flight_id}_qa.json` only. If you prefer the CLI, `spectralbridge-qa` wraps the same logic for batch folders.

---

## Recipe 4: Load and explore the merged Parquet

The merged Parquet is the analysis starting point. Use pandas or pyarrow/DuckDB depending on scale.

```python
import pandas as pd
from pathlib import Path

flight_dir = Path("csc_output") / "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
merged_parquet = flight_dir / f"{flight_dir.name}_merged_pixel_extraction.parquet"

merged_df = pd.read_parquet(merged_parquet)
merged_df.head()
```

Inspect available fields to guide filtering and joins:

```python
[col for col in merged_df.columns if "wl" in col][:10]  # sample band columns
```

For large files, prefer streaming SQL with DuckDB:

```python
import duckdb

rel = duckdb.read_parquet(str(merged_parquet))
rel.limit(5).df()
```

---

## Recipe 5: Extract spectra for polygons

Link pixels to polygons using the optional polygon pipeline utilities built on top of the merged Parquet and ENVI outputs.

```python
from spectralbridge.paths import FlightlinePaths
from spectralbridge.polygons import run_polygon_pipeline_for_flightline

flight_paths = FlightlinePaths("csc_output", "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance")
polygons_path = "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"

result = run_polygon_pipeline_for_flightline(
    flight_paths,
    polygons_path,
    products=[
        "envi",
        "brdfandtopo_corrected_envi",
        "landsat_tm_envi",
        "landsat_oli_envi",
    ],
)

result["polygon_merged_parquet"]
```

The helper rasterises polygons, filters per-product Parquet tables, and writes `<flight_id>_polygons_merged_pixel_extraction.parquet` for direct use in modeling notebooks. See `docs/pipeline/polygons.md` for deeper details.

---

## Recipe 6: Compare sensors for the same targets

Inspect corrected NEON and its synthetic sensor resamples for the same pixels. This is an internal diagnostic, not independent validation. Inspect the actual stage prefixes first; product aliases vary.

```python
import pandas as pd
from pathlib import Path

flight_dir = Path("csc_output") / "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
merged_parquet = flight_dir / f"{flight_dir.name}_merged_pixel_extraction.parquet"

df = pd.read_parquet(merged_parquet)

# A bounded view of the fields actually present; inspect prefixes before selecting.
print([c for c in df.columns if "_wl" in c])
comparison = df.head(100)
comparison.head()
```

Select each product's verified native wavelength columns from this schema, then
plot each product on its own axis or with its own wavelength coordinates. The
first five columns of two stages are not necessarily matched bands. See the
[Parquet data-model guide](parquet.md) before combining native grids, and the
[evidence hierarchy](../validation/evidence-hierarchy.md) before interpreting agreement.

---

## Where to go next

- Return to the [Start Here notebook workflow](notebook-example.md) if you need to rerun the pipeline.
- Review [Outputs & file structure](../pipeline/outputs.md) for naming guarantees.
- Read the [Concepts](../concepts/why-calibration.md) page for the scientific rationale behind the translation steps.
