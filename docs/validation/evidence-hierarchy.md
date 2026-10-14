# What does a successful result establish?

Keep four questions separate when evaluating a SpectralBridge run.

| Evidence level | What to inspect | What it establishes | What it does not establish |
| --- | --- | --- | --- |
| Execution | Process status, exceptions and logs | The requested code ran or stopped | Required products exist |
| Artifact completion | Resolved configuration, required readable files and provenance | The requested output contract was fulfilled | Numerical or scientific quality |
| Internal QA | Recorded checks, warnings, thresholds, spectra and maps | Evaluated properties met or failed the recorded rules | Agreement with independent observations |
| Independent scientific comparison | Suitable external observations, alignment/aggregation, uncertainty and study design | Agreement for the stated comparison and support | Universal sensor equivalence or transferability |

Passing a level does not establish the next. A `warn` can require interpretation
without being a crash; a missing report is not a pass. High R² among products
constructed from the same source spectrum does not independently validate a
sensor calibration. Configured thresholds are review aids, not universal
scientific approval criteria.

Software correctness is a separate prerequisite: unit/integration tests and CI
exercise numerical contracts, deterministic outputs and restart behavior against
their test inputs. See [tests and contribution](../dev/contributing.md) and the
[release gates](../dev/releasing.md). A passing test suite is not independent
scientific validation. Workflow evidence comes from readable real-run products,
provenance and internal QA; scientific agreement requires a suitable independent
comparison with stated spatial support, acquisition alignment and uncertainty.

Start with [stage QA](stage-qa-guide.md) and the [R10C real-run
walkthrough](real-data-example.md). The [evidence index](index.md) records the
actual campaigns and their source revision/date, including synthetic contract
checks. The [technical supplement](supplement.md) is a publication evidence
record with historical run accounting, provenance and limitations. It is not an
alternative tutorial or a live validation certificate.

For work with external Landsat observations, consult the explicit comparison
scope in [the drone/translation guide](../tutorials/micasense-to-landsat.md).
Spatial support, acquisition conditions and independent reference quality remain
part of the scientific study design.

The [six-level scientific validation map](scientific-validation.md) connects numerical correctness, pipeline contracts, biological associations, synthetic sensor reduction, the separate real-Landsat pilot and incomplete ecological abundance validation.
