# BRDF and topographic correction methods

These shared methods reduce directional and terrain-related variation only when
their input and model assumptions are supported. Start with
[Choosing Radiometric, Topographic, and BRDF Corrections](concepts/correction-eligibility.md).
Shared kernels do not establish complete equivalence to a FlexBRDF workflow.

The Ross/Li kernel helpers and parts of the BRDF path have documented HyTools
implementation lineage. SCS+C is treated separately as a shared published
method. See the repository's
[HyTools provenance audit](https://github.com/earthlab/spectralbridge/blob/main/HYTOOLS_PROVENANCE.md)
for the fixed revisions and component-level classifications.

## Topographic correction (SCS+C)

The SCS+C equations follow Soenen, Peddle, and Coburn (2005),
DOI [`10.1109/TGRS.2005.852480`](https://doi.org/10.1109/TGRS.2005.852480).

* For each band a regression `rho = a*cos(i) + b` is fit over valid pixels to
  recover the C-parameter `C=b/a`.
* The surface correction applies `(cos(theta_s)*cos(beta) + C)/(cos(i)+C)` to
  the reflectance in unitless space before converting back to NEON scaling;
  a small denominator guard handles near-zero values, but does **not** guarantee
  stable or physically justified gains just above the guard.
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
* SCS+C retains its established ratio/denominator guards and ancillary masks.
  A neutral fallback is not physical validation.
* Current BRDF application requires a validated saved model and rejects
  nonpositive/nonfinite predictions; the historical identity-factor fallback
  does not authorize current BRDF products.

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
* Populated unsupported strata, missing coefficients and out-of-stratum
  application cannot be rescued with neutral coefficients or bin-zero remapping.
  Bands/strata without finite source observations are `NOT_APPLICABLE`, retain
  nodata and have null coefficients.

## BRDF fitting and application

The Ross/Li kernel family is described by Wanner, Li, and Strahler (1995),
DOI [`10.1029/95JD02371`](https://doi.org/10.1029/95JD02371), and Lucht, Schaaf,
and Strahler (2000), DOI
[`10.1109/36.841980`](https://doi.org/10.1109/36.841980). SpectralBridge's
kernel implementation was adapted from HyTools; citing the scientific methods
does not replace that software attribution.

* Per-band, per-bin regressions solve `rho = f_iso + f_vol*K_vol + f_geo*K_geo`.
* Calculations enter physical units once through
  `physical = scale * stored + offset`, and invert that mapping on writing
  storage-scale rasters. NEON's documented H5 `Scale_Factor` is a divisor; its
  multiplier is the reciprocal. Drone calibration needs explicit provenance.
  The October 26 raw-attribute multiplication rollback is historical behavior
  superseded by the verified October 30 shared radiometry contract.
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

* Modeling occurs in physical unitless reflectance through the explicit affine
  boundary. The BRDF fitting range (default 0–2) selects eligible observations;
  it does not clip scientific outputs. Finite negative corrected values are not
  automatically nodata in library visualization.
* All masks propagate cube no-data and NDVI bin assignments; non-finite outputs
  resolve to the cube `no_data` value.

## What the models estimate and what makes a fit eligible

RossThick represents directional scattering in a vegetation volume; LiDenseR
represents geometric effects such as mutual shadowing. Together with an
isotropic baseline, their three coefficients describe reflectance as a function
of illumination and view. Normalization multiplies by the predicted reference
signal divided by the predicted observed signal. The reference is a processing
choice, not ground truth.

The shared fitter requires authoritative physical radiometry, at least four
eligible observations per populated band/stratum, rank three and condition
number no greater than `1/sqrt(float32 epsilon)` (about 2896). Predictions at
observed and reference geometry must be positive and resolved above rounding and
approximately 95% coefficient-uncertainty bounds. The model records support,
exclusions, singular values, uncertainty, reference extrapolation and factor
summaries. `VALID` is computational eligibility; empirical accuracy still needs
independent targets, angles and application-domain evidence. `UNSUPPORTED` or
`INVALID` models supply no usable coefficients. The fit uses the recorded
scene solar mean in application, so strip size does not change that geometry.
Combined models fit the same scene-topographic observations they later correct.

| Investigated drone mosaic | Angular design rank | Supported bands |
| --- | --- | --- |
| Gordon | 1 / 3 | 0 / 10 |
| Goldhill | 1 / 3 | 0 / 10 |
| Ruby | 1 / 3 | 0 / 10 |

These files contain assigned zero views. With scene solar zenith the three
kernel columns cannot provide independent information. This rules out this fit
on these mosaics; it does not rule out drone BRDF generally. NEON directional
observations can provide suitable geometry, but each product/revision, calibration
and design must be checked. Already BRDF/topographically corrected NEON products
must not be treated as uncorrected directional inputs.

### Goldhill: a historical downstream failure

Stage-isolation replay finds the extreme red streak only when historical BRDF is
applied. The defective historical kernel, very small eligible red fitting
population and unsupported model led to a prediction crossing zero. Its old
identity guard switched to enormous positive ratios, with maximum red gain
11,742,750. Reversing numerical normalization preserved that discontinuity;
scaling cannot supply missing angular information. The repaired kernels and
current validity gates reject the fit rather than approve an identity fallback.
See the [labelled visual case study](validation/drone-findings.md#3-brdf-identifiability-and-the-goldhill-artifact)
and [controlled experiment](dev/drone-radiometric-recovery-experiment.md).
Smaller upstream seamlines remain a separate hypothesis.

## SCS+C stability and scientific limits

SCS+C uses a per-band illumination regression to estimate `C`, then adjusts for
slope and solar incidence. It assumes credible physical inputs, terrain and
illumination, an appropriate regression population and a suitable surface model.
Units, grid/true-North conventions, shadowing, terrain resolution and bare-earth
versus canopy surface all matter.

| Flight | Maximum source-DN diagnostic gain | Source-valid coverage loss |
| --- | ---: | ---: |
| Gordon | 528× | 4.08% |
| Goldhill | 357× | 5.49% |
| Ruby | 373× | 1.49% |

These isolated numerical diagnostics are not calibrated reflectance results.
Exact replay shows denominator cancellation just above 0.001, despite modest
condition numbers (11–15) for the two-term topographic fits. Some extreme cells
have back-facing illumination. This does not prove a unit error; actual terrain
and acquisition provenance remain unresolved. Coverage loss is from existing
ancillary/illumination validity, not inverse normalization.

Mathematical execution, numerical stability, physical justification and
independent scientific validation are four different tests. The polygon
assessment found mixed consistency and separability effects. Topographic
correction is **not approved for these three flights**. Review C uncertainty,
denominators, gains, masks and held-out biological/invariant targets; an arbitrary
gain cap is not a substitute. See the [latest mechanism audit](dev/photogrammetry-metadata-investigation.md)
and [polygon study](dev/drone-brdf-identifiability-investigation.md).

Last updated: 2026-11-02
