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

* The correction driver currently walks the scene in `100 x 100` tiles.
* Tile bounds are simple raster slices with no halo, overlap, feathering, or
  rolling-window context.
* Topographic correction is fit per chunk. In practice that means the SCS+C
  regression `rho = a*cos(i) + b` and its derived `C = b/a` term are solved
  independently inside each tile for each band.
* BRDF coefficients are fit once at the scene level, then applied chunk by
  chunk using the local pixel geometry for that tile.

This distinction matters when interpreting artifacts. If a visible seam aligns
with the chunk grid, the present implementation makes chunk-local topographic
fitting the first place to investigate.

## NDVI binning

* NDVI is derived from bands nearest 665 nm and 865 nm after converting to
  unitless reflectance.
* Pixels are assigned to configurable bins (defaults ~0.05–1.0 over 25 bins
  with percentile clipping) used for BRDF fitting and application.
* The fitted `*_brdf_model.json` stores the realized bin boundaries as
  `ndvi_edges`. Those values document which NDVI stratum each row of
  `iso`/`vol`/`geo` coefficients belongs to; they are BRDF model metadata, not
  a standalone NDVI output raster.
* When coefficients are missing or bin counts mismatch, neutral coefficients
  are broadcast across all bins to avoid dropping pixels. Pixels with NDVI
  outside the bin range are remapped into the first bin to preserve coverage
  when no explicit coefficients are available.

## BRDF fitting and application

* Per-band, per-bin regressions solve `rho = f_iso + f_vol*K_vol + f_geo*K_geo`.
* The streamlined BRDF model now persists the kernel settings used during fit
  and apply, including the volume kernel, geometric kernel, geometric
  parameters (`b/r`, `h/b`), and `solar_zn_type`.
* Current defaults follow the repo's historical HyTools-backed settings:
  `RossThick` volume, `LiDenseR` geometric, `b/r = 10`, `h/b = 2`, and
  `solar_zn_type = scene`.
* BRDF normalization uses the FlexBRDF ratio `R_ref/R_pix`, evaluating kernels
  at both pixel geometry and a configurable reference geometry.

## Scaling and thresholds

* Modeling occurs in unitless reflectance; scale factors are applied only at the
  edges. Optional clamps guard obviously invalid reflectance values.
* All masks propagate cube no-data and NDVI bin assignments; non-finite outputs
  resolve to the cube `no_data` value.
