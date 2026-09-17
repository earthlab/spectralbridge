# Streamlined BRDF + Topographic corrections

This document summarises the updated streamlined correction path so it aligns with
HyTools/FlexBRDF behaviour.

## Topographic correction (SCS+C)

* For each band a regression `rho = a*cos(i) + b` is fit over valid pixels to
  recover the C-parameter `C=b/a`.
* The surface correction applies `(cos(theta_s)*cos(beta) + C)/(cos(i)+C)` to
  the reflectance in unitless space before converting back to NEON scaling;
  a small denominator guard prevents extreme ratios when `cos(i)+C` is nearly
  zero.
* This SCS+C path is now the default; a cosine-ratio fallback remains available
  via the `use_scs_c` flag.

### Topographic modes and defaults

* `apply_topo_correct` supports two modes:
  * Legacy cosine-ratio (`use_scs_c=False`).
  * SCS+C (`use_scs_c=True`) matching HyTools/FlexBRDF behaviour.
* The current default is `use_scs_c=True`, which is a change from older
  releases that defaulted to cosine-ratio. Callers that require the legacy
  behaviour should explicitly pass `use_scs_c=False` (or the equivalent CLI
  flag) to disable SCS+C.

## Implementation notes

The current streamlined NEON correction path applies BRDF/topographic correction
in fixed non-overlapping spatial chunks.

* The correction driver applies in tiled footprints with no halo or feathering.
* ``topo_fit_mode="scene"`` (default) fits SCS+C once over the full flightline
  using streamed sufficient statistics, then applies those ``C`` values in
  full-width row strips. ``_SCENE_APPLY_CHUNK_Y`` defaults high enough that
  apply is typically one full-height strip (unchunked); lower it (e.g. 500)
  if memory is tight on long NEON lines.
* ``topo_fit_mode="tile"`` fits and applies independently inside each
  ``100 x 100`` tile.
* BRDF coefficients are fit once at the scene level, then applied chunk by
  chunk using the local pixel geometry for that tile.
* Ratio / BRDF guards: non-positive SCS+C ratios and non-positive BRDF kernel
  factors fall back to a neutral factor of ``1.0`` instead of ``NaN``. This
  prevents the previous cascade where invalid factors were written as the cube
  ``no_data`` value (``-9999``) across otherwise-valid pixels.

This distinction matters when interpreting artifacts. If a visible seam aligns
with the 100x100 grid, inspect whether `topo_fit_mode="tile"` was used. The
default `topo_fit_mode="scene"` fits topographic correction once over the full
footprint and is the recommended setting for new NEON runs.

## NDVI binning

* NDVI is derived from bands nearest 665 nm and 865 nm after converting to
  unitless reflectance.
* NDVI binning is optional and defaults to off. With the default setting, BRDF
  fitting uses a single scene-wide coefficient row instead of NDVI-stratified
  bins.
* If enabled, pixels are assigned to configurable bins (default bounds
  ~0.05–1.0 over 25 bins with percentile clipping) used for BRDF fitting and
  application.
* The fitted `*_brdf_model.json` stores the realized bin boundaries as
  `ndvi_edges`. When NDVI binning is off, this is `[-1, 1]` for the single
  neutral bin. When binning is on, those values document which NDVI stratum
  each row of `iso`/`vol`/`geo` coefficients belongs to; they are BRDF model
  metadata, not a standalone NDVI output raster.
* When coefficients are missing or bin counts mismatch, neutral coefficients
  are broadcast across all bins to avoid dropping pixels. Pixels with NDVI
  outside the bin range are remapped into the first bin to preserve coverage
  when no explicit coefficients are available.

## BRDF fitting and application

* Per-band, per-bin regressions solve `rho = f_iso + f_vol*K_vol + f_geo*K_geo`.
* Stored reflectance is converted to unitless reflectance before fitting and
  correction via `reflectance_to_unitless_multiplier()`. Both conventions are
  accepted:
  * multiply style (`Scale_Factor=1e-4` → `unitless = DN * 1e-4`)
  * NEON/ENVI divisor style (`Scale_Factor=10000` → `unitless = DN / 10000`)
* Treating NEON `10000` as a multiplier incorrectly pushes nearly all pixels
  outside the BRDF `rho_max` gate and collapses `iso`/`vol`/`geo` to zero.
* The streamlined BRDF model now persists the kernel settings used during fit
  and apply, including the volume kernel, geometric kernel, geometric
  parameters (`b/r`, `h/b`), and `solar_zn_type`.
* The shared correction helpers keep streamlined-compatible defaults, while the
  NEON and drone correction pipelines explicitly request the historical
  HyTools-style settings: `RossThick` volume, `LiDenseR` geometric,
  `b/r = 10`, `h/b = 2`, and `solar_zn_type = scene`.
* BRDF normalization uses the FlexBRDF ratio `R_ref/R_pix`, evaluating kernels
  at both pixel geometry and a configurable reference geometry.

## Scaling and thresholds

* Modeling occurs in unitless reflectance; scale factors are applied only at the
  edges. Optional clamps guard obviously invalid reflectance values.
* All masks propagate cube no-data and NDVI bin assignments; non-finite outputs
  resolve to the cube `no_data` value.
