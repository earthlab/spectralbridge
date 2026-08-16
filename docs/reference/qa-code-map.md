# QA implementation map

The QA implementation is deliberately separate from the scientific pipeline.
It reads persisted artifacts, calculates diagnostics, writes reports, and never
changes reflectance, coefficients, masks, or stage filenames.

## Where each responsibility lives

| Module | One responsibility | Change this module when… |
| --- | --- | --- |
| `qa/schema.py` | Versioned JSON objects and four-state status vocabulary | A report field or serialized contract changes |
| `qa/paths.py` | Deterministic locations for stage and combined artifacts | A new report artifact needs a canonical filename |
| `qa/thresholds.py` | Provisional thresholds and high-is-bad/low-is-bad classification | A reviewed validation campaign supports a threshold change |
| `qa/metrics.py` | Sensor-independent numerical summaries | A reusable array diagnostic is needed |
| `qa/brightness.py` | Before/after brightness application audit | Brightness QA needs another metric, not a new coefficient |
| `qa/network.py` | Translation-edge, grouped, path, and cycle diagnostics | Paired sensor-model validation is supplied |
| `qa/plots.py` | Fixed-scale, location-labelled figures | A metric already exists and needs a visual representation |
| `qa/stages.py` | Assemble one stage report from canonical artifacts | A stage needs to connect existing metrics, plots, and checks |
| `qa/reporting.py` | Standalone HTML and combined cross-stage synthesis | Presentation or cross-stage interpretation changes |
| `qa/runner.py` | Rebuild all reports from a completed flightline | Artifact discovery for completed runs changes |

The package exports the reusable public diagnostics from `qa/__init__.py`.
Helpers beginning with `_` are implementation details and can change without
becoming part of the scientific API.

## Execution flow

1. The pipeline writes its normal stage artifact.
2. `emit_stage_qa` fingerprints declared inputs and outputs.
3. ENVI or table metadata is read using bounded deterministic sampling.
4. Functions in `metrics.py`, `brightness.py`, or `network.py` return plain
   serializable dictionaries.
5. `thresholds.py` converts evaluated values to `PASS`, `WARN`, `FAIL`, or
   `NOT EVALUATED`.
6. `plots.py` renders from the same values using the versioned display contract.
7. `reporting.py` writes JSON/HTML and assembles the combined report.

Stages communicate through files. QA does not retain hidden in-memory state and
does not rerun or modify the scientific correction.

## Readability conventions

- Metric functions calculate values; they do not decide stage status or render.
- Plot functions receive calculated values and never alter the product.
- Threshold functions contain the comparison direction and boundary values.
- The stage coordinator records unavailable diagnostics explicitly instead of
  filling them with simulated evidence.
- Every fixed display limit belongs to `qa_plot_contract()` so a validation
  campaign cannot silently rescale from run to run.
- Every new JSON field must be serializable, named with units where ambiguity is
  possible, and covered by a contract test.

## Adding a diagnostic safely

1. Decide whether the diagnostic is a reusable metric, stage-only assembly, or
   a visualization.
2. Put numerical work in `metrics.py` or a focused module such as
   `brightness.py`.
3. Return values without a status; add threshold classification in the stage
   coordinator.
4. Add a plot only when it materially helps interpretation.
5. Add a focused numerical test, a status-boundary test, and—when plotted—a
   fixed-axis/location-label test.
6. Explain the check in the [stage QA test guide](../validation/stage-qa-guide.md).
7. Regenerate a real report without changing its source products and inspect
   both the image and JSON.

## Test ownership

| Test area | Main protection |
| --- | --- |
| `tests/test_stage_qa.py` | Paths, schemas, sampling, metrics, status rules, figures, report restart safety, and completed-run discovery |
| `tests/test_brightness_coefficients.py` | Packaged coefficient order and correction behavior, including NoData preservation |
| `tests/test_validation_campaign.py` | Deterministic offline campaign execution and machine-readable records |
| `tests/test_validation_docs.py` | Every recorded input, diagnostic, and check has a website explanation; every example image exists; generated pages are current |
| `tests/test_qa/test_qa_metrics_smoke.py` | Compatibility QA payload and image smoke contracts |

The [Validation evidence](../validation/index.md) section separates these
software contracts from real-flightline observations and from the planned
multi-site scientific validation campaign.
