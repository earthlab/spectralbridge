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
