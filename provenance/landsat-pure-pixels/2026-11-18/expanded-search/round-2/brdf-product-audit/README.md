# Landsat BRDF product audit

Checked 19 November 2026. **The current Figure 4 Landsat curves and test results
use Collection 2 Level-2 surface reflectance, not BRDF-normalized Landsat.**

## What is actually in use

Panel A reads the local Niwot scene
`LC09_L2SP_034032_20230820_20230822_02_T1_SR_B1` through B7, screens QA and applies
Collection 2 scaling. Panel B's 481-cell cohort uses 13 Landsat 8/9 scenes from
the Planetary Computer `landsat-c2-l2` collection. The scene inventory is retained
here. `landsat_seasonal_archive.reflectance()` reads coastal/blue/green/red/NIR/
SWIR assets and applies `scale_landsat_sr()`; no BRDF c-factor or angular
normalization is applied. The plotting division by B1–B5 sum is a spectral
normalization, not BRDF correction. Atmospheric correction and LaSRC's assumed
zero view angle do not make Collection 2 SR an NBAR product.

No HLS/NBAR Landsat product was found in the searched local archive/artifact/
provenance filenames. This does not assert the absence of products outside those
locations. The current data loaders unambiguously select the unnormalized SR.

## Which public product supplies BRDF normalization

| Product | Landsat-derived | BRDF/nadir normalization | Appropriate role |
| --- | --- | --- | --- |
| USGS Landsat Collection 2 Level-2 SR | Yes | No separate NBAR adjustment | Current baseline |
| NASA HLS L30 v2 (HLSL30.002) | Yes, Landsat 8/9 | Yes, supported reflectance bands B1–B7 | BRDF-normalized Landsat candidate |
| NASA HLS S30 v2 | No, Sentinel-2 | Yes | Separate Sentinel-derived comparator |

NASA's HLS product guide Table 2 identifies L30 as BRDF-adjusted except B09;
B01–B07 are present in the exact Niwot granule metadata. HLS L30 retains OLI
bandpasses as its reference. It should not be relabelled as exclusively OLI-2.
The BRDF algorithm is the global-coefficient c-factor approach described by NASA,
normalizing to nadir view and making a small solar-angle adjustment based on the
predicted Landsat/Sentinel overpass geometry. It is not an identical correction
to a flight-specific SpectralBridge fit or a guarantee of matched illumination.
The current package BRDFReference defaults use a 45-degree solar zenith and nadir
view; the production kernel config is RossThick/LiDenseR. Actual historical AOP
correction JSON must be inspected before claiming its geometry matches HLS.
HLS BRDF normalization also does not establish equivalent topographic correction.

## Exact Niwot-date candidate verified

NASA CMR returned one L30 granule covering (-105.58,40.05) on 20 August 2023:
`HLS.L30.T13TDE.2023232T174317.v2.0`, acquisition start
2023-08-20T17:43:17.608Z, platform Landsat 9. Public STAC metadata confirms B01–B07,
Fmask and angle assets, EPSG32613, 30 m resolution, and a 3660x3660 MGRS tile.
This verifies product availability and identity, not local-pixel QA acceptance.
The CMR tile-level cloud value is 29%; local Fmask still needs evaluation.
Public metadata were retrieved; reflectance raster assets were not downloaded.

## Why the old purity counts cannot simply be reused

The local native Niwot transform is [30,0,317085,0,-30,4583115]; HLS is
[30,0,399960,0,-30,4500000]. The lattice phase differs by 15 m in both axes.
The HLS guide section 4.3 confirms cubic-convolution resampling of Landsat
reflectance into the MGRS grid. Each output pixel can incorporate source support
beyond its displayed square; nominal polygon coverage alone may overstate
spectral purity. The original 481 native Landsat cells are not 481 unchanged HLS
observations. Recompute footprint cover, conservative source-kernel support,
Fmask/aerosol screening, dated reference support and spatial group identities
before rerunning the tests. Keep C2 SR and HLS results as paired product-specific
analyses rather than replacing values under the old labels.

## Sources

- https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance
- https://hls.gsfc.nasa.gov/products-description/
- https://hls.gsfc.nasa.gov/algorithms/brdf-adjustment/
- https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf
- https://doi.org/10.5067/HLS/HLSL30.002

Saved metadata, descriptions, exact code/document hashes and grid comparison are
in this folder. This audit changes no spectra, labels, figure values or tests.
