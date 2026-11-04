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
