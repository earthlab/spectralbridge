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
* Fitting percentile edges use only source-footprint and angular-valid pixels
  with valid red/NIR observations, using the same 665/865 nm selections as NDVI.
  Transparent background and declared NoData/quality exclusions cannot set the
  stratum boundaries.

## BRDF fitting and application

The [BRDF mathematical validation report](reports/BRDF_MATHEMATICAL_VALIDATION.md)
independently verifies the reciprocal dense and sparse equations, angular domain
and numerical behavior. Kernel helpers now broadcast scalar/vector/raster inputs
and return float64; invalid polar geometry returns NaN. Ambiguous nonreciprocal
names `li_dense` and `li_sparse` are rejected; use `LiDenseR` or
`LiSparseReciprocal` explicitly. BRDF model JSON and completed correction headers
record `ross-li-reciprocal-f64-v1`. Unversioned or incompatible coefficients must
be refitted in a fresh output directory; existing products are not regenerated.
This does not change radiometry, fitting thresholds or crown-parameter defaults.

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
* Storage encodings distinguish raw DN, range-normalized DN, scaled physical
  reflectance, fractional physical reflectance and unknown units. Scalar or
  per-band affine coefficients carry calibration provenance, NoData and declared
  source-quality semantics. A normalized fraction is diagnostic only until
  physical calibration is verified. Conversion preserves finite zeros/negative
  observations; the configurable fitting interval is a separate selection step.
  Declared TIFF alpha and H5 footprint masks survive ingestion and windowing.
  See the [real-data radiometric validation](reports/RADIOMETRIC_SCALING_VALIDATION.md).
* Native-band translation and physical Parquet extraction use this same affine
  contract. Stored-space cross-band convolution requires a common zero-offset
  calibration; convert a validated input to fractional physical units first when
  band-specific scales or offsets would not commute with spectral weighting.
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

New fits also record validation policy
`source-footprint-resolved-predictions-v1`, wavelength identities and the compact
3-by-3 coefficient covariance for each supported band/stratum. Application
rechecks the same positivity, rounding and OLS uncertainty conditions used by
fitting; a small positive but unresolved denominator raises an explicit error,
without identity substitution or factor clipping. Declared source footprints
are enforced independently of the combined cube mask. Declared saturation and
NoData remain distinct from observed zeros. Stable rank and pixel counts are
reported separately; an effective independent sample size is not invented.

Missing angular inputs produce an `UNSUPPORTED` model record with the missing
prerequisite, rather than an uncaught lookup error. Models from an older
validation policy are not reused by fitting/application: use a fresh output
directory and preserve historical artifacts. Approved BRDF library inputs and
completed-product reuse also require the current kernel and validation-policy
header fields; raw products explicitly marked `NOT_REQUESTED` retain their
separate physical-calibration contract. These checks do not change the
Ross/Li equations, physical fitting interval, reference geometry or production
calibration declarations. The
[clean-source Goldhill investigation](dev/goldhill-clean-source-brdf-investigation.md)
records the factorial experiment, actual NEON regression control and remaining
drone prerequisites; it does not certify Goldhill calibration or supplied views.

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

## Opt-in experimental drone viewing geometry

`drone_view_geometry` provides pure nadir-ray, ideal rectangular-footprint,
assignment and kernel-mixture helpers. It is an explicit experiment input utility;
it does not alter drone or NEON defaults, approve radiometry, infer real mosaic
contributors, or replace shared BRDF equations and safeguards. Callers must supply
common projected-metre coordinates and an explicit grid-to-true-north conversion.
Simulated kernel weights are not measured mosaic weights, and one mosaic value
must never be duplicated into multiple directional observations.

The [Goldhill reconstruction experiment](dev/goldhill-viewing-geometry-experiment.md)
contains native experimental products, missing-datum/contributor provenance,
assignment-seam and ecological diagnostics, and an unchanged real NEON control.
Its combined topographic products retain unresolved extremes; numerical model
acceptance does not establish production readiness.

Last updated: 2026-11-04

## Opt-in conditioned drone experiments

The integrated drone reliability investigation adds explicit fitting subsets,
spatial uncertainty groups and a conditioned SCS+C model. The shared equations
and default NEON path remain unchanged. See
[the investigation](dev/drone-integrated-reliability.md) for the source identity,
chunking, uncertainty policy, unsupported-state contract and calibration limits.
Experimental products retain their status through ENVI serialization and cannot
enter the approved spectral library. These are conditional research options,
not new automatic production defaults.
