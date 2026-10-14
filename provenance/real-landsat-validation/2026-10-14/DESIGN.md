# Independent real-Landsat validation: first flight-line pilot

Written before reflectance comparisons. Observational validation, not tuning.
The first unit is the one complete real NEON H5 already available locally:
NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance. Its 1-m raster is
1115 x 5351 x 426, UTM 13N, with explicit Scale_Factor=10000 and an atmospheric
surface-reflectance description. BRDF Correction=False requires the canonical
pipeline before making synthetic OLI. The other local H5 is a one-pixel fixture;
it is not real validation evidence. Sparse polygon extracts cannot substitute
for complete image support. This is one full flight, not a selected good pixel
patch or pooled sites/years.

## Preparation and provenance

Use existing ENVI export, scene-wide SCS+C/BRDF and Gaussian OLI convolution
functions, canonical naming, existing brightness percentages and no new fitted
cross-sensor coefficients. Bound correction application to 32-row strips without
changing scene-wide fits. Preserve raw source, correction parameters, synthetic
undarkened and adjusted rasters. Do not materialize full pixel Parquets. Explicitly
key the declared seven response centers in convolution so new wavelength headers
are numeric rather than relying on exporter fallback or guessed band order.

## Scene search before comparison

Reuse Planetary Computer Collection `landsat-c2-l2`, public Landsat 8/9 OLI Level-2
surface reflectance. Search the full acquisition calendar day +/-16 days. Record
all candidates including incompatible ETM+ scenes and the nested same-date,
<=1, <=3, <=7 and <=16-day windows. No scene is selected on reflectance agreement.
First rank admissible scenes by absolute time distance, then decreasing QA-clear
NEON overlap, sensor match, spatial coverage and quality/tier/cloud metadata.
Reject absent required seven SR assets, absent QA_PIXEL/QA_RADSAT, wrong collection
or processing level, insufficient coverage or <100 common eligible pixels.
Evaluate QA of all compatible candidates; retrieve SR only for the selected one.
Do not mosaic dates. Keep failed candidates and exact reasons.

NEON H5 Acquisition_Time is `2021-09-15, 191530 [Computer Time in sec]`, consistent
with its raw filename. UTC is the NEON general timestamp convention but this
legacy field has no timezone suffix. Record the original string, the UTC-basis
interpretation and its caveat; never fabricate a precise verified timezone.
Same-calendar-day flags remain distinct from signed elapsed hours. Primary
selection is robust to ordinary UTC/local interpretation for the available
OLI candidates, but all reported hours carry that timestamp caveat.

## QA and physical units

Reject QA_PIXEL fill, dilated cloud, high-confidence cirrus/cloud, shadow and
snow (bits 0-5). Reject QA_RADSAT saturation in bands 1-7 and terrain occlusion
(bit 11). Retain water with a diagnostic label. Report category masks, saturation
and invalid counts. Decode Collection 2 DN in official range 1-65455 as
DN*0.0000275-0.2; reject fill 0, do not clip negative or >1 decoded reflectance.
Require matching asset grids and documented seven physical bands. NEON stored
values are divided by the explicit inherited 10000 metadata, not inferred from
observed numeric magnitudes. Missing scale/coordinates refuse validation.

## Spatial support and pairing

Use the observed Landsat pixel grid as the authority. Compute area-weighted
NEON channel means and within-footprint variance, contributing-pixel count,
geometric coverage, valid fraction conditional on footprint and valid area /
full Landsat pixel area. Require >=90% full-pixel valid NEON coverage and identical
QA/pixel support for both synthetic variants. Do not upsample Landsat. Spatial
weights reflect partial cells, including raster-edge cells; normalization over
only overlapping source cells is not accepted as a coverage measure.

## Statistics, uncertainty and sensitivities

Set x=actual Landsat SR, y=aggregated synthetic SR; residual=y-x everywhere.
Primary agreement is bias, median bias, MAE, RMSE and empirical residual spread.
Report Pearson/Spearman and r-squared only as association; also identity-line
R-squared, which can be negative. Normalize RMSE by reference IQR only when
nondegenerate and state its denominator. Deming lambda=1 is a descriptive
errors-in-both-axes line, with lambda=.25/4 sensitivity because relative sensor
error variance is unknown. Do not calibrate the validation data or change gains.

Use 499 bootstrap replicates of fixed 300-m spatial blocks for conditional
within-flight uncertainty; no iid-pixel p-values. Report number of spatial blocks
and that one flight cannot estimate cross-flight/site uncertainty. Bland-Altman
plots, mean +/-1.96 SD descriptive limits and empirical 2.5/97.5 percentiles;
brightness/absolute-error association without iid significance tests. Compute
seven-band spectral angles and magnitude errors together. Do not use SSIM as
primary; fixed-stretch RGB similarity is display context, not reflectance proof.

Original alignment is primary. Evaluate the nine fixed source shifts dx/dy in
{-30,0,30} m using identical common cells across shifts; report the entire grid,
never silently apply its best-performing offset. Homogeneity uses preregistered
within-flight heterogeneity tertiles (low/high source within-cell RMS SD), not
residual-based inclusion. High coverage >=99% and >=90-m conservative clear-QA
proximity sensitivities remain visible. Gold subset requires same UTC calendar
date, primary coverage and clear-QA proximity; report absence explicitly.

## Outputs and scope

Generate paired RGB with shared fixed [0,0.4] unitless stretch, residual and QA
maps, seven band scatterplots with identity/Deming lines, representative low,
median/high/max-error seven-channel spectra, angle maps/distribution, failure
gallery and a paper summary, plus compact pixel/flight/band diagnostics. No
outliers are removed for display metrics. Save stable Landsat row/column IDs,
coordinates, metadata and item/product IDs. Freeze source/config/output hashes.
Run targeted and full offline tests plus a small cached-real-window integration
check. Do not claim cross-site/year replication, held-out fitted calibration,
classification or a universal adequacy threshold from this one pilot.
