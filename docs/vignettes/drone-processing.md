# Module vignette 6: process drone imagery

**Notebook:** [View the drone notebook in the repository](https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/06_drone_pipeline.ipynb). GitHub displays the cells; clone or download the file to run them.

Use this module for local drone TIFF packages or HDF5 inputs. Discovery is
recursive, the original package remains traceable, and TIFF inputs enter the
same established HDF5, ENVI, topographic, and BRDF correction machinery.

## Scientific branches

```text
DRONE
TIFF + ancillary + manifest
  -> working H5 -> ENVI -> topo/BRDF -> corrected MicaSense
  -> affine cross-sensor translation -> Landsat-like raster
  -> full or polygon spectral library -> QA

NORMAL NEON
NEON H5 -> ENVI -> topo/BRDF -> corrected hyperspectral
  -> spectral convolution -> Landsat-like raster
  -> full or polygon spectral library -> QA

OPTIONAL VALIDATION
actual Landsat
            \
drone-like --- actual-Landsat grid -> pairwise QA
            /
NEON-like
```

The paths are shared through corrected ENVI and then diverge. Drone data use
reviewed affine coefficients derived by the independent bulk workflow. NEON
hyperspectral data use spectral convolution. The corrected native MicaSense
raster remains a first-class output and is never overwritten. A translated
product is Landsat-like; it is not an actual Landsat observation.

## Prepare inputs and coefficients

Place valid drone HDF5 files or reflectance TIFF packages under one input
directory. TIFF packages may include aligned terrain/view sidecars and are
matched to the bundled field manifest unless `drone_manifest_path` overrides
it. See the [detailed tutorial](../tutorials/micasense-to-landsat.md) for the
complete TIFF contract.

Production translation consumes a static, versioned registry generated from
the completed compact bulk output. It does not fit coefficients. The production
weighting is fixed to `site_balanced`, reflecting intended transfer to new
flightlines and sites rather than optimization of the pooled pixel fit.
SpectralBridge validates equation direction, sensor identities, the exact 18
physical pair-band mappings, wavelengths, finite coefficients, confidence, and
bulk-run provenance before writing a translated product.

## Run it

```python
from spectralbridge import run_drone_pipeline

results = run_drone_pipeline(
    input_h5_dir="drone_inputs",
    output_dir="drone_outputs",
    polygon_path="plots.geojson",
    extraction_mode="polygon",
    apply_topo=True,
    apply_brdf=True,
    apply_translation=True,
    translation_coefficients="drone_translation_coefficients_v1.json",
    translation_strict=False,
)

print(results["processed"])
print(results["translation_outputs"])
print(results["translated_merged"])
```

Use `extraction_mode="full"` for all corrected pixels. Omitting
`extraction_mode` preserves the earlier behavior: polygon extraction when a
polygon is supplied, otherwise raster and QA outputs only. Translation remains
opt-in. Once a reviewed registry is packaged, its path may be omitted; until
then, an explicit generated registry is required. Normal mode writes `caution`
bands with warnings, while `translation_strict=True` refuses them. A `reject`
coefficient is never applied.

## Standalone and comparison QA

Every translated run produces per-target translation JSON and PNG diagnostics
without NEON or network access. They show band mapping, coefficient evidence,
corrected-versus-translated values, reflectance shifts, valid fractions,
nodata preservation, and unusual translated values.

Set `landsat_qa=True` to request an overlapping Landsat Collection 2 Level 2
scene from Microsoft Planetary Computer. Install this optional support with:

```bash
python -m pip install "earthlab-spectralbridge[landsat]"
```

Alternatively, use `landsat_product="landsat_stack.tif"` to supply an
analysis-ready multiband raster or a previously cached observation manifest.
The comparison selects the closest acceptable scene within
`landsat_search_days`, applies the Landsat QA pixel mask, and aggregates the
translated drone product onto the actual Landsat grid using valid-aware area
averaging. Failed searches, cloud rejection, or insufficient overlap are
recorded as optional-QA limitations and do not fail the core drone run.

Add `comparison_neon_product="neon_landsat_like.img"` to compare an existing
normal-pipeline NEON product on the same Landsat support. The three reported
pairs are drone-like versus actual, NEON-like versus actual, and drone-like
versus NEON-like. NEON is optional and is never processed by drone code.

## Restart and outputs

Valid working H5, corrected ENVI, translated ENVI, and translated Parquet
products are reused when their inputs and translation signatures match.
Optional Landsat failure does not invalidate or recompute core products. See
[outputs and naming](../pipeline/outputs.md) for the complete contract, and
review every QA JSON before treating a coefficient application as trustworthy.

## Continue

- [Review QA outputs](qa-and-analysis.md)
- [Extract polygon spectra](polygon-extraction.md)
- [Detailed MicaSense tutorial](../tutorials/micasense-to-landsat.md)
- [Package architecture](../dev/architecture.md)
