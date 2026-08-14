# Module vignette 3: harmonize target sensors

**Notebook:** [View the Landsat harmonization notebook in the repository](https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/03_harmonize_to_landsat.ipynb). GitHub displays the cells; clone or download the file to run them.

Use this module when a corrected NEON cube exists and you want reflectance in
configured target-sensor bandspaces such as Landsat or MicaSense. SpectralBridge
integrates corrected spectra against the registered spectral response
definitions.

## Continue the standard run

Rerun the same `spectralbridge-pipeline` command used to create the corrected
cube. Earlier valid stages will be skipped and each target sensor will be
checked independently.

```bash
spectralbridge-pipeline \
  --base-folder spectralbridge_output \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --engine thread \
  --max-workers 2
```

Read the sensor summary in the log. It separates products that were created,
already existed, or failed.

## Confirm the result

Target products follow the pattern:

```text
<flightline>_<sensor>_envi.img
<flightline>_<sensor>_envi.hdr
<flightline>_<sensor>_envi.parquet
```

Use the matching ENVI header to interpret band order and wavelengths. Use the
Parquet sidecar or merged table for tabular analysis.

## Continue

- [Build analysis tables](analysis-tables.md)
- [Review QA outputs](qa-and-analysis.md)
- Technical details: [stage contracts](../pipeline/stages.md) and
  [configuration](../reference/configuration.md)
