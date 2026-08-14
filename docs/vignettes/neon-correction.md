# Module vignette 2: correct NEON reflectance

Use this module to turn a NEON directional-reflectance HDF5 into raw ENVI and
BRDF/topography-corrected ENVI products. The corrected cube is the canonical
science product used by sensor harmonization.

## Run through the correction module

The supported user entry point is the restart-safe orchestrator. Point it at the
same workspace used for acquisition:

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

The orchestrator will continue into later modules after correction. On a rerun,
valid correction outputs are reused.

## Confirm the checkpoint

Inside the per-flightline directory, look for:

```text
<flightline>_envi.img
<flightline>_envi.hdr
<flightline>_brdfandtopo_corrected_envi.json
<flightline>_brdfandtopo_corrected_envi.img
<flightline>_brdfandtopo_corrected_envi.hdr
```

The JSON records correction parameters; the corrected ENVI pair carries the
corrected reflectance cube. Keep both members of every ENVI pair together.

## Continue

- [Harmonize target sensors](sensor-harmonization.md)
- [Carry on from a partial run](carry-on-wayward-son.md)
- Technical details: [BRDF and topographic
  correction](../brdf_topo_algorithm.md)
