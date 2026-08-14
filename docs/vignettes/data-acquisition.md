# Module vignette 1: acquire NEON data

**Notebook:** [Open or download the acquisition notebook](notebooks/01_acquire_neon.ipynb).

Use this module when you need to place one or more NEON directional-reflectance
HDF5 flightlines into a SpectralBridge workspace. If the HDF5 already exists in
the canonical location, continue to [NEON correction](neon-correction.md).

## Download one flightline

```bash
spectralbridge-download NIWO \
  --year-month 2023-08 \
  --product DP1.30006.001 \
  --flight NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --output spectralbridge_output
```

The full pipeline can also perform this acquisition automatically. Use the
standalone command when you want to stage data before a later processing run.
This command writes beneath `spectralbridge_output/NIWO/`; use that site folder
as the later pipeline's `--base-folder` so the existing HDF5 is discovered.

## Confirm the result

```bash
find spectralbridge_output/NIWO -maxdepth 1 -type f -name '*.h5'
```

Keep the original flightline identifier in the filename. Downstream naming and
restart checks use that provenance.

## Continue

- [Correct NEON reflectance](neon-correction.md)
- [Run the full pipeline](full-pipeline.md)
- Technical details: [CLI](../usage/cli.md) and [stage
  contracts](../pipeline/stages.md)
