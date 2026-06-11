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

## 2026-06-02 - publication cleanup review
Branch: main

```text
i want to clean up the repo but not delete anything. there is a depricated folder. If we feel like anything is deletable, we should move it to the depricated folder rather than actually delete it. I don't expect there to be much vestigial code or documentation but I want to streamline where I can. I like verbose documentation so it's a feature not a bug to have tones of documentation but let's make sure it's correct documentation like it says the correct thing in the correct place. We are about to start a full code review and I want you to do a review first. I want you to comb through everything and try to give feedback on what needs done. I want you to make sure we have an agents.md file and a prompt log in the repo and that the human read me is up to date and accurate. If you find any issues that you want me to fix or address, add them to a features request document as you go and we'll review that at the end. You are welcome to fix small things along the way but I don't want you to make major changes without permission because they may break the code. for example, we use a lot of parquet to speed things up but you love to go back to cvs as an instinct. Don't change our parquet or our chunking or things, just try to clean things up for publication. If there is a chance that it could break something, add it to the feature request list rather than doing it youself. We want this to be ready for publication now that it works the way we want.
```

## 2026-06-03 - continue feature request backlog
Branch: main

```text
do those now
```

## 2026-06-03 - next feature request set
Branch: main

```text
do the next set
```

## 2026-06-03 - continue next queue items
Branch: main

```text
do those next things
```

## 2026-06-03 - continue backlog after P10
Branch: main

```text
now do the next
```

## 2026-06-03 - release hygiene audit
Branch: main

```text
do the next one
```

## 2026-06-03 - dependency review
Branch: main

```text
do the next thing
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
## 2026-03-24 - explain median correction map
Branch: $(git branch --show-current 2>/dev/null || echo unknown)

```text
i don't understand the median correction map in the qa plot. does it perform the correction using a moving window? why do the datat look like that?
```

## 2026-04-10 - analyze BRDF chunking artifact
Branch: main

```text
The way we are chunking through brdf correction is creating a relic in the data. can you tell me about the current brdf function and how is it currently chunking and how easy is it to switch that to a rolling window to get rid of the artifact?
```

## 2026-04-10 - move legacy hytools correction module
Branch: main

```text
can we rename the legacy one as hytools and move to the depricated folder?
```

## 2026-04-10 - annotate topo chunking code
Branch: main

```text
can you show me the code that is chunking the topo?
```

## 2026-04-10 - annotate chunking functions for team readability
Branch: main

```text
can you annotate all those functions so the team can look at everything an know what's happeing? I think we can do a big annotation before each function to get all the big stuff and variable definitions done. Then do minimal annotations throughout the function just to give the general workflow. Where there is math happening, try to explain the math. no emoji. 
```

## 2026-04-10 - update docs for topo chunking
Branch: main

```text
Do we need to update the website to assist that documentation?
```

## 2026-04-10 - make docs updates
Branch: main

```text
yes make those updates to the documentation
```

## 2026-04-10 - debug drone QA flat outputs and nodata polygons
Branch: main

```text
i'm running the drone pipeline in a vm and the qa plots are all totally flat like we're not doing a correction. we have polygons overlaying but they seem to all be getting -9999 values
```

## 2026-04-10 - enable BRDF by default for drone pipeline
Branch: main

```text
let's turn it on by default
```

## 2026-04-10 - add CSV sidecars for drone parquet outputs
Branch: main

```text
after we make the parquet, we should make a csv from that parquet table. the csv is too slow for primary write but it's easier to open on more computers so we want a copy. 
```

## 2026-04-10 - keep drone QA rendering when CSV sidecars fail
Branch: main

```text
i'm not seeing the qa plots of qa .json anymore on the first run after all those updates 
```

## 2026-04-10 - keep polygon metadata on every drone pixel row
Branch: main

```text
the csv, and therefore the parquet file seem to not be keeping the polygon id information. we want all the polygon infroamtion to come alone. that means duplicating the polygon infromation across rows so that each row is for a pixel and each pixel knows what polygon it came from and then the data for the polygon will then say what speciees the polygon is representing and what other things we measured about that thing. 
```

## 2026-04-10 - fail drone correction when requested correction cannot run
Branch: main

```text
I think it's probably one of the first two. we want to know what happened. If we can't correct, we should not pass on the raw to the corrected file, we should fail to make a corrected file so that we know what happened. it shoudl also go in the qa json so we can see that hit happened. 
```

## 2026-04-10 - explain ndvi edges
Branch: main

```text
It's ok to have it I just didn't understand what it was doing. can you add some explanation to the code annotation and to the documentation on the website?
```

## 2026-04-10 - patch ndvi modeling error
Branch: main

```text
now let's patch that ndvi error so we're doing the modeling properly
```

## 2026-04-10 - fix ndvi handoff and drone QA correction status
Branch: main

```text
now can you try to fix the ndvi error? Also, in the qa plot the ouput on the top right says we corrected but the map on the bottom right says that we didn't. can you make sure the correction info is properly flowing to the output and to the qa plot?
```

## 2026-04-10 - restore brdf kernel parameter choice
Branch: main

```text
since we don't mask, we don't care that much about NDVI? we cut the mask because it was too computationally expensive with big files. we should add back in the kernel/parameter choice. i don't understand the group and sample thing
```

## 2026-04-10 - fix it up
Branch: main

```text
fix it up
```

## 2026-04-10 - fix brdf pytest regressions
Branch: unknown

```text
Run pytest -q
...FF..F...........................................ssss................. [ 64
## 2026-04-10 - fix brdf pytest regressions
Branch: unknown

```text
Run pytest -q
...FF..F...........................................ssss................. [ 64%]
..................s.....................                                 [100%]
=================================== FAILURES ===================================
________________________ test_outliers_masked_from_fit _________________________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_outliers_masked_from_fit0')

    def test_outliers_masked_from_fit(tmp_path: Path) -> None:
        unitless = np.full((3, 3, 2), 0.2, dtype=np.float32)
        unitless[..., 1] = 0.35  # ensure NDVI falls inside bins
        unitless[0, 0, 0] = 1.5  # beyond valid range and should be excluded
        scaled = unitless / 1e-4
        cube = _FakeCube(scaled, scale_factor=1e-4)

        coeff_path = fit_and_save_brdf_model(
            cube,
            tmp_path / "outlier",
            ndvi_config=NDVIBinningConfig(n_bins=1, ndvi_min=-1.0, perc_min=None, perc_max=None),
        )
        model = json.loads(coeff_path.read_text())

        valid_mean = float(np.mean(unitless[..., 0][unitless[..., 0] < 1.0]))
>       assert model["iso"][0][0] == pytest.approx(valid_mean, rel=0.6)
E       assert 0.0034788267221301794 == 0.20000000298023224 ± 0.12
E
E         comparison failed
E         Obtained: 0.0034788267221301794
E         Expected: 0.20000000298023224 ± 0.12

tests/test_brdf_scale.py:122: AssertionError
____________ test_correction_uses_saved_ndvi_edges_from_coeff_file _____________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_correction_uses_saved_ndv0')

    def test_correction_uses_saved_ndvi_edges_from_coeff_file(tmp_path: Path) -> None:
        red = np.float32(0.05)
        nir = np.float32(0.28333333)  # NDVI ~= 0.7
        unitless = np.stack(
            [
                np.full((2, 2), red, dtype=np.float32),
                np.full((2, 2), nir, dtype=np.float32),
            ],
            axis=-1,
        )
        cube = _FakeCube(unitless, scale_factor=1.0)

        coeff_dir = tmp_path / "scene"
        coeff_dir.mkdir()
        coeff_path = coeff_dir / "scene_brdf_model.json"
        payload = {
            "iso": [[1.0, 1.0], [1.0, 1.0]],
            "vol": [[0.0, 0.0], [2.0, 2.0]],
            "geo": [[0.0, 0.0], [0.0, 0.0]],
            "volume_kernel": "RossThick",
            "geom_kernel": "LiSparseReciprocal",
            "ndvi_edges": [0.0, 0.8, 1.0],
        }
        coeff_path.write_text(json.dumps(payload), encoding="utf-8")

>       corrected = apply_brdf_correct(
            cube,
            cube.data,
            0,
            cube.lines,
            0,
            cube.columns,
            coeff_path=coeff_path,
            ndvi_config=NDVIBinningConfig(
                n_bins=2,
                ndvi_min=0.0,
                ndvi_max=1.0,
                perc_min=None,
                perc_max=None,
            ),
        )

tests/test_brdf_scale.py:153:
...
E       TypeError: float() argument must be a string or a real number, not 'NoneType'

src/spectralbridge/corrections.py:726: TypeError
________ test_brdf_ratio_increases_reflectance_when_reference_brighter _________

    def test_brdf_ratio_increases_reflectance_when_reference_brighter():
        cube = _DummyCube()
        chunk = np.full((2, 2, 2), 0.1, dtype=np.float32)
        ndvi_config = NDVIBinningConfig(n_bins=1, ndvi_min=-1.0, ndvi_max=1.0)
        coeffs = {
            "iso": np.array([[0.8, 0.8]], dtype=np.float32),
            "vol": np.array([[0.1, 0.1]], dtype=np.float32),
            "geo": np.array([[0.1, 0.1]], dtype=np.float32),
            "volume_kernel": "RossThick",
            "geom_kernel": "LiSparseReciprocal",
            "ndvi_edges": [-1.0, 1.0],
        }
        cube.brdf_coefficients = coeffs
>       corrected = apply_brdf_correct(
            cube,
            chunk,
            0,
            2,
            0,
            2,
            ndvi_config=ndvi_config,
            reference_geometry=ReferenceGeometry(solar_zenith_deg=10.0),
        )

tests/test_brdf_topo_streamlined.py:57:
...
=========================== short test summary info ============================
FAILED tests/test_brdf_scale.py::test_outliers_masked_from_fit - assert 0.0034788267221301794 == 0.20000000298023224 ± 0.12

  comparison failed
  Obtained: 0.0034788267221301794
  Expected: 0.20000000298023224 ± 0.12
FAILED tests/test_brdf_scale.py::test_correction_uses_saved_ndvi_edges_from_coeff_file - TypeError: float() argument must be a string or a real number, not 'NoneType'
FAILED tests/test_brdf_topo_streamlined.py::test_brdf_ratio_increases_reflectance_when_reference_brighter - TypeError: float() argument must be a string or a real number, not 'NoneType'
(raylet) [2026-04-10 21:59:58,986 I 2922 2922] logging.cc:303: Set ray log level from environment variable RAY_BACKEND_LOG_LEVEL to 2 [repeated 4x across cluster] (Ray deduplicates logs by default. Set RAY_DEDUP_LOGS=0 to disable log deduplication, or see https://docs.ray.io/en/master/ray-observability/user-guides/configure-logging.html#log-deduplication for more options.)
Error: Process completed with exit code 1.
```
## 2026-04-10 - make ndvi brdf binning optional
Branch: unknown

```text
and the brdf was used in hytools to facilitate a mask so we don't really need it for the brdf? can we make it a user choice that is default off?
```
## 2026-04-10 - fix drone ndvi option regressions
Branch: unknown

```text
Run pytest -q
.....................FF......FF....FF.F..............ssss............... [ 63%]
....................s.....................                               [100%]
=================================== FAILURES ===================================
... drone pipeline failures after NDVI BRDF option patch ...
```
## 2026-04-10 - fix drone helper kwarg compatibility
Branch: unknown

```text
Run pytest -q
.....................FF......FF....FF.F..............ssss............... [ 63%]
....................s.....................                               [100%]
=================================== FAILURES ===================================
... drone pipeline failures due to unexpected brdf_kernel_config kwargs ...
```
## 2026-04-13 - improve drone QA bottom panels
Branch: unknown

```text
I want the bottom left figure of the qa panel to look like the overlay debug plot rather than the long skinny one thats there now. Also, the table on the bottom right we should show more columns or focus on the right most columns rather than left columns.
```
## 2026-04-13 - improve drone QA top-right and correction map
Branch: unknown

```text
The older version of this has a good version of the top right and a bad verson of the median correction map and the later version has a good median map but a bad band fidelaty plot. I would like all of these plots to be really good.
```
## 2026-04-13 - improve drone QA spectral and correction diagnostics
Branch: main

```text
Update the drone QA panel implementation in src/spectralbridge/qa_plots.py so the three weakest diagnostics become genuinely useful for debugging drone correction behavior.

Scope
This prompt covers the following three panels in the drone QA figure created by render_drone_panel(...):
	•	top-right: spectral panel
	•	row 3 left: wavelength-wise correction panel
	•	row 3 right: spatial correction map

The current QA figure is hiding important information by over-collapsing distributions into medians. I want to preserve readability, but make these panels diagnostic enough to understand whether corrections are real, how variable they are, and where they occur.

High-level goals
	1.	Top-right panel should show spectral variance, not just the raw and corrected medians.
	2.	Row-3-left panel should show the full distribution of correction effects across wavelengths, not just a single signed median line.
	3.	Row-3-right panel should better explain and diagnose the spatial correction pattern, especially for cases where one site shows a clear map and others look flat or uninformative.
	4.	Keep the rest of the drone QA layout unchanged unless required by these fixes.
	5.	Keep changes narrowly scoped to drone QA behavior. Do not regress non-drone QA.

Important context
	•	render_drone_panel(...) currently computes sampled spectral arrays:
	•	raw_sample
	•	corr_sample
	•	sample_mask
	•	The top-right and row-3-left diagnostics currently collapse too much information.
	•	The row-3-right panel currently uses the full raster spatially, but only one summary statistic across bands.
	•	The current sample cap is too small for debugging subtle site-to-site differences.

Required changes
	1.	Increase the sample size substantially for drone QA spectral diagnostics

In render_drone_panel(...), increase the current sampling cap from:

max_samples = min(25_000, raw_cube.shape[1] * raw_cube.shape[2])

to a much larger value, for example:

max_samples = min(250_000, raw_cube.shape[1] * raw_cube.shape[2])

Better option:
	•	add a keyword argument such as qa_max_samples: int = 250_000 to render_drone_panel(...)
	•	use that value when building raw_sample and corr_sample

Requirements:
	•	deterministic behavior should be preserved through the existing deterministic sampler
	•	do not change non-drone QA sampling behavior
	•	keep memory use reasonable

Reason:
	•	the current spectral diagnostics may be too lossy to reveal real variance or subtle correction behavior

	2.	Fix the top-right panel so it shows spectral variance, not just medians

Context
	•	The current top-right panel is rendered by _render_drone_band_fidelity(...).
	•	Right now it only plots two 1D summaries: raw median and corrected median.
	•	I want to keep those medians, but also show a cloud of sampled per-pixel spectra behind them so spread and variance are visible.

Update _render_drone_band_fidelity(...) to accept these additional arguments:
	•	raw_sample: np.ndarray | None = None
	•	corr_sample: np.ndarray | None = None
	•	sample_mask: np.ndarray | None = None
	•	keyword-only max_traces: int = 150

Implementation requirements
	•	keep the existing median line logic
	•	before plotting the medians, plot a deterministic subsample of individual raw and corrected spectra using the sampled arrays
	•	use sample_mask[:, j] to mask invalid per-band values for each sampled pixel
	•	exclude nodata-like values <= -9990 before plotting
	•	draw sampled traces first with low alpha and thin lines so they form a transparent cloud behind the medians
	•	then draw the median lines on top thicker and visually dominant
	•	preserve the existing band marker and band_map behavior
	•	update the title to something like Band Fidelity And Sampled Spectra

Implementation guidance
	•	do not plot all pixels; subsample to at most about 100 to 150 traces
	•	use deterministic sampling with a fixed RNG seed
	•	use very low alpha for sampled traces, around 0.02 to 0.06
	•	keep the median lines clearly readable on top
	•	do not smooth the individual traces
	•	it is fine to keep the existing display-only despiking for the median lines
	•	make the function robust when any sampled arrays are omitted, empty, or shape-mismatched

Also add a robust y-axis limit in _render_drone_band_fidelity(...) using only valid sampled values so a few bad values do not flatten the plot.
	•	use percentile-based limits from valid sampled values
	•	ignore invalid, nodata-like, and obviously contaminated values
	•	keep most of the real signal visible

Update the call in render_drone_panel(...) so _render_drone_band_fidelity(...) receives:
	•	raw_sample=raw_sample
	•	corr_sample=corr_sample
	•	sample_mask=sample_mask

Acceptance criteria for the top-right panel
	•	the panel visibly shows spread and variance through transparent sampled traces
	•	the raw and corrected median lines are still present and easy to see
	•	the panel no longer looks like it only contains two summaries
	•	the panel remains readable and is not flattened by a few extreme values

	3.	Fix the row-3-left panel so it shows correction distribution, not just signed median

Context
	•	The current implementation computes:
diff = corr_sample - raw_sample
delta_median = np.nanmedian(diff, axis=1)
	•	This produces only one signed median per wavelength.
	•	That is too insensitive and can remain near zero even when corrections are large but cancel in sign or are spatially heterogeneous.
	•	We want to show the distribution of correction effects across pixels for each wavelength.

Goal
Replace the existing Δ Median vs λ panel with a distribution-aware visualization that shows:
	•	signed central tendency
	•	spread / variance / dispersion
	•	magnitude of change through an absolute-delta summary

Update _correction_report(...)
Compute and return these arrays from diff:
	•	delta_median = np.nanmedian(diff, axis=1)
	•	delta_q25 = np.nanpercentile(diff, 25, axis=1)
	•	delta_q75 = np.nanpercentile(diff, 75, axis=1)
	•	delta_q10 = np.nanpercentile(diff, 10, axis=1)
	•	delta_q90 = np.nanpercentile(diff, 90, axis=1)
	•	delta_abs_median = np.nanmedian(np.abs(diff), axis=1)

Requirements for _correction_report(...)
	•	all computations must ignore invalid / nodata values
	•	continue excluding NaN and nodata-like values <= -9990
	•	continue protecting against spurious huge deltas due to contamination
	•	keep existing useful summary fields such as largest_delta_indices
	•	extend the return payload / dataclass cleanly rather than breaking downstream code

Update _render_delta(...) or equivalent rendering function for this panel
Replace the current single-line plot with:
	•	a shaded region between q10 and q90 with low alpha
	•	a shaded region between q25 and q75 with slightly higher alpha
	•	a solid line for delta_median
	•	a dashed line for delta_abs_median
	•	a horizontal reference line at 0

Example structure:

ax.fill_between(xs, delta_q10, delta_q90, alpha=0.15, label="10–90%")
ax.fill_between(xs, delta_q25, delta_q75, alpha=0.25, label="IQR")
ax.plot(xs, delta_median, linewidth=2.0, label="signed median Δ")
ax.plot(xs, delta_abs_median, linewidth=2.0, linestyle="--", label="median |Δ|")
ax.axhline(0, color="black", linewidth=0.8)

Strongly encouraged addition
	•	add a small number of faint sampled traces of diff[:, j]
	•	deterministic sampling with a fixed RNG seed
	•	very low alpha 0.02 to 0.05
	•	thin linewidth
	•	plotted behind everything else

Update the title from:
	•	Δ Median vs λ

to something more accurate, for example:
	•	Correction Distribution vs Wavelength
or
	•	Signed and Absolute Correction Across Bands

Axis labels should remain:
	•	x-axis: wavelength (nm)
	•	y-axis: reflectance Δ

Robustness requirements
	•	works if sample arrays are empty or partially invalid
	•	does not crash with NaNs or nodata
	•	avoids extreme outliers dominating the y-axis; percentile-based y-limits are acceptable

Why this matters
	•	median alone can hide real corrections due to sign cancellation
	•	percentile ribbons expose spread and heterogeneity across pixels
	•	median absolute delta gives a direct measure of correction strength
	•	together this makes the panel responsive to correction-level changes and diagnostically useful

Acceptance criteria for the row-3-left panel
	•	the panel visibly shows spread and distribution
	•	the absolute correction line responds when correction strength changes
	•	the plot no longer appears flat when corrections are present
	•	existing QA generation still runs and the panel remains readable

	4.	Fix the row-3-right panel so it better explains the spatial correction pattern

Context
	•	The current row-3-right panel is rendered by _render_drone_correction_magnitude(...).
	•	It computes something like:
diff = corr_cube - raw_cube on valid cells
abs_delta = np.nanmedian(np.abs(diff), axis=0)
	•	This is a spatial map of per-pixel median absolute correction across bands.
	•	It is useful, but too easy to misread and too limited when one site shows a good map and others look flat.

Goal
Keep the existing statistic, but make the spatial correction panel much more diagnostic by:
	•	clarifying what is being shown
	•	adding informative summary stats
	•	adding at least one additional spatial diagnostic that reveals tail behavior or thresholded change
	•	exposing support / validity so flat maps can be distinguished from low-information maps

Required updates to _render_drone_correction_magnitude(...)
A. Preserve the existing per-pixel median absolute correction map, but rename it more clearly
	•	update the title from Median |Correction| Across Bands to something like:
	•	Per-Pixel Median Absolute Correction Across Bands

B. Add summary statistics directly onto the panel as a text box
Include at minimum:
	•	global median of abs_delta
	•	95th percentile of abs_delta
	•	percent of pixels above a change threshold
	•	percent of valid pixels or median valid bands per pixel used in the map

C. Compute and expose at least one additional per-pixel spatial diagnostic from diff
Choose one of these preferred options, or both if layout allows:
	•	abs_delta_p90 = np.nanpercentile(np.abs(diff), 90, axis=0)
	•	changed_frac = np.nanmean(np.abs(diff) > change_threshold, axis=0) * 100.0

Strong preference:
	•	include changed_frac because it is very interpretable
	•	a reasonable default threshold would be around 0.01 reflectance units, but make it a named constant near the top of the file so it is easy to tune

D. Add support / validity information
Compute something like:
	•	valid_band_count = np.sum(valid_mask, axis=0)
	•	valid_band_fraction = np.mean(valid_mask, axis=0) * 100.0

Use this in one of these ways:
	•	annotate the panel text box with summary values from it
	•	or add a lightweight overlay / contour / side summary if that can be done without disrupting layout
	•	or return it in the JSON payload even if not directly plotted

E. Use robust display scaling and report the scale used
	•	continue using percentile-based vmax for the main map
	•	annotate the chosen vmax in the panel text box or title so users can interpret differences across sites

F. Return richer summary values to the QA payload JSON
Add or expose values such as:
	•	spatial_abs_delta_median
	•	spatial_abs_delta_p95
	•	spatial_abs_delta_p90
	•	spatial_abs_delta_max
	•	pixels_above_change_threshold_pct
	•	median_valid_bands_per_pixel
	•	change_threshold

The current payload already includes some correction stats. Extend it rather than replacing it.

Preferred implementation pattern for row-3-right
	•	keep the current map in the existing row-3-right slot
	•	improve the title and annotation
	•	compute the additional diagnostics and include them in the returned summary / JSON payload
	•	if you can add a second spatial map without disrupting the layout too much, do so only if it is very clean; otherwise prioritize the text box and payload metrics

Important
	•	do not accidentally convert this panel to sampled behavior; it should stay based on the full raster spatially
	•	this panel should continue using full-resolution spatial information

Acceptance criteria for the row-3-right panel
	•	the map title clearly states what statistic is being shown
	•	the panel now explains itself through summary stats
	•	the JSON payload contains enough values to compare Gordon, Ruby, and Goldhill numerically
	•	users can distinguish between truly tiny corrections and a misleadingly flat-looking display
	•	the panel remains readable and the layout is not cluttered

	5.	Testing

Add focused tests in the most appropriate existing test module, likely tests/test_drone_pipeline.py.

Top-right panel tests
At minimum verify:
	•	_render_drone_band_fidelity(...) works when sample arrays are omitted
	•	_render_drone_band_fidelity(...) accepts sampled arrays and plots additional traces
	•	the median lines are still present
	•	nodata-like values do not crash the function

A practical test pattern:
	•	create a small fake wavelength array
	•	create small raw and corrected median spectra
	•	create small 2D raw_sample, corr_sample, and sample_mask
	•	call _render_drone_band_fidelity(...) on a real matplotlib axis
	•	assert that the number of lines is greater when sampled arrays are passed than when omitted

Row-3-left panel tests
At minimum verify:
	•	_correction_report(...) now produces the extra quantile arrays and delta_abs_median
	•	_render_delta(...) can render those richer summaries without crashing
	•	nodata-like values and contaminated deltas are safely ignored

Row-3-right panel tests
At minimum verify:
	•	_render_drone_correction_magnitude(...) still returns the original spatial summary values or a compatible superset
	•	new summary values such as p95 or thresholded change are computed and finite when valid data exist
	•	the function remains robust when valid-mask support is sparse

If needed, refactor carefully so the computational part and plotting part can be tested separately.
	6.	Keep the changes narrowly scoped

Please do not:
	•	redesign unrelated drone QA panels
	•	change non-drone QA figures unless needed for shared helper compatibility
	•	introduce broad formatting churn
	•	change behavior outside the QA plotting path unless required for these diagnostics

Final acceptance criteria
	•	top-right panel now shows spectral variance through sampled trace clouds plus medians
	•	row-3-left panel now shows signed and absolute correction distribution across wavelengths
	•	row-3-right panel now better explains spatial correction magnitude and adds richer diagnostics
	•	drone QA figures become useful for comparing sites like Gordon, Ruby, and Goldhill
	•	a much larger spectral sample is used for the drone QA diagnostics
	•	tests cover the new behavior
	•	the implementation remains readable, robust, and narrowly scoped to the drone QA path

Please implement this directly in the repo.
```
## 2026-04-13 - decouple drone QA from polygon overlap and reorder invalid maps
Branch: main

```text
Create a narrowly scoped follow-up change for the drone QA path in spectralbridge.

This prompt is only for two fixes:
	1.	always run / render drone QA regardless of polygon overlap status
	2.	move the -9999 / invalid row to the bottom of the drone QA figure

Do not rework the other QA panels in this prompt.
Do not revisit the spectral variance or correction-distribution changes here.
Keep this focused.

Goal 1: always generate drone QA even when polygons do not overlap

Problem
	•	Right now the drone QA plot appears to be gated by polygon overlap or polygon extraction success.
	•	That is not what I want.
	•	Polygon presence should only affect extraction behavior.
	•	The correction products and drone QA figure should still be produced whether polygons overlap or not.

Required behavior
	•	Always generate the drone QA PNG and QA JSON whenever the raw and corrected ENVI products needed for QA exist.
	•	Do not gate QA generation on polygon overlap.
	•	Do not skip QA generation just because:
	•	polygon extraction returned zero rows
	•	polygons do not overlap the raster
	•	polygon file is empty
	•	polygon extraction failed
	•	merged parquet is missing because extraction did not produce output
	•	If polygons are provided, keep using them for extraction behavior only.
	•	If polygons are missing or invalid, QA should still render from the raster products.

Implementation guidance
	•	Find the part of the drone pipeline where QA generation is currently conditioned on polygon overlap, extraction success, or merged parquet existence.
	•	Decouple QA generation from those conditions.
	•	Treat polygon-derived outputs as optional inputs to the QA figure, not prerequisites.
	•	It is acceptable for the merged-preview panel to show a message such as:
	•	No merged parquet available
	•	Polygon extraction produced no overlapping rows
	•	Keep the polygon overlay debug panel if a polygon path exists, even if there is no overlap.
	•	If no polygon path exists at all, QA should still render and the polygon panel can display its existing no-polygon message.

Acceptance criteria for Goal 1
	•	Drone QA PNG is produced even when polygons do not overlap.
	•	Drone QA JSON is produced even when polygons do not overlap.
	•	Correction diagnostics still render regardless of polygon status.
	•	Polygon status affects extraction outputs only, not whether QA exists.

Goal 2: move the -9999 / invalid maps to the last row of the drone QA figure

Desired row order
Update render_drone_panel(...) so the figure rows are ordered like this:

Row 1
	•	left: original ENVI RGB preview
	•	right: spectral panel

Row 2
	•	left: wavelength-wise correction panel
	•	right: spatial correction magnitude panel

Row 3
	•	left: polygon overlay debug
	•	right: merged table preview

Row 4
	•	left: raw ENVI -9999 / invalid map
	•	right: corrected ENVI -9999 / invalid map

In other words:
	•	move the current invalid-map row to the bottom
	•	keep correction diagnostics above it
	•	keep polygon overlay and merged preview together above the invalid maps

Implementation requirements
	•	Update subplot assignment logic in render_drone_panel(...) only as needed for this reorder.
	•	Preserve titles, annotations, colorbars, and text boxes.
	•	Make sure the correction status box still appears on the intended spectral panel.
	•	Make sure any axis/grid exclusions still target the right panels after the reorder.
	•	Keep the overall figure readable.

Acceptance criteria for Goal 2
	•	The raw and corrected -9999 / invalid maps are the last row in the drone QA figure.
	•	The correction-related panels now appear before the invalid maps.
	•	The polygon overlay and merged preview stay together above the invalid maps.

Testing
Add or update focused tests for the two behaviors above.

At minimum verify:
	1.	QA can still be generated when polygon-related outputs are absent or when merged parquet is missing.
	2.	The reordered panel layout still renders without losing key annotations or crashing.

Keep the code changes narrowly scoped to the drone QA generation path.
Do not make unrelated refactors in this prompt.
```
## 2026-04-13 - instrument drone QA spectral sampling diagnostics
Branch: main

```text
Investigate whether the drone QA spectral diagnostics are unintentionally behaving like polygon-only summaries in polygon-mode runs, even though they are supposed to sample the full raster cubes.

This is a debugging / instrumentation task, not a broad refactor.
Do not redesign the QA figure in this prompt.
Do not change correction math yet unless you find a clearly necessary bug.
The goal is to flush out where the behavior is coming from.

Observed behavior to explain
	•	Drone QA runs without polygons tend to show signal across the full wavelength axis.
	•	Drone QA runs with polygons sometimes look like the spectral diagnostics are only reflecting the polygon-related subset, or only a narrow wavelength region.
	•	In the current QA plotting code, the spectral summaries are supposed to come from raw_cube, corr_cube, and both_valid, not from polygon-extracted parquet rows.
	•	We need to determine whether the QA plotting is actually sampling the full raster, and if so, why polygon-mode runs still behave differently.

Main question to answer
Are the drone QA spectral diagnostics actually built from the full raster cubes in polygon-mode runs, and if they are, what upstream difference is causing them to look polygon-limited?

Tasks
	1.	Instrument the QA sampling path in render_drone_panel(...)

Add targeted debug logging around the construction of:
	•	raw_cube
	•	corr_cube
	•	raw_valid
	•	corr_valid
	•	both_valid
	•	raw_sample
	•	corr_sample
	•	sample_mask

For each flightline, log at minimum:
	•	flightline ID / scene name
	•	raw cube shape
	•	corrected cube shape
	•	wavelengths count
	•	percent valid in raw_valid
	•	percent valid in corr_valid
	•	percent valid in both_valid
	•	sample array shapes
	•	number of bands with at least one valid sampled pixel
	•	valid sampled pixel counts per band
	•	min / median / max of valid sampled counts per band

Make this logging concise but informative.
It should be easy to compare across scenes like Gordon, Ruby, Goldhill, and no-polygon cases.
	2.	Explicitly verify whether spectral QA uses raster cubes or polygon-derived tables

Add a one-time debug statement in the spectral QA path making it explicit that:
	•	the top-right spectral panel is using sampled values from raw_cube and corr_cube
	•	the row-3-left correction-distribution panel is using diff = corr_sample - raw_sample
	•	polygon parquet rows are not the direct source for these two panels

This is partly for human confirmation while reading logs.
	3.	Check whether polygon-mode changes the raster products before QA

Add targeted comparisons for polygon vs non-polygon runs to determine whether the corrected raster content itself differs.

For each scene, log:
	•	np.nanmean(np.abs(corr_cube - raw_cube))
	•	np.nanmedian(np.abs(corr_cube - raw_cube))
	•	np.nanmax(np.abs(corr_cube - raw_cube))
	•	number / percent of pixels with any nontrivial correction above a small threshold

Use a named threshold constant near the top of the file, for example:
	•	_DRONE_CHANGE_THRESHOLD = 0.01

This will help distinguish:
	•	true no-op correction
	•	sparse correction
	•	catastrophic outliers

	4.	Check whether valid support collapses outside a subset of bands in polygon-mode runs

For the sampled QA arrays, compute and log per-band support such as:
	•	sample_valid_counts = np.sum(sample_mask, axis=1)
	•	percent of bands with support above small thresholds, e.g. >10, >100 sampled pixels

Also log the wavelength positions of bands with meaningful support.

Goal:
	•	determine whether polygon-mode runs retain valid support across the full wavelength range or only in a narrow subset

	5.	Check whether the corrected cube is effectively identical to the raw cube in some scenes

For scenes like GAH2 / Ruby where QA looks flat, verify whether:
	•	corr_cube is numerically almost identical to raw_cube
	•	correction is a true near-identity operation

Add concise logs such as:
	•	global mean absolute difference
	•	global median absolute difference
	•	fraction of finite comparisons above _DRONE_CHANGE_THRESHOLD

	6.	Check for catastrophic outliers in scenes like Goldhill

Add logs to identify whether a small number of pixels or bands are dominating the correction diagnostics.
For example:
	•	count of comparisons with abs(diff) > 1
	•	count with abs(diff) > 10
	•	count with abs(diff) > 100
	•	location or summary of the worst offending bands / pixels if practical

Do not add huge verbose dumps.
Keep it summarized.
	7.	Add a temporary QA payload / JSON debug block if helpful

If it helps comparison, extend the drone QA JSON payload with a small debug_sampling section containing:
	•	raw_cube_shape
	•	corr_cube_shape
	•	both_valid_pct
	•	sample_shape
	•	sample_valid_counts_per_band_summary
	•	bands_with_any_sample_support
	•	bands_with_gt10_support
	•	bands_with_gt100_support
	•	global_mean_abs_diff
	•	global_median_abs_diff
	•	fraction_above_change_threshold

Do this only if it can be kept compact and useful.
	8.	Keep changes narrowly scoped and safe

Do not:
	•	redesign the QA panels in this prompt
	•	change extraction behavior
	•	change correction behavior unless you find an obvious bug and can explain it clearly
	•	introduce a lot of unrelated cleanup

This task is for diagnosis first.

Deliverables
	1.	Add the targeted instrumentation and any compact JSON debug fields.
	2.	Summarize findings directly in code comments where appropriate if you confirm anything important.
	3.	If you identify a likely root cause, leave a short comment in the code or a concise note in the PR description explaining whether the issue is:
	•	plotting-path confusion
	•	valid-mask collapse
	•	true no-op correction
	•	outlier domination
	•	polygon-mode changing raster content upstream
	•	something else

Acceptance criteria
	•	We can clearly tell from logs whether top-right and row-3-left are sampling full raster cubes or not.
	•	We can compare polygon and non-polygon runs quantitatively.
	•	We can see whether polygon-mode causes valid support to collapse by band.
	•	We can distinguish no-op scenes from unstable-outlier scenes.
	•	The debugging additions are concise enough to be practical during development.
```
## 2026-04-13 - auto-build drone qa html summary after pipeline runs
Branch: main

```text
can you look at the code and try to find how to fix this?
```
## 2026-04-13 - switch drone qa summary from html to pdf
Branch: main

```text
can we make it a pdf instead of an html?
```
## 2026-04-13 - lock in larger drone qa spectral sample size
Branch: main

```text
Update the drone QA sampling strategy in src/spectralbridge/qa_plots.py to significantly increase sample size for spectral diagnostics while keeping performance and memory safe.
```
## 2026-04-13 - harden drone qa failure-mode diagnostics
Branch: main

```text
Implement a focused debugging and hardening pass for the drone QA path in spectralbridge to address three distinct failure modes that the current QA plots are revealing:
	1.	flat / no-op correction scenes
	2.	spatial maps dominated by extreme outliers
	3.	wavelength plots with missing chunks due to band-support collapse

This prompt is not for cosmetic plot cleanup alone. The goal is to make the QA both diagnose and explain these three cases clearly, while also hardening the correction diagnostics against misleading visual output.

Keep changes narrowly scoped to the drone QA / correction-diagnostic path.
Do not redesign unrelated pipeline behavior.
Do not remove existing QA information unless replacing it with a strictly better equivalent.

High-level goals
	•	distinguish true no-op correction scenes from healthy scenes
	•	distinguish outlier-dominated scenes from truly flat scenes
	•	expose per-band support so missing wavelength chunks are interpretable instead of mysterious
	•	make the spatial correction map more robust and informative
	•	add compact scene-level classification / warnings to the QA output and JSON

Failure mode 1: flat / no-op correction scenes

Problem
Some scenes appear completely flat in both the wavelength-wise correction panel and the spatial correction map. This indicates that corr_cube is effectively identical to raw_cube, or nearly so.

Required changes
	1.	Add scene-level correction-strength diagnostics from the full raster in the drone QA path.

After both cubes are loaded and valid masks are computed, calculate at minimum:

full_diff = np.where(both_valid, corr_cube - raw_cube, np.nan)
full_abs_diff = np.abs(full_diff)

global_mean_abs_diff = float(np.nanmean(full_abs_diff))
global_median_abs_diff = float(np.nanmedian(full_abs_diff))
global_p95_abs_diff = float(np.nanpercentile(full_abs_diff, 95))
fraction_above_change_threshold = float(
    np.nanmean(full_abs_diff > _DRONE_CHANGE_THRESHOLD) * 100.0
)
pixels_with_any_nontrivial_change_pct = float(
    np.nanmean(np.nanmax(full_abs_diff, axis=0) > _DRONE_CHANGE_THRESHOLD) * 100.0
)

Add a named constant near the top of the file:

_DRONE_CHANGE_THRESHOLD = 0.01

	2.	Add a no-op detection heuristic.

Define a compact rule that identifies scenes where correction is effectively a no-op. For example:
	•	global mean absolute diff is below a small threshold
	•	global median absolute diff is near zero
	•	fraction above change threshold is near zero

Use a clear named boolean such as:

is_effective_noop_correction = ...

	3.	Surface this in the QA output.

	•	Add a warning / classification line in the QA payload JSON
	•	Add a visible text warning in the spatial correction map panel or correction-status box such as:
	•	Effective no-op correction detected

Acceptance criteria for no-op detection
	•	scenes like Ruby / GAH2 are automatically labeled as near-identity / no-op if the data support that conclusion
	•	healthy scenes like Gordon are not mislabeled

Failure mode 2: spatial maps dominated by extreme outliers

Problem
Some scenes appear visually flat not because the correction is truly zero, but because a small number of catastrophic outliers stretch the map scale so much that the rest of the raster collapses into one color.

Required changes
4. Add outlier diagnostics to the drone QA path.

Compute and summarize counts like:

n_abs_diff_gt_1 = int(np.sum(full_abs_diff > 1))
n_abs_diff_gt_10 = int(np.sum(full_abs_diff > 10))
n_abs_diff_gt_100 = int(np.sum(full_abs_diff > 100))

Also identify the top offending wavelength bands from the full raster or sampled correction arrays, whichever is more practical and robust.
	5.	Improve the spatial correction panel computation and annotation.

Keep the existing per-pixel median absolute correction map, but add:
	•	spatial_abs_delta_p90 = np.nanpercentile(np.abs(full_diff), 90, axis=0)
	•	display_vmax_main and any clipping value used for display

	6.	Add a second, more robust spatial diagnostic.

Strong preference: compute and expose a thresholded change-fraction map:

changed_frac = np.nanmean(np.abs(full_diff) > _DRONE_CHANGE_THRESHOLD, axis=0) * 100.0

If layout allows cleanly, add this as an additional panel or inset. If layout should remain stable, then at minimum:
	•	compute it
	•	summarize it in the text box
	•	store it in the JSON payload

	7.	Use robust display scaling for the existing spatial map.

Continue to use percentile-based vmax, but harden it so a few catastrophic pixels do not destroy the display.

Preferred behavior:
	•	use a robust percentile for display, such as 95th or 99th percentile of finite abs_delta
	•	annotate the chosen vmax in the panel text box
	•	preserve unclipped statistics in JSON so the user can still see that outliers exist

	8.	Add an outlier-dominated scene heuristic.

For example, scenes can be flagged as outlier-dominated if:
	•	global median absolute diff is low
	•	but max or p95 is huge
	•	and counts above large thresholds are nontrivial

Add a compact scene classification such as:
	•	outlier_dominated_correction

Acceptance criteria for outlier handling
	•	scenes like Goldhill can be identified as outlier-dominated rather than just looking flat
	•	the spatial map becomes visually interpretable even when a few pixels explode
	•	the JSON preserves both robust and extreme-value summaries

Failure mode 3: wavelength plots with missing chunks due to support collapse

Problem
Some wavelength-wise correction plots only show activity in a narrow band range or appear to have missing chunks. This likely reflects band-support collapse, where few or no valid comparisons survive for many bands.

Required changes
9. Add explicit per-band support diagnostics.

From the sampled QA arrays, compute:

sample_valid_counts = np.sum(sample_mask, axis=1)
bands_with_any_support = int(np.sum(sample_valid_counts > 0))
bands_with_gt10_support = int(np.sum(sample_valid_counts > 10))
bands_with_gt100_support = int(np.sum(sample_valid_counts > 100))

Also keep or compute a compact summary:
	•	min / median / max sampled support per band
	•	wavelength positions of poorly supported bands if practical

	10.	Surface support in the wavelength-wise correction panel.

Add one of these cleanly:
	•	a secondary support line or shaded strip at the bottom showing normalized per-band support
	•	or a compact annotation box summarizing support coverage
	•	or both if the panel remains readable

Strong preference:
	•	visually mark unsupported / weakly supported bands so missing chunks are explained rather than just blank

	11.	Add a support-collapse heuristic.

Example:
	•	if many bands have very low or zero support, classify the scene as support-collapsed or band-support-limited

Add a compact label such as:
	•	band_support_collapsed

	12.	Update the row-3-left panel title / annotation if needed.

The panel should make it clear that it is based on valid sampled comparisons, and that missing sections may reflect insufficient support rather than zero correction.

Acceptance criteria for support diagnostics
	•	missing chunks in the wavelength plot become interpretable
	•	scenes with broad support look clearly different from scenes with narrow surviving support
	•	the QA JSON stores enough support information for scene-to-scene comparison

Scene classification summary
	13.	Add a compact scene classification block.

Based on the diagnostics above, classify each scene into one or more categories, for example:
	•	healthy_correction
	•	effective_noop_correction
	•	outlier_dominated_correction
	•	band_support_collapsed

Implementation guidance
	•	allow multiple flags if appropriate
	•	keep logic simple and interpretable
	•	store classification flags in the QA JSON
	•	render the most important warning(s) in the QA figure text annotations

Suggested logic examples
	•	healthy: nontrivial correction strength, broad support, not outlier-dominated
	•	no-op: near-zero mean/median diff and near-zero fraction above threshold
	•	outlier-dominated: low median diff but large max/p95 and many extreme outliers
	•	support-collapsed: low number of supported bands or strong concentration of support in a narrow subset

JSON / payload updates
	14.	Extend the drone QA JSON payload with compact new fields.

Include at minimum:
	•	global_mean_abs_diff
	•	global_median_abs_diff
	•	global_p95_abs_diff
	•	fraction_above_change_threshold
	•	pixels_with_any_nontrivial_change_pct
	•	n_abs_diff_gt_1
	•	n_abs_diff_gt_10
	•	n_abs_diff_gt_100
	•	bands_with_any_support
	•	bands_with_gt10_support
	•	bands_with_gt100_support
	•	sample_valid_counts_summary
	•	scene_classification
	•	change_threshold
	•	robust spatial-map display stats like chosen vmax

Keep the payload compact and human-readable.

Plotting constraints
	15.	Keep the current general drone QA layout unless a very small local addition is needed.

Do not perform a major layout redesign in this prompt.
If you add new visual content, prefer:
	•	annotation boxes
	•	support strips
	•	insets
	•	JSON payload enrichment

over large panel rearrangements.

Testing
	16.	Add focused tests for the new diagnostics and classification logic.

At minimum verify:
	•	no-op scenes can be detected from synthetic near-identity data
	•	outlier-dominated scenes can be detected from synthetic mostly-flat data with a few extreme values
	•	support-collapse metrics are computed correctly from synthetic sample masks
	•	the new JSON payload fields are present
	•	existing drone QA rendering still works without crashing

If helpful, factor small pure functions for:
	•	scene classification
	•	support summaries
	•	outlier summaries

so they can be tested directly.

Important constraints
	•	do not change extraction behavior
	•	do not change correction behavior unless you find a truly obvious bug and can justify it
	•	do not add heavy dependencies
	•	do not make unrelated refactors

Deliverables
	•	implement the new diagnostics
	•	make the QA output explicitly explain the three failure modes
	•	keep the implementation readable and compact
	•	leave short comments where the logic is especially non-obvious

Acceptance criteria
	•	flat / no-op scenes are explicitly identified instead of just looking blank
	•	outlier-dominated scenes are explicitly identified and the spatial map is visually interpretable
	•	missing wavelength chunks are explained by support diagnostics
	•	the QA JSON contains enough information to compare scenes side by side
	•	the drone QA figure becomes a diagnostic tool that distinguishes these cases clearly rather than leaving them ambiguous
```

## 2026-04-13 - harden drone pipeline qa semantics and nodata-aware sampling
Branch: main

```text
Implement a focused but comprehensive hardening pass for the drone pipeline so that correction and QA always run, polygon extraction is optional, and QA sampling is not dominated by -9999 / nodata edge zones.

This prompt is about pipeline semantics, nodata-aware sampling, and clearer QA behavior.
Do not hardcode any specific polygon layer or site-specific logic.
Polygon subsets are run-specific and may differ from run to run.

Core intended behavior
	•	All drone rasters should be corrected.
	•	All drone rasters should get QA products.
	•	If polygons are provided and they intersect, polygon extraction should run.
	•	If polygons are provided but do not intersect, correction and QA should still run, but polygon extraction should be skipped.
	•	If no polygons are provided, correction and QA should still run.
	•	Full extraction remains a separate option and should not be implicitly triggered just because polygons do not overlap.
	•	Merge only the extraction outputs that actually exist.

Problem summary
	1.	The current pipeline still treats no polygon overlap too much like a scene-level skip, even though correction and QA should still be produced.
	2.	Drone scenes contain large -9999 / nodata edge zones.
	3.	The current QA spectral sampling appears to spend too much sample budget in these nodata-heavy regions, then masks them later.
	4.	This can underrepresent valid interior data and make QA spectral plots look sparse, band-limited, or misleading.
	5.	We need nodata-aware sampling and clearer separation of correction/QA from extraction.

Goals
	1.	Decouple correction and QA from polygon extraction outcome.
	2.	Make QA spectral sampling operate on valid pixels after nodata masking.
	3.	Preserve deterministic sampling and broad spatial coverage.
	4.	Make no-overlap scenes report clearly as qa-only / no extraction rather than full failure.
	5.	Reduce misleading -9999 chaos in QA outputs without changing the science.

Required changes
	1.	Fix pipeline semantics so correction and QA always run

In the drone pipeline:
	•	correction should run for every discovered drone flightline that has the required raster inputs
	•	QA should run for every corrected flightline that has the required QA inputs
	•	polygon overlap should only determine whether polygon extraction runs
	•	no-overlap should not suppress correction or QA

Required behavior by case
A. polygons provided and overlap exists
	•	correction runs
	•	QA runs
	•	polygon extraction runs
	•	extraction outputs can be merged

B. polygons provided but no overlap exists
	•	correction runs
	•	QA runs
	•	polygon extraction does not run
	•	scene should not be treated as fully skipped if correction and QA succeeded
	•	result should be reported with a status that clearly means something like:
	•	qa_only_no_polygon_overlap
	•	or corrected_and_qa_but_not_extracted

C. no polygons provided
	•	correction runs
	•	QA runs
	•	no polygon extraction
	•	optional full extraction remains a separate mode only when explicitly requested

Implementation guidance
	•	Find where skipped_no_polygon_overlap is currently applied in a way that prevents downstream QA semantics from being represented correctly.
	•	Preserve useful warnings about polygon non-overlap, but do not treat them as scene-level stop conditions for correction/QA.
	•	Make sure results summaries distinguish:
	•	corrected + qa + extracted
	•	corrected + qa only
	•	true failure

	2.	Make drone QA sampling nodata-aware

Current problem
	•	large -9999 edge zones consume too many sample slots
	•	invalid areas are sampled first and masked later
	•	valid interior data may be underrepresented

Required change
Update the QA sampling helper used for drone spectral diagnostics so it samples from eligible valid pixels after nodata masking, rather than striding uniformly over the full raster grid.

Implementation pattern
Given the existing 3D band mask, compute a per-pixel eligibility mask such as:

pixel_valid_fraction = np.mean(mask, axis=0)
pixel_valid = pixel_valid_fraction >= _DRONE_QA_MIN_VALID_BAND_FRACTION

Add a named constant:

_DRONE_QA_MIN_VALID_BAND_FRACTION = 0.25

Then:
	•	collect eligible (row, col) coordinates from pixel_valid
	•	deterministically subsample those eligible coordinates up to the requested sample cap
	•	extract the full spectra at those coordinates
	•	return sampled spectra and sampled masks in the same shape expected by downstream QA plotting

Important
	•	Keep the sampling deterministic.
	•	Do not sample from -9999-dominated pixels just because they lie on a regular stride grid.
	•	Do not require every band to be valid; use a reasonable fraction threshold.
	•	Preserve broad spatial coverage across valid regions rather than sampling only a dense cluster.

	3.	Preserve deterministic and spatially representative sampling

Do not just randomly sample all eligible pixels without structure.
Use a deterministic approach that still spreads samples spatially across valid regions.

Acceptable strategies
	•	deterministic thinning over eligible coordinates
	•	deterministic subsampling with a fixed RNG seed
	•	or a simple grid-based approach restricted to eligible pixels

Strong preference
	•	eligible-pixel filtering first
	•	deterministic coordinate selection second

	4.	Add compact nodata-aware sampling diagnostics

Add QA debug fields and logs showing at minimum:
	•	total raster pixels
	•	eligible pixels after nodata / validity filtering
	•	eligible pixel fraction
	•	sampled pixel count
	•	sample fraction of eligible pixels
	•	minimum valid-band fraction threshold used

These should go into the drone QA JSON payload and concise logs.

Suggested JSON fields
	•	total_pixels
	•	eligible_pixels_for_sampling
	•	eligible_pixel_pct
	•	sampled_pixels
	•	sampled_vs_eligible_pct
	•	min_valid_band_fraction_for_sampling

	5.	Make nodata presence more explicit in QA without corrupting analysis

Important constraint
	•	do not use -9999 as real data in calculations
	•	do not silently replace invalid values with zero in scientific summaries

But do improve visual communication:
	•	keep analysis on valid data only
	•	clearly mark nodata / invalid regions and bands in QA displays
	•	continue using conspicuous nodata colors or markers where appropriate

If you already have masked-array map display logic, keep it consistent.
If not, use masked arrays for maps and explicit nodata marking in spectral displays.
	6.	Make merged-preview behavior less misleading when extraction is absent

If polygon extraction did not run because there was no overlap:
	•	QA should still render
	•	merged preview should clearly say something like:
	•	No merged parquet available because polygon extraction did not run
	•	or QA generated; no polygon extraction output for this scene

Do not let this panel imply the scene itself failed.
	7.	Keep full extraction as an explicit separate mode

Do not automatically trigger full extraction when polygons do not overlap.
That should remain a separate option and separate workflow path.

If there is already a full-extraction mode flag, leave it intact.
If not, do not invent one here unless it is already part of the repo design.
	8.	Result summary / status updates

Update scene-level and batch-level reporting so statuses reflect the intended semantics.
Examples of useful statuses:
	•	success_extracted
	•	success_qa_only_no_polygon_overlap
	•	success_qa_only_no_polygons
	•	failed_other

Keep naming aligned with repo conventions, but make sure the summary distinguishes:
	•	actual extraction success
	•	successful correction + QA without extraction
	•	true failures

	9.	Tests

Add focused tests for both semantics and nodata-aware sampling.

At minimum verify:
A. pipeline semantics
	•	when polygons do not overlap, correction and QA still run
	•	extraction does not run
	•	status reflects qa-only rather than full skip/failure

B. no-polygon case
	•	correction and QA still run
	•	no extraction is attempted unless explicitly requested elsewhere

C. nodata-aware sampling
	•	a raster with large -9999 edge zones no longer spends most sample slots on invalid edges
	•	sampled spectra come from eligible valid pixels
	•	deterministic behavior is preserved

D. downstream compatibility
	•	QA rendering still works with the new sampled output format
	•	JSON payload includes the new sampling diagnostics

If helpful, factor a small pure helper function for nodata-aware coordinate selection so it can be tested directly.
	10.	Keep changes narrowly scoped

Do not:
	•	hardcode any particular polygon layer
	•	hardcode any site-specific exceptions
	•	redesign unrelated QA panels
	•	change correction science beyond safe handling of nodata-aware sampling inputs
	•	auto-run full extraction when polygons do not overlap

Acceptance criteria
	•	correction runs for all drone scenes with valid raster inputs
	•	QA runs for all corrected drone scenes regardless of polygon overlap
	•	polygon extraction only runs when polygons are provided and intersect
	•	no-overlap scenes are reported as qa-only rather than treated like full scene skips
	•	QA spectral sampling is based on valid pixels after nodata removal
	•	large -9999 edge zones no longer dominate the sample budget
	•	QA JSON and logs clearly report sampling eligibility and scene status
	•	merged-preview messaging is no longer misleading when extraction did not occur

Deliverables
	•	updated drone pipeline semantics
	•	nodata-aware deterministic QA sampling
	•	clearer scene status reporting
	•	compact QA debug fields for sampling eligibility
	•	focused tests covering these behaviors

Keep the implementation readable and practical.
```

## 2026-04-13 - fix qa summary pdf malformed png handling
Branch: main

```text
  pytest -q
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.11.15/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.15/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.15/x64/lib
    CSCAL_TEST_MODE: unit
.....................................................................sss [ 54%]
s...................................sF.....................              [100%]
=================================== FAILURES ===================================
____________________ test_build_drone_qa_summary_writes_pdf ____________________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_build_drone_qa_summary_wr0')

    def test_build_drone_qa_summary_writes_pdf(tmp_path: Path) -> None:
        scene_a = tmp_path / "AAA_20230814"
        scene_b = tmp_path / "BBB_20230815" / "nested"
        scene_a.mkdir(parents=True)
        scene_b.mkdir(parents=True)

        qa_a = scene_a / "AAA_20230814__qa.png"
        qa_b = scene_b / "BBB_20230815__qa.png"
        qa_a.write_bytes(b"png-a")
        qa_b.write_bytes(b"png-b")
        (scene_a / "AAA_20230814__polygons.parquet").write_text("parquet", encoding="utf-8")

>       pdf_path = build_drone_qa_summary(tmp_path)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_qa_summary.py:20: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/spectralbridge/utils/qa_summary.py:80: in build_drone_qa_summary
    image = plt.imread(qa_png)
            ^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/matplotlib/pyplot.py:2614: in imread
    return matplotlib.image.imread(fname, format)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/matplotlib/image.py:1520: in imread
    with img_open(fname) as image:
         ^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/PIL/ImageFile.py:150: in __init__
    self._open()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <PIL.PngImagePlugin.PngImageFile image mode= size=0x0 at 0x7FBE10261150>

    def _open(self) -> None:
        assert self.fp is not None
        if not _accept(self.fp.read(8)):
            msg = "not a PNG file"
>           raise SyntaxError(msg)
E           SyntaxError: not a PNG file

/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/PIL/PngImagePlugin.py:766: SyntaxError
=============================== warnings summary ===============================
src/spectralbridge/polygons.py:21
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:21: DeprecationWarning: cross_sensor_cal is deprecated; use spectralbridge instead.
    from cross_sensor_cal.exports.schema_utils import ensure_coord_columns

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2233: RuntimeWarning: All-NaN slice encountered
    return np.nanmedian(masked, axis=(1, 2))

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:388: RuntimeWarning: All-NaN slice encountered
    delta_median = np.nanmedian(diff, axis=1)

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/numpy/lib/_nanfunctions_impl.py:1593: RuntimeWarning: All-NaN slice encountered
    return fnb._ureduce(a,

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:393: RuntimeWarning: All-NaN slice encountered
    delta_abs_median = np.nanmedian(np.abs(diff), axis=1)

tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2385: RuntimeWarning: All-NaN slice encountered
    abs_delta = np.nanmedian(full_abs_diff, axis=0)

tests/test_pipeline_convolution.py::test_pipeline_idempotence_skip_behavior
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/ray/_private/worker.py:2052: FutureWarning: Tip: In future versions of Ray, Ray will no longer override accelerator visible devices env var if num_gpus=0 or num_gpus=None (default). To enable this behavior and turn off this error message, set RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
    warnings.warn(

tests/test_polygon_pipeline.py::test_build_polygon_pixel_index
tests/test_polygon_pipeline.py::test_extract_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_merge_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_run_polygon_pipeline_for_flightline
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:1714: Pandas4Warning: The copy keyword is deprecated and will be removed in a future version. Copy-on-Write is active in pandas since 3.0 which utilizes a lazy copy mechanism that defers copies until necessary. Use .copy() to make an eager copy if necessary.
    polygon_ids = polygons["polygon_id"].astype("int64", copy=False)

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 10060 (\N{CROSS MARK}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 65039 (\N{VARIATION SELECTOR-16}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_qa_summary.py::test_build_drone_qa_summary_writes_pdf - SyntaxError: not a PNG file
Error: Process completed with exit code 1.
```

## 2026-06-02 - smoke and website test coverage review
Branch: main

```text
do we have good smoke tests for each of the functions and playwright tests for the website?
```

## 2026-06-02 - add smoke and website tests
Branch: main

```text
we can delete all the popclimtoy anything, that was a different repo that was accidentally pushed to this repo and is totally unrelated. can you remove those and then remove that from the feature request list. add the smoke tests and the playwright tests and clarify Ray. remove those form feature request list when done
```

## 2026-06-02 - resolve publication feature requests
Branch: main

```text
work through that list and do each one. document what you do so we know
```

## 2026-06-02 - root script container context
Branch: main

```text
the root script issue is because we run it in a container and that makes for some strange roots.
```

## 2026-06-02 - fix docs playwright heading selector
Branch: main

```text
Run python -m http.server 8000 --directory site > /tmp/spectralbridge-docs-http.log 2>&1 &
F                                                                        [100%]
=================================== FAILURES ===================================
_________________ test_docs_site_core_pages_render_in_browser __________________

    def test_docs_site_core_pages_render_in_browser() -> None:
        base_url = _docs_site_url()

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on local environment
            raise AssertionError(
                "Playwright is required for docs browser smoke tests. "
                "Install pytest-playwright/playwright and Chromium."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page_errors, console_errors, failed_assets = _collect_page_health(page, base_url)

            try:
                page.goto(base_url, wait_until="networkidle")
                assert "SpectralBridge" in page.title()
>               assert page.get_by_role("heading", name="SpectralBridge").is_visible()
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_docs_playwright.py:67:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/sync_api/_generated.py:19208: in is_visible
    self._sync(self._impl_obj.is_visible(timeout=to_milliseconds(timeout)))
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_locator.py:548: in is_visible
    return await self._frame.is_visible(
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_frame.py:411: in is_visible
    return await self._channel.send(
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x7f41e959b050>
cb = <function Channel.send.<locals>.<lambda> at 0x7f41db8814e0>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: Locator.is_visible: Error: strict mode violation: get_by_role("heading", name="SpectralBridge") resolved to 2 elements:
E               1) <h1 id="spectralbridge">…</h1> aka get_by_role("heading", name="SpectralBridge ¶")
E               2) <h2 id="what-spectralbridge-does">…</h2> aka get_by_role("heading", name="What SpectralBridge does ¶")
E
E           Call log:
E               - checking visibility of get_by_role("heading", name="SpectralBridge")

/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py:559: Error
=========================== short test summary info ============================
FAILED tests/test_docs_playwright.py::test_docs_site_core_pages_render_in_browser - playwright._impl._errors.Error: Locator.is_visible: Error: strict mode violation: get_by_role("heading", name="SpectralBridge") resolved to 2 elements:
    1) <h1 id="spectralbridge">…</h1> aka get_by_role("heading", name="SpectralBridge ¶")
    2) <h2 id="what-spectralbridge-does">…</h2> aka get_by_role("heading", name="What SpectralBridge does ¶")

Call log:
    - checking visibility of get_by_role("heading", name="SpectralBridge")
Error: Process completed with exit code 1.
```
## 2026-06-02 - fix failing pytest smoke tests
Branch: main

```text
Run pytest -q
.................s....................................................ss [ 24%]
ss...................................................................... [ 48%]
.....................................F................F................. [ 72%]
............................................FFF.............s........... [ 96%]
...........                                                              [100%]
=================================== FAILURES ===================================
_ test_public_function_import_and_signature_smoke[spectralbridge.mask_raster.find_raster_files] _

module_name = 'spectralbridge.mask_raster', function_name = 'find_raster_files'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = importlib.import_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.mask_raster' has no attribute 'find_raster_files'

tests/test_public_api_smoke.py:53: AttributeError
_ test_public_function_import_and_signature_smoke[spectralbridge.pipelines.download.run_download] _

module_name = 'spectralbridge.pipelines.download'
function_name = 'run_download'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
>       module = importlib.import_module(module_name)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_public_api_smoke.py:52: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1204: in _gcd_import
    ???
<frozen importlib._bootstrap>:1176: in _find_and_load
    ???
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

name = 'spectralbridge.pipelines.download'
import_ = <function _gcd_import at 0x7fef9674fd80>

>   ???
E   ModuleNotFoundError: No module named 'spectralbridge.pipelines.download'

<frozen importlib._bootstrap>:1140: ModuleNotFoundError
_ test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.apply_resampler] _

module_name = 'spectralbridge.standard_resample'
function_name = 'apply_resampler'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = importlib.import_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.standard_resample' has no attribute 'apply_resampler'

tests/test_public_api_smoke.py:53: AttributeError
_ test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.load_envi_data] _

module_name = 'spectralbridge.standard_resample'
function_name = 'load_envi_data'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = importlib.import_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.standard_resample' has no attribute 'load_envi_data'

tests/test_public_api_smoke.py:53: AttributeError
_ test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.translate_to_sensor] _

module_name = 'spectralbridge.standard_resample'
function_name = 'translate_to_sensor'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = importlib.import_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.standard_resample' has no attribute 'translate_to_sensor'

tests/test_public_api_smoke.py:53: AttributeError
=============================== warnings summary ===============================
src/spectralbridge/polygons.py:21
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:21: DeprecationWarning: cross_sensor_cal is deprecated; use spectralbridge instead.
    from cross_sensor_cal.exports.schema_utils import ensure_coord_columns

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2233: RuntimeWarning: All-NaN slice encountered
    return np.nanmedian(masked, axis=(1, 2))

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:388: RuntimeWarning: All-NaN slice encountered
    delta_median = np.nanmedian(diff, axis=1)

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/numpy/lib/_nanfunctions_impl.py:1593: RuntimeWarning: All-NaN slice encountered
    return fnb._ureduce(a,

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:393: RuntimeWarning: All-NaN slice encountered
    delta_abs_median = np.nanmedian(np.abs(diff), axis=1)

tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2385: RuntimeWarning: All-NaN slice encountered
    abs_delta = np.nanmedian(full_abs_diff, axis=0)

tests/test_pipeline_convolution.py::test_pipeline_idempotence_skip_behavior
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/opentelemetry/util/_importlib_metadata.py:32: DeprecationWarning: SelectableGroups dict interface is deprecated. Use select.
    return EntryPoints(ep for group_eps in eps.values() for ep in group_eps)

tests/test_pipeline_convolution.py::test_pipeline_idempotence_skip_behavior
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/ray/_private/worker.py:2051: FutureWarning: Tip: In future versions of Ray, Ray will no longer override accelerator visible devices env var if num_gpus=0 or num_gpus=None (default). To enable this behavior and turn off this error message, set RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
    warnings.warn(

tests/test_polygon_pipeline.py::test_build_polygon_pixel_index
tests/test_polygon_pipeline.py::test_extract_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_merge_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_run_polygon_pipeline_for_flightline
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:1714: Pandas4Warning: The copy keyword is deprecated and will be removed in a future version. Copy-on-Write is active in pandas since 3.0 which utilizes a lazy copy mechanism that defers copies until necessary. Use .copy() to make an eager copy if necessary.
    polygon_ids = polygons["polygon_id"].astype("int64", copy=False)

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 10060 (\\N{CROSS MARK}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 65039 (\\N{VARIATION SELECTOR-16}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.mask_raster.find_raster_files] - AttributeError: module 'spectralbridge.mask_raster' has no attribute 'find_raster_files'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.pipelines.download.run_download] - ModuleNotFoundError: No module named 'spectralbridge.pipelines.download'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.apply_resampler] - AttributeError: module 'spectralbridge.standard_resample' has no attribute 'apply_resampler'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.load_envi_data] - AttributeError: module 'spectralbridge.standard_resample' has no attribute 'load_envi_data'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.standard_resample.translate_to_sensor] - AttributeError: module 'spectralbridge.standard_resample' has no attribute 'translate_to_sensor'
(raylet) [2026-06-02 17:59:49,806 I 2920 2920] logging.cc:303: Set ray log level from environment variable RAY_BACKEND_LOG_LEVEL to 2 [repeated 4x across cluster] (Ray deduplicates logs by default. Set RAY_DEDUP_LOGS=0 to disable log deduplication, or see https://docs.ray.io/en/master/ray-observability/user-guides/configure-logging.html#log-deduplication for more options.)
Error: Process completed with exit code 1.Run python -m http.server 8000 --directory site > /tmp/spectralbridge-docs-http.log 2>&1 &
F                                                                        [100%]
=================================== FAILURES ===================================
_________________ test_docs_site_core_pages_render_in_browser __________________

    def test_docs_site_core_pages_render_in_browser() -> None:
        base_url = _docs_site_url()

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on local environment
            raise AssertionError(
                "Playwright is required for docs browser smoke tests. "
                "Install pytest-playwright/playwright and Chromium."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page_errors, console_errors, failed_assets = _collect_page_health(page, base_url)

            try:
                page.goto(base_url, wait_until="networkidle")
                assert "SpectralBridge" in page.title()
                assert page.locator("h1#spectralbridge").is_visible()

                logo = page.locator("img[alt='SpectralBridge logo']").first
                assert logo.evaluate("(img) => img.naturalWidth") > 0

                page.goto(urljoin(base_url, "quickstart/"), wait_until="networkidle")
                assert page.get_by_role("heading", name="Quickstart").is_visible()

                page.goto(urljoin(base_url, "pipeline/outputs/"), wait_until="networkidle")
                assert page.get_by_role("heading", name="Outputs & File Structure").is_visible()
                assert page.get_by_text("_merged_pixel_extraction.parquet").first.is_visible()

                page.goto(base_url, wait_until="networkidle")
>               page.locator("label.md-search__icon[for='__search']").first.click()

tests/test_docs_playwright.py:80: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/sync_api/_generated.py:17422: in click
    self._sync(
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_locator.py:163: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_frame.py:569: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x7f40c70d2090>
cb = <function Channel.send.<locals>.<lambda> at 0x7f40c6bed620>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
E           Call log:
E             - waiting for locator("label.md-search__icon[for='__search']").first
E               - locator resolved to <label for="__search" class="md-search__icon md-icon">…</label>
E             - attempting click action
E               2 × waiting for element to be visible, enabled and stable
E                 - element is visible, enabled and stable
E                 - scrolling into view if needed
E                 - done scrolling
E                 - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
E               - retrying click action
E               - waiting 20ms
E               2 × waiting for element to be visible, enabled and stable
E                 - element is visible, enabled and stable
E                 - scrolling into view if needed
E                 - done scrolling
E                 - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
E               - retrying click action
E                 - waiting 100ms
E               57 × waiting for element to be visible, enabled and stable
E                  - element is visible, enabled and stable
E                  - scrolling into view if needed
E                  - done scrolling
E                  - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
E                - retrying click action
E                  - waiting 500ms

/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py:559: TimeoutError
=========================== short test summary info ============================
FAILED tests/test_docs_playwright.py::test_docs_site_core_pages_render_in_browser - playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("label.md-search__icon[for='__search']").first
    - locator resolved to <label for="__search" class="md-search__icon md-icon">…</label>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
    - retrying click action
      - waiting 100ms
    57 × waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <input type="text" required="" name="query" autocorrect="off" autocomplete="off" spellcheck="false" aria-label="Search" placeholder="Search" autocapitalize="off" class="md-search__input" data-md-component="search-query"/> intercepts pointer events
     - retrying click action
       - waiting 500ms
Error: Process completed with exit code 1.
```
## 2026-06-02 - hardening governance and drone pipeline validation
Branch: main

```text
# SpectralBridge Package Hardening, Drone Pipeline Validation, Release Readiness, and Agent Governance

## Mission

SpectralBridge is evolving from a research codebase into reusable scientific infrastructure.

The priorities of the project are:

1. Correctness
2. Reproducibility
3. Restart safety
4. Transparency
5. Validation
6. Maintainability
7. Performance

Performance optimizations should never compromise correctness, restartability, reproducibility, or QA transparency.

The goal of this effort is not to redesign SpectralBridge.

The goal is to strengthen and validate what already exists while preserving behavior.

---

# Priority 0 — Update AGENTS.md

Before making technical changes, review and update AGENTS.md.

The repository has reached a level of maturity where development process matters almost as much as implementation.

Future work should be:

- resumable
- test-driven
- reviewable
- reproducible
- restart-safe
- maintainable

---

## Feature-Request-Driven Development

Agents should treat:

text FEATURE_REQUESTS.md 

as the authoritative project work queue.

Required workflow:

1. Read FEATURE_REQUESTS.md.
2. Select highest-priority unfinished item.
3. Update FEATURE_REQUESTS.md before coding.
4. Implement changes.
5. Add tests.
6. Update documentation if required.
7. Update FEATURE_REQUESTS.md after completion.
8. Record blockers and next steps.

If interrupted:

- document status
- record remaining work
- identify blockers
- identify recommended next task

Future agents should be able to resume immediately.

---

## Testing Expectations

Work is not complete until:

- tests exist
- tests pass
- regressions are protected

Preference order:

1. Regression tests
2. Behavior tests
3. Contract tests
4. Integration tests
5. Refactors

New functionality without tests should be considered incomplete.

---

## Stability Requirements

Agents should protect:

- restart-safe execution
- chunked processing
- deterministic outputs
- QA transparency
- reproducibility

Do not trade stability for implementation convenience.

---

## Package Philosophy

SpectralBridge is scientific infrastructure.

Agents should favor:

- stable APIs
- explicit validation
- explicit status reporting
- backward compatibility
- additive improvements

Avoid unnecessary breaking changes.

---

## Data Processing Philosophy

Assume:

- large datasets
- cloud environments
- HPC environments
- CyVerse deployments
- ACCESS allocations
- laptops

Preserve:

- chunking
- checkpointing
- restart-safe behavior

Avoid:

- whole-scene loading
- memory-intensive shortcuts

unless clearly justified.

---

## HDF5 Contract Philosophy

SpectralBridge starts from HDF5.

Agents should not:

- add TIFF conversion logic
- repair malformed TIFF conversions

Instead:

- validate inputs
- document assumptions
- add regression tests

Input contracts should be explicit.

---

## Documentation Expectations

When public behavior changes:

Update:

- README
- docs
- examples
- feature requests

Documentation debt should not accumulate.

---

## Architecture Review Guidance

Avoid speculative refactors.

Before refactoring:

- identify duplication
- identify measurable benefit
- create feature request
- document rationale

Large architecture changes should be deliberate.

---

## Public API Guidance

Protect intentionally public APIs.

Examples:

python spectralbridge.go_forth_and_multiply spectralbridge.process_one_flightline spectralbridge.run_drone_pipeline 

Distinguish:

- public API
- implementation details

before making changes.

---

## CI Expectations

If a regression could have been caught by CI:

add a test.

Any change affecting:

text src/spectralbridge tests pyproject.toml workflows 

should consider CI coverage.

---

## Leave-The-Camp-Cleaner Rule

If an agent notices:

- broken docs
- stale comments
- missing tests
- dead code
- obvious bugs

they should either:

- fix it
- or create a feature request

No known issue should disappear from project memory.

---

## End-of-Work Reporting

At the end of work:

update FEATURE_REQUESTS.md with:

- completed items
- deferred items
- blockers
- next recommended task

---

## SpectralBridge Development Motto

Protect correctness.
Preserve restartability.
Prefer validation over assumptions.
Leave a trail for the next agent.

---

# Project Context

SpectralBridge processes:

- NEON airborne hyperspectral data
- drone hyperspectral data

Drone workflows start from HDF5 inputs.

A previously observed artifact was traced to an upstream TIFF→HDF5 conversion issue.

The translator failed to correctly preserve orientation.

This produced mirrored ancillary layers.

The upstream translator has now been fixed.

SpectralBridge should:

- NOT add TIFF conversion
- NOT repair malformed TIFF conversions
- validate and document HDF5 contracts

Chunking remains a required design principle.

---

# Priority 1 — HDF5 Orientation Contract Tests

Add regression tests protecting HDF5 orientation assumptions.

Requirements:

Use:

- tiny synthetic HDF5
- non-square arrays
- asymmetric values

Example:

text 11 12 13 14 21 22 23 24 31 32 33 34 

Include:

- reflectance
- slope
- aspect
- solar_zn
- solar_az
- sensor_zn
- sensor_az

Verify:

- reflectance alignment
- ancillary alignment
- transpose detection
- diagonal mirror detection
- row reversal detection
- column reversal detection

Document:

This protects against upstream TIFF→HDF5 orientation regressions.

---

# Priority 2 — Spectral Axis Orientation Tests

Protect _orient_cube() behavior.

Test:

text (lines, columns, bands) (bands, lines, columns) (lines, bands, columns) 

Verify:

- correct spectral-axis placement
- no spatial correction
- no mirroring
- no row/column flipping

---

# Priority 3 — Ancillary Raster Contract Tests

Protect ancillary shape assumptions.

Verify:

python cube.get_ancillary(...) 

fails clearly when ancillary dimensions do not match:

text (lines, columns) 

Requirements:

- explicit errors
- actionable messages

---

# Priority 4 — Preserve Chunked Processing

Chunking is required.

Do not replace chunked processing with whole-scene loading.

Preserve:

- chunked reading
- chunked correction
- chunked extraction
- restart-safe processing

If full-raster extraction is added:

- write chunk-by-chunk
- avoid full-scene memory loads
- preserve restart behavior

---

# Priority 5 — Per-Flight Parquet Validation

Every successful flight should produce a per-flight parquet.

Expected outputs:

Polygon mode:

text <flight_stem>__polygons.parquet 

Full extraction:

text <flight_stem>__extracted.parquet 

Merged output:

text drone_merged.parquet 

Requirements:

Review implementation.

Verify behavior.

Restore missing functionality using chunked processing if needed.

Add QA metadata:

- parquet path
- merge path
- CSV sidecar path
- extraction status
- skip reason
- failure reason

---

# Priority 6 — Drone QA and Failure-State Tests

Add:

- orientation tests
- polygon extraction tests
- no-polygon extraction tests
- chunking tests
- CRS tests
- overlap tests
- metadata preservation tests
- overlay image tests
- correction failure tests
- CSV failure tests

Protect behavior through tests.

---

# Priority 7 — Restart, Checkpoint, and Recovery Integrity

This is one of the most valuable guarantees in SpectralBridge.

Add tests covering:

### Partial restart

Reuse completed work.

### Corrupt intermediate recovery

Rebuild corrupt outputs.

### Missing downstream products

Resume correctly.

### Mixed-flight recovery

Recover selectively.

### Output validation

Validate before skipping.

### Explicit status reporting

Support statuses such as:

text skipped_existing_valid_output recomputed_missing_output recomputed_corrupt_output failed_validation 

---

# Priority 8 — Output Schema Stability

Protect schema contracts.

Required fields:

text flightline_id row col x y band wavelength_nm fwhm_nm reflectance 

Verify:

- names
- dtypes
- presence

Protect:

- ENVI parquet
- corrected parquet
- merged parquet

Verify polygon metadata survives extraction and merge.

---

# Priority 9 — Namespace and Container Compatibility

Context:

SpectralBridge runs in:

- Docker
- CyVerse
- ACCESS
- HPC
- JupyterHub
- cloud workspaces

Compatibility-first.

Keep:

python import spectralbridge 

canonical.

Preserve:

python import cross_sensor_cal 

compatibility.

Do not perform a breaking namespace migration.

Add tests for:

python import spectralbridge import cross_sensor_cal 

and key public imports.

Verify:

- imports
- warnings
- compatibility

Avoid:

- hardcoded paths
- cwd assumptions
- repo-root assumptions

Test CLI entry points.

Document preferred namespace.

---

# Priority 10 — CI Hardening

Expand CI coverage.

Trigger on:

text src/spectralbridge/** tests/** pyproject.toml .github/workflows/** 

Run:

bash pip install -e ".[tests]" ruff check src tests pytest -q tests/test_drone_pipeline.py pytest -q tests/test_qa python -c "import spectralbridge; print(spectralbridge.__version__)" 

Optional:

bash python -m build 

Keep CI practical.

---

# Priority 11 — Logging Review

Review:

- duplicate handlers
- notebook behavior
- multiprocessing behavior
- Ray behavior

Document findings.

Avoid major refactors.

---

# Priority 12 — Public API Contract Review

Protect intentionally public APIs.

Review whether current smoke tests are protecting the right contract.

Avoid accidentally freezing internal helpers into public APIs.

---

# Priority 13 — Release Hygiene

Audit:

- LICENSE
- README
- CITATION
- package resources
- MANIFEST

Verify:

- no large datasets
- no temporary outputs
- no prompt logs
- no development artifacts

ship unintentionally.

---

# Priority 14 — Versioning Review

Review:

- pyproject version
- package version
- release process

Prevent version drift.

---

# Priority 15 — Dependency Review

Review:

- ray
- geopandas
- rasterio

Document whether extras make sense.

Avoid breaking installs.

---

# Priority 16 — Documentation Modernization

Prefer:

python import spectralbridge 

in examples.

Retain compatibility documentation.

Document:

- HDF5 contract
- chunking strategy
- restart behavior
- parquet authority
- CSV sidecars
- drone workflows
- NEON workflows

---

# Priority 17 — Architecture Audit

Perform a lightweight architecture review.

Document findings only.

Review:

1. Duplicate metadata parsers
2. Duplicate path builders
3. Duplicate output discovery
4. Multiple chunking implementations
5. Restart-safe consistency
6. QA consistency
7. Shared drone/NEON infrastructure opportunities

Create feature requests instead of large refactors.

---

# Constraints

Do NOT:

- add TIFF conversion logic
- break NEON behavior
- perform namespace migrations
- perform speculative refactors
- add large fixtures

Prefer:

- synthetic test data
- tiny HDF5 fixtures
- tiny rasters
- tiny polygons

Keep changes reviewable.

---

# Recommended Execution Order

1. Update AGENTS.md
2. Update FEATURE_REQUESTS.md
3. Add HDF5 orientation tests
4. Add ancillary contract tests
5. Verify per-flight parquet behavior
6. Restore chunked no-polygon extraction if required
7. Add restart/checkpoint tests
8. Add schema tests
9. Expand CI
10. Add namespace compatibility tests
11. Perform hygiene review
12. Perform architecture review
13. Update docs

---

# Final Report Requirements

Report:

- AGENTS.md changes
- FEATURE_REQUESTS.md changes
- completed items
- remaining items
- blockers
- tests added
- CI updates
- chunking status
- parquet status
- namespace status
- restart-safe status
- documentation updates
- architecture findings
- commands executed
- test results
- build results

Explicitly confirm:

- TIFF conversion was not added
- NEON behavior was not changed
- chunking was preserved
- compatibility imports still work
- package remains installable
- tests pass
```
## 2026-06-02 - license migration and citation infrastructure audit
Branch: main

```text
# SpectralBridge License Migration, Citation Infrastructure, and Open Science Documentation

## Goal

Prepare SpectralBridge for long-term scientific infrastructure use by transitioning to Apache License 2.0 and ensuring all related documentation, metadata, citation infrastructure, and release materials are consistent.

This task is documentation-, governance-, and release-focused.

Do not perform unrelated refactors.

Do not modify scientific workflows, processing logic, chunking behavior, or pipeline architecture.

---

# First Step: Review Existing State

Before making changes:

Review:

- LICENSE
- README.md
- CONTRIBUTING.md
- AGENTS.md
- FEATURE_REQUESTS.md
- pyproject.toml
- package metadata
- GitHub templates
- release documentation
- existing citation files
- existing DOI references

Document current findings.

Identify inconsistencies.

Update FEATURE_REQUESTS.md with any discovered gaps before implementing changes.

---

# Target License

Recommended target:

text Apache License 2.0 

Rationale:

- NSF-compatible
- Open science compatible
- OSI-approved
- Commercial use allowed
- Modification allowed
- Redistribution allowed
- Explicit patent grant
- Appropriate for scientific cyberinfrastructure
- Preserves future commercialization opportunities

---

# License Audit

Determine:

1. Current repository license
2. License references throughout repository
3. Package metadata references
4. Documentation references
5. Release references

Create a checklist of locations that require updates.

---

# Apache 2.0 Migration

If repository maintainers approve migration:

Update:

- LICENSE
- package metadata
- pyproject.toml
- README references
- documentation references

Ensure consistency everywhere.

If legal review may be required:

Document migration steps rather than making assumptions.

Do not silently change legal ownership information.

---

# Add NOTICE File

Review whether Apache 2.0 requires a NOTICE file for current repository content.

If appropriate:

Create:

text NOTICE 

Include:

- project name
- copyright holders
- attribution information

Keep content concise.

---

# Add CITATION.cff

Create or update:

text CITATION.cff 

Include:

- project title
- project description
- repository URL
- preferred citation
- authors
- affiliations when available
- version support
- release support

Use current repository metadata.

If information is missing:

Add TODO notes for maintainers.

---

# Software Citation Documentation

Add a dedicated section to README.

Example structure:

## Citation

If you use SpectralBridge in research, please cite:

- the software release
- associated publications
- relevant methods papers

Also reference:

text CITATION.cff 

as the authoritative citation source.

---

# DOI and Release Infrastructure Review

Review current release process.

Document:

1. GitHub releases present?
2. Release tags present?
3. Semantic versioning used?
4. DOI generation configured?
5. Zenodo integration configured?
6. Citation workflow documented?

Create feature requests for any missing infrastructure.

Do not create external accounts.

Do not assume Zenodo is already configured.

---

# Open Science Documentation

Add documentation describing:

## Open Science Philosophy

SpectralBridge is intended to be:

- reusable scientific infrastructure
- reproducible
- transparent
- community driven

The project supports:

- open science
- reproducible workflows
- software citation
- interoperable data products

## Licensing Philosophy

The project uses Apache License 2.0 because it:

- supports broad adoption
- supports scientific collaboration
- supports commercial use
- supports future sustainability

## Citation Philosophy

Users should cite:

- software releases
- associated publications
- relevant methods papers

when using SpectralBridge in research.

---

# Commercialization Documentation

Add a short documentation section explaining:

Apache 2.0 does not prevent commercial use.

Potential value-added services may include:

- hosted processing
- cloud deployment
- workflow support
- training
- consulting
- interoperability validation
- sensor integration

The software remains open source.

This is compatible with both open science and commercial engagement.

Keep this section brief and professional.

---

# AGENTS.md Updates

Add guidance for future agents.

Include:

## Open Science Expectations

Agents should consider:

- reproducibility
- software citation
- documentation
- release readiness
- long-term maintainability

when making changes.

## Documentation Expectations

Public behavior changes should update:

- README
- docs
- citation files
- release notes

when appropriate.

---

# FEATURE_REQUESTS.md Updates

Add durable feature requests for:

- DOI integration
- Zenodo configuration
- release automation
- citation improvements
- publication tracking
- software paper creation
- long-term governance

if these do not already exist.

---

# Release Hygiene Review

Review repository for:

- outdated license references
- outdated project names
- inconsistent branding
- missing citation references
- missing acknowledgements

Document findings.

Fix low-risk inconsistencies.

Create feature requests for larger issues.

---

# Deliverables

Update:

- LICENSE
- NOTICE (if appropriate)
- README.md
- CONTRIBUTING.md (if needed)
- AGENTS.md
- FEATURE_REQUESTS.md
- CITATION.cff
- package metadata

Provide a final report including:

- current license
- migration actions taken
- files updated
- citation infrastructure status
- DOI readiness
- Zenodo readiness
- open science readiness
- commercialization readiness
- remaining recommendations

Do not modify scientific processing code as part of this task.

Focus on governance, licensing, citation, documentation, and release infrastructure.
```
## 2026-06-02 - fix cli public api smoke regressions
Branch: main

```text
Run pytest -q
.................s....................................................ss [ 23%]
ss........................................................FFF........... [ 47%]
........................................................................ [ 70%]
...................................................................s.... [ 94%]
..................                                                       [100%]
=================================== FAILURES ===================================
_ test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.download_main] _

module_name = 'spectralbridge.cli.__init__', function_name = 'download_main'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
>       module = _load_repo_module(module_name)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_public_api_smoke.py:113: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_public_api_smoke.py:79: in _load_repo_module
    spec.loader.exec_module(module)
<frozen importlib._bootstrap_external>:940: in exec_module
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
src/spectralbridge/cli/__init__.py:9: in <module>
    from .pipeline_cli import main as pipeline_cli_main
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

    """Command line entry point for the cross-sensor pipeline."""
    from __future__ import annotations
    
    import argparse
    from pathlib import Path
    from typing import Sequence
    
    from spectralbridge._cli_compat import warn_if_legacy_command
    
>   from ..pipelines.pipeline import go_forth_and_multiply
E   ModuleNotFoundError: No module named 'spectralbridge.cli.pipelines'

src/spectralbridge/cli/pipeline_cli.py:10: ModuleNotFoundError
_ test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.pipeline_main] _

module_name = 'spectralbridge.cli.__init__', function_name = 'pipeline_main'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = _load_repo_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.cli.__init__' has no attribute 'pipeline_main'

tests/test_public_api_smoke.py:114: AttributeError
_ test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.qa_main] _

module_name = 'spectralbridge.cli.__init__', function_name = 'qa_main'

    @pytest.mark.parametrize(
        ("module_name", "function_name"),
        PUBLIC_FUNCTIONS,
        ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
    )
    def test_public_function_import_and_signature_smoke(
        module_name: str,
        function_name: str,
    ) -> None:
        module = _load_repo_module(module_name)
>       function = getattr(module, function_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'spectralbridge.cli.__init__' has no attribute 'qa_main'

tests/test_public_api_smoke.py:114: AttributeError
=============================== warnings summary ===============================
src/spectralbridge/polygons.py:21
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:21: DeprecationWarning: cross_sensor_cal is deprecated; use spectralbridge instead.
    from cross_sensor_cal.exports.schema_utils import ensure_coord_columns

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2233: RuntimeWarning: All-NaN slice encountered
    return np.nanmedian(masked, axis=(1, 2))

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:388: RuntimeWarning: All-NaN slice encountered
    delta_median = np.nanmedian(diff, axis=1)

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/numpy/lib/_nanfunctions_impl.py:1593: RuntimeWarning: All-NaN slice encountered
    return fnb._ureduce(a,

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:393: RuntimeWarning: All-NaN slice encountered
    delta_abs_median = np.nanmedian(np.abs(diff), axis=1)

tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2385: RuntimeWarning: All-NaN slice encountered
    abs_delta = np.nanmedian(full_abs_diff, axis=0)

tests/test_pipeline_convolution.py::test_pipeline_idempotence_skip_behavior
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/opentelemetry/util/_importlib_metadata.py:32: DeprecationWarning: SelectableGroups dict interface is deprecated. Use select.
    return EntryPoints(ep for group_eps in eps.values() for ep in group_eps)

tests/test_pipeline_convolution.py::test_pipeline_idempotence_skip_behavior
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/ray/_private/worker.py:2051: FutureWarning: Tip: In future versions of Ray, Ray will no longer override accelerator visible devices env var if num_gpus=0 or num_gpus=None (default). To enable this behavior and turn off this error message, set RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
    warnings.warn(

tests/test_polygon_pipeline.py::test_build_polygon_pixel_index
tests/test_polygon_pipeline.py::test_extract_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_merge_polygon_parquets_for_flightline
tests/test_polygon_pipeline.py::test_run_polygon_pipeline_for_flightline
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:1714: Pandas4Warning: The copy keyword is deprecated and will be removed in a future version. Copy-on-Write is active in pandas since 3.0 which utilizes a lazy copy mechanism that defers copies until necessary. Use .copy() to make an eager copy if necessary.
    polygon_ids = polygons["polygon_id"].astype("int64", copy=False)

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 10060 (\\N{CROSS MARK}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

tests/test_qa/test_qa_metrics_smoke.py::test_render_panel_writes_png_and_json
tests/test_qa/test_qa_metrics_smoke.py::test_metrics_arrays_are_serialisable
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:1236: UserWarning: Glyph 65039 (\\N{VARIATION SELECTOR-16}) missing from font(s) DejaVu Sans Mono.
    pdf.savefig(fig, bbox_inches="tight")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.download_main] - ModuleNotFoundError: No module named 'spectralbridge.cli.pipelines'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.pipeline_main] - AttributeError: module 'spectralbridge.cli.__init__' has no attribute 'pipeline_main'
FAILED tests/test_public_api_smoke.py::test_public_function_import_and_signature_smoke[spectralbridge.cli.__init__.qa_main] - AttributeError: module 'spectralbridge.cli.__init__' has no attribute 'qa_main'
(raylet) [2026-06-02 21:45:10,922 I 2902 2902] logging.cc:303: Set ray log level from environment variable RAY_BACKEND_LOG_LEVEL to 2 [repeated 4x across cluster] (Ray deduplicates logs by default. Set RAY_DEDUP_LOGS=0 to disable log deduplication, or see https://docs.ray.io/en/master/ray-observability/user-guides/configure-logging.html#log-deduplication for more options.)
Error: Process completed with exit code 1.
```

## 2026-06-02 - replace docs hero image
Branch: main

```text
Here is a replacement for the hero image
```

## 2026-06-02 - remove public cross-sensor-cal references
Branch: main

```text
the website still opens with SpectralBridge (formerly cross-sensor-cal)  even though we were supposed to get rid of all the cross sensor cal references.
```

## 2026-06-02 - homepage refresh
Branch: main

```text
# SpectralBridge Homepage Refresh

## Goal

Redesign the SpectralBridge homepage so it feels like a mature scientific infrastructure platform rather than a research software repository.

The homepage should communicate:

- scientific credibility
- ease of use
- interoperability
- reproducibility
- scalability
- open science

The visual style should align more closely with modern scientific infrastructure projects such as:

- Jupyter
- xarray
- Apache Arrow
- QGIS
- Planetary Computer

and fit within the broader Earth Lab / ESIIL ecosystem.

Use the new SpectralBridge hero banner and simplified logo.

Do not focus the homepage on technical implementation details such as BRDF correction, topographic correction, file formats, or internal processing steps.

Focus on outcomes and value.

---

# Hero Section

Use the new wide SpectralBridge banner graphic.

Hero text:

## SpectralBridge

### Connect drone, airborne, and satellite observations through a single reproducible workflow.

Process hyperspectral imagery across sensors, ecosystems, and scales using transparent, scalable, and scientifically defensible methods.

Buttons:

- Get Started
- Documentation
- Example Workflow

---

# What Is SpectralBridge?

Section title:

## What is SpectralBridge?

Body text:

SpectralBridge is an open-source platform for transforming raw hyperspectral imagery into analysis-ready data products.

Whether you're working with drone surveys, airborne campaigns, ecological observatories, or future sensor systems, SpectralBridge provides a common framework for correction, harmonization, extraction, quality assurance, and analysis.

By creating consistent workflows across sensors and scales, SpectralBridge helps researchers focus on science rather than data wrangling.

---

# Why SpectralBridge?

Create a three-card section.

## Cross-Sensor Interoperability

Compare and integrate measurements collected by drones, aircraft, ecological observatories, and future sensor systems using a common analytical framework.

## Reproducible Science

Every processing step is transparent, documented, and designed to support repeatable scientific workflows.

## Scalable Infrastructure

Run locally, in containers, on cloud platforms, or on high-performance computing systems without changing your workflow.

---

# Workflow Section

Title:

## From Raw Data to Analysis-Ready Products

Subtitle:

A transparent workflow for transforming hyperspectral imagery into scientifically defensible data products.

Workflow diagram:

text Raw Data ↓ Quality Assessment ↓ Correction & Harmonization ↓ Extraction & Summarization ↓ Analysis-Ready Products 

Supporting text:

SpectralBridge helps standardize hyperspectral processing while preserving transparency, reproducibility, and scientific traceability at every step.

---

# Supported Platforms

Title:

## Built for Environmental Observations Across Scales

Create four cards.

### Drone Systems

Process hyperspectral imagery collected from low-altitude drone platforms.

### Airborne Campaigns

Support regional airborne surveys and research aircraft missions.

### NEON Airborne Observation Platform

Work directly with NEON hyperspectral products using dedicated workflows.

### Future Sensors

Designed to support emerging environmental sensing technologies and evolving data standards.

---

# Scientific Applications

Title:

## Scientific Applications

Intro text:

SpectralBridge supports a wide range of environmental monitoring and research applications.

Applications grid:

- Biodiversity Monitoring
- Ecosystem Change Detection
- Vegetation Functional Traits
- Wildfire Science
- Restoration Ecology
- Carbon Dynamics
- Remote Sensing Validation
- Long-Term Ecological Monitoring

---

# Open Science Section

Title:

## Open Science by Design

Body text:

SpectralBridge is built as open scientific infrastructure.

The project emphasizes:

- Transparency
- Reproducibility
- Interoperability
- Scalability
- Community Contribution

All workflows are designed to support reproducible environmental data science and long-term scientific reuse.

Buttons:

- View Source Code
- Citation Information

---

# Call to Action

Title:

## Build Once. Compare Everywhere.

Body text:

SpectralBridge helps connect environmental observations across sensors, ecosystems, and scales through transparent and reproducible workflows.

Buttons:

- Get Started
- Explore Examples

---

# Footer

Retain the overall footer structure already used across the broader Earth Lab / ESIIL ecosystem.

Do not invent new partner organizations.

Reuse existing footer content, logos, acknowledgements, and funding language where appropriate.

Ensure visual consistency with:

- Earth Lab
- ESIIL
- OASIS

The footer should make SpectralBridge feel like part of a larger scientific infrastructure ecosystem rather than a standalone software project.

---

# Design Guidance

The homepage should feel:

- open
- modern
- scientific
- welcoming
- trustworthy

Avoid:

- dense walls of text
- excessive jargon
- implementation details
- overly technical introductions

Prioritize:

- clear value proposition
- visual hierarchy
- whitespace
- accessibility
- mobile responsiveness

The first impression should be:

"SpectralBridge helps me connect and compare hyperspectral observations across sensors and scales."

not:

"SpectralBridge performs BRDF correction."

The science outcomes are the story. The processing details belong in the documentation.
```

## 2026-06-02 - replace header logo
Branch: main

```text
here is a logo for the header to replace the current header logo which seems to be using the hero
```

## 2026-06-02 - replace favicon
Branch: main

```text
favicon
```

## 2026-06-02 - oasis-style footer
Branch: main

```text
can you get all the assests from this repo and make a footer like this [CU-ESIIL/Project_group_OASIS](https://github.com/CU-ESIIL/Project_group_OASIS)
```

## 2026-06-02 - fix docs homepage h1 smoke test
Branch: main

```text
Run python -m http.server 8000 --directory site > /tmp/spectralbridge-docs-http.log 2>&1 &
F                                                                        [100%]
=================================== FAILURES ===================================
_________________ test_docs_site_core_pages_render_in_browser __________________

    def test_docs_site_core_pages_render_in_browser() -> None:
        base_url = _docs_site_url()

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on local environment
            raise AssertionError(
                "Playwright is required for docs browser smoke tests. "
                "Install pytest-playwright/playwright and Chromium."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page_errors, console_errors, failed_assets = _collect_page_health(page, base_url)

            try:
                page.goto(base_url, wait_until="networkidle")
                assert "SpectralBridge" in page.title()
>               assert page.locator("h1#spectralbridge").is_visible()
E               AssertionError: assert False
E                +  where False = is_visible()
E                +    where is_visible = <Locator frame=<Frame name= url='http://127.0.0.1:8000/'> selector='h1#spectralbridge'>.is_visible
E                +      where <Locator frame=<Frame name= url='http://127.0.0.1:8000/'> selector='h1#spectralbridge'> = locator('h1#spectralbridge')
E                +        where locator = <Page url='http://127.0.0.1:8000/'>.locator

tests/test_docs_playwright.py:67: AssertionError
=========================== short test summary info ============================
FAILED tests/test_docs_playwright.py::test_docs_site_core_pages_render_in_browser - AssertionError: assert False
 +  where False = is_visible()
 +    where is_visible = <Locator frame=<Frame name= url='http://127.0.0.1:8000/'> selector='h1#spectralbridge'>.is_visible
 +      where <Locator frame=<Frame name= url='http://127.0.0.1:8000/'> selector='h1#spectralbridge'> = locator('h1#spectralbridge')
 +        where locator = <Page url='http://127.0.0.1:8000/'>.locator
Error: Process completed with exit code 1.
```

## 2026-06-02 - homepage quality redesign pass
Branch: main

```text
this is not a great homepage
```

## 2026-06-02 - homepage layout and header cleanup
Branch: main

```text
the homepage content is leaving room for a sidebar but there is not side bar. also, the header logo is way too small so you can read it and the logo had the name and then the text repeats the name in the header
```

## 2026-06-02 - docs consistency and workflow accuracy
Branch: main

```text
i think these arrows are not going the correct direction. also, the quick start page looks like the old design. can you make all the sub pages match the primary page and also make sure that the the sub pages are up to date with the real details in the package.
```

## 2026-06-02 - work through feature requests
Branch: main

```text
start working through all the feature requests and do any that you're able to. remove a task from the list if it's done. our goal is to finish all the feature requests but don't do anything that will break the functionality so skip the feature request if you think it will break something. We want this to be publication quality, so do the best you can at making it perfect on the first try.
```

## 2026-06-03 - continue next feature request
Branch: main

```text
do the next one
```

## 2026-06-03 - continue next feature request
Branch: main

```text
do the next
```

## 2026-06-03 - zenodo doi badge update
Branch: main

```text
now p18 but I think we already have a zenodo doi for this and we just need to update the badge
```

## 2026-06-03 - release automation and notes
Branch: main

```text
do the next thing
```

## 2026-06-03 - software citation and publication tracking
Branch: main

```text
do the next thing
```

## 2026-06-03 - mixed drone tiff or h5 input support
Branch: main

```text
I want to change the drone pipeline so that it can take the tiff and do the conversion of it can take the h5. The function should recognize which is coming in and treat accordingly
```

## 2026-06-03 - mixed drone input cleanup retry
Branch: main

```text
try again
```

## 2026-06-03 - drone polygon parquet schema stabilization
Branch: main

```text
Fix drone polygon extraction Parquet schema instability.

Problem:
The drone pipeline now reaches polygon extraction correctly, but chunked Parquet writing fails when polygon metadata columns have all-null values in one chunk and strings in another. PyArrow then infers conflicting schemas, e.g. species: null vs species: string, cover_subcategory: null vs string, dead_subcategory: null vs string.

Task:
Make polygon extraction write a stable schema across chunks.

Requirements:
- Locate the chunked polygon Parquet writing path used by extract_polygon_parquet_from_envi.
- Before writing each chunk, normalize polygon attribute columns to stable dtypes.
- Text/object/categorical polygon metadata columns should be string dtype even when all values are missing in a chunk.
- Preserve numeric columns as numeric.
- Preserve datetime columns as timestamp.
- Preserve geometry WKB as binary.
- Preserve polygon_id as integer.
- Do not convert all columns blindly to string.
- Ensure the first chunk cannot lock a text field to Arrow null type.
- Add a regression test using a polygon file where one chunk has all-null species/cover_subcategory/dead_subcategory and a later chunk has strings.
- Test should fail before the fix and pass after.
- Keep NEON behavior unchanged unless the same shared polygon extraction writer is intentionally made safer for both.
- Add a clear comment explaining that this protects chunked Parquet writes from null-only chunk schema inference.

Run:
pytest -q tests/test_drone_pipeline.py
pytest -q tests/test_polygons.py
ruff check src tests
```

## 2026-06-03 - drone qa panel labeling cleanup
Branch: main

```text
i think we can remove it and make sure all the plots in the qa plot are properly labelled.
```

## 2026-06-03 - finish p16 and p24
Branch: main

```text
do those two
```

## 2026-06-09 - aop qa png redesign
Branch: main

```text
let's do that.
```

## 2026-06-09 - drone manifest solar geometry
Branch: main

```text
# Codex Prompt: Restore Drone Solar Geometry Using Flight Manifest CSV

## Background

The SpectralBridge drone workflow is intentionally designed as a thin adapter around the existing NEON AOP pipeline.

The architecture is:

text Drone TIFF + ancillary data     ↓ convert_drone_tiff_to_h5()     ↓ NEON-like H5     ↓ Standard SpectralBridge pipeline     ↓ ENVI     ↓ Topo / BRDF correction     ↓ QA     ↓ Extraction 

The standard pipeline should remain unchanged.

The goal of this PR is to improve the drone adapter so that it produces a more complete NEON-equivalent H5 by computing solar geometry when it is not explicitly supplied.

---

## Problem

Historically the drone workflow used a flight timestamp (date_time_str) to compute:

text Solar_Zenith_Angle Solar_Azimuth_Angle 

before writing the H5.

The current package implementation supports:

python solar_zenith_tiff solar_azimuth_tiff sensor_zenith_tiff sensor_azimuth_tiff 

or scalar angle inputs, but does not automatically compute solar geometry from acquisition time.

As a result:

- drone H5 files may have missing solar geometry
- topo/BRDF correction may run with incomplete metadata
- the resulting H5 is structurally similar to NEON but not fully equivalent

---

## New Input

Assume the user provides:

python drone_manifest_path="Drone Field Data Macrosystems - UAS Data Processing For Extraction.csv" 

The CSV contains flight metadata including:

text Plot Day of data collection Mean Time of data collection (24 hr clock) 

Example:

text AOP_GOLDHILL 2023-08-15 19:53:07  AOP_GORDON 2023-08-15 20:58:39  AOP_RUBY 2023-08-16 18:53:18 

The CSV should become the authoritative source of acquisition datetime information for drone flights.

---

## Required Changes

### 1. Add manifest support to run_drone_pipeline()

Add optional argument:

python drone_manifest_path: str | Path | None = None 

Pass this through to the TIFF → H5 conversion stage.

Do not require it for existing workflows.

---

### 2. Create a manifest loader

New helper:

python load_drone_manifest() 

Responsibilities:

- read CSV
- normalize flight identifiers
- parse acquisition datetime
- build lookup dictionary

Return:

python {     "AOP_GOLDHILL": datetime(...),     "AOP_GORDON": datetime(...),     ... } 

Handle:

- whitespace
- mixed separators
- missing rows
- malformed dates

Provide informative warnings.

---

### 3. Add flight lookup helper

Create:

python lookup_flight_datetime(     flight_id,     manifest ) 

This should match:

text AOP_GOLDHILL_20230814 

to

text AOP_GOLDHILL 

and return the acquisition datetime.

Document matching rules.

---

### 4. Restore solar geometry computation

Inside:

python convert_drone_tiff_to_h5() 

Add logic:

### Priority 1

Use supplied:

python solar_zenith_tiff solar_azimuth_tiff 

if present.

### Priority 2

Use supplied scalar angles if present.

### Priority 3

If no solar geometry exists:

python acquisition_datetime + pixel lat/lon 

compute:

python Solar_Zenith_Angle Solar_Azimuth_Angle 

for every pixel.

Write these datasets into the generated H5 using the same names expected by the standard AOP pipeline.

### Priority 4

If geometry still cannot be produced:

raise a clear error when correction is requested.

---

## Coordinate Requirements

Use the raster CRS and transform to generate:

python longitude latitude 

for each pixel.

Avoid assumptions about projection.

Use rasterio / pyproj utilities already present in the project where possible.

---

## QA Improvements

Add fields to QA JSON:

json {   "solar_geometry_source": "...",   "acquisition_datetime_used": "...",   "solar_zenith_mean": ...,   "solar_zenith_min": ...,   "solar_zenith_max": ...,   "solar_azimuth_mean": ...,   "solar_azimuth_min": ...,   "solar_azimuth_max": ... } 

Allowed values:

text solar_geometry_source:  raster scalar manifest_computed missing 

---

## Failure Behavior

Add:

python require_solar_geometry: bool = True 

If:

python apply_topo=True 

or

python apply_brdf=True 

and no geometry exists:

text raise RuntimeError 

unless:

python require_solar_geometry=False 

---

## Testing

Add minimal tests.

### Test 1

Manifest loading:

python AOP_GOLDHILL → datetime parsed correctly 

### Test 2

Flight lookup:

python AOP_GOLDHILL_20230814 → AOP_GOLDHILL 

### Test 3

Manifest-derived geometry:

Synthetic raster

→ geometry computed

→ datasets written to H5

### Test 4

Missing geometry

Correction requested

→ clear exception raised

---

## Design Constraints

- Do not modify the standard NEON pipeline.
- Keep all changes inside the drone adapter layer.
- Maintain backwards compatibility.
- Preserve existing workflows that already provide solar angle rasters.
- Make the generated drone H5 as semantically equivalent to a NEON AOP H5 as possible.
- Add clear logging and QA reporting so users can determine exactly where solar geometry originated.
```

## 2026-06-10 - validate drone field manifest
Branch: main

```text
here is the manifest.
```

## 2026-06-10 - drone manifest relative path error
Branch: main

```text
Attached traceback shows run_drone_pipeline(..., drone_manifest_path="Drone Field Data Macrosystems - UAS Data Processing For Extraction.csv") failing with FileNotFoundError because the relative manifest CSV path was not found from the notebook working directory.
```

## 2026-06-10 - drone manifest input-dir fallback
Branch: main

```text
Traceback shows the improved drone_manifest_path error only checked the notebook working directory and the raw relative filename, but did not check the relative input_h5_dir folder (`drone_inputs`) for the manifest CSV.
```

## 2026-06-10 - update aop qa png phash baseline
Branch: main

```text
Run pytest tests/test_qa -q
...F                                                                     [100%]
test_panel_phash_matches_baseline failed because the AOP QA PNG perceptual hash no longer matches the old baseline after the redesigned QA panel.
```

## 2026-06-10 - bundle drone manifest
Branch: main

```text
re: drone_manifest_path yes, put it in the repo and refernce the code to it
```

## 2026-06-10 - docs playwright 403 console errors
Branch: main

```text
Run python -m http.server 8000 --directory site > /tmp/spectralbridge-docs-http.log 2>&1 &
test_docs_site_core_pages_render_in_browser failed because console_errors contained two "Failed to load resource: the server responded with a status of 403 ()" entries.
```

## 2026-06-10 - drone empty input discovery clarity
Branch: main

```text
[drone] Skipping manifest row 31 for MTST_11 with malformed acquisition datetime: 'nan' 'nan'
[drone] Skipping manifest row 46 with missing Plot value in [/home/jovyan/data-store/spectralbridge/src/spectralbridge/data/drone_field_manifest.csv](https://afa48b26d.cyverse.run/lab/tree/spectralbridge/spectralbridge/src/spectralbridge/data/drone_field_manifest.csv)
Processed: 0
Failed: 0
Merged parquet: None
QA summary: drone_outputs/drone_qa_summary.json
{'attempted_total': 0,
 'brightness_adjustment_applied': False,
 'brightness_adjustment_requested': False,
 'brightness_offset': 0.0,
 'cloud_mask_applied': False,
 'convolution': 'skipped',
 'discovered_total': 0,
 'drone_manifest_path': '/home/jovyan/data-store/spectralbridge/src/spectralbridge/data/drone_field_manifest.csv',
 'files': [],
 'ndvi_brdf_bins_enabled': False,
 'platform': 'drone',
 'polygon_path': 'Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg',
 'require_solar_geometry': True,
 'run_root': 'drone_outputs'}
```

## 2026-06-11 - CI full test failure log
Branch: main

```text
Attached pasted-text.txt shows full pytest failure log with drone pipeline, parquet export, Ray engine, polygon ArrowDtype, and stage export failures after recent changes.
```
