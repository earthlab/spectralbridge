# Dependency Review

Review date: 2026-06-03

This note records the current dependency posture of SpectralBridge with a focus
on `ray`, `geopandas`, and `rasterio`, plus whether moving them into different
extras would be safe.

## Reviewed sources

- `pyproject.toml`
- `src/spectralbridge/_optional.py`
- `src/spectralbridge/_ray_utils.py`
- `src/spectralbridge/pipelines/pipeline.py`
- `src/spectralbridge/pipelines/drone.py`
- `src/spectralbridge/polygons.py`
- `src/spectralbridge/parquet_export.py`
- `src/spectralbridge/polygon_extraction.py`
- `docs/env.md`

## Current dependency layout

### Required runtime dependencies

The main package currently declares all of the following as core dependencies:

- `numpy`
- `scipy`
- `pandas`
- `pyarrow`
- `pyproj`
- `h5py`
- `requests`
- `tqdm`
- `matplotlib`
- `rasterio`
- `shapely`
- `geopandas`
- `spectral`
- `ray[default]`
- `duckdb`

### Optional dependency groups

- `tests`
- `full`
- `docs`
- `dev`

The current `full` extra only repeats `spectral` and `ray[default]`, both of
which are already required in the base install.

## Findings

### 1. `ray` is still part of the intended standard runtime

`ray` is imported lazily through `src/spectralbridge/_optional.py` and
`src/spectralbridge/_ray_utils.py`, but the package treats Ray as the default
parallel engine and the contributor docs already describe it as required.

Implication:

- moving Ray out of core dependencies today would change the install contract
  and likely break documented/default behavior

Recommendation:

- keep `ray[default]` in required dependencies for now
- if a future “lite install” is desired, treat that as a deliberate packaging
  redesign rather than a small metadata tweak

### 2. `rasterio` is deeply embedded in core workflows

`rasterio` is not just for optional plotting or edge-case utilities. It is used
in:

- ENVI/parquet export
- polygon extraction
- polygon overlap diagnostics
- drone spatial diagnostics
- masking helpers

Implication:

- making `rasterio` optional in packaging would break major advertised
  workflows, not just add-on features

Recommendation:

- keep `rasterio` in required dependencies

### 3. `geopandas` is required for a meaningful portion of polygon/drone tooling

`geopandas` is used in:

- polygon index creation
- polygon overlap filtering
- overlay visualization
- drone polygon workflows
- QA overlay support

Implication:

- it is optional only in the narrow sense that some workflows can run without
  polygons, but the project currently ships these capabilities as first-class
  features

Recommendation:

- keep `geopandas` in required dependencies unless the project intentionally
  introduces separate install profiles and docs for polygon-free usage

### 4. Optional import helpers currently describe a “full” extra that is not the real install story

`src/spectralbridge/_optional.py` still raises messages referring to the
standard environment and a conceptual `"full"` extra, but the actual package
metadata already installs `ray`, `rasterio`, and `geopandas` by default.

Implication:

- the import helpers are survivable, but they reflect an older packaging idea
  more than the current dependency contract

Recommendation:

- do not change this in the same pass unless the package’s extras strategy is
  being redesigned; document the mismatch first

### 5. `docs/env.md` had drifted behind the real dependency set

Before this review, `docs/env.md` described `gdal` and `xarray` as core libs
but did not reflect the actual package dependencies in `pyproject.toml`.

This was updated in the current pass to reflect the real runtime stack and to
clarify that `rioxarray` / `xarray` are useful optional notebook companions,
not direct package requirements.

### 6. The current `full` extra is redundant

Because `spectral` and `ray[default]` already live in base dependencies, the
`full` extra does not currently provide additional installation value.

Recommendation:

- avoid changing extras automatically in this pass
- revisit extras design only as part of a broader packaging/install strategy

## Recommendation summary

Current safest posture:

1. keep `ray[default]` required
2. keep `rasterio` required
3. keep `geopandas` required
4. treat extras redesign as a separate packaging project, not a release-hygiene tweak

## Follow-up

If maintainers want a lighter install profile later, it should be introduced as
a deliberate compatibility project with:

- clear “core vs full” workflow boundaries
- updated optional-import error messages
- revised docs for installation modes
- CI coverage for both install profiles

No dependency declarations were changed automatically in this review.
