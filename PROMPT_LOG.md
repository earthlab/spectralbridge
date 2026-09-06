# PROMPT_LOG.md

This file stores verbatim user prompts for Codex work in this repository.

- New entries should be appended, not rewritten.
- Prompts should be logged verbatim in fenced `text` blocks.
- Logging begins with the request that introduced this file; older prompts were not backfilled automatically.

Default AI system: OpenAI Codex
Default model: Not recorded

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

## 2026-09-04 - bounded stage-complete installed-artifact validation
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
You are working in the current earthlab/spectralbridge repository.

We have completed the first PyPI publication-hardening audit. The audit correctly found that the current installed-wheel smoke does not yet exercise every major stage of the normal NEON and drone pipelines.

However, we now need to refine the release criterion.

A real production SpectralBridge flightline can require roughly 250 GB of RAM. Therefore:

The release gate MUST NOT require a production-scale pipeline run in CI.

Instead, the release requirement is:

The exact built wheel must be able to execute every major public pipeline stage on deliberately tiny, bounded synthetic fixtures outside the repository checkout, while separate production-validation evidence documents real large-memory runs.

This task is to implement that bounded, stage-complete installed-artifact validation.

Do not change scientific algorithms or defaults.

Do not attempt to make production-scale processing fit into CI.

Do not reduce scientific fidelity of the actual pipeline.

The goal is to test the SAME code paths at tiny scale.

Before changing anything, read carefully:

* AGENTS.md
* FEATURE_REQUESTS.md
* PROMPT_LOG.md
* docs/dev/publication-hardening-audit-2026-09-04.md
* scripts/check_installed_artifact.py
* normal NEON pipeline orchestration
* drone pipeline orchestration
* bulk pipeline
* correction code
* convolution/resampling code
* extraction code
* merge code
* QA code
* existing synthetic fixtures and tests
* release workflow
* CI workflows

1. Update the publication-hardening contract

Amend the authoritative publication-hardening audit so the release blocker is stated correctly.

The required distinction is:

CI/package validation

Must demonstrate from the installed wheel, outside the checkout:

* all public APIs import
* all required package resources resolve
* every major stage of all three pipelines executes on small bounded fixtures
* expected outputs are created
* restart/idempotent behavior is exercised where appropriate
* no repository-relative dependencies are required

Production scientific validation

Must separately document selected real large-memory runs.

CI is not required to reproduce a 250 GB production execution.

The audit should explicitly say that scale reduction for fixtures is acceptable only when the actual production code paths and algorithms are being exercised.

2. Extend the installed-artifact smoke framework

Refactor or extend:

scripts/check_installed_artifact.py

so it can exercise stage-complete tiny workflows for:

1. normal NEON pipeline
2. drone pipeline
3. bulk pipeline

The script must continue to verify that imports come from site-packages, not the repository checkout.

The smoke must remain deterministic, offline, and appropriate for standard CI hardware.

Aim for fixture sizes measured in KB/MB, not GB.

3. Normal NEON stage-complete synthetic smoke

Build or reuse a tiny synthetic NEON-style HDF5 fixture that is structurally sufficient to exercise the installed normal pipeline.

The test should execute, where technically possible, the actual code paths for:

* HDF5 input/read
* ENVI export
* topographic/BRDF model preparation
* correction application
* spectral convolution/resampling
* Parquet/table export
* merge
* QA generation

Do not substitute mocks for entire scientific stages unless absolutely necessary.

Mocks may be used only for things such as:

* network download
* external service access
* irrelevant timing/logging behavior

The scientific transformation functions themselves should run on the tiny fixture.

If a production stage requires dimensions or metadata that make a truly tiny fixture impossible, identify the minimum valid synthetic shape and document why.

The fixture should contain enough spectral/spatial variation that calculations are nondegenerate.

Do not require meaningful scientific validation from this fixture. This is a packaging/code-path test.

4. Bound resource use explicitly

The synthetic normal smoke must be designed so CI cannot accidentally allocate production-scale arrays.

Use tiny:

* rows
* columns
* band counts where algorithmically permitted
* worker counts
* chunks
* thread counts

Use:

* engine="thread" or another lightweight backend where appropriate
* max_workers=1
* bounded chunk dimensions
* no Ray cluster unless the code path specifically requires one

If the production code supports configuration that safely reduces fixture scale without changing algorithm semantics, use that.

Do NOT add special “fake science” branches that production users would never execute.

Prefer a small real input to a special testing implementation.

5. Normal-pipeline stage assertions

The installed smoke should verify existence and basic readability of expected artifacts, for example:

* ENVI image/header
* corrected ENVI image/header
* convolved sensor product
* Parquet extraction
* merged table
* QA JSON/figure/report as appropriate

Also verify:

* canonical filenames
* nonzero artifact sizes
* readable schemas/headers
* reasonable finite values in a small sample
* restart behavior does not unnecessarily recompute valid outputs

Do not assert exact floating-point values unless stable and scientifically meaningful.

6. Drone stage-complete synthetic smoke

Extend the drone installed-wheel smoke so it exercises the actual drone code paths for:

* input discovery
* HDF5/raster reading as applicable
* correction path
* sensor/output generation
* full extraction mode
* polygon extraction mode
* QA generation

Use a tiny synthetic drone fixture.

If full and polygon extraction require different fixtures, keep them both tiny.

The polygon fixture should include a minimal valid geometry that intersects the synthetic scene.

Verify outputs are created and readable.

Do not require a drone CLI if the supported public interface remains the Python API.

7. Bulk pipeline smoke

Keep the existing small bulk smoke, but make sure it still exercises:

* discovery
* canonical flightline catalog
* DuckDB database creation
* dataset census
* sensor translation
* leave-one-site-out
* optional materialization behavior if appropriate

Do not make the bulk smoke scan large data.

8. Add resource-budget guardrails

Add explicit guardrails to the installed-artifact smoke.

At minimum:

* fixture dimensions must be hard-coded/small
* worker/thread counts must be bounded
* temporary outputs must stay under a reasonable size threshold
* avoid accidental recursive discovery outside the fixture temp directory
* avoid network activity

If practical, record:

* elapsed time
* peak output-directory size
* fixture dimensions

Do not add fragile platform-specific memory instrumentation unless it is reliable.

The main goal is preventing accidental scale escalation.

9. Separate smoke from scientific validation

Do not present the tiny synthetic smoke as scientific validation.

Add clear language to the docs and audit:

Synthetic installed-wheel smoke proves:

* packaging integrity
* resource availability
* orchestration
* stage connectivity
* installed-artifact execution

It does NOT prove:

* scientific accuracy on real landscapes
* performance at production scale
* stability across sites
* empirical calibration validity

Those are covered by existing and future real-data validation campaigns.

10. Production validation record

Create or extend a durable location for real-run evidence.

Do not run a new 250 GB production job during this task.

Instead, identify existing real validated runs in the repo and document the intended release evidence contract.

A production validation record should eventually include:

* canonical flightline ID
* site
* SpectralBridge version/commit
* Python/environment
* pipeline configuration
* approximate hardware/RAM
* major output artifacts
* QA result
* known warnings
* artifact hashes where appropriate

If existing runs already provide sufficient information, reference them.

If not, add a template/checklist for maintainers to fill after the next validated large-VM run.

11. Release CI integration

Update CI/release-support code so the intended future release gate is:

1. build wheel and sdist once
2. run twine check
3. create clean environment
4. install exact wheel
5. run stage-complete installed-artifact smoke
6. repeat on supported Python matrix
7. run package-data validation
8. run docs/version/transparency gates
9. only then allow release

Do not publish to PyPI yet unless explicitly requested separately.

If modifying the release workflow would be too large for this task, add a dedicated release-artifact workflow/check that can later be required by the publishing workflow.

12. Python matrix

Use the audit findings to define a practical CI support matrix.

At minimum consider:

* Python 3.10
* Python 3.11
* Python 3.12

Do not automatically add 3.13/3.14 to the supported contract merely because abbreviated clean installs passed locally.

If the stage-complete smoke passes reliably on newer versions and maintainers want them, document that separately.

13. Remove repository-relative validation dependency

The audit found that the normal pipeline looks for:

bin/validate_parquets

relative to the repository and silently skips it when installed.

Resolve this cleanly.

Either:

* move the implementation into the installed package and call it package-locally

or

* formally classify it as a maintainer-only repository check and remove it from the installed runtime contract/documentation

Prefer package-local implementation if it is part of normal runtime validation.

Do not leave an advertised installed feature depending on a non-installed repo script.

14. Tests for the smoke framework itself

Add focused tests around synthetic fixture generation and installed-artifact checks where reasonable.

Verify:

* fixtures are tiny
* fixtures are structurally valid
* expected stages execute
* outputs are isolated to temp directories
* source checkout is not imported
* network is not required
* invalid/missing package resources fail loudly
* repo-relative assumptions are detected

Avoid duplicating the entire existing unit suite.

15. Documentation

Update release/developer docs to explain the two-tier validation model:

Tier A: installed-artifact CI smoke

* tiny
* bounded
* stage-complete
* every release
* proves package wiring

Tier B: production validation

* real flightlines
* large-memory VM
* periodic/release-candidate
* proves real scientific and operational behavior

This distinction should be clear enough that a reviewer understands why a 250 GB workflow is not run in GitHub Actions.

16. Verification

Run as many of these as possible:

* full pytest
* focused normal-pipeline tests
* focused drone tests
* bulk tests
* package build
* twine check
* clean wheel install
* stage-complete installed-wheel smoke
* Python 3.10/3.11/3.12 clean smoke
* sdist install smoke if practical
* Ruff
* compile checks
* docs-link checks
* strict MkDocs build
* AI transparency check
* git diff --check

Record actual results only.

17. Do not change scientific behavior

Do NOT:

* alter BRDF equations
* alter topographic equations
* change brightness coefficients
* change sensor-response definitions
* weaken QA thresholds
* change production defaults
* add test-only numerical shortcuts to production algorithms
* skip a scientific stage merely because it is expensive

The fixture should be smaller, not the science.

18. Final report

Report:

1. revised publication validation contract
2. exact normal stages now exercised from installed wheel
3. exact drone stages now exercised from installed wheel
4. exact bulk stages exercised
5. synthetic fixture dimensions and approximate output sizes
6. runtime/resource guardrails
7. whether any stage could not be exercised and why
8. repository-relative dependencies removed/fixed
9. CI/release workflow changes
10. supported Python matrix tested
11. exact commands/checks and results
12. remaining PyPI blockers
13. production validation evidence still needed

Update FEATURE_REQUESTS.md and PROMPT_LOG.md according to repository policy.

The goal is NOT to prove that a tiny synthetic dataset is scientifically representative.

The goal is to prove that the exact PyPI artifact can execute the complete scientific software paths on bounded fixtures, while real large-memory runs remain a separate validation layer.
```

## 2026-09-03 - PyPI publication-hardening audit
Branch: main
AI system: OpenAI Codex
Model: GPT-5

````text
You are working in the current earthlab/spectralbridge repository.

We are now switching from feature development to PyPI publication hardening.

Do NOT broadly refactor the package yet. This task is primarily an evidence-based release-readiness audit plus only the smallest changes needed to make the audit itself runnable and accurate.

The central publication requirement is:

A user must be able to install SpectralBridge from the built package into a completely clean environment and successfully access and run all THREE supported pipelines without cloning the GitHub repository.

The three supported pipelines are:

1. Normal NEON SpectralBridge pipeline
2. Drone pipeline
3. Bulk cross-run analysis pipeline

Treat that as a release-blocking contract.

Before doing anything, read the current repository carefully, especially:

* AGENTS.md
* FEATURE_REQUESTS.md
* PROMPT_LOG.md
* pyproject.toml
* MANIFEST.in
* CITATION.cff
* CHANGELOG.md
* README.md
* START_HERE.md
* .github/workflows/
* src/spectralbridge/
* src/spectralbridge/pipelines/
* src/spectralbridge/bulk/
* drone pipeline code
* CLI entry points
* package-data directories
* examples and notebooks
* tests
* documentation
* release workflow
* existing publication-readiness audits

Create a new authoritative publication-hardening audit document in a sensible developer/docs location.

Do not assume previous audits are still current.

Primary audit question

Can the exact SpectralBridge distribution artifact that would be uploaded to PyPI be installed into a clean environment and run all three supported pipelines without access to the repository checkout?

The answer must be demonstrated, not inferred.

1. Determine the actual package/public API

Inventory the package as it currently exists.

Identify:

* current package version
* spectralbridge.__version__
* Python package namespaces
* public imports
* console scripts
* normal NEON pipeline entry point
* drone pipeline entry point
* bulk pipeline entry point
* legacy aliases
* optional/experimental entry points
* runtime package data
* data/config files required by each pipeline

Produce a table showing each public workflow and how a user invokes it from:

* Python
* CLI, where applicable

For each of the three pipelines, identify the smallest documented runnable call.

2. Build the real distribution artifacts

Build both:

* wheel
* source distribution

using the repository’s intended release tooling.

Run distribution metadata validation such as twine check if available.

Inspect the actual contents of BOTH artifacts.

Do not assume a file is packaged simply because it exists in the repository.

Produce an explicit inventory of packaged runtime resources.

3. Clean-install tests must use the built artifact

Create clean test environments that do NOT have the repository on PYTHONPATH.

Install only the built wheel plus dependencies.

Verify that imports resolve from the installed package rather than the checkout.

Where practical, also test the sdist-built installation.

This distinction is release critical.

4. Test all three pipelines from the installed package

A. Normal NEON pipeline

From a clean wheel installation verify:

* import spectralbridge
* from spectralbridge import go_forth_and_multiply or the current canonical API
* CLI --help
* relevant path/naming/config imports
* package data needed for sensor convolution
* brightness/config resources
* BRDF/topographic resources
* QA resources
* a small offline/synthetic smoke workflow if one exists

Do not require downloading a real multi-GB NEON flightline for CI.

If necessary, create or reuse a very small fixture that exercises the installed package through a meaningful abbreviated path.

The smoke test should demonstrate that no repository-relative file assumptions exist.

B. Drone pipeline

The drone pipeline must be runnable from the installed package.

Audit carefully whether it currently depends on:

* example scripts that are not installed
* repo-relative JSON
* notebooks
* local data files
* root-level helper modules
* package resources that are missing from wheel/sdist
* hard-coded filesystem paths

Establish a canonical installed-package Python API and, if appropriate, CLI.

Do NOT require the user to run a script from examples/ after cloning the repo as the only supported way to access the drone pipeline.

A clean user should be able to do something conceptually like:

from spectralbridge import run_drone_pipeline

or the current canonical equivalent.

If the canonical API already exists, verify it.

If not, identify this as a release blocker rather than inventing a large refactor during the audit.

Create or identify a tiny synthetic drone fixture that can validate:

* package import
* configuration parsing
* pipeline orchestration
* expected output creation

without external large files.

C. Bulk pipeline

From a clean installed wheel verify:

from spectralbridge import run_bulk_pipeline

and:

spectralbridge-bulk --help

Use tiny synthetic merged Parquet fixtures to verify that the installed package can:

* discover flightlines
* create the bulk catalog
* create the DuckDB database
* run dataset census
* run sensor translation
* run leave-one-site-out if fixture structure supports it

No repository checkout may be required.

5. Add an installed-wheel three-pipeline smoke test

Design a release-level smoke test specifically for the built artifact.

Prefer a script/test that:

1. creates a fresh temporary environment
2. installs the wheel
3. executes an installed-package smoke test for the NEON pipeline
4. executes an installed-package smoke test for the drone pipeline
5. executes an installed-package smoke test for the bulk pipeline

The smoke fixtures must be small enough for CI.

This should become a release gate eventually.

If implementing this safely is straightforward, add it now.

If not, document exactly what prevents it.

6. Audit package data

Inspect all runtime non-Python files required by the three pipelines.

Examples may include:

* sensor response functions
* CSVs
* JSON coefficient files
* brightness configuration
* metadata templates
* schemas
* packaged lookup tables
* reference wavelength information
* any files loaded using filesystem paths

For every runtime resource identify:

* repository path
* package destination
* which pipeline uses it
* whether it exists in wheel
* whether it exists in sdist
* how code locates it

Prefer importlib.resources or equivalent package-safe access.

Flag repository-relative resource access as a release blocker.

7. Audit dependencies

Review pyproject.toml.

Classify dependencies into:

* required for normal NEON pipeline
* required for drone pipeline
* required for bulk pipeline
* documentation only
* testing only
* notebook/development only

Determine whether the standard pip install spectralbridge should intentionally install everything required for ALL THREE pipelines.

For this release, assume the desired user contract is:

pip install spectralbridge is sufficient to run the normal NEON pipeline, drone pipeline, and bulk pipeline.

Do not move essential pipeline dependencies into optional extras if that would violate this contract.

Optional extras are acceptable for:

* docs
* notebooks
* development
* tests
* clearly nonessential tooling

Flag missing runtime dependencies.

8. Python support matrix

Determine what Python versions the dependency set realistically supports.

Resolve inconsistencies among:

* requires-python
* README
* CI
* docs
* actual clean installs

At minimum test the currently claimed primary versions.

Prefer a documented CI matrix instead of saying “periodically validated.”

Do not claim Python versions that cannot install all three pipelines.

9. CLI audit

Inventory all console scripts from pyproject.toml.

For every supported command:

* run --help
* check import success from installed wheel
* check exit code
* check that help text reflects current naming
* check for repo-relative assumptions
* identify legacy aliases

Make a recommendation for which CLI names are canonical and which are compatibility aliases.

For the release, the user should have obvious commands for:

* main pipeline
* bulk pipeline
* QA

If the drone pipeline should have a CLI, evaluate whether adding one is worth doing before publication. Do not add one merely for symmetry if the Python API is the intended supported interface.

10. Version synchronization audit

Compare:

* pyproject.toml
* spectralbridge.__version__
* CHANGELOG.md
* CITATION.cff
* current tags/releases
* docs mentioning versions
* release workflow

Flag every mismatch.

Recommend one canonical publication version strategy.

Do not silently change to 1.0.0 or another version without documenting the implications of existing version history.

11. Release workflow audit

Read .github/workflows/release.yml and related workflows.

Determine whether a tag-based release:

* builds from the tagged commit
* runs tests first
* validates metadata
* builds wheel and sdist
* installs/tests the artifact
* checks all three pipelines
* publishes to PyPI safely
* prevents version/tag mismatch
* supports TestPyPI dry runs if useful

Identify release-blocking gaps.

Do not publish anything during this task.

12. CI audit

Evaluate whether current CI protects the release contract.

Required checks should eventually include:

* lint
* unit tests
* package build
* wheel/sdist validation
* clean installed-wheel test
* all-three-pipeline smoke test
* docs build
* package-data check
* AI transparency check
* version synchronization

Also inspect whether current workflow path filters could accidentally skip important release checks.

13. Public API and backward compatibility

Inventory public imports currently used in:

* README
* docs
* examples
* tests

Identify:

* canonical APIs
* undocumented-but-used APIs
* deprecated imports
* old cross_sensor_cal compatibility namespace
* duplicate names
* APIs that are likely to change

Recommend the smallest stable public surface for publication.

Do not remove compatibility paths in the audit unless something is actively broken.

14. Documentation clean-room audit

Pretend you are a researcher who only knows:

pip install spectralbridge

Determine whether public docs allow that person to run:

1. the normal pipeline
2. the drone pipeline
3. the bulk pipeline

without cloning GitHub.

Flag every instruction that currently assumes:

* git clone
* running repo scripts
* local notebooks
* local JSON files
* working from repository root
* developer environment setup

Recommend replacement package-first instructions.

15. README / PyPI landing-page audit

The README will become the PyPI long description.

Check that it clearly explains:

* what SpectralBridge does
* scientific scope
* installation
* supported Python
* minimal normal-pipeline example
* drone pipeline entry
* bulk pipeline entry
* QA
* docs link
* citation
* license
* issue/support link
* stable vs experimental functionality

Also identify rendering risks on PyPI.

16. Scientific configuration reproducibility

Inventory scientifically meaningful runtime configuration that can change results, including where applicable:

* sensor response curves
* brightness coefficients
* BRDF/topographic defaults
* thresholds
* masks
* QA thresholds
* bulk-analysis schema/version
* translation pair definitions

Determine whether each is packaged and versioned sufficiently to reproduce a result from a specific SpectralBridge release.

Flag mutable/unversioned configuration risks.

17. Citation, DOI, and authorship audit

Read CITATION.cff and current DOI documentation.

Determine:

* whether author names are placeholders
* whether ORCIDs/affiliations are complete
* whether current Zenodo DOI corresponds to the current package identity/version
* whether concept DOI vs release DOI strategy is clear
* whether package version and citation version agree

Do not invent author metadata.

List exactly what requires maintainer input.

18. License and provenance audit

Verify:

* package license metadata
* repository license
* third-party adapted code notices
* bundled sensor response data
* coefficient files
* example/test data
* images/assets distributed in wheel/sdist if any

Identify anything needing explicit attribution or legal review.

Also flag deprecated packaging license metadata if still present.

19. Repository hygiene audit

Search current tracked files for likely release problems:

* :memory:
* scratch files
* accidental binaries
* giant unrelated outputs
* hard-coded user paths
* local environment paths
* credentials/tokens
* private URLs
* stale notebooks/scripts
* generated files unintentionally included in package
* repository-root imports

Do not rewrite git history.

20. Produce a prioritized release-blocker report

Create a publication-hardening audit with categories:

BLOCKER

Must be fixed before PyPI release.

HIGH PRIORITY

Should be fixed before publication unless explicitly accepted.

MEDIUM

Can be handled immediately after initial release.

NON-BLOCKING

Cleanup or future improvement.

For every item include:

* problem
* evidence
* affected pipeline(s)
* user impact
* recommended fix
* whether Codex can fix it independently or needs maintainer input

21. Build a concrete PyPI release checklist

End the audit with a concise ordered checklist that takes the repository from current state to published PyPI release.

The checklist must explicitly include a gate that verifies:

A wheel installed into a clean environment can run the normal NEON pipeline, drone pipeline, and bulk pipeline without a repository checkout.

22. Verification during this audit

Run as many of the following as the environment allows:

* full pytest
* focused pipeline tests
* package build
* twine check
* wheel-content inspection
* sdist-content inspection
* clean wheel install
* installed-package imports
* all CLI --help
* small installed-wheel smoke tests for all three pipelines
* Python compile checks
* Ruff
* docs link checks
* strict MkDocs build
* AI transparency check
* git diff --check

Do not claim checks passed unless they were actually run.

23. Minimal fixes allowed during this task

This task is primarily an audit.

You may make SMALL obvious fixes only when needed to:

* repair the audit tooling
* make a package-resource check possible
* fix a trivial packaging omission with no design implications
* add a release-smoke test that does not alter scientific behavior

Do NOT:

* redesign the pipelines
* change scientific algorithms
* change correction coefficients
* change defaults without evidence
* publish to TestPyPI or PyPI
* create a release tag
* remove compatibility APIs broadly

Log the prompt and work according to repository AI-transparency policy.

Update FEATURE_REQUESTS.md with the audit outcome.

Final response

Report back with:

1. overall PyPI readiness verdict
2. whether a clean wheel can currently run each of the three pipelines
3. blockers
4. high-priority issues
5. package-data findings
6. dependency findings
7. Python support findings
8. version/citation/DOI findings
9. release workflow findings
10. clean-install test results
11. exact commands/checks run
12. files changed during the audit
13. ordered next-step checklist

Be conservative.

The goal is not to declare SpectralBridge ready.

The goal is to know exactly what must be true before we can confidently publish it.
````

## 2026-08-17 - diagnose BRDF kernel crash at initialization
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
why is my kernel crashing on the brdf step at 0% completion
```

## 2026-08-17 - add combined QA PDF summary
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
the qa output is nice but the html is a little restrictive for summary. can you add a pdf print of the whole summary after it's produced by the html? this should have all the pages as part of a single pdf that I could download or compare to other flight line pdfs.
```

## 2026-08-17 - repair full-suite pytest failures
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
# Files pasted by the user:

## "Run pytest -q --cov=spectralbridge --cov-branch \\ .................FF.......s..…": /Users/tuff/.codex/attachments/e8f02981-3a6f-4330-aedf-bde871598404/pasted-text.txt

Pasted text contains the user's request.

## My request:
```

## 2026-08-17 - add synthetic sensor regression diagnostic
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
can you add a plot of the synthetic products and the linear regression coefficients for that plot? we'll work on the rest later.
```

## 2026-08-14 - clarify NEON-mediated drone-to-Landsat translation
Branch: main

```text
the drone to landsat is good but it actually drone to landsat translated by neon.
```

## 2026-08-14 - organize repository and add runnable notebook vignettes
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
I need to make sure the repo is organized and labelled clearly without breaking any code. I want the json files to be easy to understnad what they are and what they're doing. I want the python scripts to be clearly documented and easy to understand. Right now there feels like so much information that a new user will have no idea where to start or how to find and validate the code themselves. We need more jupyter notebooks organized in the vingnettes so that people can just open and run them. this is a package that people will want to load and run in many different environments, I want them to be able to pull the repo into a container, open a script and run it and and the whole pipeline runs. Don't modify the pipeline as it's working well now, but make sure that we have scripts to run these as notebooks for someone who just wants part of the pipeline or want's to modify for their own purposes. I think some people will want to add additional corrections to the topo and brdf but we don't yet explain how they would do that by matching the naming convention and patching in between the correct modules. again, don't break the current code, just add more guidance for new users to how to use it and what it does and why they would use it and why they would do it a particular way. trying to make the repo less sprawling.
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

## 2026-08-14 - publication, coverage, and AI transparency audit
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
I want to audit this repo and see how ready it is for publication. I also want to audit the tests and the test coverage. I also want to add an automated ai transparency statement the looks at the prompt log and produces figures of summary statistics of how ai was used along with text summaries of how ai was used and which ai was used.
```

## 2026-08-14 - simplify website and organize educational vignettes
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
let's clean up the website so it feels less overwhelming. let's put all of the educational material in one section and all the more technical descriptions in another section. in the educational section, we want a single vingetter for each module and we want a vinette to run the full pipeline and to use the carry on my wayward son if they have part of the pipeline done.
```

## 2026-08-14 - pipeline validation framework and website section
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
we need some validation tests in a validation section. This should involve running each function with multiple different inputs to make sure that each step reliable does what it's should do and has some diagnostics to show how well it does it. We want a validation section on the website and in that section we want each module to have it's own page showing the list of variations of inputs it used and then showing the results of how it did with that variation. for example, we can try 100 different iterations of the neon h5 download from different sites using different site codes and 100 iterations of converting h5 to envi raw and then 100 of correcting that with topo and then 100 of correcting brdf, convolution ,then testing the parquet extraction and the conversion to csv, and the save functions and the qa plot. We can use all of that to inform the qa plots and make them as good as possible.
```

## 2026-08-14 - redesign website in an Impact Media Lab style
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
I don't love the design of the website, can you make it more like an impact media lab site?
```

## 2026-08-14 - align website palette with original SpectralBridge logo
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
can we change the color palette to be more like the logo we had before? I like the hierarchy and such of the website, but we don't want the actual IML color palette and such. go back to the logo we had and then play off of that for a webite theme. Also know the audience is scientists who want to convert hyperspectral data between drone and landsat.
```

## 2026-08-14 - fix drone merged-preview CI regression
Branch: main
AI system: OpenAI Codex
Model: GPT-5 family (exact deployment identifier not exposed)

```text
Run pytest -q tests/test_drone_pipeline.py
.....................F.F.............................                    [100%]
=================================== FAILURES ============================___________ test_render_drone_merged_preview_prefers_non_nodata_rows ___________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_render_drone_merged_previ0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7f1fa8f3e650>

    def test_render_drone_merged_preview_prefers_non_nodata_rows(
        tmp_path: Path, monkeypatch
    ) -> None:
        merged_path = tmp_path / "merged.parquet"
        merged_path.write_text("placeholder", encoding="utf-8")
        df = pd.DataFrame(
            {
                "flight_id": ["SPR1_20230628", "SPR1_20230628"],
                "pixel_id": [1, 2],
                "row": [0, 1],
                "col": [0, 1],
                "corr_b001_wl0440nm": [-9999.0, 0.12],
                "corr_b002_wl0560nm": [-9999.0, 0.23],
                "corr_b003_wl0650nm": [-9999.0, 0.34],
            }
        )
        monkeypatch.setattr(pd, "read_parquet", lambda path: df.copy())

        summary = _render_drone_merged_preview(_FakeAxes(), merged_path, "SPR1_20230628")

>       assert summary["rows_total"] == 2
E       assert 0 == 2

tests/test_drone_pipeline.py:1049: AssertionError
________ test_render_drone_merged_preview_prioritizes_rightmost_columns ________

tmp_path = PosixPath('/tmp/pytest-of-runner/pytest-0/test_render_drone_merged_previ1')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7f1fa8d905d0>

    def test_render_drone_merged_preview_prioritizes_rightmost_columns(
        tmp_path: Path, monkeypatch
    ) -> None:
        merged_path = tmp_path / "merged.parquet"
        merged_path.write_text("placeholder", encoding="utf-8")
        df = pd.DataFrame(
            {
                "flight_id": ["SPR1_20230628"],
                "pixel_id": [1],
                "row": [0],
                "col": [1],
                "x": [100.0],
                "y": [200.0],
                "left_a": [10.0],
                "left_b": [20.0],
                "corr_b001_wl0440nm": [0.12],
                "corr_b002_wl0560nm": [0.23],
                "corr_b003_wl0650nm": [0.34],
                "corr_b004_wl0862nm": [0.45],
            }
        )
        monkeypatch.setattr(pd, "read_parquet", lambda path: df.copy())

        summary = _render_drone_merged_preview(_FakeAxes(), merged_path, "SPR1_20230628")

>       assert summary["rows_previewed"] == 1
E       assert 0 == 1

tests/test_drone_pipeline.py:1091: AssertionError
=============================== warnings summary ===============================
src/spectralbridge/polygons.py:30
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/polygons.py:30: DeprecationWarning: cross_sensor_cal is deprecated; use spectralbridge instead.
    from cross_sensor_cal.exports.schema_utils import ensure_coord_columns

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2373: RuntimeWarning: All-NaN slice encountered
    return np.nanmedian(masked, axis=(1, 2))

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:490: RuntimeWarning: All-NaN slice encountered
    delta_median = np.nanmedian(diff, axis=1)

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/site-packages/numpy/lib/_nanfunctions_impl.py:1593: RuntimeWarning: All-NaN slice encountered
    return fnb._ureduce(a,

tests/test_drone_pipeline.py::test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:495: RuntimeWarning: All-NaN slice encountered
    delta_abs_median = np.nanmedian(np.abs(diff), axis=1)

tests/test_drone_pipeline.py::test_render_drone_correction_magnitude_returns_richer_spatial_summary
  /home/runner/work/spectralbridge/spectralbridge/src/spectralbridge/qa_plots.py:2525: RuntimeWarning: All-NaN slice encountered
    abs_delta = np.nanmedian(full_abs_diff, axis=0)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_drone_pipeline.py::test_render_drone_merged_preview_prefers_non_nodata_rows - assert 0 == 2
FAILED tests/test_drone_pipeline.py::test_render_drone_merged_preview_prioritizes_rightmost_columns - assert 0 == 1
Error: Process completed with exit code 1.
```

## 2026-08-14 - repair cloud workflow documentation page
Branch: main

```text
this page is messed up [https://earthlab.github.io/spectralbridge/tutorials/cloud-workflow/](https://earthlab.github.io/spectralbridge/tutorials/cloud-workflow/)
```

## 2026-08-14 - repair FAQ and audit Markdown-in-HTML pages
Branch: main

```text
this is messed up too [https://earthlab.github.io/spectralbridge/tutorials/cloud-workflow/](https://earthlab.github.io/spectralbridge/tutorials/cloud-workflow/) [https://earthlab.github.io/spectralbridge/faq/](https://earthlab.github.io/spectralbridge/faq/)
```

## 2026-08-14 - add scientific visual story to homepage
Branch: main

```text
here is a panel of images to add to the homepage. These are scientific figures but they are also conceptual to help understand what the package does. can you use this but stylize it to match the website and be readable and engaging? don't just crame it all in one image for example.
```

## 2026-08-14 - preserve technical figure and enlarge it
Branch: main

```text
that is too abstracted. go back to the more technical one that i gave you but just make the font big
```

## 2026-08-14 - route notebook links to repository viewer
Branch: main

```text
this doesn't look like a notebook [https://earthlab.github.io/spectralbridge/vignettes/notebooks/02_correct_neon.ipynb](https://earthlab.github.io/spectralbridge/vignettes/notebooks/02_correct_neon.ipynb) . we want the notebooks to be actuall notebook files in the repo that can be opens and seen on the web. we can't run them live, but have them link to the notebook in the repo.
```

## 2026-08-14 - align vignettes with active research notebooks
Branch: main

```text
the code in the notebooks looks different than the notebooks i've been using throughout the develepment. I've been using some other functions to orcestrate the pipeline and check outputs. can you look at the to python notebooks that I regularly use in the top layer and try to mimic the code and documentation structure a little more to match my notebooks?
```

## 2026-08-14 - build stage-by-stage scientific QA
Branch: main

```text
Codex Prompt: Build Stage-by-Stage QA for SpectralBridge

Work in the existing earthlab/spectralbridge repository. First inspect the current pipeline, documentation, QA code, data structures, intermediate artifacts, and naming conventions. Do not invent pipeline stages or assume filenames from this prompt when the repository already defines them.

The goal is to build a comprehensive QA system in which:

1. Every major processing stage automatically produces its own QA report at the end of that stage.
2. Each stage report combines:
    * real-data maps/images,
    * diagnostic plots,
    * summary statistics,
    * model-based tests,
    * automated PASS / WARN / FAIL checks,
    * concise interpretation of what the diagnostics mean.
3. After the full pipeline finishes, produce a single combined QA document containing the important plots and metrics from every stage.
4. The combined report must perform additional analyses that are only possible after viewing the entire workflow together and explicitly identify any new insight, inconsistency, or artifact revealed by cross-stage comparison.
5. QA artifacts must be deterministic, restart-safe, versioned, and provenance-aware, consistent with the rest of SpectralBridge.
6. Use real processed data for QA. Do not generate fake scientific results. Conceptual diagrams are acceptable only where they explain an operation such as spectral convolution.

The QA should answer three questions throughout:

Did this operation do what it was physically intended to do?

Did it preserve the scientific signal we care about?

Did it introduce any new spatial, spectral, numerical, or computational artifact?

Overall implementation

Create a reusable QA framework rather than a collection of one-off plotting scripts.

Prefer a structure like:

src/spectralbridge/qa/

with modular code for:

* common plotting
* common metrics
* spatial diagnostics
* spectral diagnostics
* model diagnostics
* chunk/seam diagnostics
* calibration diagnostics
* triangle/network diagnostics
* report assembly
* QA thresholds/status classification

Adapt this to the existing repository architecture if another location is more appropriate.

Each processing stage should emit a machine-readable QA artifact, ideally JSON plus tables as appropriate, containing:

* stage name
* input artifact IDs/paths
* output artifact IDs/paths
* software/version information
* parameters
* sample sizes
* metrics
* thresholds
* PASS/WARN/FAIL status
* warnings
* paths to plots
* concise automated interpretation

Also generate a human-readable stage report in HTML and/or PDF, depending on what fits the existing documentation workflow best.

Do not hard-code thresholds without documenting them. Where scientifically defensible thresholds are not yet known, expose them in configuration and label the current defaults as provisional.

⸻

QA LEVELS

Implement four levels of QA where applicable.

Level 1: Visual diagnostics

Maps, RGB/false color, spectra, distributions, correction maps, residual maps.

Level 2: Summary statistics

Bias, variance, quantiles, RMSE, MAE, correlation, valid-pixel fractions, correction-factor ranges, etc.

Level 3: Diagnostic models

Fit models that directly test whether an unwanted physical relationship remains after correction.

Level 4: Invariance and stress tests

Test whether results change with chunk size, restart point, worker count, processing layout, or other implementation details that should not affect the scientific result.

Not every stage requires every level. Apply them where scientifically meaningful.

⸻

STAGE 0 / INPUT DATA QA

For every source entering the correction pipeline, especially NEON and MicaSense:

Spatial plots

Generate:

* natural RGB where bands permit
* useful false-color composite where appropriate
* valid/invalid pixel map
* no-data map
* saturation/clipping map if detectable
* mask layers such as water, shadow, cloud, etc. when available
* spatial coverage/footprint map

Do not present colorized data as though it were true RGB. Clearly label false-color products.

Use consistent map extent and orientation wherever before/after comparison is intended.

Spectral plots

Generate:

* median spectrum
* 5th–95th percentile or similarly useful envelope
* optional representative individual spectra
* bandwise distributions
* fraction valid by wavelength
* fraction clipped/saturated by wavelength
* missing/bad-band summary

Flag suspicious spectral discontinuities and extreme outliers.

Summary metrics

Include at minimum:

* number/fraction valid pixels
* missing data fraction
* reflectance quantiles
* negative reflectance fraction where meaningful
* reflectance > physically plausible range where meaningful
* saturation fraction
* spectral coverage

⸻

TOPOGRAPHIC CORRECTION QA

The central scientific question is:

Did correction remove terrain-illumination dependence without destroying legitimate spectral/ecological structure?

Use the actual illumination variable used by the algorithm, e.g. illumination condition/cos(i), rather than inventing a proxy.

Spatial diagnostics

Produce before/after maps using identical display limits.

Also map:

correction magnitude

[
\Delta R = R_{corrected} - R_{input}
]

Use a zero-centered diverging color scale with symmetric limits.

Map the terrain/illumination predictor itself so the correction can be visually compared against the physical pattern it is intended to remove.

If possible, make multi-band or representative-band versions.

Diagnostic models

For representative wavelengths and preferably all useful wavelengths, fit before and after relationships such as:

[
R_\lambda = \beta_0 + \beta_1 I + \epsilon
]

where I is the appropriate illumination predictor.

Save by wavelength:

* slope
* correlation
* R²
* RMSE
* sample size

Generate a wavelength diagnostic showing before vs after:

* slope versus wavelength
* R² versus wavelength

The desired pattern is a major reduction in illumination dependence after correction.

Signal preservation

Do not declare success merely because the illumination relationship disappears.

Also quantify:

* before/after spectral centroid or median changes
* within-cover or within-homogeneous-region variability where available
* distribution shifts
* spectral angle/distance between before and corrected spectra
* extreme correction factors

Where land cover or homogeneous target labels exist, determine whether within-class variation decreases without unreasonable shifts in class means.

Automated interpretation

Report statements such as:

* illumination dependence reduced substantially
* dependence remains in wavelengths X–Y
* correction increased variance
* extreme corrections concentrated in particular terrain classes
* insufficient valid observations for a reliable test

⸻

BRDF CORRECTION QA

This stage needs especially deep QA because we have already observed possible visual artifacts related to chunking.

Treat two distinct questions separately:

A. Did BRDF correction remove viewing/illumination geometry effects?

B. Did the implementation introduce spatial/computational artifacts?

Physical BRDF diagnostics

Use the actual geometry variables available to the model, such as:

* view zenith angle
* solar zenith angle
* relative azimuth
* other BRDF model variables

Generate spatial maps of the relevant geometry.

Fit before/after diagnostic models such as:

[
R_\lambda = f(VZA, SZA, RAA, \ldots) + \epsilon
]

A simple linear diagnostic is acceptable initially, but use a more appropriate model if necessary.

For every useful wavelength, calculate before and after:

* geometry-model R²
* relevant slopes/effect sizes
* residual variance
* RMSE

Plot these metrics versus wavelength.

The QA should show whether viewing-geometry dependence actually decreases.

BRDF correction magnitude

Map:

[
\Delta R_{BRDF} = R_{after} - R_{before}
]

using symmetric zero-centered diverging limits.

Also map the BRDF correction factor if the algorithm generates one.

Summarize its distribution and identify pathological tails.

Flag pixels/bands with unusually large corrections.

Chunk-boundary artifact detection

This must be a first-class automated QA component.

The pipeline knows or can reconstruct chunk boundaries. Use them.

For each boundary, compare neighboring-pixel discontinuities crossing chunk boundaries against ordinary neighboring-pixel discontinuities in the image interior.

Develop a metric along the lines of:

[
SeamScore_\lambda =
\frac{\operatorname{median}(|R_i-R_j|){\text{across chunk boundaries}}}
{\operatorname{median}(|R_i-R_j|){\text{ordinary neighboring pixels}}}
]

Calculate this before and after BRDF correction.

Plot:

Seam score vs wavelength

with a clear reference at 1.

Also report percentiles and maximum seam scores.

Generate a map highlighting:

* chunk boundaries
* strong local gradients
* detected seam locations

Test whether high-gradient pixels are significantly enriched along computational boundaries.

If appropriate, calculate an edge-enrichment statistic or permutation/bootstrap comparison.

The QA should distinguish:

* genuine landscape boundaries
* flight-line artifacts
* computational chunk seams

as well as practical diagnostics allow.

Chunk invariance test

For a representative subset that is small enough to rerun efficiently, process identical data with multiple chunk configurations.

For example, adapt to appropriate sizes in the real pipeline:

* baseline chunk layout
* smaller chunks
* larger chunks
* shifted chunk boundaries if possible

Then calculate:

[
\Delta C = C_a - C_b
]

for every comparison.

Report:

* maximum absolute difference
* median absolute difference
* RMSE
* 95th/99th percentile absolute difference
* fraction exceeding numerical tolerance

Generate spatial difference maps.

If the implementation is correct, results should be invariant to chunking within documented numerical tolerance.

This should be a strong automated FAIL condition if differences are materially above tolerance.

Other spatial artifact tests

Add deeper diagnostics where useful:

* gradient magnitude maps
* local variance maps
* before/after spatial autocorrelation
* local Moran’s I or similar only if computationally practical and interpretable

For debugging mode, optionally provide a 2-D Fourier/power-spectrum diagnostic capable of identifying periodic spatial structure corresponding to chunk dimensions.

This need not be part of every routine report, but implement it as an available deep diagnostic because regular chunking artifacts can produce identifiable spatial frequencies.

⸻

SPECTRAL CONVOLUTION QA

Use the term spectral convolution rather than generic bandpass resampling unless existing code/docs use a more precise established term.

This stage takes corrected spectra and applies target-sensor spectral response functions.

For example:

* NEON → MicaSense-equivalent bands
* NEON → Landsat-equivalent bands

Concept/real-data figure

Use real NEON spectra and real sensor response functions.

Plot:

* input hyperspectral spectrum
* target SRFs
* resulting convolved band values

Clearly distinguish the underlying real spectrum from the target spectral response functions.

Numerical QA

For every target band calculate:

* SRF normalization
* effective wavelength if useful
* wavelength coverage
* fraction of SRF supported by valid source wavelengths
* contribution from masked/bad source bands
* number of valid source wavelengths
* convolution output range

Flag target bands for which spectral support is incomplete.

Create a metric such as:

SRF valid coverage fraction

and establish configurable warning/failure thresholds.

Reference/unit tests

Create fixed reference spectra with known expected convolution outputs.

The same spectra must reproduce the same convolved values across software releases within a documented numerical tolerance.

These should become automated package tests, not merely plots.

⸻

EMPIRICAL CALIBRATION / SENSOR TRANSLATION QA

The goal is not simply high in-sample correlation.

We need to establish that translation is accurate on held-out data and that residual error is not systematically structured.

For each learned translation edge, calculate out-of-sample:

* bias
* MAE
* RMSE
* unbiased RMSE where appropriate
* R²
* fitted slope
* fitted intercept
* sample size

Use spatially blocked cross-validation where spatial dependence would otherwise leak information between train and test data.

Where multiple sites/acquisition dates exist, consider site/date blocked validation or leave-one-site-out validation as an additional deep QA diagnostic.

Core plots

For each band/pair create:

Observed vs translated

Use hexbin/density plots for large datasets.

Include:

* 1:1 line
* fitted relationship
* metrics
* sample size

Residual vs predicted/observed reflectance

Inspect heteroscedasticity and nonlinear structure.

Residual maps

Map:

[
R_{translated} - R_{observed}
]

Use a zero-centered diverging scale with symmetric limits.

Metrics by band

Plot bias, RMSE/ubRMSE, R², slope/intercept as functions of wavelength/band.

Residual structure model

Fit diagnostic models to determine whether errors remain predictable from variables that should ideally not matter.

Test residual dependence on available variables such as:

* reflectance magnitude
* land-cover type
* illumination
* view geometry
* terrain
* wavelength/band
* spatial coordinates/region
* flight line/chunk
* acquisition date
* site

The point is not necessarily formal inference.

Ask:

Can we predict where the translation will be wrong?

Summarize which variables explain substantial residual structure.

If residuals remain strongly predictable, surface this prominently in the QA report.

⸻

LANDSAT QA

Landsat Collection 2 NBAR is acquired directly rather than being passed through the NEON/MicaSense correction pipeline.

Represent that correctly in both code and documentation.

For Landsat generate QA around acquisition and comparability:

* source product metadata
* acquisition/date
* valid-pixel mask
* QA bits/cloud/shadow/water/snow if applicable
* spatial footprint
* band distributions
* coverage relative to comparison region
* resampling/alignment diagnostics if any spatial matching occurs

Do not pretend that topographic/BRDF correction is being rerun on Landsat if it is not.

The important comparison is between:

directly acquired Landsat NBAR

and

Landsat-like observations generated from another sensor through spectral convolution/calibration.

⸻

SENSOR TRIANGLE QA

SpectralBridge ultimately produces translations between the three sensor spaces:

* NEON
* MicaSense
* Landsat

Treat each triangle edge as a model with its own QA.

But also exploit the network structure.

Edge QA

For each edge produce:

* held-out metrics
* observed vs translated
* residual plots
* residual maps
* per-band errors
* uncertainty

Path consistency

This should be a first-class SpectralBridge diagnostic.

For example compare:

[
T_{M \rightarrow L}(T_{N \rightarrow M}(N))
]

against:

[
T_{N \rightarrow L}(N)
]

Quantify the disagreement between direct and indirect paths.

Do this wherever transformations permit scientifically meaningful comparison.

Cycle consistency

Where bidirectional models permit it, test closed loops such as:

[
N \rightarrow M \rightarrow L \rightarrow N
]

and calculate:

[
CycleError = N’ - N
]

Do analogous cycles beginning from other nodes.

Report:

* cycle bias
* MAE
* RMSE
* error by wavelength/band
* error distributions
* relevant residual maps

The intuitive QA question is:

If we travel around the SpectralBridge triangle, do we return to the same observation?

This should be visible in the final QA report.

Final triangle visualization

Create a clean triangle figure in which each edge includes a concise cross-validated performance summary.

Do not overload the figure.

For example, edge annotations could show:

RMSE / bias / n

or a compact quality score.

Use line styling/width only if it communicates a clearly defined metric and remains interpretable.

⸻

CROSS-STAGE QA

The full pipeline report should do more than concatenate stage reports.

Once all stages are available, calculate additional diagnostics to determine how errors and transformations accumulate.

Track changes through the pipeline

For representative bands/wavelengths, track:

* median reflectance
* variance
* spatial variance
* spectral distance
* valid-pixel fraction
* extreme-value fraction

through every stage.

Produce a concise “pipeline evolution” graphic.

Correction magnitude accumulation

Compare:

* topographic correction magnitude
* BRDF correction magnitude
* calibration correction magnitude

Determine whether one stage dominates total changes.

Look for spatial regions where multiple stages all make unusually large corrections.

Error propagation

Where uncertainty estimates exist, propagate/summarize them through the pipeline.

Compare predicted uncertainty to actual held-out residual error.

Test whether uncertainty is calibrated.

For example, if possible ask whether approximately the expected fraction of observed errors falls inside nominal prediction intervals.

Cross-stage artifact attribution

If a spatial artifact appears in the final product, attempt to identify the first processing stage at which it appears.

This is especially important for chunk artifacts.

Compare maps and gradient/seam statistics stage-by-stage.

The combined report should explicitly state things like:

* chunk-aligned seams first appear after BRDF correction
* illumination dependence is removed by topographic correction and remains low afterward
* a particular wavelength becomes unstable after BRDF
* calibration removes bias but introduces land-cover-dependent residuals
* translation error is concentrated in low-reflectance/shadowed pixels
* direct and indirect triangle translations disagree for specific bands

Do not manufacture such statements. Derive them from actual metrics.

⸻

FINAL QA REPORT

At the end of a successful pipeline run, automatically assemble one comprehensive report.

Design it for both:

* a scientist inspecting the processing
* a developer debugging the pipeline

Keep plots large and legible. Do not create a giant mosaic of tiny unreadable figures.

Prefer one clear question per figure.

Organize approximately as:

1. Executive QA summary

Show:

* overall status
* stage-by-stage PASS/WARN/FAIL
* major warnings
* key numerical metrics
* short plain-language interpretation

2. Input data

Most useful maps/spectral summaries.

3. Topographic correction

Most useful before/after physical diagnostic and correction map.

4. BRDF correction

Physical geometry diagnostic plus seam/chunk diagnostics.

5. Spectral convolution

Real spectrum + SRF + output-band diagnostic and coverage metrics.

6. Sensor calibration/translations

Held-out comparison plots, residual maps, metrics.

7. Sensor triangle

Edge QA plus path/cycle consistency.

8. Cross-stage synthesis

This is important.

Generate new plots and analyses that combine information from all previous stages.

Write an automatically generated section titled something like:

What we learn from the full pipeline

This section should identify actual findings supported by the QA, not generic boilerplate.

Examples of the kinds of conclusions it should be capable of producing:

* correction succeeds physically but produces computational seams
* most error enters at a particular stage
* one wavelength range is consistently unstable
* translation performance differs systematically by land cover
* indirect triangle translation has higher error than direct translation
* uncertainty estimates are too optimistic
* processing is sensitive to chunk configuration
* all invariance tests pass within numerical tolerance

Include quantitative evidence for every automated conclusion.

⸻

COLOR AND VISUALIZATION RULES

Use scientifically appropriate color mappings.

Absolute continuous variables

Use perceptually uniform sequential color maps.

Examples:

* reflectance
* illumination
* view angle
* uncertainty
* correction factor when one-sided

Signed differences/residuals

Use a diverging color map centered exactly on zero.

Examples:

* corrected minus raw
* predicted minus observed
* chunk configuration A minus B
* cycle error

Make positive/negative limits symmetric around zero.

Categorical masks

Use discrete colors for:

* invalid
* water
* shadow
* cloud
* saturated
* etc.

Before/after comparisons

Use identical:

* map extents
* value limits
* normalization
* wavelength/band selections

unless there is a scientifically compelling reason not to.

If different scales are necessary, state it prominently.

Large datasets

Prefer:

* hexbin
* density
* quantile summaries

over plotting millions of opaque scatter points.

⸻

TESTING

Add automated tests for the QA framework itself.

At minimum test:

* deterministic QA metrics
* deterministic output paths
* numerical convolution reference cases
* seam score on synthetic known seam/no-seam arrays
* chunk invariance comparison
* residual metrics
* QA threshold logic
* report generation
* handling of missing ancillary variables
* graceful behavior when a diagnostic cannot be computed

A missing diagnostic should not silently disappear.

Report it explicitly as:

NOT EVALUATED

with the reason.

⸻

PERFORMANCE

QA must not make routine processing prohibitively expensive.

Use:

* reproducible sampling for very large scatter/model diagnostics
* reduced-resolution map previews where appropriate
* cached intermediate summaries
* optional deep QA mode for expensive tests

However:

chunk invariance and seam detection should remain prominent because we already have evidence that BRDF chunking can produce visually obvious artifacts.

Implement at least two QA modes if useful:

standard

and

deep

Standard should run automatically.

Deep can add:

* multiple chunk reruns
* Fourier diagnostics
* additional blocked cross-validation
* expensive spatial statistics

⸻

DOCUMENTATION

Add documentation explaining for every diagnostic:

* what is plotted/calculated
* why it matters scientifically
* what a good result looks like
* what a bad result looks like
* current threshold
* whether the threshold is provisional
* how to reproduce the diagnostic
* which pipeline artifact it evaluates

Make the QA documentation useful to an environmental scientist who is not a remote-sensing algorithm developer.

⸻

IMPORTANT SCIENTIFIC DISTINCTIONS

Preserve these distinctions everywhere:

1. NEON and MicaSense go through the relevant correction pipeline.
2. Landsat Collection 2 NBAR is obtained directly and is not artificially sent through the same correction pipeline.
3. Spectral convolution projects high-spectral-resolution observations into a target sensor’s spectral response space.
4. Empirical calibration/translation is distinct from convolution.
5. Convolution creates comparable sensor representations.
6. Calibration learns relationships between those representations and observed sensor measurements.
7. QA must test both physical correctness and computational correctness.
8. A statistically improved correction can still fail QA if it introduces seams, grid artifacts, spectral distortion, or chunk dependence.
9. High R² alone is never sufficient evidence of a successful translation.
10. The sensor triangle enables unique path- and cycle-consistency tests that should be treated as core SpectralBridge QA rather than optional extras.

⸻

DELIVERABLES

Implement the code, tests, and documentation rather than only writing a proposal.

At completion provide:

1. a concise description of the QA architecture added
2. files created/changed
3. which diagnostics run at each pipeline stage
4. example commands for generating QA
5. example stage QA outputs using available real test/example data
6. one complete combined QA report
7. test results
8. any diagnostics that could not yet be implemented and why
9. any concerning behavior discovered in the existing pipeline while implementing QA, especially BRDF/chunking issues
10. recommendations for thresholds that still require empirical tuning

Before coding, inspect the existing pipeline thoroughly and write a short implementation plan based on the repository as it actually exists. Then implement it incrementally, running tests and generating real QA artifacts as you go.
:::
```

## 2026-08-14 - authorize one real-data QA run
Branch: main

```text
you can download one and run it through all the tests and qa.
```
## 2026-08-14 - provide local HDF5 for real QA run
Branch: main

```text
I just added an h5 to the repo
```
## 2026-08-14 - confirm local HDF5 placement
Branch: main

```text
it was in downloads, now in repo
```

## 2026-08-14 - interpret real-data QA failures and runtime
Branch: main

```text
what do we do about those fails? can we adjust something or is this a data quality issue? how long does it take to run the whole pipeline through extraction to parquet?
```

## 2026-08-15 - reconsider remaining real-data QA failures
Branch: main

```text
we're still failing two test but I'm not sure we should be. the fraction of NA is fixed based on how the plane flew over the site but then the bounding box goes around the whole flight track can we spend some time thinking through these two remaining failures and if they're actually failures.
```

## 2026-08-15 - label bad QA information without masking
Branch: main

```text
I don't want to mask things yet, I just want to interprete the bad information correctly as bad and mark it as suche but don't remove it yet.
```

## 2026-08-15 - standardize QA plot axes and location labels
Branch: main

```text
we need to standardize the plot axes so that we can compare reports between runs. this is only one run and we need to run like 300 of these and we'll want them to be interoperable. so y and x axes in figures should be a standard range when possible and maps should be labelled with their location so we can flip between graphs to compare without needing to look at the report header.
```

## 2026-08-15 - add figures for every QA stage and port brightness plots
Branch: main

```text
can we produce images for all stages? currently we don't have good figures for the parquet extration and merge and we don't have plots for the correction. Also, we need a test an plot for the brightness correction and we need to recreate and add these plots in python when the original is in r [https://github.com/earthlab/spectralbridge/blob/a30498ac606304bca3067acbff0e0348b68db767/coef_plots_Ty.qmd](https://github.com/earthlab/spectralbridge/blob/a30498ac606304bca3067acbff0e0348b68db767/coef_plots_Ty.qmd)
```

## 2026-08-15 - organize QA code and expand validation website guidance
Branch: main

```text
make sure all this qa stuff that we've added is cleanly organized and keeps all the code human readable and that's it's documented well. update the validation section of the website with detailed exlinations about each of the test organized in each of the sections. give example images from the test run we've been doing.
```

## 2026-08-17 - repair stale docs browser assertion
Branch: main
AI system: OpenAI Codex
Model: GPT-5

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
                assert page.locator("h1#spectralbridge").is_visible()

                logo = page.locator("img[alt='SpectralBridge logo']").first
                assert logo.evaluate("(img) => img.naturalWidth") > 0

                assert page.get_by_role(
                    "heading", name="Three technical views. Read them one at a time."
                ).is_visible()
                assert page.locator(".sb-science-panel").count() == 3
                assert page.locator(".sb-science-panel__figure svg").count() == 3
                assert page.locator(
                    "a[href$='images/homepage/spectralbridge-technical-overview.png']"
                ).count() == 3
                desktop_figure = page.locator(".sb-science-panel__figure").first
                assert desktop_figure.bounding_box()["width"] > 500

                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                )
                mobile_viewport = page.locator(".sb-science-panel__viewport").first
                assert mobile_viewport.evaluate(
                    "element => element.scrollWidth > element.clientWidth"
                )
                page.set_viewport_size({"width": 1280, "height": 900})

                page.goto(urljoin(base_url, "vignettes/"), wait_until="networkidle")
                assert page.get_by_role("heading", name="Choose a vignette").is_visible()
                assert page.get_by_role(
                    "link",
                    name="Carry On My Wayward Son (resume a run)",
                ).is_visible()
                assert page.get_by_role(
                    "link",
                    name="7. Extract polygon spectra",
                ).is_visible()

                page.goto(
                    urljoin(base_url, "vignettes/notebook-vignettes/"),
                    wait_until="networkidle",
                )
                assert page.get_by_role(
                    "heading", name="Runnable notebook vignettes"
                ).is_visible()
                notebook_links = page.locator(
                    f"a[href^='{GITHUB_NOTEBOOK_BASE}'][href$='.ipynb']"
                )
                assert notebook_links.count() == 9
                assert page.get_by_role(
                    "link", name="Correct NEON reflectance", exact=True
                ).get_attribute("href") == (
                    f"{GITHUB_NOTEBOOK_BASE}02_correct_neon.ipynb"
                )

                page.goto(urljoin(base_url, "reference/"), wait_until="networkidle")
                assert page.get_by_role("heading", name="Technical reference map").is_visible()
                assert page.get_by_role("link", name="Stage order and restart behavior").first.is_visible()

                page.goto(urljoin(base_url, "validation/"), wait_until="networkidle")
                assert page.get_by_role("heading", name="Validation evidence").is_visible()
                assert page.get_by_role("link", name="Topographic correction").first.is_visible()
                assert page.get_by_text("offline-contract-5-per-module").first.is_visible()

                page.goto(
                    urljoin(base_url, "validation/topographic_correction/"),
                    wait_until="networkidle",
                )
                assert page.get_by_role(
                    "heading", name="Validation: Topographic correction"
                ).is_visible()
                assert page.get_by_text("topographic_correction-005").is_visible()
>               assert page.get_by_text("Synthetic correlation reduction").is_visible()
E               assert False
E                +  where False = is_visible()
E                +    where is_visible = <Locator frame=<Frame name= url='http://127.0.0.1:8000/validation/topographic_correction/'> selector='internal:text="Synthetic correlation reduction"i'>.is_visible
E                +      where <Locator frame=<Frame name= url='http://127.0.0.1:8000/validation/topographic_correction/'> selector='internal:text="Synthetic correlation reduction"i'> = get_by_text('Synthetic correlation reduction')
E                +        where get_by_text = <Page url='http://127.0.0.1:8000/validation/topographic_correction/'>.get_by_text

tests/test_docs_playwright.py:160: AssertionError
=========================== short test summary info ============================
FAILED tests/test_docs_playwright.py::test_docs_site_core_pages_render_in_browser - assert False
 +  where False = is_visible()
 +    where is_visible = <Locator frame=<Frame name= url='http://127.0.0.1:8000/validation/topographic_correction/'> selector='internal:text="Synthetic correlation reduction"i'>.is_visible
 +      where <Locator frame=<Frame name= url='http://127.0.0.1:8000/validation/topographic_correction/'> selector='internal:text="Synthetic correlation reduction"i'> = get_by_text('Synthetic correlation reduction')
 +        where get_by_text = <Page url='http://127.0.0.1:8000/validation/topographic_correction/'>.get_by_text
Error: Process completed with exit code 1.
```
## 2026-07-09 - configurable scene-wide topo fit
Branch: main

```text
Option 2 looks like the best option becuase we would want new runs. 
So to confirm, after the modification- 
1) The topo correction will then be scene wide and not just on the chunks. 
2) No other modification will be there
3) This modification is configurable ? Like can we just send in a variable where it says we want this behaviour or not 
```

## 2026-07-13 - diagnose BRDF/topo -9999 wipe
Branch: main

```text
here is the output-
corr img exists: True size_gb: 14.529892128
corr hdr exists: True
dims: 844 x 10103 x 426

row=5051, col=422
  band   0: raw=    87.00  corr= -9999.00
...
So there is an issue with BRDF and Topo correction since its making a pixels invalid. THe negative 9999 values are coming from somewhere. This could be either from the h5 whos format could be chnaged recently (the json keys may be shifted). or it could be from somewhere else. We need to figure this part out before running the entire pipeline. Maybe focus on the brdf_topo.py and the corrections.py file. also FYI for line 264 and 265 in the brdf_topo.py file i tried combinations of chunk_y = 100
    chunk_x = 100, and chunky with 500 and chunkx with cube. somehting. I dont think this is the problem. One Nan value also just propagetes and makes everything invalud i think. Can we run some some comprehensive tests for this stage and diagone the root cause and get the BRDF and topo correction to run properly?
```

## 2026-07-13 - re-run BRDF correction after sync
Branch: main

```text
OKay i made the update to 1 to 6. Can we run the brdf correction code block again and testr
```

## 2026-07-14 - confirm 0/1 means unchunked apply
Branch: main

```text
check this- 2026-07-14 17:50:40,909	INFO util.py:154 -- Outdated packages:
...
BRDF+topo correction:   0%|          | 0/1 [00:00<?, ?tile/s]
...
This means the BRDF and topo corrrection was unchuinked right?
```

## 2026-07-22 - full vs polygon extraction call
Branch: main

```text
to run the full extraction instead of the polygon extraction. I can run this rihgt?
go_forth_and_multiply(
    base_folder=base_folder,
    site_code=site_code,
    year_month=year_month,
    product_code=product_code,
    flight_lines=flight_lines,
    engine="thread",
    max_workers=1,
    polygon_path=polygon_path,
    extraction_mode="full",
)
```

## 2026-07-22 - run pipeline from local H5 only
Branch: main

```text
Alright, we need to do find a way to run the pipeline. Since the h5 isnt available for download, I have just the .h5s for this pipeline- NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance

Give me a sciprt i can run the pipeline just from this. We problably need to cerate certain folders for the pipeline to run n stuff. Refer to the patch_script_toworkfromcorrectedfiles.py to get an idea of how we can accomplish this. 
```

## 2026-07-22 - which 6 files to sync
Branch: main

```text
Which are the 6 files which we updated again? I want to copy them and update the files in another instance which has the old code. 
```

## 2026-07-22 - set SCENE_APPLY_CHUNK_Y=100000
Branch: main

```text
I dont think you made the change to nochunk to brdf_topo.py-
...
Make this change to your file
```

## 2026-07-22 - push/update 7 files on GitHub
Branch: main

```text
can you run the github commands to update the 7 files (if not there, we need to add them) in the repo. 
```

## 2026-07-22 - verify 7 files on GitHub for fresh pulls
Branch: main

```text
alright, Id like to do fresh pulls from the github repo from now on to run the pipleine on another instance. Can we quickly check if the 7 files nad other important files in the pipeline looks good to go in the Github repo?
```

## 2026-07-22 - single notebook cell for full pipeline setup+run
Branch: main

```text
alright cool. Also, I need a single notebook cell which does all of this. Usually after downloading the repo, in the notebook - here is what i do-
...
```

## 2026-07-22 - R10C full extract stuck on filter/CSV
Branch: main

```text
here is how the pipeline ran-
...
Is thhere somehting in place to reach a larrge merged parquet like this
```

## 2026-07-22 - streaming no-data filter for large merges
Branch: main

```text
I want somehting in place to do the filtering efficiently as well so that pipeline runs all the way through
```

## 2026-07-22 - can I just re-run local-h5 cell?
Branch: main

```text
i can just run this cell again nad the pipeline will now finish right?
...
```

## 2026-07-22 - confirm re-run after merge_duckdb sync
Branch: main

```text
i alrady updated @src/spectralbridge/merge_duckdb.py , i can just run that cell again right
```

## 2026-07-22 - R10C full run assessment after streaming filter
Branch: main

```text
here is how the piepleine ran-
...
whats happening and how did i go
```

## 2026-07-22 - explain row count mismatch
Branch: main

```text
what is this row count mismatch?3. Row count mismatch
Expected after filtering: 3.04M kept vs 4.56M pre-filter.
```

## 2026-07-22 - fix QA pyarrow pandas.period clash
Branch: main

```text
okay, should we update the code so that the pyarrow thing doesnt occur?
```

## 2026-07-22 - push merge_duckdb + qa_plots
Branch: main

```text
alright lets push the new changes (@src/spectralbridge/merge_duckdb.py and qa_plots.py
```

## 2026-07-22 - does notebook cell support NEON download too?
Branch: main

```text
okay cool, also the cell you gave me, does it work if the neon data is available to download as well? and if its not is it going to do the patching with the h5 path?
```

## 2026-07-22 - one-shot cell both cases / prefer NEON then local
Branch: main

```text
yes I am talking about this cell-
...
would this work for both cases?it should first check if the neon data is available for download or else do the patching stuff.
```

## 2026-07-22 - separate NEON download vs local-H5 cells
Branch: main

```text
actually lets seperate the concerns. Give me one celll i can run for the neon download and a seperate cell which does have all the installations but has the other function for patching where I provide the h5 link. 
```

## 2026-07-22 - gocmd put i/o timeout on CSV
Branch: main

```text
(base) jovyan@aed48c4ae:~/data-store/spectralbridge$ ./gocmd put NEON_TM_2 i:/iplant/home/shared/earthlab/macrosystems/Processed_NEON_TM_July_2026/
Unexpected error!
...
write tcp 10.42.102.213:48394->206.207.252.35:1247: i/o timeout

im getting this error for gocmds, whats wrong
```

## 2026-07-22 - did gocmd only fail on CSV?
Branch: main

```text
did it only fail to upload the csv ?
Have a look at the second one as well-
(same gocmd put error on merged_pixel_extraction.csv / i/o timeout)
```

## 2026-07-22 - gocmd ls results (empty paste)
Branch: main

```text
here you go-
```

## 2026-07-22 - CyVerse L002 listing + H5 symlink
Branch: main

```text
(base) jovyan@aed48c4ae:... gocmd ls ...L002...
...
Also, the h5 didnt upload coz of the sym link i think-
```

## 2026-07-22 - script to verify gocmd upload completeness
Branch: main

```text
can we be sure all the files for trasnferred except the H5 and .csv in both cases. 
Give me a python script i can run from /home/jovyan/data-store/spectralbridge to check this first. Notice the gocmd ls in kind of weird and spits out a string kind of output 
```

## 2026-07-23 - drone H5 missing solar geometry
Branch: main

```text
getting this -
[drone] Skipping manifest row 31 for MTST_11 with malformed acquisition datetime: 'nan' 'nan'
[drone] Skipping manifest row 46 with missing Plot value in /home/jovyan/data-store/spectralbridge/src/spectralbridge/data/drone_field_manifest.csv
[drone] Starting batch: 3 discovered | 3 to process | extraction_mode=full | polygon=None | run_root=drone_outputs/aop_aug14_2023
Click to show javascript error.
[drone] [1/3] AOP_GOLDHILL_20230814 | source=summer-2023-10cm-10k/AOP-GOLDHILL-08-14-23-ExportPackage | type=h5 | stage=preparing working H5
[drone] FAILED for summer-2023-10cm-10k/AOP-GOLDHILL-08-14-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5
Traceback (most recent call last):
  File "/home/jovyan/data-store/spectralbridge/src/spectralbridge/pipelines/drone.py", line 2373, in run_drone_pipeline
    raise RuntimeError(
RuntimeError: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback.
[drone] [1/3] AOP_GOLDHILL_20230814 -> failed_other: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback. (0.3s)
[drone] [2/3] AOP_GORDON_20230814 | source=summer-2023-10cm-10k/AOP-GORDON-08-14-23-ExportPackage | type=h5 | stage=preparing working H5
[drone] FAILED for summer-2023-10cm-10k/AOP-GORDON-08-14-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5
Traceback (most recent call last):
  File "/home/jovyan/data-store/spectralbridge/src/spectralbridge/pipelines/drone.py", line 2373, in run_drone_pipeline
    raise RuntimeError(
RuntimeError: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback.
[drone] [2/3] AOP_GORDON_20230814 -> failed_other: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback. (0.3s)
[drone] [3/3] AOP_Ruby_20230814 | source=summer-2023-10cm-10k/AOP-Ruby-08-14-23-ExportPackage | type=h5 | stage=preparing working H5
[drone] FAILED for summer-2023-10cm-10k/AOP-Ruby-08-14-23-ExportPackage/NEON_D13_NIWO_test_aligned_orthomosaic.h5
Traceback (most recent call last):
  File "/home/jovyan/data-store/spectralbridge/src/spectralbridge/pipelines/drone.py", line 2373, in run_drone_pipeline
    raise RuntimeError(
RuntimeError: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback.
[drone] [3/3] AOP_Ruby_20230814 -> failed_other: Drone correction requested but no solar geometry is available. Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, or a drone_manifest_path with acquisition datetime values; set require_solar_geometry=False to permit an uncorrected fallback. (0.1s)
Processed: 0
Failed: 3
Merged: None
```

## 2026-07-23 - runtime from oldest vs newest file mtime
Branch: main

```text
for this folder-
(base) jovyan@aef7aad8b:~/data-store/spectralbridge/NEON_TM_5/NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance$ ls
<full listing of L005 ENVI/parquet/QA products omitted for brevity>

I want to the difference between the time for the oldest file and the newest, so that we know the runtime, give me the commadn
```

## 2026-07-24 - run pipeline from BRDF corrected ENVIs
Branch: main

```text
We'll work on the drone pipeline soon again. 
I realiase the patch script cell can be used to specify the path of the .h5, create required folders and run the full pipeline from there.
I want to know if there's a way to run the pipeline from BRDF corrected envis as well. 
```

## 2026-07-24 - is patch script enough from only corrected ENVI pair?
Branch: main

```text
Im interested in the NEON pipeline and not the drone one for now. 
So patch_script_toworkfromcorrectedfiles.py is sufficient to run the whole NEON pipeline from just these 2 files NEON_D13_NIWO_DP1_L005-1_20230815_directional_reflectance_brdfandtopo_corrected_envi.hdr
NEON_D13_NIWO_DP1_L005-1_20230815_directional_reflectance_brdfandtopo_corrected_envi.img?

Or do we need to build another scirpt for this?

ALso, does the absense of the previous files in the pipeline after the later stages (like parquet creation, merged parquet creation, will there be somehting missing from the merged_parquet creation?) 
```

## 2026-07-24 - where to place corrected ENVI + full cell for R10C L005
Branch: main

```text
okay, I want to try the patch script on NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance flightline.
Tell me where I have to place the brdf corrected .img and .hdr and give me the complete cell the to run the pipeline (without polygon extraction (full)). 
```

## 2026-07-24 - cell that builds folder structure from two file paths
Branch: main

```text
I want a cell which can do this even without the folder structure.
The script/cell should just take it the two file paths (brdf corrected .img and .hdr), also take in a base folder name ( which can be anything) and create the folder structrue required and proceed with the full piepleine. 
```

## 2026-07-24 - symlinks vs real files, and pip install needed?
Branch: main

```text
okay i used this cell. Are any files created symlinks or is everything actual files?
Also for this cell to work, does it need any pip install %e or something?
```

## 2026-07-24 - add pip install / cd for fresh instance
Branch: main

```text
lets assume I havent been running the flightline processsing and I just started the instance and downloaded the spectralbridge repo in /home/jovyan/data-store/ path.

Add the % pip install cding into the spectralbrdge repo. and if needed cd out and go through with the rest of the pipeline
```

## 2026-07-24 - add polygon path + extraction mode params to cell
Branch: main

```text
What if I want polygon extraction as well? Can you update the top of the cell with 2 more parameters? like, polygonpath parameter and ercation parameter which takes full or polygon (mention this in the comments)
```

## 2026-08-13 - mask negatives in oli_envi for violins
Branch: main

```text
okay  we'll get to the drone stuff a little later. I wanted to know what we can do for making the violin plots a little better.
Since there are negative values in the oli_envi, can we try to remove the negative values? Would that removing all rows with even one negtative value from the .img. I know we do something like for the final csv (taking off rows with >90% negtative vlaues) but i want to do it to the oli_envi as well
```

## 2026-08-13 - count remaining pixels after any-band negative drop
Branch: main

```text
okay so each row in the .img represents a pixel right? 
I want to know how many rows remian after taking off rows iwth even one band negative value.
```

## 2026-08-13 - write nonneg oli_envi sibling rasters
Branch: main

```text
Just before I run this cell-
from __future__ import annotations
...
Give me the cell to create new .imgs after taking off all the pixels with even one band as negative. It shouldnt replace the existing files but create new files.
```

## 2026-08-13 - clarify nonneg raster still has -9999
Branch: main

```text
if remaining pixels are writtten to -9999, the raster still has negative vlaues and thatll show up later right
```

## 2026-08-13 - audit notebook -9999 handling through violins
Branch: main

```text
you have the notebook right, can you check if all the plots/cells till the violin plots deal with -9999 as no data and not as reflectance values
```

## 2026-08-13 - do violins still use induced -9999
Branch: main

```text
so using noneg files - do the violin plots still read the -9999 vaues which we just induced by making making pixel with even one negative value as -9999? I mean, do the violin plots still read this as negative refleactance values
```

## 2026-08-13 - confirm any-band negative pixels were dropped
Branch: main

```text
so we actually did drop all pixels which have even one band as negative right?
```

## 2026-08-13 - audit new notebook for violin outlier filters
Branch: main

```text
I just uploaded a new notebook. Can you check if we are removing any outliers in this? I know we we worked on some outlier removal code to remove ROI*band points from violins. I dont want that here. I want this to be pure non-neg file values
```

## 2026-08-13 - list cells that drop violin outliers
Branch: main

```text
can you tell which are all the cells where we drop the outliers?
```

## 2026-08-13 - band 4 pct negative vs abs positive
Branch: main

```text
baseline = "HLS_L30_Boulder_09162021.tif"

fig, ax, summary = violin_pct_and_abs_diffs_labeled_auto(
    result,
    baseline_image=baseline,
    statistic="mean",
    bands=range(1, 8),
    alpha=0.05,          # test threshold
    fdr=True,            # FDR across bands
    pct_label_decimals=1,
    abs_label_decimals=4,
    abs_reflectance_scale=1.0,  # use 100.0 if you want Δ shown in % units
    save_path="spectral_stats/violin_auto_labels.png",
    add_jitter_points=True
)

display(summary)   # shows per-band n, p-values, choice (mean/median), and the label values used


Im looking at this cell, and this the output-
	band	n	p_raw	p_adj	choice	pct_value	abs_value
0	1	55	0.845818	0.845818	mean	2.317123	19.797246
1	2	55	0.140418	0.196586	mean	1.041665	23.331659
2	3	55	0.343364	0.400591	mean	1.747460	33.541506
3	4	55	0.047108	0.082438	mean	-1.055455	25.248675
4	5	55	0.000607	0.002123	median	2.566724	53.915771
5	6	55	0.001478	0.003449	median	1.097476	31.224854
6	7	55	0.000006	0.000044	median	1.849171	36.095825


Im wondering for Band 4, how the percent value is negative but abs_value is positive?
```

## 2026-08-13 - why mean Δ+ but mean %Δ-
Branch: main

```text
here is the output-
mean Δ   should match abs_value ~ 25.25
mean %Δ  should match pct_value ~ -1.06

I didnt still understand. If B-A for band 4 is positive, how can pct_value be negtaive
```

## 2026-08-13 - subtract abs_value to correct NEON to Landsat?
Branch: main

```text
okay so, we are trying to add something to the neon data to correct it to landsat. So it looks for all bands- we have to subtract the abs_value from this table. Is that correct?
```

## 2026-08-13 - confirm replace brightness JSON with pct
Branch: main

```text
so to my understanding, I just have to replace the landsat_to_micasense.json with these. And its the percentage values which are actually used right?
```

## 2026-08-17 - which of 2 brightness json files
Branch: main

```text
Wait I dont want to add any new .jsons. Which is the file where I have to use these coefficients (percentages). My college said its there 2 files in- https://github.com/earthlab/spectralbridge/tree/main/src/spectralbridge/data/brightness Read the descroption of those 2 files. I think they are the ones where we can put in these new values right?
```

## 2026-08-17 - generate mean/median choice percents
Branch: main

```text
Those percentage values which we generated, looks like we decided to keep choice as median instead of mean for some and median for others, can you give me code to generate that?
```

## 2026-08-17 - NEON download 400 SITE_CODE
Branch: main

```text
okay we ll get to the cofficients in a little while. Im trying this one cell code to download neon h5 and run the whole pipeline- [NEON_TOKEN REDACTED] SITE_CODE = "NEON" YEAR_MONTH = "2020-07" FLIGHT_LINES = ["NEON_D13_NIWO_DP1_20200731_151902_reflectance"] ... HTTPError 400 for url .../DP1.30006.001/NEON/2020-07 ... requests has no attribute ProxyError
```

## 2026-08-17 - 5 flightlines sequential?
Branch: main

```text
okay. Quick question- in that code cell i can put about 5 flgithlines here- 
FLIGHT_LINES = [
    "NEON_D13_NIWO_DP1_20200731_151902_reflectance",
]

and its going to run in sequence right
```

## 2026-08-17 - review unpulled remote QA
Branch: main

```text
okay also, my firend said he added some new QA stuff. Can take a look at the repo now (the new version which we havent pulled) and see if the QA stuff he has added  doesnt slow down the pipeline too mucg
```

## 2026-08-17 - median pct_value for JSON coeffs
Branch: main

```text
Okay i just ran this-
import json
import pandas as pd

# `summary` from violin_pct_and_abs_diffs_labeled_auto(...)
out = summary.copy()
out["json_coeff_pct"] = -out["pct_value"]  # stored as subtracted NEON-HLS %

display(out[["band", "n", "p_adj", "choice", "pct_value", "json_coeff_pct"]])

bands = {str(int(r.band)): float(r.json_coeff_pct) for r in out.itertuples()}
payload = {
    "system_pair": "landsat_to_micasense",
    "description": "Brightness coefficients to adjust Landsat convolutions relative to HLS (subtracting NEON->Landsat percent differences by band; mean or median chosen by FDR normality test).",
    "unit": "percent",
    "bands": bands,
}
print(json.dumps(payload, indent=2))

And i got this- 
	band	n	p_adj	choice	pct_value	json_coeff_pct
0	1	55	0.845818	mean	2.317123	-2.317123
1	2	55	0.196586	mean	1.041665	-1.041665
2	3	55	0.400591	mean	1.747460	-1.747460
3	4	55	0.082438	mean	-1.055455	1.055455
4	5	55	0.002123	median	2.566724	-2.566724
5	6	55	0.003449	median	1.097476	-1.097476
6	7	55	0.000044	median	1.849171	-1.849171
{
  "system_pair": "landsat_to_micasense",
  "description": "Brightness coefficients to adjust Landsat convolutions relative to HLS (subtracting NEON->Landsat percent differences by band; mean or median chosen by FDR normality test).",
  "unit": "percent",
  "bands": {
    "1": -2.317122544256198,
    "2": -1.0416645346519113,
    "3": -1.747459593466453,
    "4": 1.0554552692015908,
    "5": -2.566724304759174,
    "6": -1.0974761245479203,
    "7": -1.849171372710681
  }
}

Are we getting the pct_values for the median?
```

## 2026-08-17 - force median for all bands
Branch: main

```text
Yes I know the funtion picks statistic as median and mean but I wna thte choice to be median for all bands, lets geenrate the pct values based on this
```

## 2026-08-17 - confirm all-median coeffs look right
Branch: main

```text
here you go-
	band	n	choice	pct_value	json_coeff_pct
0	1	55	median	4.444952	-4.444952
1	2	55	median	2.412679	-2.412679
2	3	55	median	1.670916	-1.670916
3	4	55	median	-0.694524	0.694524
4	5	55	median	2.566724	-2.566724
5	6	55	median	1.097476	-1.097476
6	7	55	median	1.849171	-1.849171


Does that look right?
```

## 2026-08-17 - update brightness JSONs and push
Branch: main

```text
Okay now lets use this and update the 2 .json files in the github repo accordingly. THe landsattomicasnse fits right in i think for these 7 pct values. For the other file, we need to take the 6 values (bands 2-7). Update the jsons and push the changes
```

## 2026-08-17 - JSON values only, keep descriptions
Branch: main

```text
I dont want the description or naything changed in the jsons, just the values. 
```

## 2026-08-17 - commit brightness JSON values only
Branch: main

```text
Yes commit just these json files. 
```

## 2026-08-17 - confirm JSON commit vs origin ahead
Branch: main

```text
okay the json stuff is commited already right even though main is few commits ahead?
```

## 2026-08-17 - pull remote then push JSON commit
Branch: main

```text
oh so its not on github yet? THen yes, lets pull those commits and push this
```

## 2026-08-17 - QA crash after BRDF corrected img
Branch: main

```text
op - 16:13:19 up 12 days, 23:09,  0 users,  load average: 2.04, 1.38, 1.05
Tasks:   4 total,   1 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  8.2 us,  0.4 sy,  0.0 ni, 91.2 id,  0.1 hi,  0.0 si,  0.0 st
MiB Mem : 257315.3 total, 129131.3 free,  68227.1 used,  59956.9 buff/cache
MiB Swap:   4111.9 total,   4111.9 free,      0.0 used. 186746.2 avail Mem 

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND                                                                              
    134 jovyan    20   0   78.6g  50.0g 135932 S 329.9  19.9   9:44.86 python                                                                               
      1 jovyan    20   0  759516 130908  23188 S   1.0   0.0   0:08.60 jupyter-lab                                                                          
    345 jovyan    20   0    8444   5120   3652 S   0.0   0.0   0:01.30 bash                                                                                 
    456 jovyan    20   0   10404   4096   3412 R   0.0   0.0   0:00.00 top     

Is any recent QA edit causing a problem? Coz I see that the kernel crashed just after exporting the brdf corrrected .img. 
```

## 2026-08-17 - update brightness JSONs and push
Branch: main

```text
Okay now lets use this and update the 2 .json files in the github repo accordingly. THe landsattomicasnse fits right in i think for these 7 pct values. For the other file, we need to take the 6 values (bands 2-7). Update the jsons and push the changes
```

## 2026-08-17 - gocmd skip existing remote files
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
is there a way we can skip if the file exists. The go command asks this, that I give the option na - no all.
```

## 2026-08-17 - gocmd csv skip vs reupload
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Have a look at this. It says skip uploading file but then uploads it anyway. And then it looks like it failed on the .csv and thats a big file (73GB)
```

## 2026-08-17 - gocmd skip vs uploading print
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
if it skipped- why do i still get- skip uploading a file "/home/jovyan/data-store/spectralbridge/NIWO_a01/NEON_D13_NIWO_DP1_20200731_151902_reflectance/NEON_D13_NIWO_DP1_20200731_151902_reflectance_micasense_to_match_tm_etm+_undarkened_envi.parquet" to "/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/NIWO_a01/NEON_D13_NIWO_DP1_20200731_151902_reflectance/NEON_D13_NIWO_DP1_20200731_151902_reflectance_micasense_to_match_tm_etm+_undarkened_envi.parquet". The file with the same hash already exists!
📤 Uploading file: NEON_D13_NIWO_DP1_20200731_151902_reflectance_micasense_undarkened_envi.parquet

WHy does it say skip but still says Uploading file. Are you sure it skips
```

## 2026-08-17 - record gocmd upload failures then continue
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Incase it fails, I want it to record which file it failed like in another file (no need to keep the ocnnection to this file alwasys). And then move on to the go command of the next file on the list. Make the change to the sciurpt
```

## 2026-08-17 - include csv in gocmd upload
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
wait i dont want to exclude csv. Please include that as well
```

## 2026-08-17 - why 81 vs 95 files to upload
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
how come here it found 81 files -
base) jovyan@a27c5f39d:~/data-store/spectralbridge$ python move_folders_from_instance_to_remote.py
...
📊 Found 81 files to upload (excluding .duckdb_tmp)

but (base) jovyan@ae24ee2d3:~/data-store/spectralbridge$ python move_folders_from_instance_to_remote.py
...
📊 Found 95 files to upload (excluding .duckdb_tmp)

Whats the difference
```

## 2026-08-17 - NIWO_a01 vs a02 file list
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Whats the difference-
(base) jovyan@a27c5f39d find NIWO_a02 ...
(and NIWO_a01 95-file listing with checkpoint pngs)
```

## 2026-08-17 - exclude jupyter checkpoints from gocmd upload
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
yes lets exclude the checkpoints
```

## 2026-08-18 - truncated remote csv vs local 72G
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
check this- isee this file in the DE-
NEON_D13_NIWO_DP1_L018-1_20230815_directional_reflectance_merged_pixel_extraction.csv
2026-08-17 22:44:49	59.7 GiB

and on my instnace i see it as- 
-rw-r--r-- 1 jovyan jovyan  72G Aug 17 23:52 NEON_D13_NIWO_DP1_L018-1_20230815_directional_reflectance_merged_pixel_extraction.csv

There is a difference in size and when i try go command again it says file already exists. Does it actually exist? Its hard to even download that file there and check. 
```

## 2026-08-18 - replace repo gocmd with latest linux-amd64
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay cool. Notice there is a gocmd executable in the spectralbridge repo?
I need that replaced to the latest verison. And the way to download the latest version is- 
GOCMD_VER=$(curl -L -s https://raw.githubusercontent.com/cyverse/gocommands/main/VERSION.txt); \
curl -L -s https://github.com/cyverse/gocommands/releases/download/${GOCMD_VER}/gocmd-${GOCMD_VER}-linux-amd64.tar.gz | tar zxvf -
Can you delelte the old veriosn, download this new version, push just this to github
```

## 2026-08-18 - gocmd upload CLI sources dest quiet notebook
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Alright, can you update the @move_folders_from_instance_to_remote.py file to take in 2 parameters of source paths and 1 parameters of destination paths. 
We're gonna be calling the same scirpt with different source folders everytime from the notebook. Also, I dont want it to spit a lot of outputs into the notebook cell. Just what it started with and how many files are there transfer and transferring that file. I dont want the progress to get displayed in the cell and produce a lot of output. 
```

## 2026-08-18 - gocmd upload variable sources last dest
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
what if I want to transfer only 1 file? lets make it in such a way that it can even accpet 2 arguments or more than 3 arugments. Only the last one is the destination
```

## 2026-08-18 - confirm polygon extraction_mode in notebook cell
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay i think we worked enough with the move sciprt. I want to know. If we provide the polygon path to the single code cell and change extraction mode to polygon, the polygon extraction happens instead of the full right ? and the files will be created accordingly? Can you please check
```

## 2026-08-18 - terminal equivalent of run_transfer
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
whats the equivalent of running this-
from move_folders_from_instance_to_remote import run_transfer
run_transfer(
    "/home/jovyan/data-store/spectralbridge/NIWO_a01_test",
    "i:/iplant/home/shared/earthlab/macrosystems/",
)

FRom terminal.
```

## 2026-08-18 - push move script to github
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
lets psuh the changes we made to the move script to github
```

## 2026-08-18 - push move script and aop polygons geojson
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Wait i also just added a aop_polygons geojson, please commit and push that as well. 
```

## 2026-08-18 - create Flightline_Process notebook
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
OKay now, Create a Flightline_Process notebook in the repo. With the first cell as -
[NEON pipeline cell; NEON_TOKEN redacted]
The only change being it should be polygon extraction. So change extraction mode and change the polygon path to the aop polygons file we just added. It should be relative to spectral bridge.
Then the second cell should be the gocommand init scirpt-
[gocmd init]
AND then the third cell should be the transfer cell. ... destination is i:/iplant/home/shared/earthlab/macrosystems/ and the soruce is the base folder in the first cell.
THen the 4th cell should be with rm -rf command to delete the file that we just transfered using go command. Create this notebook
```

## 2026-08-18 - push Flightline_Process notebook
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
yes push it
```

## 2026-08-18 - default Flightline_Process kernel to macrosystems
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay i have one problem. The default kernel this notebook opened was Python3, but I want it to be macrosystems. is there a way we can make that happen by defualt?
```

## 2026-08-18 - polygon filtered geojson and parquet names
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
I want to know if the polygon extraction would create - NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance_filtered_polygons.geojson and then the parquets created would have _envi_polygons.parquet in them
```

## 2026-08-18 - generate assigned flightline notebooks from xlsx
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay cool. Now that you know how the notebook looks. Lets do this. 
I uploaded .xlsx called NEON_Flightlinetoprocess just now. Refer to row 70 to row 135 in that. There are 2 flightlines assinged to each notebook. In total you will have to create about 30 notebooks inside spectralbridge.  Each of them will have the 4 cells. The second cell will be the same, the third cell would be adjusted to the source of that notebook (2 flightline folders and the same destination - /iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines. The 4th cell would also want to delete the respective base source folder. 

Keep in mind the notebook needs to be macrosystems kernel. 

The first cell would need to prepoluated with the flightlines assined to the the notebook ( 2 per notebook). Also its gonna be polygon extraction. Make sure to change the FLIGHT_LINES as well as the Base_Folder. Maybe the 2 flightlines assigned to cibele-01.ipynb can we WREF_c01 and then the 2 flightlines assigned to nayani-08.ipynb can be YELL_n08. Also change the site code accorudingly (WREF or YELL etc), and the year month as well. So basically that notebook is for those 2 flightlines exclusively. 
```

## 2026-08-18 - confirm ty-16 has 3 flightlines
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Did you make sure ty-16.ipynb has 3 flightlines isntead of 2
```

## 2026-08-18 - cell 3 transfer base folder not flightlines
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
For cell 3, the soruce just needs to be the base folder in the notebook- example- YELL_c04, not the 2 flightlines inside it. 
```

## 2026-08-18 - commit 32 assigned notebooks
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Alright looks good. Lets commit the 32 notebooks
```

## 2026-08-18 - push assigned notebooks
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
lets push the notebooks 
```

## 2026-08-18 - create Matt assigned notebooks
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
We forgot Matt. I shared a new excel where rows- 55 to 70 are assingend to Matt. Create Matt's notebooks keeping in the alll the fine details of customising each notebook and commit and push them
```

## 2026-08-18 - check polygon vs NEON CRS handling
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Is the aop polygons coordinate system and neon flightline coordinate system taken into account before doing the polygon extraction, just wanted to check
```

## 2026-08-18 - switch notebooks to merged AOP polygons
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay the polygon file changed. I just uploaded it, its called @merged_all_AOP_polygon_data_2023_2024.geojson . Can you upload this file to github and also change and push all the notebooks to relfect this new polygons file. It would be cell 1 i think
```

## 2026-08-19 - fix nested qa upload folders
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Yes make sure the nested QA folders are created properly/
```

## 2026-08-19 - explicit cleanup folder in notebook cell 4
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
Lets also make the change to the 4th cell where the base folder is replaced with the explicit folder name. 
Make the change to all the notebooks and push the changes
```

## 2026-09-02 - split failed ENVI left/right and resume BRDF
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay lets keep the drone processing aside for now. I have some flightlines which didnt run. They only go til they create the directional_reflectance.hdr and img and I think they also create couple of other files but it doesnt go trhough with the brdf correction. Check the screenshot.

So i want to run it only till it creates the envi pair. And then split the envi in half. (split it into left half and right half not top and bottom, its llike the flight made only half the run). idk what we have to do with the .hdr. Run the pipeline on these 2 envis seperately. Mayne you can take in a parameter to run the pipeline this way. So all the files have to renamed appropirately. Maybe after we split it we have to create the folder structure we have and put the envis and run the pipeline on the 2 folders so that it picks up from the envis. Can we do somehting like this?
```

## 2026-09-03 - split_across_track pipeline parameter
Branch: main
AI system: Cursor Agent
Model: Not recorded

```text
okay got it. lets have the pipeline do this. Make sure the full-fightline processing is not affected at all. I want to pass a parameter which would mean I want to process this flightline by cuting it in half. I provide an output directory folder right, in that you can have 2 flightline folders one for left half and one for right half and one .h5 common to both. and then inside the files corresponding to that that half (here I want all the files htat owuld exist for a normal flghtline processing). How do you want to go about this ? I dont have the envis. Should I first run the full pipeline till it creates envis and then start splitting and created the folder strucutre that we need?
```

## 2026-09-03 - add independent bulk cross-run analysis pipeline
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
we calculate these regressions from the bulk set of data, not for one pipeline. I think we should introduce a bulk pipeline where we give it a full file tree full of processed data and the bulk pipeline calculates these from all the outputs. The way this pipline will work is that I will move a file to the home directory and give the pipeline that file path and it should search the file for all the proper data and then do some analyses based on that. I want it to merge all the merged parquets from the individual runs into a super parquet or maybe a duckdb is better? Anyway, let's make this cleanly seperatedd from the main pipeline and the drone pipeline but it's own useful pipeline with it's own documentation and such.
```

## 2026-09-03 - restore stashed bulk pipeline changes after pull
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
i hadn't pulled before we did taht and now i have some stashed changes that we need to get back into action
```

## 2026-09-03 - production bulk population-analysis architecture
Branch: main
AI system: OpenAI Codex
Model: GPT-5

````text
You are working in the current earthlab/spectralbridge repository.

Before changing anything, read the current repo carefully, especially:

* AGENTS.md
* FEATURE_REQUESTS.md
* PROMPT_LOG.md
* src/spectralbridge/pipelines/bulk.py
* src/spectralbridge/sensor_pairs.py
* tests/test_bulk_pipeline.py
* docs/vignettes/bulk-analysis.md
* the normal NEON pipeline and its output naming/path helpers
* the QA and merged-Parquet schemas
* any existing validation and manuscript-oriented analysis code

The current bulk pipeline is a good first framework, but we now need to formalize it for the real production data and begin building the scientific analysis layer.

Real input model

The real bulk input is a large staging directory produced from distributed computing.

Inside that directory are many completed SpectralBridge flightline output folders copied from different machines to a central data store.

Important constraints:

1. Each scientifically meaningful unit is ONE independently processed flightline.
2. Some machines processed two flightlines in one session, so there may be “sister” run folders from the same machine. These are still completely independent flightlines and MUST NOT be paired, averaged, grouped, or otherwise treated as one scientific unit.
3. Distributed-compute folders may have unique storage names added only to avoid overwrite collisions. Folder names therefore MUST NOT be treated as authoritative scientific identifiers.
4. Canonical flightline identity should be recovered from the actual SpectralBridge products and/or metadata inside each run.
5. A true duplicate canonical flightline ID appearing in more than one source folder should be detected and explicitly reported. Do not silently double-count it.
6. Individual completed flightline outputs may be roughly 40–80 GB.
7. The bulk analysis will run on a large VM with substantial RAM, CPU, local scratch, and disk, but the implementation must still avoid unnecessary multi-terabyte copies and avoid loading entire datasets into Python memory.
8. The input staging directory is READ ONLY. Do not modify, rename, delete, reorganize, or write into any source flightline folder.
9. All new products must go into a completely fresh bulk-output directory containing only clean deliverables.

Primary architectural goal

Refactor the bulk pipeline into a durable population-analysis layer above the existing individual-flightline pipeline.

Conceptually:

distributed completed flightline outputs
↓
source discovery and validation
↓
canonical flightline catalog
↓
DuckDB-backed virtual/queryable bulk dataset
↓
modular analyses
↓
fresh clean deliverables directory

Do NOT make the accidental distributed-compute directory structure part of the scientific model.

The scientific hierarchy should be approximately:

site
→ acquisition/date
→ flightline
→ pixel

Machine ID, distributed job ID, sister-run grouping, copy destination, etc. are computational provenance only.

Phase 1: Harden discovery and cataloging

Build or refactor discovery so that the pipeline recursively searches the supplied input directory for valid completed SpectralBridge flightline products.

For every candidate flightline, produce a canonical catalog record including as much as can be recovered reliably:

* canonical flightline ID
* NEON site
* acquisition date
* source directory
* canonical merged Parquet
* polygon merged Parquet if present
* QA products if present
* processing metadata / manifests if present
* available sensors
* processing stages represented
* row count
* file size
* schema fingerprint
* brightness coefficient/configuration state if recoverable
* BRDF/topographic configuration if recoverable
* validity/rejection status
* rejection reason
* duplicate status
* source provenance

Do not infer scientific identity from arbitrary outer folder names.

Add explicit duplicate canonical-flightline detection.

If two source directories contain the same canonical flightline ID, record them as duplicate candidates and do not silently include both in population analyses.

Preserve original source paths for provenance.

Phase 2: Avoid unnecessary physical duplication

The current bulk pipeline materializes bulk_observations.parquet.

For production-scale data this may produce unnecessary multi-terabyte duplication.

Change the architecture so that the DEFAULT analysis mode uses DuckDB to query the original accepted Parquet files virtually, using union-by-name and explicit provenance columns.

The database should expose useful views/tables such as:

* flightlines
* bulk_sources
* bulk_observations or equivalent virtual observation view
* analysis result tables

Do not duplicate the complete observation population by default.

Retain OPTIONAL materialization for cases where a portable super-Parquet is explicitly requested, e.g. with a clear option such as:

materialize_observations=True

or a CLI equivalent.

If materialization is requested, document clearly that it may require very large disk space.

Use DuckDB projection/predicate pushdown so analyses read only the columns needed.

Support:

* configurable DuckDB thread count
* configurable memory limit
* configurable local scratch/temp directory
* graceful spill-to-disk
* restart-safe operation

Phase 3: Fresh output contract

Create a clean bulk-output structure. Use the repository’s naming conventions where possible, but conceptually aim for something like:

bulk_output/
catalog/
flightlines.parquet
source_files.parquet
duplicates.parquet
rejected_sources.parquet
bulk_manifest.json

database/
    spectralbridge_bulk.duckdb
analyses/
    dataset_census/
    sensor_translation/
    correction_effects/
    site_variability/
    flightline_variability/
    qa_population/
coefficients/
    candidate_translation_coefficients.parquet
    candidate_translation_coefficients.json
tables/
figures/
reports/
logs/

You may refine this structure if the existing repository conventions suggest a better layout.

The critical requirements are:

* source data remains untouched
* all bulk outputs are isolated
* deliverables are clean and interpretable
* generated intermediate/cache products are clearly separated from publication-facing deliverables
* every result has machine-readable provenance

Phase 4: Modular analysis framework

Do not keep growing pipelines/bulk.py into one giant statistics module.

Create a modular analysis architecture.

A reasonable structure might be:

src/spectralbridge/bulk/
catalog.py
dataset.py
provenance.py
analyses/
dataset_census.py
sensor_translation.py
correction_effects.py
qa_population.py

or another clean architecture consistent with the rest of the repo.

run_bulk_pipeline() should orchestrate analyses rather than implement every calculation inline.

Each analysis module should:

* declare its required input columns/tables
* avoid reading unrelated columns
* write deterministic outputs
* record settings and provenance
* be independently restartable/reusable
* expose a Python API where useful
* be testable on tiny synthetic fixtures

Phase 5: First scientific analyses

Implement the first THREE production analysis families.

A. Dataset census / preflight

Before expensive analysis, generate a fast preflight summary based mostly on metadata/schema inspection.

Report at minimum:

* candidate source directories
* accepted canonical flightlines
* unique canonical flightlines
* duplicates
* rejected/unreadable sources
* total source size
* merged-Parquet size
* total row/pixel count where available
* sites represented
* acquisition dates/years
* sensors represented
* schemas represented
* translation-eligible flightlines
* major missing products or inconsistencies

Produce machine-readable Parquet/JSON plus a concise human-readable report.

This should run before the expensive analyses and should make it easy to sanity-check the collection.

B. Cross-sensor translation analysis

Preserve the current synthetic MicaSense↔Landsat analysis, but expand it substantially.

Important scientific boundary:

Both axes are synthetic sensor products derived from the same corrected NEON hyperspectral source.

Therefore these analyses characterize synthetic sensor translation relationships. They are NOT empirical field calibration between independently observed instruments.

Keep that evidence boundary explicit in code, metadata, docs, and outputs.

For each valid wavelength-matched sensor/band pair calculate at least:

* slope
* intercept
* correlation
* R²
* bias
* RMSE
* MAE
* value ranges
* valid row count
* contributing flightline count
* contributing site count

Calculate results at several levels:

1. pixel-pooled
2. per-flightline
3. per-site
4. flightline-balanced summary
5. site-balanced summary

Do NOT let a very large 80 GB flightline dominate every scientific conclusion simply because it contains more pixels.

The pooled-pixel statistic is useful, but it must not be the only population result.

Write separate, clearly named analysis tables.

C. Leave-one-site-out generalization framework

Build a first generalization analysis for compatible cross-sensor pairs.

For each site:

1. fit the translation relationship using all OTHER sites
2. apply it to the held-out site
3. calculate held-out:
    * RMSE
    * MAE
    * bias
    * R²/correlation where meaningful
    * slope/intercept of observed vs predicted where useful
    * sample count
    * held-out flightline count

Repeat for all eligible sites.

This is a core scientific validation because it asks whether translation relationships generalize beyond the sites used to estimate them.

Design this analysis so more sophisticated validation can be added later without rewriting the bulk framework.

Phase 6: Statistical independence

Make flightline identity explicit in all analyses.

Distributed-compute sister runs MUST NOT affect weighting, grouping, replication, or statistical structure.

Where analyses operate at pixel level, preserve flightline and site identifiers so hierarchical/balanced analyses can be calculated correctly.

Do not treat billions of pixels as billions of independent landscape replicates.

Document the distinction between:

* pixel-level observations
* flightline-level replication
* site-level replication

Phase 7: Prepare hooks for later analyses

Do NOT implement all of these now, but make the architecture ready for later modules including:

* effectiveness of topographic correction
* effectiveness of BRDF correction
* spectral-shape preservation across processing stages
* wavelength-specific correction magnitude
* per-flightline correction fingerprints
* site/flightline variability
* brightness-adjustment validation
* translation residuals across reflectance/ecological space
* linear vs nonlinear translation
* variance partitioning among pixel/flightline/site
* learning curves for number of sites/flightlines
* population-aware QA/outlier detection
* recurrent failure-mode characterization
* true duplicate-run reproducibility checks
* spectral morphospace / PCA-style population analysis
* uncertainty models for translated observations
* deterministic manuscript figures/tables

Do not build speculative complexity for these yet. Build clean interfaces that make them easy to add.

Phase 8: Testing

Add focused tests for at least:

* recursive discovery under arbitrary outer run-folder names
* canonical flightline identity extraction
* two sister runs from the same machine remaining independent
* true duplicate canonical-flightline detection
* rejected/corrupt source handling
* source directories remaining bitwise/unmodified where feasible
* virtual DuckDB union across heterogeneous schemas
* exclusion of polygon subsets by default
* optional inclusion of polygon data
* no accidental full-observation materialization by default
* optional materialization behavior
* restart/reuse behavior
* changed source invalidating the appropriate derived state
* dataset census counts
* pooled regression correctness
* per-flightline regression correctness
* per-site regression correctness
* balanced summary behavior
* leave-one-site-out correctness
* degenerate/insufficient-data handling
* source provenance retained in all relevant outputs

Use small synthetic Parquets for unit tests.

Do not require production-sized fixtures.

Phase 9: Documentation and CLI

Update the public bulk documentation and CLI.

The docs must clearly explain:

* expected real input structure
* arbitrary distributed-compute directory names
* canonical flightline identification
* sister runs vs true duplicates
* read-only source behavior
* fresh output directory
* very large source-file expectations
* virtual DuckDB default
* optional materialization
* memory/thread/scratch configuration
* scientific observational hierarchy
* pixel-pooled vs flightline/site-balanced analyses
* synthetic-regression evidence boundary
* leave-one-site-out interpretation
* restart behavior
* output directory contract

Provide a realistic CLI example for a large VM, something like:

spectralbridge-bulk /data/spectralbridge_completed_runs \ --output-dir /data/spectralbridge_bulk_analysis \ --threads <N> \ --memory-limit <XGB> \ --temp-directory /scratch/spectralbridge_bulk

Do not hard-code machine-specific values.

Phase 10: Deliverables and report back

Before completing:

* run focused bulk tests
* run the relevant broader test suite
* run Ruff if available
* run compile checks
* run documentation link/build checks
* regenerate AI transparency artifacts according to repository policy
* update FEATURE_REQUESTS.md
* update PROMPT_LOG.md
* preserve unrelated existing functionality
* do not change normal full-flightline processing behavior
* do not change drone-pipeline behavior

At the end, report:

1. files added/modified
2. final bulk architecture
3. canonical input/output contract
4. how duplicate/sister runs are handled
5. whether full observation materialization is still default or optional
6. analyses implemented
7. exact tests/checks run and results
8. known limitations
9. recommended next scientific analysis to add

Important: this is infrastructure for real, very large scientific datasets. Prefer explicit, auditable, restart-safe behavior over clever abstraction. Do not silently guess when identity, provenance, or statistical grouping is ambiguous.
````

## 2026-09-03 - preserve main and drone pipelines
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
don't change the main pipeline or the drone pipeline,
```

## 2026-09-03 - continue production bulk implementation
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
continue
```

## 2026-09-03 - fix Python 3.10 Ruff syntax failures
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
Run ruff check src tests scripts/generate\_ai\_transparency.py \&#x20;
invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.10 (syntax was added in Python 3.12)\&#x20;
\&#x20;  \--> src/spectralbridge/bulk/analyses/dataset\_census.py:99:76\&#x20;
\&#x20;   \|\&#x20;
\&#x20;97 |                 con.execute(\&#x20;
\&#x20;98 |                     f"CREATE OR REPLACE TABLE {table} AS "\&#x20;
\&#x20;99 |                     f"SELECT \* FROM read\_parquet('{path.as\_posix().replace("'", "''")}')"\&#x20;
\&#x20;   \|                                                                            ^\&#x20;
100 |                 )\&#x20;
101 |             summary = {\&#x20;
\&#x20;   \|\&#x20;
invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.10 (syntax was added in Python 3.12)\&#x20;
\&#x20;  \--> src/spectralbridge/bulk/analyses/leave\_one\_site\_out.py:207:82\&#x20;
\&#x20;   \|\&#x20;
205 |             con.execute(\&#x20;
206 |                 "CREATE OR REPLACE TABLE translation\_leave\_one\_site\_out AS "\&#x20;
207 |                 f"SELECT \* FROM read\_parquet('{output.results.as\_posix().replace("'", "''")}')"\&#x20;
\&#x20;   \|                                                                                  ^\&#x20;
208 |             )\&#x20;
209 |             return {\&#x20;
\&#x20;   \|\&#x20;
invalid-syntax: Cannot reuse outer quote character in f-strings on Python 3.10 (syntax was added in Python 3.12)\&#x20;
\&#x20;  \--> src/spectralbridge/bulk/analyses/sensor\_translation.py:321:76\&#x20;
\&#x20;   \|\&#x20;
319 |                 con.execute(\&#x20;
320 |                     f"CREATE OR REPLACE TABLE {table\_name} AS "\&#x20;
321 |                     f"SELECT \* FROM read\_parquet('{path.as\_posix().replace("'", "''")}')"\&#x20;
\&#x20;   \|                                                                            ^\&#x20;
322 |                 )\&#x20;
323 |             return {\&#x20;
\&#x20;   \|\&#x20;
Found 3 errors.\&#x20;
Error: Process completed with exit code 1.
```

## 2026-09-04 - continue stage-complete validation
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
you can continue
```

## 2026-09-04 - consume completed flightline archives directly
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
You are working in the current earthlab/spectralbridge repository.

The current bulk pipeline input contract is wrong for the real production archive.

We now have the actual large-VM production directory structure and need to fix the bulk pipeline so it can consume the completed output of the normal SpectralBridge pipeline directly.

Do not work around this in notebooks.

Fix the package architecture.

Real production input structure

The real bulk input root looks like this conceptually:

Aug_2026_Processed_Flightlines/
├── NIWO_a01/
│   ├── NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance/
│   │   ├── qa/
│   │   ├── metadata / JSON sidecars
│   │   ├── ENVI headers
│   │   ├── raw/corrected/target products
│   │   └── NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance_brdfandtopo_corrected_envi.img
│   └── possibly other files/products
├── NIWO_a02/
├── NIWO_a03/
├── ...

Important facts:

* outer folders like NIWO_a01, NIWO_a02, etc. are compute/batch/storage folders only
* they are NOT scientific flightline identifiers
* the actual flightline identity is encoded in the inner canonical NEON product directory/file names
* each inner canonical flightline folder represents an independently processed flightline
* some compute jobs may have produced sister runs, but those remain independent flightlines
* a typical corrected ENVI image can be ~20–30 GB or larger
* the complete per-flightline folder may be ~40–80 GB
* the archive may eventually contain ~100 independently processed flightlines
* this will run on a large VM
* source data must be treated as read-only
* all new bulk deliverables must go into a fresh output directory

The current bulk pipeline instead looks for:

*_merged_pixel_extraction.parquet

as its primary input and therefore rejects the real archive.

That is the problem to fix.

Primary architectural requirement

The output of the normal SpectralBridge pipeline must be directly consumable by the bulk pipeline.

A user should be able to run conceptually:

from spectralbridge import run_bulk_pipeline
run_bulk_pipeline(
    "/path/to/Aug_2026_Processed_Flightlines",
    "/path/to/Aug_2026_Bulk_Analysis",
)

without first manufacturing or manually reorganizing intermediate merged-Parquet products.

This should become a publication-level contract.

Phase 1: Audit the current normal-pipeline output contract

Before changing anything, read carefully:

* AGENTS.md
* FEATURE_REQUESTS.md
* PROMPT_LOG.md
* normal pipeline orchestration
* paths.py
* file_types.py
* ENVI output naming
* target sensor output naming
* QA output structure
* current bulk pipeline
* current bulk catalog/discovery code
* current extraction/Parquet code
* current sensor translation code
* current tests
* current docs

Determine exactly which per-flightline products are reliably persisted by the normal pipeline.

Do not guess.

Identify at minimum:

* canonical flightline directory
* raw ENVI
* corrected ENVI
* target-sensor ENVI products
* QA products
* model/config sidecars
* any existing Parquet tables if present
* whether full-pixel Parquet extraction is always, sometimes, or rarely generated

Document the real current output contract in FEATURE_REQUESTS.md.

Phase 2: Redesign bulk discovery around canonical flightline folders

Bulk discovery should recursively traverse arbitrary outer batch/storage directories.

It must identify canonical completed flightline folders from their actual contents and/or canonical NEON naming.

For example:

NIWO_a01/
  NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance/

should resolve scientifically to something like:

* site: NIWO
* date: 2023-08-15
* flightline: L012-1
* canonical flightline ID: derived from the NEON naming parser

Do NOT use NIWO_a01 as the flightline ID.

Do NOT use arbitrary outer folder names as scientific identity.

If two different outer directories contain the same canonical flightline ID, treat them as true duplicate candidates and exclude them from scientific analysis unless an explicit duplicate-resolution policy is later added.

Phase 3: Support two valid bulk input modes

Retain compatibility with existing prebuilt merged-Parquet input if useful, but make completed flightline folders the primary production input.

Support conceptually:

Mode A: completed-flightline folders

Preferred/default production mode.

Bulk discovers per-flightline pipeline outputs and builds the analytical dataset from those products.

Mode B: prebuilt merged-Parquet products

Compatibility/advanced mode.

If a user already has the canonical merged Parquets, the current fast virtual-DuckDB path may still be useful.

Do not force users to create Parquets before bulk analysis.

If input mode can be auto-detected safely, implement that.

Otherwise expose a simple explicit option such as:

input_mode="auto" | "flightline_outputs" | "merged_parquet"

Do not create a confusing proliferation of modes.

Phase 4: Build a scalable flightline-to-analysis extraction layer

The bulk pipeline needs a scalable way to derive compact analytical observations from each completed flightline folder.

Do NOT blindly materialize every pixel from every 20–30 GB ENVI image into another equally huge Parquet unless scientifically necessary.

The bulk analyses need a compact analytical representation.

Determine what columns are actually required by the current analyses:

* flightline ID
* site
* acquisition date
* relevant MicaSense synthetic bands
* relevant Landsat synthetic bands
* validity/error flags
* QA state
* possibly correction metadata
* possibly selected raw/corrected summaries for later correction-effectiveness work

Use only the persisted target-sensor products needed for the current analysis where possible.

Avoid rereading hundreds of hyperspectral bands if the normal pipeline has already produced target-sensor rasters.

Prefer:

corrected target-sensor ENVI products
→ chunked extraction
→ compact Parquet

over:

corrected hyperspectral ENVI
→ reread all hyperspectral bands
→ recompute sensor convolution unnecessarily

unless the current output contract makes the latter unavoidable.

Phase 5: Per-flightline derived analytical cache

For each accepted canonical flightline, create a compact derived analysis cache inside the NEW bulk output directory, not the source directory.

Conceptually:

bulk_output/
├── cache/
│   ├── <flightline_id>/
│   │   ├── observations.parquet
│   │   ├── extraction_metadata.json
│   │   └── status.json

or another clean structure.

This cache should:

* be derived read-only from source products
* be restartable
* preserve canonical identity
* record source files and hashes/size/mtime/schema
* record which target sensor products were used
* record extraction code/version
* support independent rerun per flightline
* avoid rereading successful flightlines unnecessarily

The cache should be compact relative to the full raster products.

Phase 6: Chunked/streaming extraction

Each flightline may contain tens of GB of raster data.

Extraction must be chunked.

Requirements:

* do not load full ENVI rasters into RAM
* process bounded chunks/windows
* read only required bands/products
* configurable chunk size
* deterministic output
* bounded memory
* one flightline can fail without destroying the whole bulk run
* progress logging at flightline and chunk level

Use existing SpectralBridge ENVI readers/helpers where possible.

Do not introduce a second independent raster parser unnecessarily.

Phase 7: Preserve scientific independence

The scientific hierarchy remains:

site
→ acquisition
→ flightline
→ pixel

Outer batch folders are computational provenance only.

Sister runs from the same VM remain independent flightlines.

Do not introduce any weighting/grouping based on:

* batch folder
* machine
* worker
* copy destination

Only canonical site/date/flightline identity should drive scientific grouping.

Phase 8: QA-aware extraction

Use the per-flightline QA information where available.

The extraction/catalog should record:

* overall QA status
* relevant stage QA status
* known missing products
* known warning/failure state
* relevant no-data/invalid fractions where available

Do not automatically discard WARN flightlines unless a specific analysis requires that.

Preserve QA state so downstream analyses can stratify/filter explicitly.

FAIL or structurally incomplete flightlines may be rejected with a clear reason.

Phase 9: Preflight must work on the real archive

The cheap preflight should now inspect the real directory structure and report:

* candidate outer batch folders
* canonical flightline folders discovered
* accepted unique flightlines
* duplicate canonical flightlines
* rejected/incomplete flightlines
* sites
* dates
* raw/corrected/target products found
* QA availability
* approximate total source bytes
* estimated analysis-cache size if possible
* flightlines eligible for current translation analysis
* missing required target-sensor products
* reasons for rejection

Preflight should NOT scan full raster pixel populations.

It may inspect:

* filenames
* headers
* JSON metadata
* file sizes
* QA metadata
* ENVI metadata
* Parquet footers where available

This should be fast enough to review before launching extraction.

Phase 10: Current translation analysis path

The existing downstream analytical framework should remain conceptually intact:

per-flightline compact observations
→ DuckDB virtual federation
→ dataset census
→ pixel pooled translation
→ per-flightline translation
→ per-site translation
→ flightline-balanced translation
→ site-balanced translation
→ leave-one-site-out

Do not rewrite these analyses unless required by the new source schema.

Adapt the input layer to feed them correctly.

Phase 11: Avoid unnecessary recomputation

If the normal pipeline already persisted target sensor products such as:

* Landsat-like ENVI products
* MicaSense-like ENVI products

use those directly.

Do not recompute spectral convolution from the hyperspectral cube just because bulk can.

The normal pipeline output should be considered authoritative for the bulk run.

Only compute missing target products if there is an explicit opt-in recovery mode.

Default behavior should be:

missing required product
→ reject/flag in preflight

not

missing product
→ silently rerun the normal pipeline.

Bulk must remain downstream and read-only.

Phase 12: New output contract

Refine the output structure conceptually to something like:

bulk_output/
├── catalog/
│   ├── flightlines.parquet
│   ├── source_products.parquet
│   ├── duplicates.parquet
│   ├── rejected_sources.parquet
│   └── bulk_manifest.json
│
├── cache/
│   └── per-flightline compact analytical Parquets
│
├── database/
│   └── spectralbridge_bulk.duckdb
│
├── analyses/
│   ├── dataset_census/
│   ├── sensor_translation/
│   ├── leave_one_site_out/
│   └── future correction/QA analyses
│
├── coefficients/
├── figures/
├── tables/
├── reports/
└── logs/

Do not place derived bulk files inside the source flightline folders.

Phase 13: Robust source detection

Add tests for input structures resembling the real archive.

Synthetic fixture example:

bulk_input/
├── NIWO_a01/
│   └── NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance/
│       ├── raw/corrected ENVI
│       ├── target-sensor ENVI
│       ├── QA
│       └── metadata
├── NIWO_a02/
│   └── NEON_D13_NIWO_DP1_L013-1_20230815_directional_reflectance/
├── worker_73/
│   └── NEON_D13_YELL_DP1_L099-1_20230715_directional_reflectance/

Verify:

* all three become independent flightlines
* outer folder names are ignored scientifically
* site/date/flightline identity is recovered correctly

Phase 14: Duplicate tests

Add a fixture where:

batch_A/...L012-1...
batch_B/...L012-1...

contain the same canonical flightline.

Verify they are marked as duplicates and not both included.

Phase 15: Incomplete-flightline tests

Create fixtures missing:

* corrected product
* target Landsat product
* target MicaSense product
* QA
* ENVI header
* corrupted header

Define clearly which are:

* fatal/rejected
* analyzable with warning
* analyzable for only a subset of analyses

Do not use one global validity flag if analysis-specific eligibility is more accurate.

Phase 16: Tiny raster integration tests

Use tiny ENVI fixtures to test actual chunked extraction.

The tests should verify:

* correct pixel/band values
* no full-array loading
* chunk boundaries
* no-data handling
* source provenance
* canonical flightline metadata
* derived Parquet schema
* restart behavior

Do not require large fixtures.

Phase 17: Backward compatibility

The existing run_bulk_pipeline public API should remain usable where reasonable.

If signatures must change, preserve compatibility aliases/defaults or document a clean migration.

The production happy path should become simple.

Desired example:

from spectralbridge import run_bulk_pipeline
result = run_bulk_pipeline(
    "/home/jovyan/data-store/Aug_2026_Processed_Flightlines",
    "/home/jovyan/data-store/Aug_2026_Bulk_Analysis",
    input_mode="auto",
    threads=16,
    memory_limit="175GB",
    temp_directory="/home/jovyan/work/spectralbridge_bulk_scratch",
)

The user should not need to understand internal Parquet naming to use the bulk pipeline.

Phase 18: Jupyter/documentation update

Update the bulk vignette to describe the real production structure.

Explicitly show:

batch/storage folder
→ canonical flightline folder
→ completed normal-pipeline products

Explain that:

* outer names are ignored
* canonical inner flightline identity is authoritative
* bulk derives compact analysis observations
* source is read-only
* target sensor outputs are reused rather than recomputed
* large raw/corrected rasters remain in place
* compact bulk caches are written separately

Also update the example Jupyter workflow.

Do not require users to manually search for *_merged_pixel_extraction.parquet.

Phase 19: Preflight-only workflow

Preserve a clean two-stage user experience:

run_bulk_pipeline(..., preflight_only=True)

then inspect census/rejections.

Then:

run_bulk_pipeline(..., preflight_only=False)

for actual extraction + analysis.

Preflight should not create expensive per-pixel cache files.

Phase 20: Performance considerations

The VM currently has roughly:

* 40 CPUs
* 251 GB RAM

But do not hard-code those.

Use resource parameters already in the API.

For extraction, consider safe per-flightline concurrency carefully.

Because source rasters may each be tens of GB and storage may be network-backed, uncontrolled parallel reads could make performance worse.

Prefer configurable conservative concurrency.

If practical, separate:

* DuckDB threads
* number of concurrently extracted flightlines
* chunk size

Document defaults.

Do not use all CPUs automatically if doing so would saturate I/O.

Phase 21: Failure isolation

One bad flightline should not abort the entire collection.

Per-flightline extraction should record:

* success
* warning
* failure
* failure reason
* traceback/log reference
* source products

Bulk should continue with other valid flightlines unless configured otherwise.

Phase 22: Provenance

For every compact derived observation file, record:

* canonical flightline ID
* site
* date
* source directory
* exact source product paths
* source sizes/mtime
* SpectralBridge version
* git commit if available
* extraction schema version
* selected target sensors/bands
* validity filters
* chunk settings
* analysis run ID

This will be publication evidence.

Phase 23: Do not alter scientific algorithms

Do NOT change:

* BRDF correction
* topographic correction
* sensor-response definitions
* brightness coefficients
* QA thresholds
* normal-pipeline scientific defaults

This task is about connecting pipeline 1 outputs to pipeline 3 inputs correctly.

Phase 24: Verification

Run:

* new discovery tests
* tiny ENVI extraction tests
* duplicate tests
* incomplete-flightline tests
* current bulk tests
* normal pipeline tests relevant to output naming
* full pytest if practical
* Ruff
* compile checks
* strict docs build
* AI transparency check
* git diff –check

Also create one realistic synthetic directory tree matching:

Aug_2026_Processed_Flightlines/
  NIWO_a01/
    NEON_D13_NIWO_DP1_L012-1_20230815_directional_reflectance/

and demonstrate preflight + full tiny bulk analysis end-to-end.

Final report

Report:

1. what was wrong with the previous bulk input assumption
2. the new canonical bulk input contract
3. how arbitrary outer batch folders are handled
4. how canonical flightline identity is recovered
5. what normal-pipeline products are required
6. what products are optional
7. how per-flightline compact observations are created
8. whether target-sensor products are reused directly
9. chunking/memory strategy
10. failure isolation behavior
11. output/cache structure
12. backward compatibility with merged-Parquet mode
13. exact tests/checks run
14. remaining limitations
15. updated user invocation for the real Aug 2026 archive

Update FEATURE_REQUESTS.md and PROMPT_LOG.md according to repository policy.

The core publication requirement is:

SpectralBridge’s bulk pipeline must directly consume the completed outputs of SpectralBridge’s normal pipeline without requiring users to manually manufacture a separate intermediate dataset.
```

## 2026-09-04 - generalize bulk scientific units and analysis profiles
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
finish what you were working on before we were interupted and then move on to this next prompt

You are working in the SpectralBridge repository:

https://github.com/earthlab/spectralbridge

Before editing:
- inspect current main
- read AGENTS.md
- inspect recent git history
- read the existing standard, flightline, and bulk pipeline implementations
- inspect package metadata, tests, docs, and public API
- preserve the package’s role as a GENERIC tool for hyperspectral processing and sensor translation

IMPORTANT PRODUCT PRINCIPLE

SpectralBridge is not a package for the NIWO/WREF/YELL dataset.

Those flightlines are being used as a large real-world validation corpus.

The package must remain generic and easy to use for any user who wants to:

1. process one hyperspectral flightline
2. process multiple flightlines
3. generate translated/convolved sensor products
4. analyze populations of completed flightlines
5. compare source and target sensors
6. build reproducible cross-sensor datasets

Do not encode:
- NIWO
- WREF
- YELL
- the Aug 2026 archive
- our CyVerse hierarchy
- our batch-folder naming convention
- fixed assumptions about 123 flightlines
- fixed assumptions about a specific manuscript
- hardcoded MicaSense/Landsat-only population logic

Those belong in tests/examples/validation documentation, not package architecture.

Our production archive has exposed general problems in the bulk pipeline. Fix the GENERAL problems.

==================================================
1. DEFINE GENERIC SCIENTIFIC UNITS
==================================================

A flightline should be the atomic scientific processing unit.

A bulk input root may contain arbitrary organizational nesting around flightlines:

input_root/
    arbitrary_folder/
        canonical_flightline_A/
    some_other_folder/
        canonical_flightline_B/
        canonical_flightline_C/

The package should:

- discover scientifically identifiable flightlines recursively
- treat each independently
- not infer scientific identity from surrounding storage folders
- support multiple independent flightlines under one parent directory
- preserve source-path provenance
- explicitly report duplicate scientific identities

Do not assume a particular batch naming convention.

If current identity parsing is specifically NEON-oriented, preserve NEON support while structuring the code so identity parsing is modular and extensible rather than hardwired throughout the bulk system.

==================================================
2. SEPARATE PROCESSING COMPLETENESS FROM ANALYSIS ELIGIBILITY
==================================================

A completed full processing run and an analysis-ready flightline are not the same concept.

Introduce a clean, generic distinction between:

- processing completeness
- product availability
- analysis eligibility

For example, an analysis may only require already-generated target sensor products and should not require the original hyperspectral cube.

Design this using a generic abstraction such as:

analysis_profile
required_product_set
product_requirements
eligibility_profile

or another maintainable design consistent with the repo.

A profile should define:

- required product roles
- optional product roles
- allowed sensor families
- pairing requirements
- file integrity requirements
- whether QA metadata is required
- whether the original/corrected hyperspectral source is required

Do not make “translation” mean specifically Landsat/MicaSense.

The package should be capable of representing translation between arbitrary supported sensors.

==================================================
3. GENERIC PRODUCT REGISTRY / SENSOR PRODUCT MODEL
==================================================

Review how sensor products are currently identified.

Refactor where necessary so target products are represented generically.

A product record should be able to express concepts such as:

- sensor name
- product role
- wavelength family / matching group
- source flightline
- source processing stage
- data path
- header path
- band count
- wavelengths
- dimensions
- dtype
- nodata
- validity status

Avoid spreading filename substring checks across the codebase.

Where possible, centralize product recognition in a registry, parser, or product descriptor layer.

Current supported Landsat and MicaSense products should be entries in that system, not the architecture itself.

==================================================
4. GENERIC TRANSLATION PAIRS
==================================================

The current real-world tests use wavelength-matched MicaSense and Landsat products.

That is one instance of a general concept:

two sensor products are scientifically comparable when they share a defined translation/matching relationship.

Represent this generically.

A translation pair/group should encode:

- source sensor/product
- target sensor/product
- matched band/wavelength relationship
- expected number of bands
- compatibility rules
- analysis eligibility

The bulk translation analysis should operate over discovered valid translation relationships rather than hardcoded six-family assumptions.

The package may ship built-in definitions for existing supported sensors.

==================================================
5. ATOMIC FLIGHTLINE VALIDATION
==================================================

Validation should happen per flightline and per requested analysis profile.

For every required product validate generically:

- expected product exists
- expected header/sidecar exists when required
- file is nonzero
- metadata can be read
- dimensions are valid
- band metadata are valid
- data/header relationship is coherent
- duplicates are handled explicitly
- required sensor pairing is complete

If one flightline is invalid:

- exclude that flightline from that analysis
- do not crash the entire bulk population
- record the reason
- continue with valid flightlines

This behavior was exposed by a real zero-byte target raster in our validation archive.

That exact filename/dataset should only appear in a regression test fixture or validation note.

==================================================
6. MACHINE-READABLE EXCLUSION / QA MODEL
==================================================

Make exclusions a formal package concept.

Prefer structured reason codes such as:

missing_required_product
missing_sidecar
zero_byte_file
duplicate_product
unreadable_metadata
invalid_dimensions
incompatible_band_schema
incomplete_translation_pair
duplicate_scientific_identity
extraction_failure

Each exclusion record should include as applicable:

- flightline ID
- source path
- site/date metadata if known
- requested analysis profile
- product role
- sensor
- offending file(s)
- reason code
- human-readable detail
- processing stage where exclusion occurred

Bulk output should expose deterministic:
- Parquet
- CSV and/or JSON

exclusion tables.

==================================================
7. BULK PROCESSING SHOULD BE POPULATION-SAFE
==================================================

The bulk pipeline is an analysis across many independent scientific units.

Implement fault containment.

One bad flightline must not invalidate the population unless the user explicitly requests fail-fast behavior.

Consider an option such as:

on_invalid="exclude"   # sensible bulk default
on_invalid="error"

Similarly extraction failures should be associated with their flightline and surfaced in QA/provenance.

Do not silently swallow failures.

==================================================
8. MINIMAL ANALYSIS INPUTS
==================================================

Support bulk analysis from a minimal local archive containing only the products required for the requested analysis.

For example, a user who already generated translated target products should not need to keep or transfer:

- original HDF5
- raw hyperspectral image
- corrected hyperspectral image
- plots
- HTML reports
- unrelated sensor products

unless the selected analysis actually requires them.

This should be generic and profile-driven.

Do not create a special “Aug 2026 minimal mode.”

==================================================
9. SOURCE DATA AND DERIVED DATA MUST BE DISTINCT
==================================================

Clarify package contracts around:

- source products
- temporary extraction products
- bulk cache
- database
- reports
- final deliverables

Source trees should be treated as read-only by bulk analysis wherever possible.

Derived data should go to a separate output root.

Cache behavior should be:
- restart-safe
- deterministic
- attributable to source flightline and package version
- reusable when valid
- invalidated when relevant source inputs/configuration change

==================================================
10. GENERIC PREFLIGHT
==================================================

Preflight should answer:

“What will this analysis operate on, and is it safe to run?”

Without scanning the full pixel population, report:

- discovered flightlines
- valid flightlines
- excluded flightlines
- available sensors/products
- available translation pairs
- selected analysis profile
- required products
- selected source files
- selected source bytes
- estimated cache/output size if possible
- exclusion counts by reason
- duplicate identity count
- source/output paths
- package version/configuration

Return this as a structured Python object/dict and expose it through CLI.

Preflight must not assume a particular number of sensors or flightlines.

==================================================
11. USER-FACING API SHOULD BE SIMPLE
==================================================

A normal user should be able to do something conceptually like:

from spectralbridge import run_bulk_pipeline

result = run_bulk_pipeline(
    input_root,
    output_root,
    analysis="translation",
    preflight_only=True,
)

and then:

result = run_bulk_pipeline(
    input_root,
    output_root,
    analysis="translation",
)

If the existing API has better naming, preserve consistency.

Users should not need:
- monkey patches
- sys.path injection
- knowledge of internal modules
- manual Parquet merging
- package-source checkout

The installed package should expose the workflow.

==================================================
12. SENSOR SELECTION SHOULD BE CONFIGURABLE
==================================================

Do not require every supported sensor product to exist for every analysis.

A user may want to compare only:

- sensor A vs sensor B
- one target family
- several targets
- every available compatible translation

Support explicit selection where appropriate, for example:

sensors=[...]
translation_pairs=[...]
include_available=True

or a cleaner existing pattern.

The correct validation requirements should derive from the requested analysis, not from every sensor SpectralBridge happens to support.

==================================================
13. TEST USING SMALL GENERIC FIXTURES
==================================================

Do not put real production-scale data in tests.

Create tiny generic ENVI fixtures representing:

A. one valid flightline
B. two independent flightlines under one storage folder
C. several flightlines under nested arbitrary folders
D. valid target-only analysis input
E. missing source hyperspectral cube but valid target products
F. missing required target
G. missing header
H. zero-byte raster
I. malformed header
J. duplicate target
K. duplicate scientific identity
L. valid + invalid flightlines in same bulk root
M. optional QA absent
N. optional QA present
O. transient filesystem file disappears during discovery
P. one translation pair requested while unrelated supported sensors are absent

Tests should prove the architecture is generic.

Use neutral fixture names rather than NIWO/WREF/YELL except for an optional regression test explicitly documenting the production bug that motivated the behavior.

==================================================
14. ADD REAL-WORLD REGRESSION TESTS WITHOUT DATASET COUPLING
==================================================

The production validation archive exposed these general edge cases:

- arbitrary outer compute/storage folders
- two scientific flightlines under one outer folder
- hundreds of large output files
- target-only staging
- zero-byte distributed-compute output
- incomplete flightline should be excluded rather than crash population
- transient transfer artifacts
- huge source products not needed for downstream translation analysis

Encode each of these as small synthetic regression tests.

Mention the production test campaign in changelog/developer docs if useful, but do not make the package depend on it.

==================================================
15. DEPENDENCY / IMPORT HARDENING
==================================================

We discovered that bulk imports require pyarrow but environments can lack it.

Review packaging.

Ensure that:
- required runtime dependencies are correctly declared
- optional bulk dependencies have a coherent extra if truly optional
- ordinary package import does not unnecessarily import heavy bulk modules
- installed CLI entry points work
- PyPI install exposes standard, flightline, and bulk workflows

Test from a clean built wheel/sdist environment where feasible.

==================================================
16. DOCUMENT THE GENERIC USER JOURNEY
==================================================

Docs should make the package easy to understand for someone who has never seen our project data.

Document three workflows clearly:

A. SINGLE FLIGHTLINE
raw hyperspectral input
→ correction/processing
→ translated sensor products

B. MULTIPLE FLIGHTLINES
collection of raw or processed flightlines
→ independent processing
→ standardized outputs

C. BULK ANALYSIS
collection of completed or minimally staged flightline products
→ discovery
→ preflight
→ validation
→ exclusions
→ compact analytical cache
→ population-level translation/comparison

Show realistic but generic directory examples.

Explain:
- what is required
- what is optional
- what gets excluded
- where outputs go
- how to restart
- how to select sensors
- how to interpret preflight

==================================================
17. KEEP SCIENCE CONFIGURABLE
==================================================

Do not hardcode our current manuscript analysis as “the bulk pipeline.”

Separate:

1. generic bulk dataset construction
2. generic translation/comparison primitives
3. particular analysis modules

Where current analysis modules include:
- census
- sensor translation
- leave-one-site-out

keep those callable independently and allow future analyses to be added without rewriting discovery or extraction.

==================================================
18. PUBLICATION-QUALITY PROVENANCE
==================================================

Every bulk run should produce enough provenance to reproduce it:

- SpectralBridge version
- git commit when available
- analysis profile
- configuration
- source root
- output root
- accepted flightlines
- excluded flightlines
- sensor/product inventory
- source file hashes or lightweight fingerprints where practical
- extraction/cache schema version
- analysis parameters
- timestamps

Do this generically.

==================================================
19. BACKWARD COMPATIBILITY
==================================================

Preserve existing working APIs unless there is a strong reason to change them.

If introducing new concepts such as analysis profiles or product registries:
- provide sensible defaults
- document migration
- avoid breaking existing standard/flightline users

==================================================
20. ACCEPTANCE CRITERIA
==================================================

Before completing the work, automated tests should demonstrate:

1. arbitrary outer directory names do not affect scientific identity

2. multiple flightlines under one parent remain independent

3. a valid minimal target-only flightline can be analyzed without the original/corrected hyperspectral source when that source is not required by the requested analysis

4. requirements are derived from the selected analysis/sensor pair, not every supported sensor

5. a zero-byte required product excludes only the affected flightline

6. another valid flightline in the same bulk root proceeds

7. duplicate products and duplicate scientific identities are explicit

8. optional metadata absence does not invalidate analyses that do not require it

9. preflight reports selected source bytes without reading the full raster population

10. exclusions are deterministic and machine-readable

11. installed Python API works from a built package

12. installed CLI works

13. dependencies are correctly declared

14. standard pipeline tests still pass

15. flightline pipeline tests still pass

16. bulk tests pass using small fixtures

17. package build succeeds

18. docs build succeeds if currently part of CI

==================================================
21. DELIVERABLES
==================================================

Implement the changes rather than only describing them.

At the end provide:

- architectural summary
- public API changes
- changed files
- new tests
- documentation changes
- dependency changes
- backward compatibility notes
- exact commands/tests run
- results
- anything intentionally deferred
- PR-ready summary

Keep the design general, small, and maintainable.

Most importantly:

USE THE REAL PRODUCTION ARCHIVE AS A VALIDATION CASE,
NOT AS THE PACKAGE DATA MODEL.
```

## 2026-09-05 - continue generic bulk implementation
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
continue
```

## 2026-09-06 - fix default matched MicaSense discovery
Branch: main
AI system: OpenAI Codex
Model: GPT-5

```text
We have now tested the current SpectralBridge main branch natively against
the real staged Aug 2026 bulk dataset.

Current tested state:

- SpectralBridge 2.2.0
- commit: 72af47c4f3fb97f984612920a43a04a2f31126c6
- clean main branch
- staging dataset:
  /home/jovyan/data-store/Aug\_2026\_Bulk\_Minimal

Independent filesystem verification:

- 122 canonical flightlines
- 122 complete
- 0 incomplete
- each flightline has the six required target product families:
  landsat\_tm
  landsat\_etm
  landsat\_oli
  landsat\_oli2
  micasense\_tm\_etm
  micasense\_oli
- both .img and .hdr are present for each family

Native SpectralBridge discovery now finds all 122 flightline records, which
is progress, but rejects all 122:

Flightline records: 122
Source records: 732
Status: {'rejected': 122}
Translation eligible: {False: 122}

Every rejection has essentially this form:

"no requested compatible translation pair is complete; available sensors:
Landsat\_5\_TM, Landsat\_7\_ETM+, Landsat\_8\_OLI, Landsat\_9\_OLI-2"

This isolates the remaining bug.

The four Landsat target products are being recognized as sensors, but the
two MicaSense matched products are not appearing in available sensors:

MicaSense\_to-match\_TM\_and\_ETM+
MicaSense\_to-match\_OLI\_and\_OLI-2

Those files DO exist in every staged flightline.

The current ProductRegistry already contains descriptors for:

micasense\_matched\_oli
filename:
\*\_micasense\_to\_match\_oli\_oli2\_envi.img
sensor\_name:
MicaSense\_to-match\_OLI\_and\_OLI-2

micasense\_matched\_tm\_etm
filename:
\*\_micasense\_to\_match\_tm\_etm+\_envi.img
sensor\_name:
MicaSense\_to-match\_TM\_and\_ETM+

The configured translation pairs also correctly reference those sensor names.

Please diagnose why discover\_completed\_flightlines() / source-file
classification recognizes the four Landsat products but not the two
MicaSense matched products.

Important:
DO NOT add another notebook monkey patch.
DO NOT special-case Aug\_2026\_Bulk\_Minimal.
DO NOT weaken translation-pair validation.
DO NOT require corrected hyperspectral products for analysis="translation".
DO NOT change the scientific translation definitions merely to make the test pass.

Fix the generic package implementation.

Please specifically inspect:

1. ProductRegistry filename matching for the MicaSense products.
2. SourceFileRecord construction and whether MicaSense products receive their
   ProductDescriptor sensor\_name.
3. Header pairing logic for the MicaSense .img/.hdr products.
4. Any normalization or regex issue involving:
   micasense\_to\_match\_tm\_etm+
   micasense\_to\_match\_oli\_oli2
   especially the literal "+" in etm+.
5. The logic that builds `available sensors` for a canonical flightline.
6. Translation-pair completeness evaluation.

Add regression tests representing a target-only canonical flightline containing
exactly these six product families and their headers.

The regression test should prove:

- discovery recognizes all six sensors/products;
- the MicaSense matched products are represented by the correct sensor names;
- all four default translation pairs are complete:
  MicaSense TM/ETM+ -> Landsat 5 TM
  MicaSense TM/ETM+ -> Landsat 7 ETM+
  MicaSense OLI/OLI-2 -> Landsat 8 OLI
  MicaSense OLI/OLI-2 -> Landsat 9 OLI-2
- translation\_eligible is True;
- status is accepted;
- corrected/raw hyperspectral absence does not reject the flightline when
  analysis="translation";
- the full translation pipeline can proceed beyond the eligibility gate.

Also add a focused filename-classification test using realistic filenames from
the staged dataset, particularly the MicaSense names.

Run the relevant unit tests and the full test suite.

Then commit and push the fix to main.

In your final response report:

- root cause;
- files changed;
- tests added;
- test results;
- new commit SHA;
- whether the real 122-flightline dataset should now discover as 122 accepted,
  translation-eligible flightlines.

Do not modify or delete anything in:
/home/jovyan/data-store/Aug\_2026\_Bulk\_Minimal
```
