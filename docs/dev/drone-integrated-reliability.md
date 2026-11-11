# Integrated drone reliability investigation

The November 4, 2026 Goldhill investigation implements opt-in spatial fitting
controls and uncertainty-resolved SCS+C. It produces seven experimental native
GeoTIFFs. Both topographic and BRDF correction remain active in combined products.

The complete evidence, editable scientific report, figures, test verification and
reproduction scripts are under
`provenance/drone-integrated-reliability/2026-11-04/` in the repository.

## Package capabilities

`fit_and_save_brdf_model()` accepts `fitting_mask`, `fitting_provenance` and
`uncertainty_groups`. Training masks affect estimation, not the application
footprint. Integer groups define the conditional cluster sandwich covariance;
they do not establish independent physical observations. Masks, group identity
and provenance enter restart signatures. Unsupported models remain rejected.

`fit_conditioned_scs_c()` in `spectralbridge.topographic` requires an explicit
`SCSCPolicy` and integer uncertainty groups. It fits per-band physical values,
records spatial covariance and a bounded Fieller interval for C, and binds the
model to source identity, radiometry, wavelength order and policy. Source cubes
are immutable during fitting and application; identity caching assumes that
contract. Source hashing requires a bounded scan of the already loaded cube.
Fitting holds one band's eligible regression arrays at a time; it is not a new
out-of-core reader. Native experiments use 128-row application chunks.

`apply_conditioned_scs_c()` returns values, factors and status: 0 missing/invalid,
1 unsupported, 2 corrected. The complete C interval must preserve a positive
numerator and a denominator above the explicit numerical resolution floor.
Application is limited to fitted incidence support, with analytic flat-terrain
handling. Unsupported values become NoData; they are never identity corrections.
There is no correction-factor cap. The scalar SCS+C equation is unchanged.

`apply_drone_corrections()` accepts the conditioned model and optional BRDF
sampling arguments. These options are explicit and do not change the default
NEON path or automatically select a drone production policy. Experimental status
survives ENVI writing and blocks approved spectral-library extraction.

## Results and interpretation

The native 717 nm combined maximum changes from 63.51085 to 1.78036, but on the
shared all-ten-band support it changes from 0.65503 to 0.68932. The large native
reduction mainly reflects explicit illumination support. Joint support is
6,613,717 pixels. Original polygon identities and membership definitions are
preserved; the paired integrated evaluation uses 142,637 common memberships
across 157 identities. It shows no decisive balanced-accuracy gain.

Twenty-seven sampled spatial controls expose coefficient sensitivity and three
unsupported subsets. Displacing the vegetation signal 25 m gives R-squared
0.1144 versus 0.1049 unshifted, warning against physical interpretation of a
global spatial regression. Class-specific fits are diagnostic only. Raw-defined
homogeneity is fixed before ecological evaluation. Training excludes researcher
polygons plus 20 iterations of Manhattan dilation (2 m along the axes, not a
Euclidean-radius buffer).

The experimental DN/32768 physical interpretation, true source-image
contributors, pose conventions and vertical datum remain unverified. An isolated
research adapter permits conditional experiments without weakening production
calibration gates. No product is scientifically approved. The smallest next
retrieval is the existing four-position, 40-band-photo subset plus pose/sensor
bindings, applied calibration/export settings and contributor/seam metadata.

## Three-site continuation, 5 November 2026

The supplied Gordon, Goldhill and Ruby camera CSVs now permit a common conditional
rerun using the existing isolated Goldhill boundary, shared correction driver,
center-weighted candidate-ray kernels and conditioned SCS+C. Gordon and Goldhill
produce all three experimental correction branches; Ruby produces topography but
its BRDF and combined models fail unchanged prediction/uncertainty checks. Ruby's
matched photo tags also support15August rather than the bundled manifest16August;
the new run uses explicit photo-supported scene times with UTC still conditional.
The shared field manifest and source CSVs are not edited by this experiment.

See the [new report and evidence](https://github.com/earthlab/spectralbridge/blob/main/DRONE_CAMERA_RERUN_REPORT.md).
It retains native and shared-support extrema, including large conditional Goldhill
red gains; it does not declare the products physically calibrated or artifact-free.
Earlier Goldhill results above remain the preserved dated investigation, not
numbers silently replaced with this continuation's different support/time inputs.

## Three-site stability diagnosis, 5 November 2026

The [stability report](https://github.com/earthlab/spectralbridge/blob/main/DRONE_CORRECTION_STABILITY_REPORT.md)
traces the remaining tails and Ruby rejection without changing acceptance rules.
`cluster_covariance()` now computes the same finite-cluster sandwich estimator in
an orthonormal QR basis instead of explicitly inverting normal equations. It
rejects deficient designs rather than providing a pseudoinverse fallback. This
requires one temporary thin-Q array for one fitted band's eligible observations
(about 160 MB for 6.7 million rows and three columns); the current loaded-cube fit
is not an out-of-core estimator. Raster comparisons and verification remain
bounded in 128-row windows, and no new pixel-scale Parquet cache is introduced.

BRDF fit records now separate `reference_prediction_resolved`,
`reference_prediction_lower_margin`, `unresolved_observed_geometry_predictions`
and `rejection_components`. The existing `unsupported_application_predictions`
includes whole-domain rejection when the reference fails; it should not be read
as a count of locally unsupported observed geometries. The new fields explain
that distinction without changing the shared prediction check or cache policy.
Ruby's rejected fits have resolved observed-angle predictions and an unresolved
reference. Global rank alone does not support extrapolation to that reference.

All seven accepted experimental native products are exactly unchanged after the
numerical update, and Ruby remains unsupported for BRDF. Negative empirical C
values place the largest topographic gains near a ratio pole. Their broad
transformed C intervals remain visible in the report; boundedness and positivity
are not claims of precise or physically validated correction. No gain clipping,
identity fallback, new site-specific fitting method or calibration promotion was
introduced. Both correction components remain required for the intended workflow.


## P183 Metashape recovery (6 November 2026)

The read-only recovery investigation found Goldhill camera-table/mosaic alignment mixing, recovered estimated camera orientations and retained primary assignments, and established strong project/export evidence for DN/32768 encoding for Ruby and Goldhill. Primary assignments do not recover blending weights. Repeated-photo fits improve local angular information but do not yet approve Ruby's normalization or resolve topographic denominator tails. Source NIR metadata says 842 nm; existing production metadata was not silently changed.

The repository-root `METASHAPE_RECOVERY_REPORT.md` and `provenance/metashape-recovery/2026-11-05/` contain the report, portable tables, retrieval manifests and experimental tools. Gordon's new project remains unavailable. Preserve explicit source project/chunk binding and separate absolute viewing surfaces from ground terrain; no production acceptance gate is relaxed.


## P184 Ruby original-image experiment (6 November 2026)

The isolated workflow in `provenance/ruby-correction-recovery-2026-11-06/` now provides fixed-grid repeated-feature extraction, explicit-scale immutable input preparation, calibrated ECEF ray/DEM intersection, target-aware BRDF candidates, matched training-only SCS+C/BRDF evaluation and held-out diagnostics. The opt-in helpers in `spectralbridge.drone_original` do not change production defaults. The experiment's README documents execution, checkpoints and the gated licensed reconstruction interface. Its REPORT.md and status files record current scientific limits.

A P183 timestamp diagnostic assumed nanoseconds while pandas parsed microseconds. P184 uses calendar UTC minute labels and tests both resolutions; the prior blanket claim that every target lacked enough minute groups is superseded by `prior_temporal_group_recheck.json`. This corrects the uncertainty diagnostic without approving the original correction.

A new 10 cm input uses the verified source-specific 842 nm NIR label and explicit 0.0001 scale. Original-photo target-aware BRDF shows mixed held-out improvement; ground-DTM topographic instability remains. No real corrected source images or corrected Ruby orthomosaic were generated, and the original projects/products remain unchanged.


## P185 Ruby topographic recovery (6 November 2026)

The source-preserving experiment in `provenance/ruby-topographic-recovery-2026-11-06/` audits the negative-C baseline, compares explicit terrain scales/shadows/field-context populations, tests synthetic identifiability and SCS+C/C/Minnaert alternatives, and evaluates matched original-photo and full-frame support. `spectralbridge.drone_topography` contains opt-in research helpers; production NEON/drone defaults remain unchanged.

The mathematical audit reproduces red C near -0.17350 and finds no shared incidence/formula defect. It corrects a P184 experimental absolute-denominator check by requiring positive numerator/denominator intervals, consistent with the production uncertainty-aware path. Negative C itself remains allowed on a supported positive domain. Screening and a declared 3m ground-terrain scale yield approximately 76% numerical red support without gain caps, but paired matched means still show degradation and full ten-band SCS+C original-photo support remains incomplete. Numerical coverage is not physical approval.

The report, decision, twelve reproducible figures, source hashes, restart checkpoints and all-band full-frame support summaries are recorded in that directory. Diagnostic factor TIFFs are not corrected reflectance. Unsupported shadows/geometry/model domains remain missing; no corrected orthomosaic or production upload is claimed.
