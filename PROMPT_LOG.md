# PROMPT_LOG.md

This file stores verbatim user prompts for Codex work in this repository.

- New entries should be appended, not rewritten.
- Prompts should be logged verbatim in fenced `text` blocks.
- Logging begins with the request that introduced this file; older prompts were not backfilled automatically.

## 2026-03-21 - add AGENTS guidance and prompt logging
Branch: main

```text
this repo doesn't have an AGENTS.md file for agents for codex to reference. can you read through the repo and the webstie and try to use that information to write an AGENTS.md file to speed up future work. one thing i would like it to include is a prompt log that logs the verbatim promplts that i give codex.
```

## 2026-03-21 - fix ruff syntax errors in drone pipeline
Branch: main

```text
Run ruff check src tests
invalid-syntax: Expected a newline after line continuation character
   --> src/spectralbridge/pipelines/drone.py:404:51
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                   ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:51
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                   ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Unparenthesized generator expression cannot be used here
   --> src/spectralbridge/pipelines/drone.py:404:52
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:52
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                    ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.10 (syntax was added in Python 3.12)
   --> src/spectralbridge/pipelines/drone.py:404:55
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                       ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: Expected `,`, found `]`
   --> src/spectralbridge/pipelines/drone.py:404:81
    |
402 |     try:
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
    |                                                                                 ^
405 |         )
406 |         con.execute(
    |

invalid-syntax: f-string: unterminated string
   --> src/spectralbridge/pipelines/drone.py:405:10
    |
403 |         files = ", ".join(
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
405 |         )
    |          ^
406 |         con.execute(
407 |             "COPY (SELECT * FROM read_parquet(["
    |

invalid-syntax: f-string: expecting `}`
   --> src/spectralbridge/pipelines/drone.py:406:9
    |
404 |             [f"'{str(Path(path)).replace(chr(39), \"''\")}'" for path in outputs]
405 |         )
406 |         con.execute(
    |         ^^^
407 |             "COPY (SELECT * FROM read_parquet(["
408 |             + files
    |

invalid-syntax: Expected `,`, found `finally`
   --> src/spectralbridge/pipelines/drone.py:412:5
    |
410 |             [str(output_path)],
411 |         )
412 |     finally:
    |     ^^^^^^^
413 |         con.close()
414 |     return output_path
    |

invalid-syntax: Expected `,`, found `:`
   --> src/spectralbridge/pipelines/drone.py:412:12
    |
410 |             [str(output_path)],
411 |         )
412 |     finally:
    |            ^
413 |         con.close()
414 |     return output_path
    |

invalid-syntax: Expected `]`, found newline
   --> src/spectralbridge/pipelines/drone.py:413:20
    |
411 |         )
412 |     finally:
413 |         con.close()
    |                    ^
414 |     return output_path
    |

invalid-syntax: Expected `)`, found dedent
   --> src/spectralbridge/pipelines/drone.py:414:5
    |
412 |     finally:
413 |         con.close()
414 |     return output_path
    |     ^
    |

Found 12 errors.
Error: Process completed with exit code 1.
```

## 2026-03-21 - add drone-specific QA plot workflow
Branch: main

```text
can you fix that? build off of the neon qa plot and do it for the drone. we want to confirm that the original ENVI was created correctly and that the bands are faithful, then we want to plot the BRDF correction so that we can see what and how much was adjusted. We get a bunch of -9999 from those first steps and we need to plot wehre all the -9999 are to make sure that went OK. Then we need to see the polygons are over the flightline so we're extracting real data and then we want to show a preview of the merged table to confirm that it worked. This is a special modification for the drone pipeline that differes a bit from the neon pipeline
```

## 2026-03-21 - fix full pytest regressions after drone QA changes
Branch: main

```text
Run pytest -q
.................FFFF.F........ssss..................FF.....FFFFFF..s... [ 80%]
..F...............                                                       [100%]
=================================== FAILURES ===================================
___________________________ test_duckdb_merge_smoke ____________________________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_duckdb_merge_smoke0')

    def test_duckdb_merge_smoke(tmp_path: Path) -> None:
        flight_dir = tmp_path / "NEON_TEST_FLIGHT"
        flight_dir.mkdir()

        wavelengths = range(1, 427)
        pixel_ids = ["pix0", "pix1", "pix2"]

        # Long layout (original)
        long_rows: list[dict[str, object]] = []
        for idx, pid in enumerate(pixel_ids):
            for wl in wavelengths:
                long_rows.append(
                    {
                        "pixel_id": pid,
                        "wavelength_nm": float(wl),
                        "reflectance": (wl + idx) / 1000.0,
                        "site": "TEST",
                        "domain": "D00",
                        "flightline": "FLIGHT",
                        "row": idx,
                        "col": idx + 10,
                    }
                )
        _write_parquet(long_rows, flight_dir / "orig" / "test_original_table.parquet")

        # Wide layout (corrected)
        wide_records: list[dict[str, object]] = []
        for idx, pid in enumerate(pixel_ids):
            record = {
                "pixel_id": pid,
                "site": "TEST",
                "domain": "D00",
                "flightline": "FLIGHT",
                "row": idx,
                "col": idx + 10,
            }
            for band_idx, wl in enumerate(wavelengths, 1):
                record[f"corr_b{band_idx:03d}_wl{wl:04d}nm"] = (wl + idx) / 2000.0
            wide_records.append(record)
        _write_parquet(wide_records, flight_dir / "corr" / "test_corrected_table.parquet")

        # Long layout with micrometer wavelengths (resampled)
        resamp_records: list[dict[str, object]] = []
        resamp_wavelengths = range(500, 520)
        for idx, pid in enumerate(pixel_ids):
            record = {
                "pixel_id": pid,
                "site": "TEST",
                "domain": "D00",
                "flightline": "FLIGHT",
            }
            for band_idx, wl in enumerate(resamp_wavelengths, 1):
                record[f"resamp_b{band_idx:03d}_wl{wl:04d}nm"] = (wl + idx) / 3000.0
            resamp_records.append(record)
        _write_parquet(resamp_records, flight_dir / "resamp" / "test_resampled_table.parquet")

>       output_path = merge_flightline(flight_dir, emit_qa_panel=False)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_duckdb_merge.py:114: 
[...]
Error: Process completed with exit code 1.
```

## 2026-03-22 - drone nodata compatibility shim
Branch: work

```text
# Codex Prompt: Quarantined Drone-Pipeline Fix for Missing NoData Metadata

You are working in the `spectralbridge` repository.

Your task is to implement a clean, production-quality fix for the new **drone pipeline** so that drone HDF5 orthomosaics can be processed even when their reflectance dataset does **not** contain one of the no-data metadata attributes expected by the strict NEON reader.

This prompt is intentionally detailed. Follow it closely.

---

## Core goal

Fix the failure in the drone workflow caused by:

`Reflectance dataset missing a recognised no-data attribute.`

This is happening inside the existing NEON-oriented HDF5 reader stack when `run_drone_pipeline()` tries to process drone orthomosaic HDF5 files.

The fix must let the **drone pipeline** proceed **without changing the behavior of the existing NEON pipeline**.

---

## Absolute guardrail

Do **not** “fix” this by globally relaxing the NEON reader for all callers.

The existing NEON pipeline should remain strict by default.

The workaround / compatibility logic must be **quarantined to the drone pipeline only**.

That means:

* do not silently broaden `_extract_no_data()` for all code paths
* do not alter standard `NeonCube` / `read_neon_cube()` behavior unless a caller explicitly opts into drone-only compatibility
* do not mutate original source HDF5 files in place
* do not introduce behavior changes to the standard NEON processing path

---

## What is currently happening

The failure path is roughly:

* `src/spectralbridge/pipelines/drone.py::run_drone_pipeline()`
* constructs `NeonCube(h5_path=h5_path)`
* which goes through `src/spectralbridge/neon_cube.py`
* which calls `src/spectralbridge/io/neon.py::read_neon_cube()`
* which calls `_read_new_neon_layout()`
* which calls `_extract_no_data(reflectance_ds)`
* which raises because the drone reflectance dataset lacks a recognized no-data attribute

This occurs across many drone HDF5 files with the same error, so the issue is not a one-off bad file. It is a compatibility gap between the new drone pipeline and the strict NEON metadata contract.

---

## Important context from a prior prototype

There is already a useful prototype pattern that worked conceptually and should guide this implementation.

That prototype did the following:

1. Copied the source HDF5 into a run-specific working directory.
2. Located the reflectance dataset inside the copied HDF5.
3. Patched missing no-data-related attributes on the **copied** HDF5 only.
4. Then ran the downstream processing stack on the prepared working copy.

That is the architectural clue you should use.

The most valuable ideas from the prototype are:

* **robust reflectance dataset discovery**
* **patching missing no-data attrs only on a working copy**
* **quarantining the workaround to the drone pipeline**

Do **not** rely on the prototype’s synthetic NEON renaming unless the current pipeline structure absolutely requires it. Reuse the good ideas, not necessarily the exact mechanics.

---

## Preferred implementation strategy

### Strong preference

Implement a **drone-only preprocessing/preparation step** inside `run_drone_pipeline()`.

That preparation step should:

1. create or identify the drone pipeline’s working copy of the HDF5
2. inspect the copied HDF5 to find the reflectance dataset
3. detect whether recognized no-data metadata is missing
4. if missing, patch a small set of no-data aliases onto the **working copy only**
5. then continue with the normal downstream read / conversion flow using the prepared copy

This is the preferred approach because it:

* keeps standard NEON reader semantics untouched
* mirrors an already successful prototype pattern
* makes the drone workaround local and explicit
* is easy to reason about and test

### Acceptable fallback

If the current architecture makes preprocessing awkward, an acceptable fallback is to thread an explicit opt-in flag through the reader stack, such as `allow_missing_nodata=True`, and only pass it from the drone pipeline.

But this is second choice.

If you end up using the explicit-flag design, the default behavior must remain exactly as it is now for standard NEON paths.

---

## Design requirements

1. Preserve existing NEON behavior exactly for standard NEON workflows.
2. Add drone-specific compatibility in a quarantined way.
3. Never modify original source HDF5 files.
4. Work only on a copied / prepared file owned by the drone run.
5. Keep the implementation small, understandable, and easy to remove later if a dedicated `DroneCube` reader is introduced.
6. Preserve the rest of the drone pipeline behavior:

   * output naming conventions
   * folder handling
   * QA summary generation
   * polygon extraction behavior
   * current control flow as much as possible
7. Avoid broad refactors.

---

## Functional requirements for the preparation step

### 1. Reflectance dataset discovery

Implement or reuse a helper that can robustly locate the reflectance dataset in a drone HDF5.

Preferred logic:

* first check likely explicit paths such as:

  * `NIWO/Reflectance/Reflectance_Data`
  * `Reflectance/Reflectance_Data`
* if not found, scan datasets and choose the best reflectance-like candidate using a simple, explainable heuristic

A good heuristic can prefer dataset names containing:

* `reflectance_data`
* `reflectance`
* `reflect`

and slightly favor plausible cube-like datasets (e.g. higher dimensionality, large size)

Keep this robust but simple.

### 2. Detect whether no-data metadata is already present

Before patching, inspect the reflectance dataset attributes.

If the dataset already contains a recognized no-data attribute used by the existing NEON reader, do nothing.

If missing, patch a small set of aliases onto the working copy only.

### 3. Attributes to patch

Use a conservative, documented set such as:

* `_FillValue`
* `NoDataValue`
* `nodata`
* `no_data`
* `missing_value`
* `fill_value`

Also consider any exact names already recognized elsewhere in the repo.

The point is not to invent a new metadata standard. The point is to make the working copy readable by the existing downstream logic without changing the original file.

### 4. Fallback no-data value

Use a clear, documented fallback value such as `-9999.0` unless inspection of current code strongly suggests a different safer convention for this pipeline.

If you choose a different fallback, explain why in comments and in the final summary.

### 5. Scope of mutation

Patch only the working copy owned by the drone run.

Never patch the original input HDF5.

---

## File targets to inspect

Likely files involved:

* `src/spectralbridge/pipelines/drone.py`
* `src/spectralbridge/io/neon.py`
* `src/spectralbridge/neon_cube.py`
* any helper / utility file already used for working-file preparation or naming

You may add a small helper in an appropriate module if that keeps the drone logic tidy.

Do not create a sprawling new abstraction unless it is clearly warranted.

---

## Implementation guidance

Before editing, inspect the current code path and answer these questions for yourself in code comments or your working notes:

1. Where does the drone pipeline already create or manage a working file?
2. Is there already a staging / copy step that can host the patching logic?
3. Can the drone pipeline prepare the file before `NeonCube(...)` is instantiated?
4. What is the smallest local change that keeps NEON behavior untouched?

The best final shape is likely something like:

* a small helper in `drone.py` or a nearby utility that prepares a drone H5 working copy
* a helper that locates the reflectance dataset and patches missing attrs if necessary
* `run_drone_pipeline()` calling that helper before the existing read / convert path begins

---

## What not to do

Do not do any of the following unless absolutely necessary:

* do not globally relax `_extract_no_data()` for all callers
* do not silently change the default semantics of `read_neon_cube()`
* do not rewrite large parts of the pipeline
* do not rename all drone files into fake NEON products unless the current pipeline absolutely requires that structure
* do not remove strict validation from the standard NEON path
* do not patch the original drone HDF5 source files in place

---

## Tests

Add the **minimum number of high-value tests**.

The tests should be targeted and lightweight.

### Required tests

#### Test 1: Standard NEON strictness is preserved

Add a focused test proving that the normal strict path still raises when no recognized no-data attribute exists and the caller has **not** opted into any drone-only workaround.

If you implement the preferred preprocessing approach and keep NEON reader code unchanged, this can be a very small existing-reader test or even an assertion that the strict behavior remains unchanged.

#### Test 2: Drone preparation patches only the working copy

Add a focused unit test for the new drone-only preparation helper that:

* creates a tiny synthetic HDF5 file without no-data attrs
* runs the drone preparation step
* confirms the prepared working copy now contains the patched attrs
* confirms the original file was not modified

This is the most important test.

#### Test 3: Drone pipeline uses the preparation path

Add a focused test, likely with mocking, that confirms `run_drone_pipeline()` uses the drone preparation step before attempting the downstream read/process logic.

This test should verify the quarantine boundary, not full end-to-end processing.

### Testing style

* prefer tiny synthetic HDF5 fixtures or temporary files
* prefer mocking for pipeline orchestration
* avoid heavy integration tests unless trivial to add
* keep runtime fast

---

## Code quality requirements

* Make minimal, surgical changes
* Add concise docstrings / comments explaining why the workaround is drone-only
* Keep functions small and easy to understand
* Use clear naming
* Do not add unnecessary abstraction
* Keep the patch easy to review in a PR

---

## Final output requirements

After implementing, run the relevant tests and give a final summary that explicitly states:

1. what you changed
2. where the drone-only compatibility logic lives
3. why the existing NEON pipeline behavior is still preserved
4. whether the original HDF5 files remain untouched
5. what tests were added
6. any follow-on issues you noticed that may become the next likely failure after this one

---

## Extra caution

The repo is adding a **drone pipeline**, not weakening the **NEON pipeline**.

Make every decision with that in mind.

A good solution here is one where a reviewer can easily say:

> “Yes, this adds a local compatibility shim for drone HDF5s, and no, it does not change the behavior of our existing NEON workflows.”

That is the standard.
```
## 2026-03-22 - drone pipeline quarantine fixes
Branch: work

```text
You are working in the `spectralbridge` repository.

Your task is to fix the **drone pipeline** so it correctly handles drone HDF5 orthomosaics, organizes outputs cleanly, and uses a drone-native naming convention.

This work must be **strictly quarantined to the drone pipeline**.

Do **not** break, weaken, or broaden the existing **NEON pipeline**.

## Mission

Implement a production-quality fix for the new drone workflow that resolves **all three of these problems together**:

1. **Drone HDF5 files fail because their reflectance dataset is missing a recognized no-data attribute**
2. **Drone outputs are being named from the inner HDF5 filename instead of the actual drone package / flight identity**
3. **Drone outputs are being written into a flat folder structure that causes collisions, overwrites, QA confusion, and mis-grouped results**

The final result should be a drone pipeline where:

- drone HDF5s can be read reliably
- each drone package gets a unique, deterministic flight stem
- each flight writes to its own folder
- per-flight QA is isolated per flight
- merged outputs remain at the run level
- the existing NEON pipeline remains unchanged in behavior

## Absolute guardrails

Do **not** do any of the following:

- do not globally relax the NEON reader for all callers
- do not change standard NEON naming conventions
- do not silently alter `read_neon_cube()` semantics for NEON workflows
- do not mutate original source HDF5 files in place
- do not make drone naming depend only on the inner HDF5 filename
- do not flatten all drone outputs into a shared folder
- do not refactor large unrelated parts of the repo

The repo is **adding a drone pipeline**, not changing the **NEON pipeline**.

A reviewer should be able to say:

> “Yes, this adds a local compatibility shim and a drone-native naming/output scheme for drone inputs, and no, it does not change the behavior of our existing NEON workflows.”

That is the standard.

## What is happening now

### Problem 1: missing no-data metadata

The drone HDF5 files currently fail in the NEON-oriented reader stack because the reflectance dataset does not contain one of the exact no-data attributes expected by the strict NEON code path.

The current failure path is roughly:

- `src/spectralbridge/pipelines/drone.py::run_drone_pipeline()`
- constructs `NeonCube(h5_path=h5_path)`
- which goes through `src/spectralbridge/neon_cube.py`
- which calls `src/spectralbridge/io/neon.py::read_neon_cube()`
- which calls `_read_new_neon_layout()`
- which calls `_extract_no_data(reflectance_ds)`
- which raises `Reflectance dataset missing a recognised no-data attribute.`

This happens across many drone files, so it is a compatibility issue, not a one-off bad file.

### Problem 2: naming identity collapse

Many drone packages contain an inner HDF5 file with the same name, for example something like:

- `NEON_D13_NIWO_test_aligned_orthomosaic.h5`

If the pipeline uses that inner filename as the base identity, then many distinct flights collapse onto the same stem.

But the actual distinguishing identity lives in the **parent export-package folder**, such as:

- `AOP-GOLDHILL-08-14-23-ExportPackage`
- `AOP-GORDON-08-14-23-ExportPackage`
- `SPR2-06-28-23-ExportPackage`
- `CW3-08-16-23-ExportPackage`

That package folder name is what should drive the drone flight identity.

### Problem 3: output collisions and QA contamination

The current output structure is effectively flat, with files such as:

- `NEON_D13_NIWO_test_aligned_orthomosaic__working.h5`
- `NEON_D13_NIWO_test_aligned_orthomosaic__envi.img`
- `NEON_D13_NIWO_test_aligned_orthomosaic__corrected.img`
- `NEON_D13_NIWO_test_aligned_orthomosaic__polygons.parquet`
- `NEON_D13_NIWO_test_aligned_orthomosaic__qa.json`
- `NEON_D13_NIWO_test_aligned_orthomosaic__qa.png`

all in one run directory.

This causes collisions or silent overwrites when multiple drone packages share the same inner HDF5 filename.

That likely explains the repeated QA warnings, strange `-9999` contamination messages, and possible cross-flight QA mixing.

## Preferred solution architecture

Implement the fix in two quarantined drone-only layers:

### Layer A: drone-only HDF5 preparation

Inside the drone pipeline, prepare a **working copy** of each drone HDF5 before it is read by the existing downstream stack.

That preparation step should:

1. copy the source HDF5 into the drone flight’s working directory
2. locate the reflectance dataset in the copied HDF5
3. inspect its attrs for recognized no-data metadata
4. if missing, patch a small set of no-data aliases on the copied file only
5. then continue normal downstream processing using the prepared copy

This keeps the workaround local to drone processing and avoids changing default NEON semantics.

### Layer B: drone-native naming and per-flight output organization

Inside the drone pipeline, derive a **unique drone flight stem** from the **parent export-package folder name**, not the inner HDF5 filename.

Then create a **per-flight output directory** and place all flight-specific files there.

Only run-level aggregate products should remain in the run root.

## Required implementation details

## Part 1: drone-only HDF5 preparation

### 1.1 Locate reflectance dataset robustly

Implement or reuse a helper that can find the reflectance dataset in a drone HDF5.

Preferred behavior:

- first try likely explicit paths such as:
  - `NIWO/Reflectance/Reflectance_Data`
  - `Reflectance/Reflectance_Data`
- if not found, scan datasets and pick the best reflectance-like candidate using a small, explainable heuristic

A simple heuristic is fine. Prefer names containing:

- `reflectance_data`
- `reflectance`
- `reflect`

and slightly favor plausible cube-like datasets (higher dimensionality, large size)

Keep this robust but simple.

### 1.2 Patch no-data attrs only on the working copy

Before patching, inspect the reflectance dataset attrs.

If the dataset already contains a recognized no-data attribute used by the existing NEON reader, do nothing.

If it does not, patch a conservative set of aliases such as:

- `_FillValue`
- `NoDataValue`
- `nodata`
- `no_data`
- `missing_value`
- `fill_value`

Also check whether the repo already recognizes any additional exact keys and include those if appropriate.

### 1.3 Fallback no-data value

Use a clear documented fallback such as `-9999.0` unless inspection of the current code strongly indicates that a different value is already standard for this path.

Do not invent a complex policy here.

### 1.4 Scope of mutation

Never patch the source HDF5 in place.

Patch only the copied working file owned by the drone run.

### 1.5 Keep NEON strictness intact

Do not globally change the default strict behavior of the standard NEON reader unless an explicit opt-in is absolutely required.

If you find that a tiny explicit opt-in flag is necessary for internal plumbing, it must be passed only from the drone path, and default behavior for standard NEON callers must remain unchanged.

But the strong preference is to solve this by preparing the drone working copy before the strict reader sees it.

## Part 2: drone-native naming

### 2.1 Add a dedicated drone naming helper

Implement a helper such as:

- `derive_drone_flight_stem(h5_path: Path) -> str`

This helper must derive the unique flight stem from the **parent export-package folder name**, not just the inner HDF5 filename.

Examples of parent folder names:

- `AOP-GOLDHILL-08-14-23-ExportPackage`
- `AOP-GORDON-08-14-23-ExportPackage`
- `SPR2-06-28-23-ExportPackage`
- `SH67_1-07-07-23-ExportPackage`

### 2.2 Stem requirements

The derived stem must be:

1. unique across flights in the same batch
2. deterministic
3. human-readable
4. filesystem-safe
5. used consistently throughout the drone pipeline

Acceptable example outputs:

- `AOP_GOLDHILL_20230814`
- `AOP_GORDON_20230814`
- `SPR2_20230628`
- `SH67_1_20230707`

The exact formatting can vary slightly, but it must preserve flight uniqueness and date.

### 2.3 Date handling

Infer the date from the parent folder name when possible, converting patterns like `MM-DD-YY` into `YYYYMMDD`.

If the package name does not contain a parseable date, fall back in a deterministic and documented way, but prefer preserving the date from the package folder whenever available.

### 2.4 Do not use the inner HDF5 name as the drone identity

The inner filename may still be useful for diagnostics, but it must not be the primary unique flight stem for the drone pipeline.

## Part 3: output organization

### 3.1 Per-flight directories

Under the drone run root, create a subdirectory per flight stem.

Preferred structure:

- `drone_outputs/run_drone_pipeline/<flight_stem>/...per-flight files...`

### 3.2 Per-flight files

All flight-specific artifacts should live inside that flight directory, including for example:

- working H5 copy
- ENVI files
- corrected rasters
- polygon parquet
- polygon index parquet
- per-flight QA JSON
- per-flight QA PNG
- any other per-flight intermediates

Use the unique flight stem consistently in filenames, e.g.:

- `<flight_stem>__working.h5`
- `<flight_stem>__envi.img`
- `<flight_stem>__corrected.img`
- `<flight_stem>__polygons.parquet`
- `<flight_stem>__qa.json`
- `<flight_stem>__qa.png`

### 3.3 Run-level files

Keep only true run-level aggregate products in the run root, such as:

- `drone_qa_summary.json`
- `drone_merged.parquet`

### 3.4 Collision prevention

Add a lightweight guard against duplicate derived flight stems within one run.

If two different inputs would produce the same stem, fail clearly or disambiguate in a deterministic way.

But the preferred helper should already make collisions unlikely.

## Part 4: QA isolation and bookkeeping

You do not need to redesign QA plotting. But you do need to ensure the drone QA is not accidentally mixing flights.

Please confirm that:

- each flight’s QA paths are derived from that flight’s unique stem
- each flight’s QA reads that flight’s own inputs/outputs
- the run-level QA summary distinguishes flights by the new flight stem
- repeated warnings are not just a side effect of output collisions

If small path or bookkeeping fixes are needed for QA isolation, make them.

## What to inspect

Please inspect the current code and identify exactly where these values are currently derived and propagated:

- drone base name / stem
- working H5 path
- ENVI output path
- corrected raster path
- polygon parquet path
- polygon index path
- QA JSON path
- QA PNG path
- merged parquet path
- entries in the run-level QA summary

Find where the current drone path is collapsing many distinct packages onto the same base identity and fix that propagation consistently.

Likely files to inspect include:

- `src/spectralbridge/pipelines/drone.py`
- `src/spectralbridge/io/neon.py`
- `src/spectralbridge/neon_cube.py`
- any existing naming/path utilities already used by the drone pipeline

Make the smallest clean changes needed.

## Preferred code shape

A good final structure would likely include:

- a small helper to derive a drone flight stem from the parent export-package folder
- a small helper to prepare a drone working H5 copy and patch no-data attrs if needed
- `run_drone_pipeline()` using those helpers before downstream processing begins
- per-flight output paths built from `run_root / flight_stem / ...`

This is preferred over broad reader refactors.

## Tests

Add the **minimum number of high-value tests**.

Keep them lightweight.

### Required test 1: standard NEON strictness preserved

Add a focused test proving that the normal strict NEON path still behaves the same when missing no-data metadata and the caller has not opted into any drone-only preparation.

If you keep the NEON reader unchanged, this can be a small test or existing-reader assertion that strict behavior remains intact.

### Required test 2: drone preparation patches only the working copy

Add a focused unit test that:

- creates a tiny synthetic HDF5 file without no-data attrs
- runs the new drone preparation helper
- confirms the prepared working copy now contains the patched attrs
- confirms the original file was not modified

This is one of the most important tests.

### Required test 3: unique stem derivation from parent package folder

Add a focused test showing that two drone inputs with the same inner HDF5 filename but different parent package folders produce different flight stems.

Example concept:

- `.../SPR1-06-28-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5`
- `.../SPR2-06-28-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5`

These must produce different stems.

### Required test 4: per-flight output paths do not collide

Add a focused test showing that two different drone package inputs with the same inner HDF5 filename get different output directories and output file paths.

This can be a pure path-building unit test.

### Required test 5: drone pipeline uses the preparation + naming path

Add a focused test, likely with mocking, showing that `run_drone_pipeline()`:

- derives the drone flight stem from the parent package folder
- prepares the working copy before downstream reading
- writes paths under the per-flight directory

This does not need to be a heavy end-to-end processing test.

## Coding style

- make minimal, surgical changes
- add concise comments/docstrings explaining the drone-only workaround
- avoid broad refactors
- keep the patch easy to review
- prefer readability and explicitness over cleverness

## Final deliverables

1. Implement the drone-only HDF5 preparation fix
2. Implement the drone-native flight-stem naming fix
3. Implement per-flight output organization
4. Add the targeted tests
5. Run the relevant tests
6. Provide a final summary that explicitly states:
   - what changed
   - where the drone-only compatibility logic lives
   - how the flight stem is now derived
   - how collisions are prevented
   - that original HDF5 files are not modified
   - why the existing NEON pipeline behavior is still preserved
   - what tests were added
   - what the next most likely downstream issue is, if any

## Final reminder

This task is **not** “make the NEON reader more permissive.”

This task **is**:

Add a drone-only compatibility shim and a drone-native naming/output scheme so the new drone pipeline works correctly while the existing NEON pipeline remains untouched.

Build exactly that.
```
## 2026-03-22 - drone runtime reporting cleanup
Branch: work

```text
You are working in the `spectralbridge` repository.

Task:
Clean up the runtime reporting for the **drone pipeline only**. Do not change reporting behavior for the standard NEON pipeline.

Goal:
Make `run_drone_pipeline()` much easier to monitor during long runs by adding a clear progress display, per-flight status reporting, and distinct visual treatment for:
1. normal in-progress / success
2. no polygon overlap
3. other errors

Important guardrail:
This is for the **drone pipeline only**. Do not break or materially alter the NEON pipeline.

## Desired behavior

### 1. Overall batch progress
At the start of the run, report:
- total number of flight packages discovered
- number that will be processed
- polygon path, if provided
- run root output directory

During the run, show progress through the flight list:
- current index / total
- flight stem
- current stage if practical

Examples of stages:
- preparing H5
- converting to ENVI
- correcting
- polygon extraction
- QA
- finished

### 2. Progress bar
Add a real progress bar for the drone batch if possible.

Preferred implementation:
- use `tqdm` if it is already available or acceptable to use here

If a true progress bar is difficult in the current environment, use a robust textual fallback. But strong preference is a real progress bar.

### 3. Color-coded status
Use distinct colors in the drone progress/reporting output:

- **normal processing / success**: green or default success color
- **no polygon overlap**: yellow
- **other error**: red

If using `tqdm`, it is acceptable to combine:
- a batch progress bar
- explicit colored log/status lines for per-flight outcomes

If changing the actual bar color itself is awkward with the chosen implementation, that is okay, but the user-visible output must still clearly distinguish these three states with color-coded messages.

### 4. Per-flight reporting
For each flight, show:
- `[current/total]`
- flight stem
- source package name or path
- final outcome:
  - success
  - skipped_no_polygon_overlap
  - failed_other

Also show:
- elapsed time for that flight
- optional ETA after a few flights complete

Examples:
- `[drone] [3/17] AOP_MRS1_20230814 ...`
- `[drone] [3/17] AOP_MRS1_20230814 -> skipped_no_polygon_overlap (12.4 s)`
- `[drone] [4/17] AOP_GORDON_20230814 -> success (41.8 s)`
- `[drone] [5/17] AOP_XYZ_20230814 -> failed_other: <short reason> (8.1 s)`

### 5. No-overlap handling
When polygon extraction finds zero intersected pixels:
- do not kill the batch
- classify it distinctly, e.g. `skipped_no_polygon_overlap`
- show that outcome in yellow
- continue processing the remaining flights

This is expected behavior for some flights and should not look like a catastrophic pipeline failure.

### 6. Other errors
Unexpected exceptions should:
- be classified separately as `failed_other`
- be shown in red
- continue the batch unless current architecture absolutely requires aborting
- still be recorded in the run summary

### 7. End-of-run summary
At the end, print a concise summary with:
- total discovered
- total attempted
- success count
- skipped_no_polygon_overlap count
- failed_other count
- total wall time
- average successful flight time if easy
- run root
- QA summary JSON path
- merged parquet path, if produced

Example:
- `[drone] Complete: 17 total | 13 success | 2 skipped_no_polygon_overlap | 2 failed_other | 14m 22s total`

## Implementation guidance

Keep this local to the drone pipeline.

Good implementation pattern:
- one batch progress bar for flights
- one helper for colorized status messages
- one clean status enum/string set:
  - `success`
  - `skipped_no_polygon_overlap`
  - `failed_other`

Likely place to implement:
- `src/spectralbridge/pipelines/drone.py`

Please inspect the current call flow and make the smallest clean change.

## Environment / display constraints
This may run in terminal, notebook, or cloud logs. Make the reporting robust.

Prefer:
- `tqdm.auto` if using tqdm
- color via a lightweight approach already present in the repo, or ANSI color codes if acceptable
- avoid brittle UI assumptions

If progress-bar color changes per-flight are not practical with a single persistent bar, then:
- keep the main bar stable
- emit color-coded per-flight status lines
- ensure yellow is used for no-overlap and red for other errors

That is an acceptable outcome.

## Data / summary behavior
Make sure:
- successful flights are still included in merged outputs
- no-overlap flights are not merged
- failed_other flights are not merged
- summary JSON records the distinct statuses

## Tests
Add the minimum number of high-value tests.

Required tests:
1. A test that drone runtime reporting includes total flight count and per-flight progress information.
2. A test that no-overlap flights are classified as `skipped_no_polygon_overlap` and reported distinctly.
3. A test that other exceptions are classified as `failed_other` and reported distinctly.
4. A test that the batch continues after both a no-overlap case and another error.
5. A test that the final summary includes the three counts:
   - success
   - skipped_no_polygon_overlap
   - failed_other

Keep tests lightweight. Mock where appropriate. Avoid brittle assertions on exact timing text.

## Coding style
- minimal, surgical changes
- keep the code readable
- avoid broad refactors
- add concise comments/docstrings only where useful
- do not modify standard NEON pipeline behavior

## Final summary
After implementing, report:
- what progress/reporting changes were made
- whether tqdm or a textual fallback was used
- how colors are assigned
- how no-overlap vs other errors are classified
- what tests were added
- confirmation that the NEON pipeline behavior was not changed
```
## 2026-03-22 - drone projection overlay diagnostics
Branch: work

```text
You are working in the `spectralbridge` repository.

Task:
Add projection / overlay diagnostics to the **drone pipeline only** so we can detect whether polygons are being matched to flight lines correctly.

Do **not** modify the standard NEON pipeline.

## Goal

We suspect some drone flights may be failing or producing only nodata because the supplied polygons are not overlaying the flight rasters correctly after reprojection.

Add lightweight, high-value diagnostics to the drone pipeline so that for each flight we can tell:

- raster CRS
- raster bounds
- raster transform
- raster nodata
- polygon CRS
- polygon bounds in original CRS
- polygon bounds after reprojection to raster CRS
- whether the reprojected polygon bounds overlap the raster bounds
- optionally, how many polygons intersect the raster bounds before pixel extraction

This is for debugging and reporting. Keep it local to the drone workflow.

## Guardrails

- Do not change the behavior of the NEON pipeline.
- Do not broadly refactor shared geospatial code unless absolutely necessary.
- Prefer minimal, surgical changes in `src/spectralbridge/pipelines/drone.py` and any small local helpers.
- If shared helpers are needed, they must not change NEON behavior.

## Required behavior

### 1. Add drone-only spatial diagnostics per flight

Before polygon-pixel extraction in the drone pipeline, compute and report:

For the raster being used for polygon extraction:
- raster path
- raster CRS
- raster bounds
- raster transform
- raster width / height
- raster nodata value

For the supplied polygon dataset:
- polygon path
- polygon CRS
- polygon total bounds in original CRS
- polygon count

After reprojection to raster CRS:
- reprojected polygon CRS
- reprojected polygon total bounds
- whether reprojected polygon bounds intersect raster bounds
- optional count of polygons whose bounds intersect raster bounds

These diagnostics should be available in:
- per-flight logging
- the per-flight summary entry / run-level QA summary JSON if practical

### 2. Improve no-overlap reporting

When the drone pipeline reaches the condition:
`No pixels intersected the supplied polygons`

do not treat it as an opaque generic failure.

Instead, in the drone pipeline only:
- classify it distinctly, e.g. `skipped_no_polygon_overlap`
- include the spatial diagnostics above in the recorded result if practical
- continue the batch

The point is to make it obvious whether the issue is:
- true non-overlap
- CRS mismatch
- suspicious georeferencing mismatch

### 3. Optional quick overlay artifact

If it is easy and safe, add a simple per-flight debug artifact for drone runs only when polygons are supplied:

- a small PNG showing raster bounds box and reprojected polygon boundaries in the same CRS

This should be lightweight, not a fancy map.
It can simply plot:
- raster bounds as a rectangle
- reprojected polygons as outlines

Save it in the per-flight folder with a clear name like:
- `<flight_stem>__overlay_debug.png`

This is optional but strongly preferred if easy.

Important:
- do not make this block the pipeline if plotting fails
- only do this in the drone pipeline
- keep it lightweight

### 4. Check both likely raster targets if relevant

Inspect the current drone code and determine which raster is actually used for polygon extraction.

If useful, report diagnostics for:
- the ENVI raster
- the corrected raster

But do not add unnecessary noise. The key thing is to diagnose the raster actually used for polygon intersection/extraction.

### 5. Logging quality

Improve the runtime logs so that for each flight the user can tell:
- what CRS the raster is in
- what CRS the polygons started in
- whether reprojection happened
- whether bounds overlap before pixel extraction
- whether the flight was skipped due to no overlap

Example style:
- `[drone] [3/17] AOP_MRS1_20230814 raster_crs=EPSG:32613 polygon_crs=EPSG:4326 overlap_after_reproject=False`
- `[drone] [3/17] AOP_MRS1_20230814 -> skipped_no_polygon_overlap`

Keep the logs concise and readable.

## Implementation guidance

Please inspect the current polygon extraction path in the drone pipeline and identify where reprojection currently happens.

Likely area:
- `src/spectralbridge/pipelines/drone.py`
- especially near `_build_polygon_pixel_index_for_raster(...)` and the call site in `run_drone_pipeline()`

Add a small, local helper if useful, such as:
- `collect_drone_spatial_diagnostics(...)`
- `save_drone_overlay_debug_plot(...)`

Good output structure:
- per-flight diagnostics attached to the flight result record
- optional overlay PNG in the per-flight directory
- concise log lines during runtime

## Important behavioral constraints

- Do not alter the core NEON polygon extraction path unless absolutely necessary.
- Do not weaken NEON validation.
- Do not change NEON logging/reporting unless a shared helper is introduced in a way that preserves existing behavior exactly.

This is a drone-only diagnostics enhancement.

## Tests

Add the minimum number of high-value tests.

Required tests:
1. A test that the drone pipeline collects raster/polygon CRS and bounds diagnostics before polygon extraction.
2. A test that a no-overlap case is classified as `skipped_no_polygon_overlap` and includes diagnostic fields.
3. A test that polygons are reprojected to raster CRS before overlap diagnostics are computed.
4. If you implement the overlay PNG: a lightweight test that the debug plot function can run on a tiny synthetic example and writes an output file.
5. A test that the batch continues after one no-overlap flight.

Keep tests lightweight. Use tiny synthetic data, mocking, or temporary files. Do not add heavy integration tests.

## Final summary

After implementing, report:
- what diagnostics were added
- where they are recorded
- whether an overlay debug PNG was added
- how no-overlap is classified now
- confirmation that the NEON pipeline behavior was not changed
- what tests were added
```

## 2026-03-22 - drone per-flight parquet extraction
Branch: work

```text
Fix the drone pipeline so that it always writes one per-flight parquet before building the final merged parquet, regardless of whether polygon extraction is used.

Current expected behavior:
- Every flight should produce its own extracted parquet in that flight's output folder.
- After all per-flight parquets are written, the pipeline should merge them into one run-level merged parquet.
- This should happen in both modes:
  1. polygon extraction mode: only extract pixels intersecting polygons
  2. full-raster extraction mode: extract all valid pixels from the raster

Current bug:
- In full-raster mode (polygon_path=None), the pipeline appears to process rasters and write QA/corrected outputs, but does not write per-flight parquet files.
- Because no per-flight parquet files are created, the final merged parquet is also null.
- This is incorrect. We should never extract directly to the merged parquet. We should always write per-flight parquet first, then merge.

Required behavior:
1. Preserve current polygon extraction behavior, but ensure it writes a per-flight parquet in each flight folder.
2. In full-raster mode, write a per-flight parquet in each flight folder with the same general schema as the polygon mode / NEON-like outputs, minus polygon-specific fields.
3. After processing all flights, collect all per-flight parquet files and concatenate them into the run-level merged parquet.
4. Populate all summary fields accordingly:
   - per-flight parquet filename/path in each flight result
   - merged_path at run level
   - merged preview metadata in QA summary
5. Do not extract directly to the merged parquet. The merge stage must consume already-written per-flight parquet files.
6. Reuse existing extraction helpers if available. The only difference between modes should be the pixel selection mask:
   - polygon mode: intersecting pixels only
   - full mode: all valid pixels
7. Keep schemas as aligned as possible with existing NEON-style extraction outputs:
   - row, col, x, y, pixel_id, source_image, epsg
   - spectral band columns
   - polygon columns only when polygon extraction is used

Implementation guidance:
- Refactor the extraction stage so it is always called after correction.
- Pass an extraction mask or extraction mode into the same core extraction function rather than having separate downstream logic.
- Keep output naming consistent with the current flight-folder structure.

Definition of done:
- With polygons:
  - each flight with overlap gets a per-flight parquet
  - run-level merged parquet is created from those files
- Without polygons:
  - every successful flight gets a per-flight parquet
  - run-level merged parquet is created from those files
- The pipeline never relies on extracting directly into the merged parquet.

Add minimal tests:
- one test that polygon_path=None creates per-flight parquet files
- one test that merged parquet is created from those per-flight files
- one test that polygon mode still works unchanged
```
