# Vignette: Carry On My Wayward Son

Already have part of the pipeline done? Carry on from the files you have. The
main workflow is file-based and restart-safe: it validates expected outputs,
skips valid stages, and recomputes missing or invalid stages in order.

## The short version

Run the **same command with the same base folder and flightline identifier**.

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

The rerun does not use a manual “start at stage 4” switch. Instead, each stage
asks whether its own outputs exist and pass validation. This keeps the restart
decision tied to the on-disk evidence.

## What will happen

| Files already present | Expected behavior |
| --- | --- |
| Valid source HDF5 | Download is reused. |
| Valid raw ENVI `.img/.hdr` pair | ENVI export is skipped. |
| Parseable correction JSON | Parameter fitting is skipped. |
| Valid corrected ENVI pair | Correction is skipped. |
| Some valid target-sensor ENVI pairs | Those sensors are reused; missing sensors are attempted. |
| Valid Parquet or QA outputs | Completed downstream work is reused or refreshed according to its stage contract. |

Read the log for `skipping`, `created`, `existing`, and `failed` summaries. Those
messages explain what the rerun actually did.

## Keep the file contract intact

- Keep the original base folder and exact flightline identifier.
- Do not rename intermediate files by hand.
- Keep ENVI `.img` and `.hdr` files together.
- Let validation trigger recomputation of incomplete artifacts.
- Back up valuable results before intentionally replacing them.

## Special case: corrected ENVI exists but raw ENVI is missing

Use the recovery command to rebuild the raw export, then rerun the normal
pipeline:

```bash
spectralbridge-recover-raw \
  --base-folder spectralbridge_output \
  --brightness-offset 0.0
```

```bash
spectralbridge-pipeline --help
```

The recovery command is intentionally narrow. The normal pipeline remains the
authority for deciding which subsequent stages need work.

## Diagnose before forcing a rerun

1. Compare the directory against [Outputs and file
   structure](../pipeline/outputs.md).
2. Read [stage order and restart behavior](../pipeline/stages.md).
3. Use the [troubleshooting guide](../troubleshooting.md) for invalid ENVI,
   memory, dependency, and QA problems.

If you have no existing outputs, start with [Run the full
pipeline](full-pipeline.md).
