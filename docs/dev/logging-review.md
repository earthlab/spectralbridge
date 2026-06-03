# Logging Review

Review date: 2026-06-03

This note records the current logging posture of SpectralBridge after a
lightweight audit. It is intentionally descriptive rather than prescriptive:
the goal is to make behavior and risks visible without changing runtime
semantics in a release-hardening pass.

## Scope reviewed

- `src/spectralbridge/pipelines/pipeline.py`
- `src/spectralbridge/pipelines/drone.py`
- `src/spectralbridge/_ray_utils.py`
- `src/spectralbridge/progress_utils.py`
- `src/spectralbridge/qa_plots.py`
- `src/spectralbridge/qa_dashboard.py`
- `src/spectralbridge/cli/recover_cli.py`
- `src/spectralbridge/polygon_extraction.py`
- `src/spectralbridge/corrections.py`

## Current behavior

### 1. The NEON pipeline uses a module-owned stream handler

`src/spectralbridge/pipelines/pipeline.py` attaches a `StreamHandler` to the
module logger at import time and sets `logger.propagate = False`.

Implications:

- direct pipeline runs get predictable timestamped output even when the caller
  has not configured logging
- parent/root logger configuration does not automatically affect the pipeline
- tests that want to capture pipeline logs often need to attach handlers
  directly to `spectralbridge.pipelines.pipeline`

This is the main place where SpectralBridge behaves more like an application
than a library.

### 2. Some CLI entry points still call `logging.basicConfig(...)`

Observed in:

- `src/spectralbridge/qa_dashboard.py`
- `src/spectralbridge/cli/recover_cli.py`

Implications:

- running these CLIs as top-level commands is straightforward
- embedding them in notebooks or larger applications can unexpectedly alter the
  root logger if nothing has configured logging yet
- behavior differs from `pipeline.py`, which manages its own module logger
  instead of relying on the root logger

### 3. `qa_plots` forces its logger to `INFO` at import time

`src/spectralbridge/qa_plots.py` does:

```python
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

Implications:

- downstream callers cannot fully control verbosity through parent logger
  configuration alone
- debug-level diagnostics from that module will stay suppressed even if a
  caller raises the root logger to `DEBUG`

### 4. Some lower-level code writes to the root logger directly

`src/spectralbridge/corrections.py` uses `logging.debug(...)` and
`logging.warning(...)` instead of a module-scoped logger.

Implications:

- messages bypass any package-specific logger naming hierarchy
- formatting and routing depend entirely on the root logger
- this differs from most of the package, which uses `logging.getLogger(__name__)`

### 5. Progress reporting is mixed between logging and `tqdm`

Observed in:

- `src/spectralbridge/progress_utils.py`
- `src/spectralbridge/pipelines/pipeline.py`
- `src/spectralbridge/pipelines/drone.py`
- `src/spectralbridge/envi_download.py`
- `src/spectralbridge/merge_duckdb.py`
- `src/spectralbridge/polygon_extraction.py`

Current pattern:

- interactive paths prefer `tqdm`
- non-interactive paths emit periodic `logger.info(...)` or `tqdm.write(...)`
- the drone pipeline writes human-facing progress lines to `stderr`

Implications:

- notebook and terminal UX is generally acceptable today
- output style is not uniform across NEON, drone, and utility scripts
- automated log consumers should not assume a single progress format

### 6. Ray behavior is mostly controlled through environment variables, not logging APIs

Observed in:

- `src/spectralbridge/_ray_utils.py`
- `src/spectralbridge/pipelines/pipeline.py`

Current controls:

- `RAY_LOG_TO_STDERR=0`
- `RAY_BACKEND_LOG_LEVEL=ERROR`
- `RAY_DEDUP_LOGS=1`
- `RAY_DISABLE_DASHBOARD=1`
- optional `CSC_RAY_DEBUG`

Implications:

- SpectralBridge already suppresses a large amount of Ray noise by default
- when `CSC_RAY_DEBUG` is enabled, some diagnostics are printed directly rather
  than logged through the package logger
- worker-side log formatting is not unified with the main pipeline logger

### 7. Multiprocessing code paths do not appear to add duplicate handlers themselves

Observed in:

- `src/spectralbridge/pipelines/pipeline.py`
- `src/spectralbridge/polygon_extraction.py`
- `src/spectralbridge/merge_duckdb.py`

Findings:

- no obvious repeated handler-install loop was found in the multiprocessing or
  process-pool paths
- the main duplication risk still comes from import-time logger setup patterns,
  especially when modules are imported in different execution contexts

## Risk summary

Low-to-moderate maintainability risks exist, but no immediate correctness issue
was found in the current logging setup.

Main risks:

- inconsistent logger ownership between library modules and CLI entry points
- reduced caller control because some modules set handlers or levels at import time
- mixed progress/reporting channels across pipeline variants
- direct root-logger usage in `corrections.py`

## Recommendation

Do not refactor logging as part of unrelated scientific or pipeline work.

If cleanup is prioritized later, keep it incremental:

1. decide on a package-wide policy for library modules vs CLI entry points
2. remove import-time logger level forcing where safe
3. replace root-logger calls with module loggers
4. centralize progress/logging conventions for pipeline, drone, and utilities
5. add focused tests around log capture only if behavior becomes contractual

## Related follow-up

See the logging cleanup follow-up item added to `FEATURE_REQUESTS.md` after this
review.
