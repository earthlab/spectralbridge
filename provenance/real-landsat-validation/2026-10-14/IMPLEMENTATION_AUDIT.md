# Existing implementation and available products

- `landsat_validation.py`: existing optional Planetary Computer acquisition,
  `landsat-c2-l2`, Collection 2 scaling constants, QA_PIXEL bits 0-5,
  timestamp/sensor/asset/bounds helpers, crop cache and common-grid averaging.
  Existing drone path intentionally uses only 4/5 shared bands. It does not
  provide the requested independent seven-band flight experiment, QA_RADSAT,
  full candidate table, joint variant support, Deming/BA/spatial uncertainty or
  edge-area coverage diagnostics. Reuse shared helpers and preserve old APIs.
- `_aggregate_to_reference_grid` currently averages a valid mask using GDAL over
  contributing cells, which does not establish full Landsat-pixel geometric
  coverage at partial raster edges. The new strict flight path needs explicit
  footprint areas and source counts; do not silently interpret this mask as 90%
  Landsat support.
- `pipelines/pipeline.py`, `brdf_topo.py`, `neon_to_envi.py`, `neon_cube.py`:
  canonical export/correction/convolution stages, parameter JSON, ancillary
  geometry and reflectance scale. NeonCube loads the full cube, so the available
  128-GiB host and staged processing are accounted for; bounded 32-row application
  avoids the otherwise very large full-flight correction tile. Scene-wide fits
  and formulas are unchanged. Full-resolution Parquet export is not needed.
- `resample.py`, `_build_sensor_srfs`, packaged Landsat parameters: seven Gaussian
  channels centered at 443,482,561.4,654.6,864.7,1608.9,2200.7 nm. Corrected NEON
  is the source. Undarkened is saved before existing multiplicative band gains;
  adjusted `olioli` is not an independent observation. Values/coefficients are not
  changed in this validation.
- `_build_convolution_header` uses SRF dictionary keys as wavelengths. Generic
  `band_01` keys therefore do not supply valid physical coordinates. The new
  pilot uses explicitly declared numeric wavelength keys, with known response
  definitions, rather than guessing/relabeling old exports. This metadata issue
  is separate from any reflectance disagreement and should remain visible.
- `qa_metrics.py`, `qa_plots.py`, `drone_qa.py`: existing QA context and patterns,
  not an independent Landsat validation result. `bulk/catalog.py`, `bulk/models.py`
  and `bulk/provenance.py` provide identity, compact-statistics architecture,
  canonical signatures and atomic manifests reused by the flight extension.
- `sensor_pft_transfer.py` and P120 provenance: synthetic-only internal evidence,
  paired corrected/OLI source support, verified OLI definitions; cannot substitute
  for real Landsat imagery. Those results remain unchanged.
- Tests: existing Landsat/drone, schema, convolution, resampling and bulk tests.
  New tests target strict scene/QA/scale/support/agreement contracts with mocked
  STAC; normal tests never require live network.
- The archived R10C H5 is real full-resolution metadata-rich NEON input (about
  2.54 GB compressed), not the tiny memory-fixture H5. No production corrected
  raster pair was initially present. Its 2021-09-15 flight is the sole available
  full-acquisition pilot, independently chosen before any real agreement scores.

## Sources consulted

- USGS Collection 2 Level-2 products and official scale/offset/range:
  https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products
- USGS QA_PIXEL and QA_RADSAT bit definitions:
  https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands
- Planetary Computer STAC and Landsat asset names:
  https://planetarycomputer.microsoft.com/docs/reference/stac/
- NEON format/time conventions and pre-2022 AOP naming:
  https://www.neonscience.org/data-samples/data-management/data-formats-conventions
- SciPy errors-in-variables/ODR motivation (ODR runtime is deprecated; use the
  explicit linear Deming formula and document its variance-ratio assumption):
  https://docs.scipy.org/doc/scipy/reference/odr.html
