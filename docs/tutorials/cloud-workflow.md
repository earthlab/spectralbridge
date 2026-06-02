# Tutorial: Cloud & HPC Workflows

This tutorial describes how to run SpectralBridge efficiently in cloud or HPC
environments where data access, storage, and memory constraints differ from a
local workstation.

---

## Overview

You will learn:

- best practices for running the pipeline in object-storage environments
- when to use Ray, thread, or process execution
- how to work with large NEON datasets without long-term local persistence
- strategies for scaling multi-flightline workflows

---

## 1. Working with object storage

NEON HDF5 files can be staged from object storage or shared research storage
before running the pipeline.

Recommended workflow:

1. Stage a small number of HDF5 files into a temporary working directory.
2. Run the pipeline on those flight lines.
3. Upload corrected ENVI, Parquet, and QA outputs to persistent storage.
4. Archive or clean intermediate working files according to your storage policy.

Example staging command:

```bash
gocmd get i:/iplant/home/.../NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance.h5 .
```

---

## 2. Engine selection

Ray is included in the standard SpectralBridge install and is the default
engine for `spectralbridge-pipeline`.

Use Ray when you are processing many flight lines, running on cloud/HPC
resources, or want the default parallel dispatch behavior:

```bash
spectralbridge-pipeline ... --engine ray --max-workers 8
```

Use the thread engine for single-flightline debugging or constrained-memory
runs where you want to avoid Ray initialization:

```bash
spectralbridge-pipeline ... --engine thread --max-workers 1
```

Use the process engine only when you specifically want local multi-process
execution without Ray:

```bash
spectralbridge-pipeline ... --engine process --max-workers 2
```

---

## 3. Memory considerations

Large NEON flight lines may require tens of gigabytes of memory. To reduce
memory pressure:

- reduce `--max-workers`
- lower `--parquet-chunk-size`
- use local scratch storage for temporary files
- avoid keeping many ENVI cubes loaded in memory simultaneously
- match Ray worker memory to expected flightline size

---

## 4. Recommended HPC workflow

For cluster schedulers, a conservative pattern is one job per flight line:

- request enough memory for a single NEON flight line
- use local scratch storage for working files
- write final ENVI, Parquet, and QA products to shared storage
- merge or summarize completed outputs downstream with DuckDB or Python

This keeps failed jobs isolated and preserves restart safety.

---

## 5. Example SLURM script

```bash
#!/bin/bash
#SBATCH --job-name=spectralbridge
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

module load python

BASE=$SCRATCH/spectralbridge_${SLURM_JOB_ID}
mkdir -p "$BASE"

spectralbridge-pipeline \
  --base-folder "$BASE" \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --engine ray \
  --max-workers 8
```

---

## Next steps

- [Pipeline stages](../pipeline/stages.md)
- [Using Parquet outputs](../usage/parquet.md)
- [Troubleshooting](../troubleshooting.md)
