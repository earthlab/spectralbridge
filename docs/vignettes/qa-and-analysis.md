# Module vignette 5: review QA outputs

**Notebook:** [View the QA notebook in the repository](https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/05_qa_and_validation.ipynb). GitHub displays the cells; clone or download the file to run them.

Use this module to inspect a completed or partially completed flightline without
recomputing its scientific products. QA PNG files support quick visual triage;
QA JSON files support reproducible checks and summaries.

## Render QA from existing outputs

```bash
spectralbridge-qa \
  --base-folder spectralbridge_output \
  --quick \
  --save-json
```

The quick path uses deterministic subsampling. Use the installed command's
`--help` output before changing sampling or RGB options.

## Review the result

For each flightline, inspect:

- the QA PNG for spatial structure, masks, distributions, and correction or
  sensor anomalies;
- the QA JSON for machine-readable metrics, run context, and flagged issues;
- the merged Parquet for the values behind any anomaly.

QA is evidence for review, not an automatic declaration that a scientific
product is valid. Investigate unexpected bounds, large brightness shifts, high
invalid fractions, or unstable coefficients in context.

## Render from Python

```python
from pathlib import Path

from spectralbridge.qa_plots import render_flightline_panel

flight_dir = Path("spectralbridge_output") / (
    "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
)
png_path, metrics = render_flightline_panel(
    flightline_dir,
    quick=True,
    save_json=True,
)

print(png_path)
print(metrics.get("issues", []))
```

## Continue

- [Carry on from a partial run](carry-on-wayward-son.md)
- Technical details: [QA panels and metrics](../pipeline/qa.md) and
  [validation metrics](../reference/validation.md)
