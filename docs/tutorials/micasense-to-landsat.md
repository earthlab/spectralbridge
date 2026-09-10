---
search:
  exclude: true
---

# Tutorial: MicaSense Local Drone Workflow

!!! note "Canonical learning path"
    This older tutorial is retained for stable links. Use [Process drone
    imagery](../vignettes/drone-processing.md) for the canonical module
    vignette.

This tutorial shows the production path for local drone or MicaSense-style
inputs. The workflow preserves drone-native provenance, discovers HDF5 files
or reflectance TIFF packages recursively, converts TIFF sources into the
working HDF5 contract when needed, applies the established corrections, and
can translate corrected MicaSense into separately named Landsat-like products
using reviewed bulk coefficients.

There is no dedicated `spectralbridge-micasense-to-landsat` CLI today. Use the
Python API shown here.

## Inputs

Prepare a folder containing local drone exports. The pipeline can start from
either existing HDF5 files or reflectance TIFF packages.

Example HDF5 layout:

```text
drone_h5_exports/
  SPR1-06-28-23 ExportPackage/
    *.h5
  SPR2-06-28-23 ExportPackage/
    *.h5
```

Example TIFF layout:

```text
drone_tiff_exports/
  SPR1-06-28-23 ExportPackage/
    aligned_orthomosaic.tif
    slope.tif
    aspect.tif
    sensor_zenith.tif
    sensor_azimuth.tif
```

If you want polygon-level tables, also prepare a polygon layer supported by
GeoPandas, such as GeoPackage or GeoJSON.

## Input contract

For existing HDF5 inputs, SpectralBridge treats the local HDF5 export as the
authoritative drone input. Reflectance and ancillary rasters are expected to
already share the same spatial orientation and `(lines, columns)` footprint.

For TIFF-backed inputs, SpectralBridge now creates the per-flight
`__working.h5` file itself before continuing through the existing drone
workflow. The TIFF bridge is intentionally strict:

- reflectance TIFFs must be multiband rasters
- ancillary TIFFs must already match the reflectance raster shape, transform,
  and CRS
- TIFF packages are expected to provide aligned sidecars for:
  - `slope`
  - `aspect`
  - `sensor_zenith` or `view_zenith`
  - `sensor_azimuth` or `view_azimuth`
- solar geometry can come from:
  - aligned `solar_zenith` / `solar_azimuth` TIFFs,
  - scalar `tiff_solar_zenith_deg` / `tiff_solar_azimuth_deg` arguments passed
    to `run_drone_pipeline`, or
  - a flight manifest CSV passed as `drone_manifest_path`

SpectralBridge includes the Macrosystems drone field manifest as bundled package
data. When `drone_manifest_path` is omitted, `run_drone_pipeline()` uses that
bundled manifest by default. Pass `drone_manifest_path` only when you want to
override the bundled file with a different campaign manifest.

If both an HDF5 file and a reflectance TIFF resolve to the same derived flight
stem within one package, the existing HDF5 input takes precedence.

By default, TIFF-backed conversion uses the 10-band wavelength/FWHM vectors
from the Erick notebook workflow when the reflectance raster has 10 bands. For
other band counts, pass explicit `tiff_wavelengths_nm` and `tiff_fwhm_nm`
values.

## Run the drone pipeline

```python
from spectralbridge import run_drone_pipeline

results = run_drone_pipeline(
    input_h5_dir="drone_inputs",
    polygon_path="Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg",
    output_dir="drone_outputs",
    apply_topo=True,
    apply_brdf=True,
    use_ndvi_brdf_bins=False,
    apply_brightness_adjustment=False,
    apply_translation=True,
    translation_coefficients=(
        "bulk_analysis/coefficients/candidate_translation_coefficients.parquet"
    ),
    translation_weighting="site_balanced",
)
```

Set `polygon_path=None` when you only need ENVI and QA products.

The bundled manifest is used only when explicit solar rasters or scalar solar
angles are not supplied. Custom manifest CSVs must include:

- `Plot`
- `Day of data collection`
- `Mean Time of data collection (24 hr clock)`

Derived flight stems such as `AOP_GOLDHILL_20230814` match manifest rows such
as `AOP_GOLDHILL`. SpectralBridge uses the matched acquisition datetime plus
the reflectance TIFF CRS/transform to compute per-pixel `Solar_Zenith_Angle`
and `Solar_Azimuth_Angle` datasets in the generated working HDF5.
Manifest datetimes without timezone information are treated as UTC.

When `apply_topo=True` or `apply_brdf=True`, solar geometry is required by
default. Set `require_solar_geometry=False` only when you intentionally want to
allow an uncorrected fallback for incomplete inputs.

Each per-flight QA audit records:

- `solar_geometry_source`: `raster`, `scalar`, `manifest_computed`, or `missing`
- `acquisition_datetime_used`
- solar zenith mean/min/max
- solar azimuth mean/min/max

If your TIFF source does not use the default 10-band Erick notebook spectral
definition, also pass:

```python
tiff_wavelengths_nm=[...]
tiff_fwhm_nm=[...]
```

## Outputs

Each discovered flight gets its own output folder:

```text
drone_outputs/
  <flight_stem>/
    <flight_stem>__working.h5
    <flight_stem>__working.stage.json
    <flight_stem>__envi.img
    <flight_stem>__envi.hdr
    <flight_stem>__corrected.img
    <flight_stem>__corrected.hdr
    <flight_stem>__corrected__correction.stage.json
    <flight_stem>__landsat_like_<target>_translated_envi.img
    <flight_stem>__landsat_like_<target>_translated_envi.hdr
    <flight_stem>__landsat_like_<target>_translated_envi__translation.json
    <flight_stem>__landsat_like_<target>_translated_envi__translation_qa.png
    <flight_stem>__landsat_like_<target>_translated_envi__translation_qa.json
    <flight_stem>__polygon_index.parquet
    <flight_stem>__polygons.parquet
    <flight_stem>__landsat_like_<target>_translated_envi__polygons.parquet
    <flight_stem>__qa.png
    <flight_stem>__qa.json
    qa_publication/
      <translated_stem>__translation_quality.png
      <translated_stem>__translation_quality.pdf
  drone_merged.parquet
  drone_landsat_like_merged.parquet
  drone_qa_summary.json
  qa/summary/drone_qa_summary.png
  qa/summary/drone_qa_summary.json
  qa/report.stage.json
  qa_summary.pdf
```

Parquet remains the authoritative tabular output. CSV sidecars, when present in
drone workflows, are convenience copies for external tools.
The stage records are the restart contract: a product is reused only when the
recorded source/configuration fingerprint matches and the product validates.

## Inspect the run

```python
from pathlib import Path

output_dir = Path("drone_outputs")
print(results["qa_summary_path"])
print(results["merged"])

for qa_png in output_dir.glob("*/*__qa.png"):
    print(qa_png)
```

The QA JSON records whether requested topographic or BRDF corrections were
applied, skipped because ancillary data were unavailable, or reverted because
the corrected product failed quality checks.

## Translation and validation architecture

```text
DRONE
TIFF + ancillary + manifest
  -> working H5 -> ENVI -> topo/BRDF -> corrected MicaSense
  -> affine cross-sensor translation -> Landsat-like -> spectral library -> QA

NORMAL NEON
NEON H5 -> ENVI -> topo/BRDF -> corrected hyperspectral
  -> convolution -> Landsat-like -> spectral library -> QA
```

Drone and NEON use the same established scientific machinery through corrected
ENVI. They then diverge: the drone branch applies wavelength-aware affine bulk
relationships, while the NEON branch spectrally convolves hyperspectral data.
The coefficient artifact must contain the bulk candidate schema, including the
recorded equation `target = slope * source + intercept`, source and target
sensors/bands, weighting family, finite slope/intercept, and analysis run ID.
The pipeline will not silently select among pixel-, flightline-, and
site-balanced families.

The translated polygon or full-pixel Parquet retains the existing extracted
schema and adds provenance columns for the source package, working H5,
corrected and translated rasters, coefficient fingerprint/run/weighting,
sensor pair, and band mapping.

Standalone translation QA is always local. For optional real-observation QA,
set `landsat_qa=True` after installing
`earthlab-spectralbridge[landsat]`, or pass `landsat_product` with a supplied
analysis-ready raster. Pass `comparison_neon_product` for an optional
three-way comparison. All comparison inputs are aggregated to the actual
Landsat grid with valid-data-aware averaging; the high-resolution source
products are unchanged. Missing scenes, excessive cloud, or insufficient
overlap limit only the optional comparison, not the completed drone workflow.
